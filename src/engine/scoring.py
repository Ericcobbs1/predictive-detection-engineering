from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.baselines.rolling import BaselineStats, baseline_completeness_score


@dataclass(frozen=True)
class ScoreResult:
    risk_score: int          # 0-100
    confidence: float        # 0.0-1.0
    time_horizon: str        # early | emerging | imminent


def clamp_int(x: float, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, int(round(x))))


def clamp_float(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


def compute_risk_score(
    baseline_deviation_ratio: Optional[float],
    new_internal_targets: Optional[int],
    sustained_growth: bool,
) -> int:
    """
    MVP risk score for NS-P2-001.

    Inputs are intentionally simple and explainable.
    - deviation_ratio drives impact likelihood (bigger divergence => higher risk)
    - new_internal_targets increases confidence that this is lateral prep
    - sustained_growth is a strong behavioral signal
    """
    # Defaults
    ratio = baseline_deviation_ratio if baseline_deviation_ratio is not None else 0.0
    new_targets = int(new_internal_targets or 0)

    # Normalize ratio: 1.0 => baseline, 2.5 => threshold, 5.0+ => very high
    ratio_component = min(1.0, max(0.0, (ratio - 1.0) / 4.0))  # maps ~[1..5] -> [0..1]

    # Normalize new targets: 0..10 -> 0..1
    novelty_component = min(1.0, max(0.0, new_targets / 10.0))

    growth_component = 1.0 if sustained_growth else 0.0

    # Weighted sum (matches our spec)
    risk = (ratio_component * 40.0) + (novelty_component * 30.0) + (growth_component * 30.0)
    return clamp_int(risk, 0, 100)


def compute_confidence(
    baseline: Optional[BaselineStats],
    expected_baseline_buckets: int,
    sustained_growth: bool,
    novelty_present: bool,
    low_variance_noise: bool = True,
) -> float:
    """
    MVP confidence score for NS-P2-001 (0.0-1.0).

    Contributors (weights):
      - baseline completeness: 0.20
      - sustained growth:      0.30
      - novelty present:       0.30
      - low variance noise:    0.20
    """
    base_comp = baseline_completeness_score(baseline, expected_baseline_buckets)
    c = 0.0
    c += 0.20 * base_comp
    c += 0.30 * (1.0 if sustained_growth else 0.0)
    c += 0.30 * (1.0 if novelty_present else 0.0)
    c += 0.20 * (1.0 if low_variance_noise else 0.0)
    return clamp_float(c, 0.0, 1.0)


def time_horizon_from_risk(risk_score: int) -> str:
    if risk_score >= 86:
        return "imminent"
    if risk_score >= 70:
        return "emerging"
    return "early"


def score_ns_p2_001(
    baseline: Optional[BaselineStats],
    expected_baseline_buckets: int,
    baseline_deviation_ratio: Optional[float],
    new_internal_targets: Optional[int],
    sustained_growth: bool,
    novelty_present: bool,
) -> ScoreResult:
    risk = compute_risk_score(baseline_deviation_ratio, new_internal_targets, sustained_growth)
    conf = compute_confidence(
        baseline=baseline,
        expected_baseline_buckets=expected_baseline_buckets,
        sustained_growth=sustained_growth,
        novelty_present=novelty_present,
        low_variance_noise=True,
    )
    horizon = time_horizon_from_risk(risk)
    return ScoreResult(risk_score=risk, confidence=conf, time_horizon=horizon)
