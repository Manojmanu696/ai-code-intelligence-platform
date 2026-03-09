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


# -----------------------------
# Heuristic explanations (No LLM yet)
# -----------------------------
def _explain_and_fix(issue: Dict[str, Any]) -> Dict[str, str]:
    tool = str(issue.get("tool", "")).lower()
    rule = str(issue.get("rule_id", "")).upper()
    msg = str(issue.get("message", "")).strip()

    # ---- Bandit security rules ----
    if tool == "bandit":
        if rule == "B602":
            return {
                "explanation": "Using subprocess with shell=True can allow command injection if any part of the command is influenced by user input.",
                "fix": "Avoid shell=True. Pass args as a list: subprocess.run(['cmd','arg']). If input is dynamic, validate/allowlist it.",
            }
        if rule == "B603":
            return {
                "explanation": "Calling subprocess without shell=True is safer than shell=True, but still risky if arguments are built from untrusted input.",
                "fix": "Ensure command args are not built from untrusted strings. Use allowlists and avoid string concatenation.",
            }
        if rule == "B301":
            return {
                "explanation": "Pickle can execute arbitrary code when loading untrusted data.",
                "fix": "Never load pickle from untrusted sources. Use JSON instead, or restrict/verify the source strongly.",
            }
        if rule == "B310":
            return {
                "explanation": "Using urllib without strong validation may allow unsafe URL handling depending on the context.",
                "fix": "Validate/allowlist domains, enforce HTTPS, set timeouts, and avoid fetching from untrusted URLs.",
            }
        # fallback bandit
        return {
            "explanation": f"Security finding detected by Bandit ({rule}). This indicates a potentially unsafe coding pattern.",
            "fix": "Review the flagged code path, remove unsafe patterns, validate inputs, and prefer safe libraries/APIs.",
        }

    # ---- Flake8 quality rules ----
    if tool == "flake8":
        if rule == "E501":
            return {
                "explanation": "Line is longer than the configured limit. Long lines reduce readability and maintainability.",
                "fix": "Wrap the line using parentheses, split strings, or refactor into smaller expressions.",
            }
        if rule == "W292":
            return {
                "explanation": "File does not end with a newline. Some tools and diffs behave better with a final newline.",
                "fix": "Add a newline at the end of the file (press Enter on last line).",
            }
        if rule == "F821":
            return {
                "explanation": "You referenced a name that is not defined. This will crash at runtime.",
                "fix": "Fix the variable name, define it before use, or import it if it should come from another module.",
            }
        if rule == "E302" or rule == "E305":
            return {
                "explanation": "PEP8 spacing rule: incorrect blank lines around functions/classes.",
                "fix": "Add the required blank lines (usually 2 lines before top-level defs/classes).",
            }
        if rule == "E999":
            return {
                "explanation": "Syntax error detected. Python cannot parse the file.",
                "fix": "Fix invalid characters/indentation/quotes. Re-run scan after correcting syntax.",
            }
        # fallback flake8
        return {
            "explanation": f"Code style/quality issue detected by Flake8 ({rule}).",
            "fix": "Follow the recommended style for this rule or refactor the code to improve clarity.",
        }

    # generic
    return {
        "explanation": f"Issue detected ({tool}:{rule}).",
        "fix": "Inspect the message and apply a safe refactor. If it’s security-related, validate inputs and avoid dangerous APIs.",
    }


def _severity_rank(sev: str) -> int:
    s = (sev or "").lower()
    if s == "high":
        return 3
    if s == "medium":
        return 2
    return 1


def generate_ai_outputs(
    scan_path: Path,
    unified_issues: List[Dict[str, Any]],
    metrics: Dict[str, Any],
    score: Dict[str, Any],
) -> Path:
    """
    Creates AI-like explanations WITHOUT an LLM (rule-based),
    so your dashboard can already show:
      1) Issue explanation
      2) Fix suggestions
      3) Security risk summary
    """
    # build enriched issues
    enriched: List[Dict[str, Any]] = []
    for it in unified_issues or []:
        if not isinstance(it, dict):
            continue
        extra = _explain_and_fix(it)
        enriched.append({**it, **extra})

    # security summary (Bandit focused, but also severity-based)
    by_sev = (metrics or {}).get("totals", {}).get("by_severity", {}) or {}
    bandit_count = sum(1 for x in enriched if str(x.get("tool", "")).lower() == "bandit")

    # top risky issues
    top_risky = sorted(
        enriched,
        key=lambda x: (_severity_rank(str(x.get("severity", ""))), str(x.get("tool", "")) == "bandit"),
        reverse=True,
    )[:10]

    output = {
        "generated_at": _utc_now_iso(),
        "scan_id": scan_path.name,
        "final_score": score.get("final_score"),
        "penalty": score.get("penalty"),
        "summary": {
            "issues_total": (metrics or {}).get("totals", {}).get("issues"),
            "loc": (metrics or {}).get("totals", {}).get("loc"),
            "by_severity": by_sev,
            "bandit_findings": bandit_count,
            "risk_level": score.get("risk_level") or score.get("risk") or None,
        },
        "top_risky_issues": top_risky,
        "issues_enriched": enriched[:500],  # keep cap
        "note": "Rule-based explanations (LLM not used yet). Offline LLM can replace/upgrade this later.",
    }

    ai_file = scan_path / "ai" / "ai_summary.json"
    return _write_json(ai_file, output)