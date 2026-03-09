from __future__ import annotations

import json
from typing import Any, Dict, List


def _map_flake8_category(code: str) -> str:
    if not code:
        return "style"

    if code.startswith("F"):
        return "bug_risk"

    if code == "E999":
        return "bug_risk"

    if code.startswith(("E", "W")):
        return "style"

    if code.startswith("C"):
        return "maintainability"

    return "style"


def _map_flake8_severity(code: str) -> str:
    """
    MVP severity mapping for flake8.

    High:
      - syntax / execution-breaking / undefined-name style issues

    Medium:
      - bug-risk / import / structure issues

    Low:
      - style / formatting / hygiene
    """
    if not code:
        return "low"

    high_codes = {
        "E999",  # syntax error
        "F821",  # undefined name
        "F823",  # local variable referenced before assignment
        "F831",  # duplicate argument name
        "F706",  # return outside function
        "F704",  # yield outside function
    }

    medium_codes = {
        "F401",
        "F402",
        "F403",
        "F405",
        "F541",
        "F621",
        "F622",
        "F631",
        "F632",
        "F707",
        "F722",
        "F822",
        "E701",
        "E702",
        "E711",
        "E712",
        "E302",
        "E305",
        "E401",
        "E402",
    }

    if code in high_codes:
        return "high"

    if code in medium_codes:
        return "medium"

    if code.startswith("F"):
        return "medium"

    return "low"


def normalize_flake8(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}

    issues: List[Dict[str, Any]] = []

    if isinstance(raw, dict):
        for file_path, file_issues in raw.items():
            if not isinstance(file_issues, list):
                continue

            for item in file_issues:
                if not isinstance(item, dict):
                    continue

                code = str(item.get("code") or "").strip().upper()

                issues.append(
                    {
                        "tool": "flake8",
                        "rule_id": code,
                        "category": _map_flake8_category(code),
                        "severity": _map_flake8_severity(code),
                        "confidence": None,
                        "file": item.get("filename") or file_path,
                        "line": item.get("line_number"),
                        "message": item.get("text"),
                    }
                )

    return {
        "tool": "flake8",
        "issues": issues,
        "counts": {"total": len(issues)},
    }


def normalize_bandit(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}

    results = raw.get("results", []) if isinstance(raw, dict) else []

    issues: List[Dict[str, Any]] = []

    for item in results:
        if not isinstance(item, dict):
            continue

        severity = str(item.get("issue_severity") or "low").lower()
        confidence = str(item.get("issue_confidence") or "low").lower()

        issues.append(
            {
                "tool": "bandit",
                "rule_id": item.get("test_id"),
                "category": "security",
                "severity": severity,
                "confidence": confidence,
                "file": item.get("filename"),
                "line": item.get("line_number"),
                "message": item.get("issue_text"),
            }
        )

    loc = 0
    metrics = raw.get("metrics", {}) if isinstance(raw, dict) else {}
    if isinstance(metrics, dict):
        totals = metrics.get("_totals", {})
        if isinstance(totals, dict):
            loc = int(totals.get("loc", 0) or 0)

    return {
        "tool": "bandit",
        "loc": loc,
        "issues": issues,
        "counts": {"total": len(issues)},
    }


def build_unified_issues(
    flake8_norm: Dict[str, Any],
    bandit_norm: Dict[str, Any],
) -> List[Dict[str, Any]]:
    unified: List[Dict[str, Any]] = []

    for issue in flake8_norm.get("issues", []):
        if isinstance(issue, dict):
            unified.append(issue)

    for issue in bandit_norm.get("issues", []):
        if isinstance(issue, dict):
            unified.append(issue)

    return unified