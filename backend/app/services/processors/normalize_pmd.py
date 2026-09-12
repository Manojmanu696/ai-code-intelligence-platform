from __future__ import annotations

from typing import Any, Dict, List


def _map_priority_to_severity(priority: Any) -> str:
    """Convert PMD priority numbers into project severity levels."""
    try:
        value = int(priority)
    except (TypeError, ValueError):
        return "low"

    if value <= 2:
        return "high"
    if value == 3:
        return "medium"
    return "low"


def _category_from_ruleset(ruleset: Any) -> str:
    """Convert a PMD ruleset name into a project issue category."""
    text = str(ruleset or "").strip().lower()
    if "security" in text:
        return "security"
    if "design" in text:
        return "maintainability"
    if "performance" in text:
        return "performance"
    if "error" in text:
        return "bug_risk"
    if "style" in text:
        return "style"
    return "maintainability"


def normalize_pmd(raw: Any) -> Dict[str, Any]:
    """Convert the PMD report into the project's common issue format."""
    files = raw.get("files", []) if isinstance(raw, dict) else []
    issues: List[Dict[str, Any]] = []

    if not isinstance(files, list):
        files = []

    for file_item in files:
        if not isinstance(file_item, dict):
            continue

        filename = file_item.get("filename")
        violations = file_item.get("violations", [])
        if not isinstance(violations, list):
            continue

        for violation in violations:
            if not isinstance(violation, dict):
                continue

            rule_id = str(violation.get("rule") or "PMD").strip()
            ruleset = violation.get("ruleset")

            issues.append(
                {
                    "tool": "pmd",
                    "rule_id": rule_id,
                    "category": _category_from_ruleset(ruleset),
                    "severity": _map_priority_to_severity(violation.get("priority")),
                    "confidence": None,
                    "file": filename,
                    "line": violation.get("beginline"),
                    "message": violation.get("description"),
                    "pmd_priority": violation.get("priority"),
                    "pmd_ruleset": ruleset,
                }
            )

    loc = raw.get("loc", 0) if isinstance(raw, dict) else 0
    try:
        loc = int(loc or 0)
    except (TypeError, ValueError):
        loc = 0

    return {
        "tool": "pmd",
        "loc": max(0, loc),
        "issues": issues,
        "counts": {"total": len(issues)},
    }
