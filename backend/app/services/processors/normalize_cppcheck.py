from __future__ import annotations

from typing import Any, Dict, List


def _map_severity(value: Any) -> str:
    text = str(value or "style").strip().lower()
    if text in {"error", "warning"}:
        return "high" if text == "error" else "medium"
    if text in {"performance", "portability", "style", "information"}:
        return "low"
    return "low"


def _category(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text == "error":
        return "bug_risk"
    if text == "warning":
        return "bug_risk"
    if text == "performance":
        return "performance"
    if text == "portability":
        return "maintainability"
    return "style"


def normalize_cppcheck(raw: Any) -> Dict[str, Any]:
    files = raw.get("files", []) if isinstance(raw, dict) else []
    issues: List[Dict[str, Any]] = []
    if not isinstance(files, list):
        files = []

    for file_item in files:
        if not isinstance(file_item, dict):
            continue
        filename = file_item.get("filename")
        for item in file_item.get("issues", []) if isinstance(file_item.get("issues"), list) else []:
            if not isinstance(item, dict):
                continue
            severity_raw = item.get("severity")
            issues.append({
                "tool": "cppcheck",
                "rule_id": item.get("id") or "CPPCHECK",
                "category": _category(severity_raw),
                "severity": _map_severity(severity_raw),
                "confidence": None,
                "file": item.get("file") or filename,
                "line": item.get("line"),
                "message": item.get("message") or item.get("verbose"),
                "cppcheck_severity": severity_raw,
                "cwe": item.get("cwe"),
            })

    loc = raw.get("loc", 0) if isinstance(raw, dict) else 0
    try:
        loc = max(0, int(loc or 0))
    except (TypeError, ValueError):
        loc = 0

    return {
        "tool": "cppcheck",
        "loc": loc,
        "issues": issues,
        "counts": {"total": len(issues)},
    }
