from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


OPENAI_API_URL = "https://api.openai.com/v1/responses"


def llm_is_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _extract_text_from_response(payload: Dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = payload.get("output")
    if isinstance(output, list):
        texts: List[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                text_value = block.get("text")
                if isinstance(text_value, str) and text_value.strip():
                    texts.append(text_value.strip())
        if texts:
            return "\n".join(texts).strip()

    return ""


def _post_json(body: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
    timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "45").strip() or "45")

    request_body = {
        "model": model,
        "input": body["input"],
    }

    req = urllib.request.Request(
        OPENAI_API_URL,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)
        raise RuntimeError(f"OpenAI HTTP error: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI network error: {exc}") from exc


def _json_prompt(system_prompt: str, user_payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "input": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False, indent=2),
            },
        ]
    }


def _load_json_text(text: str) -> Dict[str, Any]:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        candidates = [part.strip() for part in parts if part.strip()]
        for candidate in candidates:
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
            try:
                value = json.loads(candidate)
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                continue

    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("LLM response was not a JSON object")
    return value


def generate_llm_issue_details(issue: Dict[str, Any]) -> Optional[Dict[str, str]]:
    if not llm_is_enabled():
        return None

    system_prompt = (
        "You are helping a secure code review platform. "
        "Return only valid JSON with keys: explanation, fix, risk, impact. "
        "Each value must be a concise plain string. "
        "Do not use markdown. "
        "Do not include code fences."
    )

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
        "task": (
            "Explain why this issue matters in a real codebase, what the actual "
            "risk is, what the likely impact is, and provide a practical fix "
            "suggestion suitable for a student engineering project."
        ),
    }

    try:
        response = _post_json(_json_prompt(system_prompt, payload))
        text = _extract_text_from_response(response)
        if not text:
            return None
        data = _load_json_text(text)
        return {
            "explanation": str(data.get("explanation") or "").strip(),
            "fix": str(data.get("fix") or "").strip(),
            "risk": str(data.get("risk") or "").strip(),
            "impact": str(data.get("impact") or "").strip(),
        }
    except Exception:
        return None


def generate_llm_project_summary(
    *,
    final_score: Any,
    risk_level: Any,
    metrics: Dict[str, Any],
    top_risky_issues: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not llm_is_enabled():
        return None

    system_prompt = (
        "You are helping a code intelligence dashboard. "
        "Return only valid JSON with keys: headline, security_overview, "
        "quality_overview, priority_action, recommendations, score_explanation. "
        "recommendations must be an array of concise strings. "
        "All other fields must be concise plain strings. "
        "Do not use markdown. "
        "Do not include code fences."
    )

    payload = {
        "final_score": final_score,
        "risk_level": risk_level,
        "metrics": metrics,
        "top_risky_issues": top_risky_issues[:5],
        "task": (
            "Generate a concise project-level AI summary for a dashboard. "
            "Explain the overall security state, code quality state, top priority "
            "action, why the score is low or medium, and give short practical "
            "recommendations."
        ),
    }

    try:
        response = _post_json(_json_prompt(system_prompt, payload))
        text = _extract_text_from_response(response)
        if not text:
            return None
        data = _load_json_text(text)

        recommendations = data.get("recommendations")
        if not isinstance(recommendations, list):
            recommendations = []

        return {
            "headline": str(data.get("headline") or "").strip(),
            "security_overview": str(data.get("security_overview") or "").strip(),
            "quality_overview": str(data.get("quality_overview") or "").strip(),
            "priority_action": str(data.get("priority_action") or "").strip(),
            "score_explanation": str(data.get("score_explanation") or "").strip(),
            "recommendations": [
                str(item).strip()
                for item in recommendations
                if str(item).strip()
            ][:8],
        }
    except Exception:
        return None