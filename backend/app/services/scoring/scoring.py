from __future__ import annotations

import math
from typing import Dict, Any


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _get_loc(metrics: Dict[str, Any]) -> int:
    """
    Try to find LOC from your metrics.json.
    We'll check common keys. If none exist, fall back to 1000 to avoid division by zero.
    """
    totals = metrics.get("totals", {}) if isinstance(metrics, dict) else {}

    # common possibilities (adaptable)
    for k in ("loc", "lines_of_code", "total_loc", "py_loc"):
        if k in totals:
            loc = _safe_int(totals.get(k), 0)
            if loc > 0:
                return loc

    # If your metrics builder doesn't store LOC yet, we still score safely.
    return 1000


def compute_score(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Best MVP scoring (density + log diminishing returns):

    1) Normalize issue counts by LOC (issues per KLOC).
    2) Apply log1p() so LOTS of low issues don't destroy the score.
    3) Medium/high severity still hurt much more than low.
    4) Clamp final_score into [0, 100].

    Output keeps your existing keys:
      final_score, penalty, weights, breakdown
    and adds:
      loc, density_per_kloc, penalty_breakdown, method
    """
    totals = metrics.get("totals", {}) if isinstance(metrics, dict) else {}
    sev = totals.get("by_severity", {}) if isinstance(totals, dict) else {}

    low = _safe_int(sev.get("low", 0))
    medium = _safe_int(sev.get("medium", 0))
    high = _safe_int(sev.get("high", 0))

    loc = max(1, _get_loc(metrics))

    # ---- densities (per 1000 LOC) ----
    d_low = (low / loc) * 1000.0
    d_med = (medium / loc) * 1000.0
    d_high = (high / loc) * 1000.0

    # ---- tuned multipliers (balanced) ----
    # Low: mild impact even if many
    # Medium: strong
    # High: very strong
    A_LOW = 6.0
    A_MED = 14.0
    A_HIGH = 45.0

    # Diminishing returns penalty
    p_low = A_LOW * math.log1p(d_low)
    p_med = A_MED * math.log1p(d_med)
    p_high = A_HIGH * math.log1p(d_high)

    penalty = p_low + p_med + p_high
    final_score = clamp(100.0 - penalty, 0.0, 100.0)

    return {
        "final_score": round(final_score, 2),
        "penalty": round(penalty, 2),

        # keep your old key name "weights" for UI consistency
        "weights": {
            "low": A_LOW,
            "medium": A_MED,
            "high": A_HIGH,
        },

        # keep your old key name "breakdown" for UI consistency
        "breakdown": {
            "low": low,
            "medium": medium,
            "high": high,
        },

        # extra helpful fields (nice for frontend explainability)
        "method": "density_log_v1",
        "loc": loc,
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