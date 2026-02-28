import json
from typing import Any, Dict, List


# -----------------------------
# Helpers
# -----------------------------

def _map_flake8_category(code: str) -> str:
    if not code:
        return "style"
    if code.startswith("F"):
        return "bug_risk"
    if code.startswith(("E", "W")):
        return "style"
    if code.startswith("C"):
        return "maintainability"
    return "style"


# -----------------------------
# Normalize flake8
# -----------------------------

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

            for it in file_issues:
                code = it.get("code")
                severity = "low"
                if code and code.startswith("F"):
                    severity = "medium"

                issues.append(
                    {
                        "tool": "flake8",
                        "rule_id": code,
                        "category": _map_flake8_category(code),
                        "severity": severity,
                        "confidence": None,
                        "file": it.get("filename") or file_path,
                        "line": it.get("line_number"),
                        "message": it.get("text"),
                    }
                )

    return {
        "tool": "flake8",
        "issues": issues,
        "counts": {"total": len(issues)},
    }


# -----------------------------
# Normalize bandit
# -----------------------------

def normalize_bandit(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            raw = {}

    results = raw.get("results", []) if isinstance(raw, dict) else []
    issues: List[Dict[str, Any]] = []

    for r in results:
        severity = (r.get("issue_severity") or "low").lower()
        confidence = (r.get("issue_confidence") or "low").lower()

        issues.append(
            {
                "tool": "bandit",
                "rule_id": r.get("test_id"),
                "category": "security",
                "severity": severity,
                "confidence": confidence,
                "file": r.get("filename"),
                "line": r.get("line_number"),
                "message": r.get("issue_text"),
            }
        )

    loc = 0
    metrics = raw.get("metrics", {})
    if isinstance(metrics, dict):
        totals = metrics.get("_totals")
        if isinstance(totals, dict):
            loc = totals.get("loc", 0)

    return {
        "tool": "bandit",
        "loc": loc,
        "issues": issues,
        "counts": {"total": len(issues)},
    }


# -----------------------------
# Unified Issues Generator
# -----------------------------

def build_unified_issues(flake8_norm: Dict[str, Any],
                         bandit_norm: Dict[str, Any]) -> List[Dict[str, Any]]:
    unified = []

    for issue in flake8_norm.get("issues", []):
        unified.append(issue)

    for issue in bandit_norm.get("issues", []):
        unified.append(issue)

    return unified