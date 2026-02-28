from __future__ import annotations

import io
import json
import re
import shutil
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request

from .ingest_utils import IngestRules, is_allowed_file, is_excluded_path


@dataclass
class IngestionReport:
    kept: int
    skipped: int
    max_file_size_bytes: int
    allowed_extensions: list[str]
    excluded_dirs: list[str]
    skipped_samples: list[dict]
    source: dict


def _parse_github_repo(repo_url: str) -> tuple[str, str]:
    """
    Accepts:
      https://github.com/OWNER/REPO
      https://github.com/OWNER/REPO.git
    Returns: (owner, repo)
    """
    m = re.match(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", repo_url.strip())
    if not m:
        raise ValueError("Invalid GitHub repo URL. Expected like: https://github.com/OWNER/REPO")
    return m.group(1), m.group(2)


def _download_github_zip(owner: str, repo: str, ref: str) -> bytes:
    # GitHub source zip:
    # https://github.com/{owner}/{repo}/archive/refs/heads/{ref}.zip
    # For tags/commits, GitHub still supports /archive/{ref}.zip in many cases,
    # but refs/heads is safest for branch names.
    url_candidates = [
        f"https://github.com/{owner}/{repo}/archive/refs/heads/{ref}.zip",
        f"https://github.com/{owner}/{repo}/archive/{ref}.zip",
    ]

    last_err: Optional[Exception] = None
    for url in url_candidates:
        try:
            req = Request(url, headers={"User-Agent": "final-folder-scanner"})
            with urlopen(req, timeout=30) as resp:
                return resp.read()
        except Exception as e:
            last_err = e

    raise RuntimeError(f"Failed to download GitHub zip for {owner}/{repo}@{ref}: {last_err}")


def ingest_github_repo_to_input(
    *,
    scan_input_dir: Path,
    scan_raw_dir: Path,
    repo_url: str,
    ref: str = "master",
    subdir: str | None = None,
    rules: IngestRules | None = None,
    skipped_sample_limit: int = 25,
) -> IngestionReport:
    rules = rules or IngestRules()

    owner, repo = _parse_github_repo(repo_url)
    zip_bytes = _download_github_zip(owner, repo, ref)

    # Clear input dir first (fresh ingestion)
    if scan_input_dir.exists():
        shutil.rmtree(scan_input_dir)
    scan_input_dir.mkdir(parents=True, exist_ok=True)

    # Extract zip into a temp folder inside raw/
    tmp_dir = scan_raw_dir / "tmp_extract"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(tmp_dir)

    # GitHub zip contains a single top folder like repo-ref/
    extracted_roots = [p for p in tmp_dir.iterdir() if p.is_dir()]
    if not extracted_roots:
        raise RuntimeError("Downloaded zip had no root folder.")
    root = extracted_roots[0]

    base = root
    if subdir:
        base = root / subdir
        if not base.exists():
            raise ValueError(f"subdir not found inside repo zip: {subdir}")

    kept = 0
    skipped = 0
    skipped_samples: list[dict] = []

    # Copy allowed files into input/ preserving relative structure
    for path in base.rglob("*"):
        if path.is_dir():
            continue

        rel = path.relative_to(root)  # keep repo root relative structure
        if is_excluded_path(rel, rules):
            skipped += 1
            if len(skipped_samples) < skipped_sample_limit:
                skipped_samples.append({"file": str(rel), "reason": "excluded_dir"})
            continue

        if not is_allowed_file(path, rules):
            skipped += 1
            if len(skipped_samples) < skipped_sample_limit:
                reason = "not_allowed"
                try:
                    if path.stat().st_size > rules.max_file_size_bytes:
                        reason = "too_large"
                except FileNotFoundError:
                    reason = "missing"
                skipped_samples.append({"file": str(rel), "reason": reason})
            continue

        dest = scan_input_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        kept += 1

    # Clean temp
    shutil.rmtree(tmp_dir, ignore_errors=True)

    report = IngestionReport(
        kept=kept,
        skipped=skipped,
        max_file_size_bytes=rules.max_file_size_bytes,
        allowed_extensions=sorted(list(rules.allowed_extensions)),
        excluded_dirs=sorted(list(rules.excluded_dirs)),
        skipped_samples=skipped_samples,
        source={
            "type": "github",
            "repo_url": repo_url,
            "owner": owner,
            "repo": repo,
            "ref": ref,
            "subdir": subdir,
        },
    )

    # Save ingestion report in raw/
    scan_raw_dir.mkdir(parents=True, exist_ok=True)
    (scan_raw_dir / "ingestion.json").write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")

    return report