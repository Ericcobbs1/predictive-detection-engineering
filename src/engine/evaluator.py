from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.baselines.rolling import BaselineStats
from src.engine.scoring import ScoreResult, score_ns_p2_001
from src.features.network_fanout import FanoutBucketFeatures, compute_growth_hits, compute_new_internal_targets_proxy


@dataclass(frozen=True)
class Signal:
    """
    Canonical signal output for Phase 2 MVP.
    """
    signal_name: str
    detection_id: str
    entity_type: str
    entity_id: str

    risk_score: int
    confidence: float
    time_horizon: str

    # Evidence
    internal_dest_count: int
    internal_conn_count: int
    baseline_avg_internal_dest_count: Optional[float]
    baseline_deviation_ratio: Optional[float]
    growth_hits: int
    new_internal_targets: int


def evaluate_ns_p2_001(
    observation_buckets: List[FanoutBucketFeatures],
    baselines: Dict[str, BaselineStats],
    *,
    deviation_ratio_threshold: float = 2.5,
    sustained_buckets: int = 3,
    min_new_targets: int = 3,
    expected_baseline_buckets: int = 30 * 24,  # 30d @ 1h
) -> List[Signal]:
    """
    Evaluate NS-P2-001 on observation bucket features + baseline stats.

    This is the code equivalent of the detection spec conditions:
      A: baseline_deviation_ratio >= 2.5
      B: sustained positive trend across N buckets
      C: new_internal_targets >= 3 (MVP proxy for now)
    """
    signals: List[Signal] = []

    growth_hits_map = compute_growth_hits(observation_buckets, sustained_buckets=sustained_buckets)

    # For MVP, treat each bucket independently and emit a signal per bucket when conditions match.
    for r in observation_buckets:
        baseline = baselines.get(r.host)
        baseline_avg = baseline.avg_internal_dest_count if baseline else None

        ratio = r.baseline_deviation_ratio
        if ratio is None and baseline_avg and baseline_avg > 0:
            ratio = float(r.internal_dest_count) / float(baseline_avg)

        growth_hits = int(growth_hits_map.get((r.host, r.bucket_start), 0))
        sustained_growth = growth_hits >= sustained_buckets

        # MVP novelty proxy: new targets = internal_dest_count
        new_targets = compute_new_internal_targets_proxy(r.internal_dest_count)
        novelty_present = new_targets >= min_new_targets

        # Conditions
        cond_a = (ratio is not None) and (ratio >= deviation_ratio_threshold)
        cond_b = sustained_growth
        cond_c = new_targets >= min_new_targets

        if not (cond_a and cond_b and cond_c):
            continue

        score: ScoreResult = score_ns_p2_001(
            baseline=baseline,
            expected_baseline_buckets=expected_baseline_buckets,
            baseline_deviation_ratio=ratio,
            new_internal_targets=new_targets,
            sustained_growth=sustained_growth,
            novelty_present=novelty_present,
        )

        signals.append(
            Signal(
                signal_name="Emerging Lateral Movement Preparation",
                detection_id="pde-spl-0401",
                entity_type="host",
                entity_id=r.host,
                risk_score=score.risk_score,
                confidence=score.confidence,
                time_horizon=score.time_horizon,
                internal_dest_count=r.internal_dest_count,
                internal_conn_count=r.internal_conn_count,
                baseline_avg_internal_dest_count=baseline_avg,
                baseline_deviation_ratio=ratio,
                growth_hits=growth_hits,
                new_internal_targets=new_targets,
            )
        )

    return signals
