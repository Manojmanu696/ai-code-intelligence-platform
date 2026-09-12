from __future__ import annotations

import math
from typing import Any, Dict


# A density score becomes unstable for tiny files: one finding in 6 LOC
# would otherwise look like 166 findings per KLOC.  We therefore use a
# minimum scoring baseline while still reporting the real LOC separately.
MIN_EFFECTIVE_LOC = 200


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _get_loc(metrics: Dict[str, Any]) -> int:
    """
    Try to find LOC from metrics.json.
    Falls back safely to 1000 if no LOC key is present.
    """
    totals = metrics.get("totals", {}) if isinstance(metrics, dict) else {}

    for key in ("loc", "lines_of_code", "total_loc", "py_loc"):
        if key in totals:
            loc = _safe_int(totals.get(key), 0)
            if loc > 0:
                return loc

    return 1000


def _risk_level_from_score(final_score: float) -> str:
    """
    Locked project risk levels:
      80-100 -> Low Risk
      50-79  -> Medium Risk
      0-49   -> High Risk
    """
    if final_score >= 80.0:
        return "Low Risk"
    if final_score >= 50.0:
        return "Medium Risk"
    return "High Risk"


def compute_score(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Density-based project health score (0-100).

    The score uses issue density per KLOC with logarithmic diminishing
    returns. A minimum effective LOC is used so very small files do not
    receive an extreme penalty simply because their denominator is tiny.

    Severity weights:
      low    = 6
      medium = 14
      high   = 45

    The deterministic score is independent of the LLM; AI is used only
    later for explanation, remediation and contextual analysis.
    """
    totals = metrics.get("totals", {}) if isinstance(metrics, dict) else {}
    sev = totals.get("by_severity", {}) if isinstance(totals, dict) else {}

    low = _safe_int(sev.get("low", 0))
    medium = _safe_int(sev.get("medium", 0))
    high = _safe_int(sev.get("high", 0))

    raw_loc = max(1, _get_loc(metrics))
    effective_loc = max(raw_loc, MIN_EFFECTIVE_LOC)

    # Densities (issues per 1000 effective LOC).
    d_low = (low / effective_loc) * 1000.0
    d_med = (medium / effective_loc) * 1000.0
    d_high = (high / effective_loc) * 1000.0

    # Severity multipliers.
    A_LOW = 6.0
    A_MED = 14.0
    A_HIGH = 45.0

    # Logarithmic diminishing returns prevents large issue counts from
    # overwhelming the score while preserving the importance of severity.
    p_low = A_LOW * math.log1p(d_low)
    p_med = A_MED * math.log1p(d_med)
    p_high = A_HIGH * math.log1p(d_high)

    penalty = p_low + p_med + p_high
    final_score = clamp(100.0 - penalty, 0.0, 100.0)
    final_score_rounded = round(final_score, 2)

    risk_level = _risk_level_from_score(final_score_rounded)

    return {
        "final_score": final_score_rounded,
        "penalty": round(penalty, 2),
        "risk_level": risk_level,
        "risk": risk_level,
        "weights": {
            "low": A_LOW,
            "medium": A_MED,
            "high": A_HIGH,
        },
        "breakdown": {
            "low": low,
            "medium": medium,
            "high": high,
        },
        "method": "density_log_v2_small_project_normalized",
        "loc": raw_loc,
        "effective_loc": effective_loc,
        "normalization_floor_loc": MIN_EFFECTIVE_LOC,
        "density_per_kloc": {
            "low": round(d_low, 2),
            "medium": round(d_med, 2),
            "high": round(d_high, 2),
        },
        "penalty_breakdown": {
            "low": round(p_low, 2),
            "medium": round(p_med, 2),
            "high": round(p_high, 2),
        },
    }
