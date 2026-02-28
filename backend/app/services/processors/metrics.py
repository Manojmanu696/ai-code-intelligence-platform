from __future__ import annotations

from typing import Any, Dict, List, Optional
from pathlib import Path
import json


# -----------------------------
# Helpers
# -----------------------------
def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _read_unified_issues_from_norm_objects(norm_objects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Backward compatible:
    - If unified issues already present in provided norm objects, use them
    - Else fall back to tool issues lists (flake8_norm + bandit_norm)
    """
    unified: List[Dict[str, Any]] = []

    # If any object looks like unified list wrapper, skip (we store unified separately on disk)
    # So here we construct unified from norm objects
    for obj in norm_objects:
        if not isinstance(obj, dict):
            continue
        issues = obj.get("issues")
        tool = obj.get("tool")
        if isinstance(issues, list) and tool in {"flake8", "bandit"}:
            # New normalize.py already emits unified-shaped issues for both tools
            for it in issues:
                if isinstance(it, dict):
                    unified.append(it)

    return unified


def _risk_score(low: int, medium: int, high: int) -> int:
    # Professional-looking weighting for file prioritization
    return (high * 10) + (medium * 4) + (low * 1)


# -----------------------------
# Main builder
# -----------------------------
def build_metrics(
    norm_objects: List[Dict[str, Any]],
    unified_issues: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Produces metrics.json with:
      totals: issues/by_tool/by_severity/loc
      top_refactor_priority: top 5 files by weighted risk
      heatmap: file -> severity counts
      most_recurring_issues: top recurring tool:rule_id
      top_files: files sorted by total issues
      metrics_version: 1
    """

    # Build unified issues if not provided
    if unified_issues is None:
        unified_issues = _read_unified_issues_from_norm_objects(norm_objects)

    # Totals
    by_tool = {"flake8": 0, "bandit": 0}
    by_severity = {"low": 0, "medium": 0, "high": 0}
    loc = 0

    # Try to pick LOC from bandit normalized (if available)
    for obj in norm_objects:
        if isinstance(obj, dict) and obj.get("tool") == "bandit":
            loc = _safe_int(obj.get("loc", 0), 0)

    # Per-file stats for heatmap + refactor priority
    heatmap: Dict[str, Dict[str, int]] = {}
    rule_counts: Dict[str, int] = {}  # tool:rule_id -> count
    file_total_counts: Dict[str, int] = {}  # file -> total issues

    for it in unified_issues:
        if not isinstance(it, dict):
            continue

        tool = (it.get("tool") or "unknown").lower()
        sev = (it.get("severity") or "low").lower()
        rule_id = it.get("rule_id") or it.get("code") or "UNKNOWN"
        file = it.get("file") or "UNKNOWN_FILE"

        # Tool totals
        if tool in by_tool:
            by_tool[tool] += 1
        else:
            by_tool[tool] = by_tool.get(tool, 0) + 1

        # Severity totals (only track our 3)
        if sev not in by_severity:
            sev = "low"
        by_severity[sev] += 1

        # Heatmap per file
        if file not in heatmap:
            heatmap[file] = {"low": 0, "medium": 0, "high": 0}
        heatmap[file][sev] += 1

        # Recurring issues (tool:rule)
        key = f"{tool}:{rule_id}"
        rule_counts[key] = rule_counts.get(key, 0) + 1

        # Total per file
        file_total_counts[file] = file_total_counts.get(file, 0) + 1

    total_issues = sum(by_tool.values())

    # Top files by total issues
    top_files = [
        {"file": f, "issues": c, **heatmap.get(f, {"low": 0, "medium": 0, "high": 0})}
        for f, c in file_total_counts.items()
    ]
    top_files.sort(key=lambda x: x["issues"], reverse=True)

    # Top 5 refactor priority (weighted risk)
    refactor_rank = []
    for f, sev_counts in heatmap.items():
        low = sev_counts.get("low", 0)
        medium = sev_counts.get("medium", 0)
        high = sev_counts.get("high", 0)
        refactor_rank.append(
            {
                "file": f,
                "risk_score": _risk_score(low, medium, high),
                "low": low,
                "medium": medium,
                "high": high,
                "total": low + medium + high,
            }
        )
    refactor_rank.sort(key=lambda x: x["risk_score"], reverse=True)
    top_refactor_priority = refactor_rank[:5]

    # Most recurring issue types
    recurring = [{"rule": k, "count": v} for k, v in rule_counts.items()]
    recurring.sort(key=lambda x: x["count"], reverse=True)
    most_recurring_issues = recurring[:10]

    return {
        "metrics_version": 1,
        "totals": {
            "issues": total_issues,
            "by_tool": by_tool,
            "by_severity": by_severity,
            "loc": loc,
        },
        "top_refactor_priority": top_refactor_priority,
        "heatmap": heatmap,
        "most_recurring_issues": most_recurring_issues,
        "top_files": top_files[:20],
    }