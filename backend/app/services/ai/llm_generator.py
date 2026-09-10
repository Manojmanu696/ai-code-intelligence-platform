from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


OLLAMA_API_URL = "http://localhost:11434/api/generate"


def llm_is_enabled() -> bool:
    """
    Check whether the local Ollama server is available.
    """

    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/tags",
            method="GET",
        )

        with urllib.request.urlopen(req, timeout=3):
            return True

    except Exception:
        return False


def _extract_text_from_response(payload: Dict[str, Any]) -> str:
    """
    Extract generated text from Ollama's response.
    """

    response = payload.get("response")

    if isinstance(response, str):
        return response.strip()

    return ""


def _post_json(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a generation request to the local Ollama server.
    """

    model = (
        os.getenv("OLLAMA_MODEL", "qwen3:8b").strip()
        or "qwen3:8b"
    )

    timeout = float(
        os.getenv(
            "OLLAMA_TIMEOUT_SECONDS",
            "120",
        ).strip()
        or "120"
    )

    request_body = {
        "model": model,
        "prompt": body["prompt"],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.2,
        },
    }

    req = urllib.request.Request(
        OLLAMA_API_URL,
        data=json.dumps(
            request_body,
            ensure_ascii=False,
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            req,
            timeout=timeout,
        ) as response:

            raw = response.read().decode("utf-8")

            return json.loads(raw)

    except urllib.error.HTTPError as exc:

        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)

        raise RuntimeError(
            f"Ollama HTTP error: {detail}"
        ) from exc

    except urllib.error.URLError as exc:

        raise RuntimeError(
            f"Ollama connection error: {exc}"
        ) from exc


def _json_prompt(
    system_prompt: str,
    user_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build a strict JSON-generation prompt.
    """

    return {
        "prompt": f"""
SYSTEM INSTRUCTIONS

{system_prompt}

USER DATA

{json.dumps(
    user_payload,
    ensure_ascii=False,
    indent=2,
)}

FINAL OUTPUT RULE

Return ONLY one valid JSON object.

Do not return:
- Markdown
- Code fences
- Explanations outside the JSON
- Additional fields
- Comments
- Analysis outside the JSON
""",
    }


def _load_json_text(text: str) -> Dict[str, Any]:
    """
    Convert the model response into a JSON object.

    Handles normal JSON as well as accidental markdown
    code fences from the model.
    """

    cleaned = text.strip()

    if not cleaned:
        raise ValueError(
            "LLM returned an empty response"
        )

    # Normal JSON response.
    try:
        value = json.loads(cleaned)

        if isinstance(value, dict):
            return value

    except json.JSONDecodeError:
        pass

    # Handle accidental ```json ... ``` responses.
    if cleaned.startswith("```"):

        parts = cleaned.split("```")

        candidates = [
            part.strip()
            for part in parts
            if part.strip()
        ]

        for candidate in candidates:

            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()

            try:
                value = json.loads(candidate)

                if isinstance(value, dict):
                    return value

            except json.JSONDecodeError:
                continue

    raise ValueError(
        "LLM response was not a valid JSON object"
    )


def generate_llm_issue_details(
    issue: Dict[str, Any],
) -> Optional[Dict[str, str]]:
    """
    Generate an AI explanation for one static-analysis issue.

    The AI receives:
    - scanner information
    - severity
    - rule ID
    - original scanner message
    - source-code context

    The AI explains the actual code instead of simply
    repeating the scanner message.
    """

    if not llm_is_enabled():
        return None

    system_prompt = """
You are an expert software engineer helping a developer
understand a static-analysis finding.

Your job is to explain the PARTICULAR finding using the
supplied issue information and, most importantly, the
supplied source code.

The developer may not know:
- Bandit
- Flake8
- security terminology
- static-analysis terminology

Therefore, explain the finding in simple, normal English.

IMPORTANT:

The scanner finding is evidence, not permission to invent
facts.

The supplied source code is the most important evidence
when it is available.

Your explanation must answer:

1. What is the code actually doing?
2. What specific part of the code caused the finding?
3. What is potentially wrong or risky about it?
4. What could realistically happen because of it?
5. What is the most appropriate fix for THIS code?

STRICT ACCURACY RULES:

- Use simple general English.
- Avoid unnecessary technical jargon.
- Do not simply repeat the scanner message.
- Explain the actual source code.
- Base your explanation on the supplied source code whenever
  source code is available.
- The supplied scanner severity is authoritative.
- NEVER increase the severity.
- NEVER describe a low or medium finding as high or critical.
- NEVER invent a critical security problem.
- NEVER say an issue is "critical" unless the supplied
  severity explicitly says "critical".
- NEVER say an issue is "high" unless the supplied severity
  explicitly says "high".
- Do not invent attacker capabilities.
- Do not assume an attacker controls a value unless the
  supplied code provides evidence for that conclusion.
- Do not claim that exploitation is confirmed when the
  scanner only identifies a potential risk.
- Clearly distinguish between a potential vulnerability and
  a confirmed vulnerability.
- Do not invent data exposure, remote code execution,
  account compromise, or other consequences unless the
  supplied code reasonably supports that conclusion.
- Do not make generic security claims unrelated to the
  actual code.
- For URL-related findings, carefully distinguish normal
  http:// and https:// URLs from file:// and other schemes.
- Do not automatically describe every urllib.request.urlopen()
  call as an attack.
- Explain why the scanner is concerned about the specific
  call in the supplied code.
- If the code already restricts or validates an input,
  acknowledge that instead of ignoring it.
- If the available source context is insufficient to prove
  an attack scenario, say that the issue is a potential risk
  rather than claiming a confirmed attack.
- The suggested fix must be specific and practical for the
  supplied code.
- Do not suggest unnecessary rewrites.
- Keep every field concise but useful.
- Do not change, reinterpret, or invent the scanner severity.

IMPORTANT SEVERITY RULE:

The severity field supplied by the scanner is authoritative.

For example:
If severity = "medium", the explanation must remain a
medium-level concern.

It must NOT say:
"critical vulnerability"
"severe vulnerability"
"critical security flaw"
"major breach"

unless the supplied evidence and severity explicitly support
such wording.

OUTPUT:

Return exactly this JSON structure:

{
  "explanation": "...",
  "fix": "...",
  "risk": "...",
  "impact": "..."
}

FIELD MEANINGS:

explanation:
Explain what the code is doing and why the scanner flagged it.

fix:
Give the most appropriate practical fix for this exact code.

risk:
Describe the realistic potential security or quality risk
without exaggeration.

impact:
Describe the realistic consequence if the issue is actually
exploitable or causes a problem.

If the available evidence does not prove exploitation,
use wording such as "could", "may", or "potentially" instead
of claiming that exploitation definitely occurs.
"""

    payload = {
        "issue": {
            "tool": issue.get("tool"),
            "rule_id": issue.get("rule_id"),
            "severity": issue.get("severity"),
            "confidence": issue.get("confidence"),
            "file": issue.get("file"),
            "line": issue.get("line"),
            "message": issue.get("message"),
            "category": issue.get("category"),
        },

        "source_code": issue.get("source_code"),

        "task": (
            "Analyze this exact static-analysis finding. "
            "Use the source code as evidence and explain "
            "the issue in simple English without exaggerating "
            "its severity or inventing an attack scenario."
        ),
    }

    try:

        response = _post_json(
            _json_prompt(
                system_prompt,
                payload,
            )
        )

        text = _extract_text_from_response(response)

        if not text:
            return None

        data = _load_json_text(text)

        return {
            "explanation": str(
                data.get("explanation") or ""
            ).strip(),

            "fix": str(
                data.get("fix") or ""
            ).strip(),

            "risk": str(
                data.get("risk") or ""
            ).strip(),

            "impact": str(
                data.get("impact") or ""
            ).strip(),
        }

    except Exception as exc:

        print(
            f"[LLM] Issue analysis failed: {exc}"
        )

        return None


def generate_llm_project_summary(
    *,
    final_score: Any,
    risk_level: Any,
    metrics: Dict[str, Any],
    top_risky_issues: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Generate an AI summary of the overall project.

    The AI explains the deterministic scan results but does
    not control or modify the project's numerical score.
    """

    if not llm_is_enabled():
        return None

    system_prompt = """
You are an expert software engineer reviewing the overall
health of a software project.

Your job is to explain the supplied scan results in simple,
normal English that a developer can understand.

The numerical score, risk level, issue counts, and scanner
severity levels are supplied by the analysis system.

You must explain those results accurately.

Do NOT simply repeat the numbers.

Use the supplied metrics and findings to explain:

- overall project health
- security concerns
- code-quality concerns
- what should be fixed first
- why the score is what it is
- practical recommendations

STRICT ACCURACY RULES:

- Treat the supplied scanner severity levels as authoritative.
- Treat the supplied final score as authoritative.
- Treat the supplied risk level as authoritative.
- NEVER change the numerical score.
- NEVER invent issue counts.
- NEVER invent severity levels.
- NEVER describe a medium or low finding as critical.
- NEVER describe a medium or low finding as high.
- NEVER claim that the project has critical security risks
  unless the supplied findings actually contain critical
  findings.
- NEVER claim that the project has high security risks unless
  the supplied findings actually contain high findings.
- Do not invent attacker capabilities.
- Do not invent attack scenarios.
- Do not claim that a vulnerability is confirmed unless the
  supplied evidence supports that conclusion.
- Clearly distinguish potential risks from confirmed
  vulnerabilities.
- Base security conclusions on the supplied findings.
- Do not exaggerate the security impact.
- Do not contradict the supplied metrics.
- Do not invent facts about the project that are not present
  in the supplied data.
- Do not make recommendations unrelated to the supplied
  findings.
- Prioritize recommendations based on severity, confidence,
  and practical importance.
- Explain why the existing score makes sense based on the
  supplied metrics and findings.
- The AI explanation must NOT modify the deterministic
  scoring system.
- Keep the summary concise and useful.

SEVERITY INTERPRETATION:

If there are no critical findings, do NOT say there are
critical risks.

If there are no high findings, do NOT say there are high
risks.

If the findings are mostly medium and low severity, describe
them as medium and low concerns.

If there are potential security issues but the supplied
information does not prove exploitation, use language such
as:
"potential security risk"
"could cause"
"may allow"
"should be reviewed"

Do not say:
"confirmed attack"
"confirmed breach"
"critical vulnerability"

unless the supplied evidence actually proves it.

PROJECT SCORE:

The final_score is calculated by the project's existing
deterministic scoring system.

Explain the score.

Do NOT recalculate it.

Do NOT change it.

Do NOT invent another score.

OUTPUT:

Return exactly this JSON structure:

{
  "headline": "...",
  "security_overview": "...",
  "quality_overview": "...",
  "priority_action": "...",
  "recommendations": ["...", "..."],
  "score_explanation": "..."
}

FIELD MEANINGS:

headline:
A short accurate description of the project's current state.

security_overview:
Summarize the actual security findings and their severity.

quality_overview:
Summarize the code-quality findings and relevant metrics.

priority_action:
State the most useful first action based on the supplied
findings.

recommendations:
Provide practical actions supported by the scan results.

score_explanation:
Explain why the supplied score is reasonable based on the
provided metrics and findings.

IMPORTANT:

Do not call anything critical or high unless the supplied
findings contain critical or high severity issues.
"""

    payload = {
        "final_score": final_score,

        "risk_level": risk_level,

        "metrics": metrics,

        "top_risky_issues": top_risky_issues[:5],

        "task": (
            "Generate a concise and accurate project-level "
            "explanation based only on the supplied scan "
            "results. Do not exaggerate severity or invent "
            "security risks."
        ),
    }

    try:

        response = _post_json(
            _json_prompt(
                system_prompt,
                payload,
            )
        )

        text = _extract_text_from_response(response)

        if not text:
            return None

        data = _load_json_text(text)

        recommendations = data.get(
            "recommendations"
        )

        if not isinstance(
            recommendations,
            list,
        ):
            recommendations = []

        return {
            "headline": str(
                data.get("headline") or ""
            ).strip(),

            "security_overview": str(
                data.get("security_overview") or ""
            ).strip(),

            "quality_overview": str(
                data.get("quality_overview") or ""
            ).strip(),

            "priority_action": str(
                data.get("priority_action") or ""
            ).strip(),

            "score_explanation": str(
                data.get("score_explanation") or ""
            ).strip(),

            "recommendations": [
                str(item).strip()
                for item in recommendations
                if str(item).strip()
            ][:8],
        }

    except Exception as exc:

        print(
            f"[LLM] Project summary failed: {exc}"
        )

        return None