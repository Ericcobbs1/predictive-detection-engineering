from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.features.auth_drift import AuthBucketFeatures, compute_growth_hits


@dataclass(frozen=True)
class AuthBaselineStats:
    src_ip: str
    avg_failures: float
    bucket_count: int


@dataclass(frozen=True)
class AuthSignal:
    signal_name: str
    detection_id: str
    entity_type: str
    entity_id: str

    risk_score: int
    confidence: float
    time_horizon: str

    failures: int
    unique_users_targeted: int
    baseline_fail_avg: Optional[float]
    failure_drift_ratio: Optional[float]
    growth_hits: int


def compute_auth_baseline_stats(
    baseline_buckets: List[AuthBucketFeatures],
) -> Dict[str, AuthBaselineStats]:
    by_src: Dict[str, List[int]] = {}
    for r in baseline_buckets:
        by_src.setdefault(r.src_ip, []).append(int(r.auth_failures_per_src))

    out: Dict[str, AuthBaselineStats] = {}
    for src, vals in by_src.items():
        avg = float(sum(vals)) / float(len(vals)) if vals else 0.0
        out[src] = AuthBaselineStats(
            src_ip=src,
            avg_failures=avg,
            bucket_count=len(vals),
        )
    return out


def score_password_spray_drift(
    *,
    failure_drift_ratio: Optional[float],
    unique_users_targeted: int,
    sustained_growth: bool,
    baseline_bucket_count: int,
    expected_baseline_buckets: int,
) -> Tuple[int, float, str]:
    ratio = float(failure_drift_ratio or 0.0)

    ratio_component = min(1.0, max(0.0, (ratio - 1.0) / 4.0))
    user_component = min(1.0, max(0.0, unique_users_targeted / 25.0))
    growth_component = 1.0 if sustained_growth else 0.0

    risk = (ratio_component * 40.0) + (user_component * 30.0) + (growth_component * 30.0)
    risk_score = int(round(max(0.0, min(100.0, risk))))

    completeness = 0.0
    if expected_baseline_buckets > 0:
        completeness = min(1.0, float(baseline_bucket_count) / float(expected_baseline_buckets))

    conf = 0.0
    conf += 0.20 * completeness
    conf += 0.30 * (1.0 if sustained_growth else 0.0)
    conf += 0.30 * (1.0 if unique_users_targeted > 0 else 0.0)
    conf += 0.20 * 1.0
    confidence = float(max(0.0, min(1.0, conf)))

    if risk_score >= 86:
        horizon = "imminent"
    elif risk_score >= 70:
        horizon = "emerging"
    else:
        horizon = "early"

    return risk_score, confidence, horizon


def evaluate_pde_spl_0402(
    observation_buckets: List[AuthBucketFeatures],
    baselines: Dict[str, AuthBaselineStats],
    *,
    drift_ratio_threshold: float = 2.5,
    sustained_buckets: int = 3,
    min_users: int = 10,
    expected_baseline_buckets: int = 30 * 24 * 4,
    min_baseline_buckets: int = 24,
) -> List[AuthSignal]:
    signals: List[AuthSignal] = []
    growth_hits_map = compute_growth_hits(observation_buckets, sustained_buckets=sustained_buckets)

    for r in observation_buckets:
        baseline = baselines.get(r.src_ip)
        baseline_avg = baseline.avg_failures if baseline else None
        baseline_count = baseline.bucket_count if baseline else 0

        failure_ratio: Optional[float] = None
        if baseline_avg is not None and baseline_avg > 0 and baseline_count >= min_baseline_buckets:
            failure_ratio = float(r.auth_failures_per_src) / float(baseline_avg)

        growth_hits = int(growth_hits_map.get((r.src_ip, r.bucket_start), 0))
        sustained_growth = growth_hits >= sustained_buckets

        cond_a = (failure_ratio is not None) and (failure_ratio >= drift_ratio_threshold)
        cond_b = sustained_growth
        cond_c = r.unique_users_targeted >= min_users

        if not (cond_a and cond_b and cond_c):
            continue

        risk, conf, horizon = score_password_spray_drift(
            failure_drift_ratio=failure_ratio,
            unique_users_targeted=r.unique_users_targeted,
            sustained_growth=sustained_growth,
            baseline_bucket_count=baseline_count,
            expected_baseline_buckets=expected_baseline_buckets,
        )

        signals.append(
            AuthSignal(
                signal_name="Password Spray Drift (Low-and-Slow)",
                detection_id="pde-spl-0402",
                entity_type="src_ip",
                entity_id=r.src_ip,
                risk_score=risk,
                confidence=conf,
                time_horizon=horizon,
                failures=r.auth_failures_per_src,
                unique_users_targeted=r.unique_users_targeted,
                baseline_fail_avg=baseline_avg,
                failure_drift_ratio=failure_ratio,
                growth_hits=growth_hits,
            )
        )

    return signals
