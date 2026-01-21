from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional
import math

from src.features.network_fanout import FanoutBucketFeatures


@dataclass(frozen=True)
class BaselineStats:
    """
    Baseline statistics per host across a baseline window.
    """
    host: str
    avg_internal_dest_count: float
    std_internal_dest_count: float
    bucket_count: int


def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values)) / float(len(values))


def _std(values: List[float], mean: float) -> float:
    if not values:
        return 0.0
    var = sum((v - mean) ** 2 for v in values) / float(len(values))
    return float(math.sqrt(var))


def compute_host_baseline_stats(
    baseline_buckets: Iterable[FanoutBucketFeatures],
) -> Dict[str, BaselineStats]:
    """
    Compute baseline statistics per host.
    """
    by_host: Dict[str, List[FanoutBucketFeatures]] = {}
    for r in baseline_buckets:
        by_host.setdefault(r.host, []).append(r)

    stats: Dict[str, BaselineStats] = {}
    for host, rows in by_host.items():
        values = [float(r.internal_dest_count) for r in rows]
        avg = _mean(values)
        std = _std(values, avg)

        stats[host] = BaselineStats(
            host=host,
            avg_internal_dest_count=avg,
            std_internal_dest_count=std,
            bucket_count=len(values),
        )

    return stats


def apply_baseline_to_observation(
    observation_buckets: List[FanoutBucketFeatures],
    baselines: Dict[str, BaselineStats],
    min_baseline_buckets: int = 24,
) -> List[FanoutBucketFeatures]:
    """
    Apply baseline deviation ratio to observation buckets.
    """
    output: List[FanoutBucketFeatures] = []

    for r in observation_buckets:
        baseline = baselines.get(r.host)
        ratio: Optional[float] = None

        if (
            baseline is not None
            and baseline.bucket_count >= min_baseline_buckets
            and baseline.avg_internal_dest_count > 0
        ):
            ratio = float(r.internal_dest_count) / float(baseline.avg_internal_dest_count)

        output.append(
            FanoutBucketFeatures(
                host=r.host,
                bucket_start=r.bucket_start,
                internal_dest_count=r.internal_dest_count,
                internal_conn_count=r.internal_conn_count,
                fanout_growth_rate=r.fanout_growth_rate,
                new_internal_targets=r.new_internal_targets,
                baseline_deviation_ratio=ratio,
            )
        )

    output.sort(key=lambda x: (x.host, x.bucket_start))
    return output


def baseline_completeness_score(
    baseline: Optional[BaselineStats],
    expected_buckets: int,
) -> float:
    if baseline is None or expected_buckets <= 0:
        return 0.0
    return min(1.0, float(baseline.bucket_count) / float(expected_buckets))


if __name__ == "__main__":
    baseline = [
        FanoutBucketFeatures("h1", 0, 2, 10),
        FanoutBucketFeatures("h1", 3600, 3, 12),
        FanoutBucketFeatures("h1", 7200, 2, 9),
    ]

    observation = [
        FanoutBucketFeatures("h1", 10800, 8, 40),
        FanoutBucketFeatures("h1", 14400, 9, 45),
    ]

    stats = compute_host_baseline_stats(baseline)
    applied = apply_baseline_to_observation(observation, stats, min_baseline_buckets=1)

    print(stats["h1"])
    for row in applied:
        print(row)
