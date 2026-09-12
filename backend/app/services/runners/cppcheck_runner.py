from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List

from app.services.runners.runner_utils import run_command, write_json

SUPPORTED_EXTENSIONS = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
SOURCE_EXTENSIONS = {".c", ".cc", ".cpp", ".cxx"}


def _source_loc(input_dir: Path) -> int:
    total = 0
    for path in input_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS:
            try:
                total += len(path.read_text(encoding="utf-8", errors="replace").splitlines())
            except OSError:
                continue
    return total


def _empty_report(loc: int = 0) -> Dict[str, Any]:
    return {"cppcheckVersion": None, "files": [], "loc": loc}


def _parse_xml(xml_text: str, loc: int) -> Dict[str, Any]:
    root = ET.fromstring(xml_text)
    version = root.attrib.get("version")
    files: Dict[str, List[Dict[str, Any]]] = {}

    for error in root.findall(".//error"):
        location = error.find("location")
        file_path = ""
        line = None
        column = None
        if location is not None:
            file_path = location.attrib.get("file", "")
            try:
                line = int(location.attrib.get("line", "0")) or None
            except ValueError:
                line = None
            try:
                column = int(location.attrib.get("column", "0")) or None
            except ValueError:
                column = None

        item = {
            "id": error.attrib.get("id"),
            "severity": error.attrib.get("severity", "style"),
            "message": error.attrib.get("msg", ""),
            "verbose": error.attrib.get("verbose", ""),
            "cwe": error.attrib.get("cwe"),
            "file": file_path,
            "line": line,
            "column": column,
        }
        files.setdefault(file_path, []).append(item)

    return {
        "cppcheckVersion": version,
        "files": [{"filename": name, "issues": issues} for name, issues in files.items()],
        "loc": loc,
    }


def run_cppcheck(input_dir: Path, out_json: Path, warnings_json: Path) -> None:
    """Run Cppcheck for C/C++ source files and save a structured raw report."""
    source_files = [
        path for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS
    ]
    loc = _source_loc(input_dir)

    if not source_files:
        write_json(out_json, _empty_report(0))
        return

    cmd = [
        "cppcheck",
        "--enable=all",
        "--xml",
        "--xml-version=2",
        "--suppress=missingIncludeSystem",
        str(input_dir),
    ]
    result = run_command(cmd, timeout_sec=180)
    xml_text = str(result.get("stderr") or "").strip()

    if xml_text:
        try:
            parsed = _parse_xml(xml_text, loc)
            write_json(out_json, parsed)
        except ET.ParseError as exc:
            write_json(
                warnings_json,
                {
                    "tool": "cppcheck",
                    "warning": f"Invalid XML output: {exc}",
                    "stderr": xml_text,
                    "returncode": result.get("returncode"),
                },
            )
            write_json(out_json, _empty_report(loc))
    else:
        write_json(out_json, _empty_report(loc))

    if result.get("stdout", "").strip() and not xml_text:
        write_json(
            warnings_json,
            {
                "tool": "cppcheck",
                "warning": "Cppcheck produced no XML report on stderr",
                "stdout": result.get("stdout", ""),
                "returncode": result.get("returncode"),
            },
        )
