from __future__ import annotations

from src.baselines.rolling import compute_host_baseline_stats
from src.engine.evaluator import evaluate_ns_p2_001
from src.engine.novelty import build_baseline_set_by_host
from src.features.network_fanout import FanoutBucketFeatures, extract_fanout_bucket_features, extract_internal_dest_sets_by_bucket


def build_sample_events_for_true_novelty():
    """
    Deterministic:
      - baseline buckets have 2 stable destinations
      - observation bucket 4 introduces novelty (but smaller than bucket 5)
      - observation bucket 5 has MORE destinations than bucket 4 so growth gate passes
    """
    base_time = 1700000000
    host = "hostA"
    events = []

    # Baseline (3 buckets): destinations .10 and .11
    for i in range(3):
        t = base_time + (i * 3600)
        events.append({"_time": t + 10, "host": host, "dest_ip": "10.0.0.10"})
        events.append({"_time": t + 20, "host": host, "dest_ip": "10.0.0.11"})

    # Observation bucket 4: 3 dests total (includes 1 baseline + 2 new) => novelty = 2
    t4 = base_time + (3 * 3600)
    events.extend(
        [
            {"_time": t4 + 10, "host": host, "dest_ip": "10.0.0.10"},  # baseline
            {"_time": t4 + 20, "host": host, "dest_ip": "10.0.0.20"},  # new
            {"_time": t4 + 30, "host": host, "dest_ip": "10.0.0.21"},  # new
        ]
    )

    # Observation bucket 5: 5 dests total (all new) => novelty = 5
    # Also ensures internal_dest_count increases (3 -> 5) so growth flag becomes 1.
    t5 = base_time + (4 * 3600)
    events.extend(
        [
            {"_time": t5 + 10, "host": host, "dest_ip": "10.0.0.30"},
            {"_time": t5 + 20, "host": host, "dest_ip": "10.0.0.31"},
            {"_time": t5 + 30, "host": host, "dest_ip": "10.0.0.32"},
            {"_time": t5 + 40, "host": host, "dest_ip": "10.0.0.33"},
            {"_time": t5 + 50, "host": host, "dest_ip": "10.0.0.34"},
        ]
    )

    return events


def split_baseline_vs_observation(bucketed, baseline_buckets: int = 3):
    by_host = {}
    for r in bucketed:
        by_host.setdefault(r.host, []).append(r)

    baseline = []
    obs = []
    for host, rows in by_host.items():
        rows.sort(key=lambda x: x.bucket_start)
        baseline.extend(rows[:baseline_buckets])
        obs.extend(rows[baseline_buckets:])

    baseline.sort(key=lambda x: (x.host, x.bucket_start))
    obs.sort(key=lambda x: (x.host, x.bucket_start))
    return baseline, obs


def attach_ratio(obs_buckets, baselines):
    """
    Ensure baseline_deviation_ratio is populated for the evaluator gating condition.
    """
    out = []
    for r in obs_buckets:
        b = baselines.get(r.host)
        avg = b.avg_internal_dest_count if b else 0.0
        ratio = (r.internal_dest_count / avg) if avg and avg > 0 else 1.0

        out.append(
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
    return out


def test_ns_p2_001_true_novelty_setdiff_used():
    events = build_sample_events_for_true_novelty()

    bucketed = extract_fanout_bucket_features(events, bucket_seconds=3600)
    dest_sets_by_bucket = extract_internal_dest_sets_by_bucket(events, bucket_seconds=3600)

    baseline_buckets, obs_buckets = split_baseline_vs_observation(bucketed, baseline_buckets=3)
    baselines = compute_host_baseline_stats(baseline_buckets)
    obs_with_ratio = attach_ratio(obs_buckets, baselines)

    # Baseline union set per host from baseline buckets
    obs_start = obs_with_ratio[0].bucket_start
    baseline_dest_sets = {(h, b): s for (h, b), s in dest_sets_by_bucket.items() if b < obs_start}
    baseline_union_by_host = build_baseline_set_by_host(baseline_dest_sets)

    # Permissive thresholds, but keep growth gate (sustained_buckets=1) to exercise the path
    signals = evaluate_ns_p2_001(
        obs_with_ratio,
        baselines,
        deviation_ratio_threshold=1.0,
        sustained_buckets=1,
        min_new_targets=1,
        expected_baseline_buckets=3,
        baseline_dest_union_by_host=baseline_union_by_host,
        current_dest_sets_by_bucket=dest_sets_by_bucket,
    )

    assert len(signals) >= 1, "Expected at least one signal (should trigger on bucket 5 where fan-out increases)."

    s = signals[0]
    # Baseline union contains .10 and .11
    # For bucket 5, all dests are new (.30-.34) => true novelty should be 5 (NOT proxy unless proxy also equals 5)
    assert s.new_internal_targets >= 1
    assert s.new_internal_targets in {2, 5}, "Expected true novelty based on set-diff (2 in bucket 4, 5 in bucket 5)."
