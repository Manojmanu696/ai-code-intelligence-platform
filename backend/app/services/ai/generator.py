from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _clean_path(value: Any) -> str:
    text = str(value or "").replace("\\", "/").strip()
    if text.startswith("input/"):
        return text[len("input/") :]
    marker = "/input/"
    if marker in text:
        return text.split(marker, 1)[1]
    return text


def _severity_rank(value: Any) -> int:
    severity = str(value or "").lower()
    if severity == "high":
        return 3
    if severity == "medium":
        return 2
    return 1


def _tool_rank(value: Any) -> int:
    tool = str(value or "").lower()
    if tool == "bandit":
        return 2
    if tool == "flake8":
        return 1
    return 0


def _priority_score(issue: Dict[str, Any]) -> int:
    severity = _severity_rank(issue.get("severity"))
    tool = _tool_rank(issue.get("tool"))
    rule = str(issue.get("rule_id") or "").upper()

    rule_bonus = 0
    if rule in {"E999", "F821", "F823", "F831"}:
        rule_bonus = 3
    elif rule in {"B310", "B603", "B110", "B112", "F401", "F841"}:
        rule_bonus = 2
    elif rule.startswith("B"):
        rule_bonus = 2
    elif rule.startswith("F"):
        rule_bonus = 1

    return (severity * 3) + (tool * 2) + rule_bonus


def _priority_label(score: int) -> str:
    if score >= 11:
        return "Immediate"
    if score >= 7:
        return "Soon"
    return "Normal"


def _explain_and_fix(issue: Dict[str, Any]) -> Dict[str, str]:
    tool = str(issue.get("tool") or "").lower()
    rule = str(issue.get("rule_id") or "").upper()

    if tool == "bandit":
        if rule == "B310":
            return {
                "explanation": (
                    "URL opening or fetching operations can be risky when "
                    "targets are not validated. This may enable unsafe "
                    "outbound requests or access to untrusted resources."
                ),
                "fix": (
                    "Validate URLs, allowlist trusted domains, enforce HTTPS, "
                    "and set timeouts before making external requests."
                ),
                "risk": "Unsafe URL access or SSRF-style behavior.",
                "impact": (
                    "The application may access malicious or internal network "
                    "resources."
                ),
            }

        if rule == "B603":
            return {
                "explanation": (
                    "Even without shell=True, subprocess calls are risky when "
                    "arguments are assembled from untrusted data."
                ),
                "fix": (
                    "Avoid string concatenation for command building and "
                    "validate every dynamic argument before execution."
                ),
                "risk": "Unsafe process execution.",
                "impact": (
                    "Untrusted input may still trigger unintended command "
                    "behavior."
                ),
            }

        if rule in {"B110", "B112"}:
            return {
                "explanation": (
                    "Broad exception suppression can hide real failures and "
                    "make debugging or security review harder."
                ),
                "fix": (
                    "Catch only expected exceptions and log or handle them "
                    "explicitly."
                ),
                "risk": "Silent failure.",
                "impact": "Real problems may be hidden and remain unresolved.",
            }

        return {
            "explanation": (
                f"Security finding detected by Bandit ({rule}). This indicates "
                "a potentially unsafe coding pattern that should be reviewed."
            ),
            "fix": (
                "Review the flagged code path, validate inputs, and replace "
                "dangerous APIs with safer alternatives."
            ),
            "risk": "Potential security weakness.",
            "impact": "May expose unsafe runtime behavior or weak controls.",
        }

    if tool == "flake8":
        if rule == "E999":
            return {
                "explanation": (
                    "Python could not parse the file because of a syntax error. "
                    "This can seriously affect runtime stability or code "
                    "correctness."
                ),
                "fix": (
                    "Review quotes, brackets, indentation, commas, and other "
                    "syntax near the flagged location, then rescan."
                ),
                "risk": "Broken syntax.",
                "impact": "The code may fail to run or load at all.",
            }

        if rule == "F401":
            return {
                "explanation": (
                    "An imported name is not used anywhere in the file. This "
                    "adds noise and makes maintenance harder."
                ),
                "fix": "Remove the unused import or use it intentionally.",
                "risk": "Code clutter.",
                "impact": (
                    "Unused imports make the code noisier and can mislead "
                    "readers."
                ),
            }

        if rule == "F841":
            return {
                "explanation": (
                    "A local variable is assigned but never used. This often "
                    "signals dead code or an incomplete refactor."
                ),
                "fix": "Remove the variable or use it intentionally.",
                "risk": "Dead code or incomplete logic.",
                "impact": "Unused variables reduce clarity and may hide bugs.",
            }

        if rule == "E501":
            return {
                "explanation": (
                    "The line exceeds the configured maximum length, which "
                    "reduces readability and can make maintenance harder."
                ),
                "fix": (
                    "Wrap the statement using parentheses, split long strings, "
                    "or refactor the expression into smaller parts."
                ),
                "risk": "Readability and maintainability issue.",
                "impact": "Long lines are harder to review and edit safely.",
            }

        if rule == "W292":
            return {
                "explanation": (
                    "The file does not end with a newline, which can create "
                    "minor tool and diff issues."
                ),
                "fix": "Add a newline at the end of the file.",
                "risk": "Style and tooling issue.",
                "impact": "Some tools and diffs behave less cleanly.",
            }

        if rule in {"E302", "E305"}:
            return {
                "explanation": (
                    "PEP 8 expects additional blank lines around top-level "
                    "definitions."
                ),
                "fix": (
                    "Insert the required blank lines around top-level "
                    "functions and classes."
                ),
                "risk": "Structure/readability issue.",
                "impact": "The file becomes harder to scan visually.",
            }

        return {
            "explanation": (
                f"Code style or quality issue detected by Flake8 ({rule})."
            ),
            "fix": (
                "Apply the recommended style fix or refactor the code to "
                "improve clarity and correctness."
            ),
            "risk": "Code quality issue.",
            "impact": "May reduce readability, maintainability, or correctness.",
        }

    return {
        "explanation": "Issue detected and enriched by the rule-based AI layer.",
        "fix": "Review the flagged code path and apply a safe correction.",
        "risk": "General project risk.",
        "impact": "May affect maintainability or runtime behavior.",
    }


def _risk_level(score: Dict[str, Any]) -> str | None:
    direct = str(score.get("risk_level") or score.get("risk") or "").strip()
    if direct:
        return direct

    try:
        final_score = float(score.get("final_score"))
    except Exception:
        return None

    if final_score >= 80:
        return "Low Risk"
    if final_score >= 50:
        return "Medium Risk"
    return "High Risk"


def _build_security_overview(enriched: List[Dict[str, Any]]) -> str:
    bandit_issues = [
        item for item in enriched if str(item.get("tool") or "").lower() == "bandit"
    ]
    high_bandit = [
        item
        for item in bandit_issues
        if str(item.get("severity") or "").lower() == "high"
    ]

    if not bandit_issues:
        return (
            "No Bandit security findings were detected in this scan. "
            "The current issues appear to be dominated by code quality "
            "rather than direct security warnings."
        )

    if high_bandit:
        return (
            f"Security findings were detected by Bandit ({len(bandit_issues)} "
            f"total), including {len(high_bandit)} high-severity issue(s). "
            "These should be handled before style cleanup."
        )

    return (
        f"Security findings were detected by Bandit ({len(bandit_issues)} "
        "total), but the majority are not marked high severity. These "
        "should still be reviewed because insecure patterns can grow into "
        "larger risks."
    )


def _build_quality_overview(enriched: List[Dict[str, Any]]) -> str:
    flake8_issues = [
        item for item in enriched if str(item.get("tool") or "").lower() == "flake8"
    ]

    if not flake8_issues:
        return "No Flake8 quality issues were detected in this scan."

    return (
        f"Code quality findings are present ({len(flake8_issues)} Flake8 "
        "issue(s)). These issues may not all be security-critical, but they "
        "still affect readability, maintainability, and runtime reliability."
    )


def _build_recommendations(
    enriched: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    score: Dict[str, Any],
) -> List[str]:
    recs: List[str] = []

    bandit_count = sum(
        1 for item in enriched if str(item.get("tool") or "").lower() == "bandit"
    )
    totals = (metrics or {}).get("totals") or {}
    by_severity = totals.get("by_severity") or {}
    high_count = int(by_severity.get("high") or 0)
    medium_count = int(by_severity.get("medium") or 0)
    final_risk = _risk_level(score) or "Unknown Risk"

    top_refactor = (metrics or {}).get("top_refactor_priority") or []
    if bandit_count > 0:
        recs.append(
            "Prioritize Bandit findings because they represent potential "
            "security weaknesses."
        )

    if medium_count >= 5:
        recs.append(
            "Group medium-severity issues by file and resolve them in batches "
            "to reduce repeated rework."
        )

    if top_refactor:
        first_file = _clean_path(top_refactor[0].get("file"))
        if first_file:
            recs.append(
                f"Start remediation with {first_file} because it appears to be "
                "the highest refactor priority."
            )

    top_files = (metrics or {}).get("top_files") or []
    if len(top_files) >= 2:
        recs.append(
            "Focus on the most issue-dense files first to reduce project risk "
            "faster."
        )

    if high_count > 0:
        recs.append("Fix high-severity issues first before focusing on style cleanup.")

    if final_risk == "High Risk":
        if bandit_count > 0:
            recs.append(
                "The project is currently in a high-risk state, so fix "
                "security and correctness issues before any broad cleanup."
            )
        else:
            recs.append(
                "The project is currently in a high-risk state, so address "
                "the most repeated quality issues before smaller formatting cleanup."
            )
    elif final_risk == "Medium Risk":
        if bandit_count > 0:
            recs.append(
                "The project is in a medium-risk state, so focus on security "
                "and correctness hotspots before polishing minor style issues."
            )
        else:
            recs.append(
                "The project is in a medium-risk state, so focus on the "
                "highest-impact code quality issues before minor formatting cleanup."
            )
    else:
        recs.append(
            "The current score is relatively healthy, so maintain the baseline "
            "by fixing newly introduced issues quickly."
        )

    deduped: List[str] = []
    seen: set[str] = set()
    for item in recs:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped[:8]


def generate_ai_outputs(
    scan_path: Path,
    unified_issues: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    score: Dict[str, Any],
) -> Path:
    enriched: List[Dict[str, Any]] = []

    for issue in unified_issues or []:
        if not isinstance(issue, dict):
            continue

        details = _explain_and_fix(issue)
        file_path = _clean_path(issue.get("file"))
        priority_score = _priority_score(issue)

        enriched.append(
            {
                **issue,
                "file": file_path,
                **details,
                "priority_score": priority_score,
                "priority": _priority_label(priority_score),
            }
        )

    top_risky = sorted(
        enriched,
        key=lambda item: (
            _priority_score(item),
            _severity_rank(item.get("severity")),
            _tool_rank(item.get("tool")),
        ),
        reverse=True,
    )[:10]

    totals = (metrics or {}).get("totals") or {}
    risk_level = _risk_level(score)
    top_refactor = (metrics or {}).get("top_refactor_priority") or []

    priority_action = "No immediate action required."
    if top_risky:
        first = top_risky[0]
        issue_file = _clean_path(first.get("file"))
        top_refactor_file = ""
        if top_refactor:
            top_refactor_file = _clean_path(top_refactor[0].get("file"))

        if top_refactor_file and top_refactor_file != issue_file:
            priority_action = (
                "First priority should be fixing the "
                f"{str(first.get('severity') or 'low').lower()}-severity "
                f"{str(first.get('tool') or '').lower()} issue "
                f"{str(first.get('rule_id') or '')} in {issue_file}, while "
                f"also reviewing {top_refactor_file} as the highest "
                "refactor-priority file."
            )
        else:
            priority_action = (
                "First priority should be fixing the "
                f"{str(first.get('severity') or 'low').lower()}-severity "
                f"{str(first.get('tool') or '').lower()} issue "
                f"{str(first.get('rule_id') or '')} in {issue_file}."
            )

    headline = (
        f"{risk_level or 'Unknown Risk'}: "
        f"{int(totals.get('issues') or 0)} issue(s) detected"
    )
    if int((totals.get("by_severity") or {}).get("high") or 0) > 0:
        headline += ", including high-severity findings. Immediate remediation is recommended."
    elif any(str(x.get("tool") or "").lower() == "bandit" for x in enriched):
        headline += " with a mix of security and code-quality findings. Security hotspots should be handled first."
    else:
        headline += ", mostly code-quality related."

    output = {
        "generated_at": _utc_now_iso(),
        "scan_id": scan_path.name,
        "final_score": score.get("final_score"),
        "penalty": score.get("penalty"),
        "summary": {
            "issues_total": totals.get("issues"),
            "loc": totals.get("loc"),
            "by_severity": totals.get("by_severity") or {},
            "bandit_findings": sum(
                1
                for item in enriched
                if str(item.get("tool") or "").lower() == "bandit"
            ),
            "risk_level": risk_level,
            "headline": headline,
            "security_overview": _build_security_overview(enriched),
            "quality_overview": _build_quality_overview(enriched),
            "priority_action": priority_action,
        },
        "top_risky_issues": top_risky,
        "issues_enriched": enriched[:500],
        "recommendations": _build_recommendations(enriched, metrics, score),
        "note": (
            "Rule-based explanations generated without LLM. This layer is "
            "designed to be upgraded by a future LLM enhancement stage."
        ),
    }

    return _write_json(scan_path / "ai" / "ai_summary.json", output)