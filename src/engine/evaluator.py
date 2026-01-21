from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from src.baselines.rolling import BaselineStats
from src.engine.scoring import ScoreResult, score_ns_p2_001
from src.engine.novelty import compute_true_novelty_count
from src.features.network_fanout import FanoutBucketFeatures, compute_growth_hits


@dataclass(frozen=True)
class Signal:
    signal_name: str
    detection_id: str
    entity_type: str
    entity_id: str  # host

    risk_score: int
    confidence: float
    time_horizon: str

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
    # Phase 2.2: optional true novelty inputs
    baseline_dest_union_by_host: Optional[Dict[str, Set[str]]] = None,
    current_dest_sets_by_bucket: Optional[Dict[Tuple[str, int], Set[str]]] = None,
) -> List[Signal]:
    """
    NS-P2-001: Emerging Lateral Movement Preparation via Internal Fan-out Drift

    Phase 2.2 enhancement:
      - If baseline_dest_union_by_host and current_dest_sets_by_bucket are provided,
        new_internal_targets is computed as true novelty:
          |current_set - baseline_union_set|
      - Otherwise, falls back to proxy:
          new_internal_targets := internal_dest_count
    """
    signals: List[Signal] = []

    growth_hits_map = compute_growth_hits(observation_buckets, sustained_buckets=sustained_buckets)

    for r in observation_buckets:
        baseline = baselines.get(r.host)
        baseline_avg = baseline.avg_internal_dest_count if baseline else None

        ratio = r.baseline_deviation_ratio
        if ratio is None and baseline_avg and baseline_avg > 0:
            ratio = float(r.internal_dest_count) / float(baseline_avg)

        growth_hits = int(growth_hits_map.get((r.host, r.bucket_start), 0))
        sustained_growth = growth_hits >= sustained_buckets

        # Phase 2.2 true novelty if inputs exist
        if baseline_dest_union_by_host is not None and current_dest_sets_by_bucket is not None:
            baseline_set = baseline_dest_union_by_host.get(r.host, set())
            current_set = current_dest_sets_by_bucket.get((r.host, r.bucket_start), set())
            new_targets = compute_true_novelty_count(current_set=current_set, baseline_set=baseline_set)
        else:
            # MVP proxy
            new_targets = int(r.internal_dest_count)

        novelty_present = new_targets >= min_new_targets

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
