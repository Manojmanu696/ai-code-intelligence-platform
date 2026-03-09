from __future__ import annotations

from typing import Any, Dict, List


def _count_by_tool(unified_issues: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for issue in unified_issues:
        tool = str(issue.get("tool") or "unknown").lower()
        counts[tool] = counts.get(tool, 0) + 1
    return counts


def _count_by_severity(unified_issues: List[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"low": 0, "medium": 0, "high": 0}
    for issue in unified_issues:
        severity = str(issue.get("severity") or "low").lower()
        if severity not in counts:
            severity = "low"
        counts[severity] += 1
    return counts


def _extract_loc(tool_outputs: List[Dict[str, Any]]) -> int:
    for item in tool_outputs:
        if not isinstance(item, dict):
            continue
        loc = item.get("loc")
        if isinstance(loc, int) and loc >= 0:
            return loc
    return 0


def _heatmap(unified_issues: List[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Dict[str, int]] = {}
    for issue in unified_issues:
        file_path = str(issue.get("file") or "unknown")
        severity = str(issue.get("severity") or "low").lower()
        if severity not in {"low", "medium", "high"}:
            severity = "low"

        if file_path not in out:
            out[file_path] = {"low": 0, "medium": 0, "high": 0}
        out[file_path][severity] += 1
    return out


def _top_files(
    heatmap: Dict[str, Dict[str, int]],
    limit: int = 10,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for file_path, counts in heatmap.items():
        total = int(counts.get("low", 0)) + int(counts.get("medium", 0)) + int(
            counts.get("high", 0)
        )
        rows.append(
            {
                "file": file_path,
                "count": total,
                "issues": total,
            }
        )

    rows.sort(key=lambda item: (item["count"], item["file"]), reverse=True)
    return rows[:limit]


def _top_refactor_priority(
    heatmap: Dict[str, Dict[str, int]],
    limit: int = 5,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for file_path, counts in heatmap.items():
        low = int(counts.get("low", 0))
        medium = int(counts.get("medium", 0))
        high = int(counts.get("high", 0))
        weighted_risk = (high * 5) + (medium * 3) + low

        rows.append(
            {
                "file": file_path,
                "weighted_risk": weighted_risk,
                "counts": {
                    "low": low,
                    "medium": medium,
                    "high": high,
                },
            }
        )

    rows.sort(
        key=lambda item: (item["weighted_risk"], item["file"]),
        reverse=True,
    )
    return rows[:limit]


def _most_recurring_issues(
    unified_issues: List[Dict[str, Any]],
    limit: int = 10,
) -> List[Dict[str, Any]]:
    counts: Dict[str, int] = {}

    for issue in unified_issues:
        tool = str(issue.get("tool") or "unknown").lower()
        rule_id = str(issue.get("rule_id") or "unknown").upper()
        key = f"{tool}:{rule_id}"
        counts[key] = counts.get(key, 0) + 1

    rows = [
        {"rule_id": key, "count": value}
        for key, value in counts.items()
    ]
    rows.sort(key=lambda item: (item["count"], item["rule_id"]), reverse=True)
    return rows[:limit]


def build_metrics(
    tool_outputs: List[Dict[str, Any]],
    unified_issues: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    unified = unified_issues or []
    loc = _extract_loc(tool_outputs)
    by_tool = _count_by_tool(unified)
    by_severity = _count_by_severity(unified)
    heatmap = _heatmap(unified)

    return {
        "metrics_version": "v1",
        "totals": {
            "issues": len(unified),
            "by_tool": by_tool,
            "by_severity": by_severity,
            "loc": loc,
        },
        "top_refactor_priority": _top_refactor_priority(heatmap, limit=5),
        "heatmap": heatmap,
        "most_recurring_issues": _most_recurring_issues(unified, limit=10),
        "top_files": _top_files(heatmap, limit=10),
    }