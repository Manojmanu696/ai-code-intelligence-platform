from __future__ import annotations
from typing import Any, Dict, List


def build_metrics(normalized_reports: List[Dict[str, Any]]) -> Dict[str, Any]:
    sev_counts = {"low": 0, "medium": 0, "high": 0}
    by_tool: Dict[str, int] = {}
    total = 0

    for rep in normalized_reports:
        tool = rep.get("tool", "unknown")
        issues = rep.get("issues", []) or []
        by_tool[tool] = len(issues)
        total += len(issues)
        for it in issues:
            sev = (it.get("severity") or "low").lower()
            if sev in sev_counts:
                sev_counts[sev] += 1

    return {
        "totals": {
            "issues": total,
            "by_tool": by_tool,
            "by_severity": sev_counts,
        }
    }