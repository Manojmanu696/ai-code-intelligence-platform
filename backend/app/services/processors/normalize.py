import json
from typing import Any, Dict, List


def normalize_flake8(raw: Any) -> Dict[str, Any]:
    """
    Accepts flake8 raw output in either format:
      A) dict: { "file.py": [ {code, line_number, ...}, ... ], ... }   (your current runner format)
      B) list: [ {filename, code, line_number, ...}, ... ]
      C) str:  JSON string of A or B

    Returns normalized dict:
      {
        "tool": "flake8",
        "issues": [
          {"file": "...", "line": 1, "col": 2, "code": "W292", "message": "..."},
          ...
        ],
        "counts": {"total": N, "by_code": {...}}
      }
    """
    # If string, try parse JSON
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}

    issues: List[Dict[str, Any]] = []

    # Case A: dict[file -> list[issue]]
    if isinstance(raw, dict):
        for file_path, file_issues in raw.items():
            if not isinstance(file_issues, list):
                continue
            for it in file_issues:
                if not isinstance(it, dict):
                    continue
                issues.append(
                    {
                        "file": it.get("filename") or file_path,
                        "line": it.get("line_number"),
                        "col": it.get("column_number"),
                        "code": it.get("code"),
                        "message": it.get("text"),
                        # optional: keep original line text if present
                        "source_line": it.get("physical_line"),
                    }
                )

    # Case B: list[issue dict]
    elif isinstance(raw, list):
        for it in raw:
            if not isinstance(it, dict):
                continue
            issues.append(
                {
                    "file": it.get("filename"),
                    "line": it.get("line_number"),
                    "col": it.get("column_number"),
                    "code": it.get("code"),
                    "message": it.get("text"),
                    "source_line": it.get("physical_line"),
                }
            )

    # Counts
    by_code: Dict[str, int] = {}
    for it in issues:
        code = it.get("code") or "UNKNOWN"
        by_code[code] = by_code.get(code, 0) + 1

    return {
        "tool": "flake8",
        "issues": issues,
        "counts": {"total": len(issues), "by_code": by_code},
    }


def normalize_bandit(raw: Any) -> Dict[str, Any]:
    """
    Bandit raw is usually a dict with keys like:
      { "results": [...], "metrics": {...}, "errors": [...] }

    Returns normalized dict:
      {
        "tool": "bandit",
        "issues": [
          {"file":"...", "line": 1, "test_id":"B101", "severity":"LOW", "confidence":"HIGH", "message":"..."},
          ...
        ],
        "counts": {"total": N, "by_severity": {...}, "by_confidence": {...}}
      }
    """
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}

    results = []
    if isinstance(raw, dict):
        results = raw.get("results") or []
    if not isinstance(results, list):
        results = []

    issues: List[Dict[str, Any]] = []
    for r in results:
        if not isinstance(r, dict):
            continue
        issues.append(
            {
                "file": r.get("filename"),
                "line": r.get("line_number"),
                "test_id": r.get("test_id"),
                "test_name": r.get("test_name"),
                "severity": r.get("issue_severity"),
                "confidence": r.get("issue_confidence"),
                "message": r.get("issue_text"),
                "more_info": r.get("more_info"),
            }
        )

    by_sev: Dict[str, int] = {}
    by_conf: Dict[str, int] = {}
    for it in issues:
        sev = it.get("severity") or "UNDEFINED"
        conf = it.get("confidence") or "UNDEFINED"
        by_sev[sev] = by_sev.get(sev, 0) + 1
        by_conf[conf] = by_conf.get(conf, 0) + 1

    return {
        "tool": "bandit",
        "issues": issues,
        "counts": {"total": len(issues), "by_severity": by_sev, "by_confidence": by_conf},
    }