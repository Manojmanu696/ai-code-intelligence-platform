from __future__ import annotations
from typing import Dict, Any


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def compute_score(metrics: Dict[str, Any]) -> Dict[str, Any]:
    sev = metrics["totals"]["by_severity"]
    low = int(sev.get("low", 0))
    medium = int(sev.get("medium", 0))
    high = int(sev.get("high", 0))

    weights = {"low": 0.5, "medium": 2.0, "high": 6.0}
    penalty = (low * weights["low"]) + (medium * weights["medium"]) + (high * weights["high"])

    final_score = clamp(100.0 - penalty, 0.0, 100.0)

    return {
        "final_score": final_score,
        "penalty": penalty,
        "weights": weights,
        "breakdown": {"low": low, "medium": medium, "high": high},
    }