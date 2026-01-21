from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.features.persistence_drift import PersistenceBucketFeatures, compute_growth_hits


@dataclass(frozen=True)
class PersistenceBaselineStats:
    host: str
    avg_events: float
    bucket_count: int


@dataclass(frozen=True)
class PersistenceSignal:
    signal_name: str
    detection_id: str
    entity_type: str
    entity_id: str

    risk_score: int
    confidence: float
    time_horizon: str

    persistence_events_per_host: int
    unique_persistence_artifacts: int
    baseline_evt_avg: Optional[float]
    persistence_drift_ratio: Optional[float]
    growth_hits: int


def compute_persistence_baseline_stats(
    baseline_buckets: List[PersistenceBucketFeatures],
) -> Dict[str, PersistenceBaselineStats]:
    by_host: Dict[str, List[int]] = {}
    for r in baseline_buckets:
        by_host.setdefault(r.host, []).append(int(r.persistence_events_per_host))

    out: Dict[str, PersistenceBaselineStats] = {}
    for host, vals in by_host.items():
        avg = float(sum(vals)) / float(len(vals)) if vals else 0.0
        out[host] = PersistenceBaselineStats(host=host, avg_events=avg, bucket_count=len(vals))
    return out


def score_persistence_drift(
    *,
    drift_ratio: Optional[float],
    unique_artifacts: int,
    sustained_growth: bool,
    baseline_bucket_count: int,
    expected_baseline_buckets: int,
) -> Tuple[int, float, str]:
    ratio = float(drift_ratio or 0.0)

    ratio_component = min(1.0, max(0.0, (ratio - 1.0) / 4.0))
    artifact_component = min(1.0, max(0.0, unique_artifacts / 10.0))
    growth_component = 1.0 if sustained_growth else 0.0

    risk = (ratio_component * 40.0) + (artifact_component * 30.0) + (growth_component * 30.0)
    risk_score = int(round(max(0.0, min(100.0, risk))))

    completeness = 0.0
    if expected_baseline_buckets > 0:
        completeness = min(1.0, float(baseline_bucket_count) / float(expected_baseline_buckets))

    conf = 0.0
    conf += 0.20 * completeness
    conf += 0.30 * (1.0 if sustained_growth else 0.0)
    conf += 0.30 * (1.0 if unique_artifacts > 0 else 0.0)
    conf += 0.20 * 1.0
    confidence = float(max(0.0, min(1.0, conf)))

    if risk_score >= 86:
        horizon = "imminent"
    elif risk_score >= 70:
        horizon = "emerging"
    else:
        horizon = "early"

    return risk_score, confidence, horizon


def evaluate_pde_spl_0403(
    observation_buckets: List[PersistenceBucketFeatures],
    baselines: Dict[str, PersistenceBaselineStats],
    *,
    drift_ratio_threshold: float = 2.5,
    sustained_buckets: int = 3,
    min_unique_artifacts: int = 2,
    expected_baseline_buckets: int = 30 * 24,
    min_baseline_buckets: int = 24,
) -> List[PersistenceSignal]:
    signals: List[PersistenceSignal] = []
    growth_hits_map = compute_growth_hits(observation_buckets, sustained_buckets=sustained_buckets)

    for r in observation_buckets:
        baseline = baselines.get(r.host)
        baseline_avg = baseline.avg_events if baseline else None
        baseline_count = baseline.bucket_count if baseline else 0

        drift_ratio: Optional[float] = None
        if baseline_avg is not None and baseline_avg > 0 and baseline_count >= min_baseline_buckets:
            drift_ratio = float(r.persistence_events_per_host) / float(baseline_avg)

        growth_hits = int(growth_hits_map.get((r.host, r.bucket_start), 0))
        sustained_growth = growth_hits >= sustained_buckets

        cond_a = (drift_ratio is not None) and (drift_ratio >= drift_ratio_threshold)
        cond_b = sustained_growth
        cond_c = r.unique_persistence_artifacts >= min_unique_artifacts

        if not (cond_a and cond_b and cond_c):
            continue

        risk, conf, horizon = score_persistence_drift(
            drift_ratio=drift_ratio,
            unique_artifacts=r.unique_persistence_artifacts,
            sustained_growth=sustained_growth,
            baseline_bucket_count=baseline_count,
            expected_baseline_buckets=expected_baseline_buckets,
        )

        signals.append(
            PersistenceSignal(
                signal_name="Persistence Mechanism Drift (Tasks/Services)",
                detection_id="pde-spl-0403",
                entity_type="host",
                entity_id=r.host,
                risk_score=risk,
                confidence=conf,
                time_horizon=horizon,
                persistence_events_per_host=r.persistence_events_per_host,
                unique_persistence_artifacts=r.unique_persistence_artifacts,
                baseline_evt_avg=baseline_avg,
                persistence_drift_ratio=drift_ratio,
                growth_hits=growth_hits,
            )
        )

    return signals
