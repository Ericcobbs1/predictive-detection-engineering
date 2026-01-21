from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.features.data_staging_drift import StagingBucketFeatures, compute_growth_hits


@dataclass(frozen=True)
class StagingBaselineStats:
    host: str
    avg_events: float
    bucket_count: int


@dataclass(frozen=True)
class StagingSignal:
    signal_name: str
    detection_id: str
    entity_type: str
    entity_id: str  # host

    risk_score: int
    confidence: float
    time_horizon: str

    staging_events_per_host: int
    unique_staging_artifacts: int
    baseline_evt_avg: Optional[float]
    staging_drift_ratio: Optional[float]
    growth_hits: int


def compute_staging_baseline_stats(
    baseline_buckets: List[StagingBucketFeatures],
) -> Dict[str, StagingBaselineStats]:
    by_host: Dict[str, List[int]] = {}
    for r in baseline_buckets:
        by_host.setdefault(r.host, []).append(int(r.staging_events_per_host))

    out: Dict[str, StagingBaselineStats] = {}
    for host, vals in by_host.items():
        avg = float(sum(vals)) / float(len(vals)) if vals else 0.0
        out[host] = StagingBaselineStats(host=host, avg_events=avg, bucket_count=len(vals))
    return out


def score_data_staging_drift(
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


def evaluate_pde_spl_0404(
    observation_buckets: List[StagingBucketFeatures],
    baselines: Dict[str, StagingBaselineStats],
    *,
    drift_ratio_threshold: float = 2.5,
    sustained_buckets: int = 3,
    min_unique_artifacts: int = 2,
    expected_baseline_buckets: int = 30 * 24,
    min_baseline_buckets: int = 24,
) -> List[StagingSignal]:
    signals: List[StagingSignal] = []
    growth_hits_map = compute_growth_hits(observation_buckets, sustained_buckets=sustained_buckets)

    for r in observation_buckets:
        baseline = baselines.get(r.host)
        baseline_avg = baseline.avg_events if baseline else None
        baseline_count = baseline.bucket_count if baseline else 0

        drift_ratio: Optional[float] = None
        if baseline_avg is not None and baseline_avg > 0 and baseline_count >= min_baseline_buckets:
            drift_ratio = float(r.staging_events_per_host) / float(baseline_avg)

        growth_hits = int(growth_hits_map.get((r.host, r.bucket_start), 0))
        sustained_growth = growth_hits >= sustained_buckets

        cond_a = (drift_ratio is not None) and (drift_ratio >= drift_ratio_threshold)
        cond_b = sustained_growth
        cond_c = r.unique_staging_artifacts >= min_unique_artifacts

        if not (cond_a and cond_b and cond_c):
            continue

        risk, conf, horizon = score_data_staging_drift(
            drift_ratio=drift_ratio,
            unique_artifacts=r.unique_staging_artifacts,
            sustained_growth=sustained_growth,
            baseline_bucket_count=baseline_count,
            expected_baseline_buckets=expected_baseline_buckets,
        )

        signals.append(
            StagingSignal(
                signal_name="Data Staging Drift (Compression/Large File Activity)",
                detection_id="pde-spl-0404",
                entity_type="host",
                entity_id=r.host,
                risk_score=risk,
                confidence=conf,
                time_horizon=horizon,
                staging_events_per_host=r.staging_events_per_host,
                unique_staging_artifacts=r.unique_staging_artifacts,
                baseline_evt_avg=baseline_avg,
                staging_drift_ratio=drift_ratio,
                growth_hits=growth_hits,
            )
        )

    return signals
