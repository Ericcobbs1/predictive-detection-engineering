from __future__ import annotations

from src.baselines.rolling import apply_baseline_to_observation, compute_host_baseline_stats
from src.engine.evaluator import evaluate_ns_p2_001
from src.features.network_fanout import extract_fanout_bucket_features


def build_sample_events():
    """
    Deterministic synthetic events:
    - baseline: low fan-out for 3 buckets
    - observation: sustained fan-out growth for 3 buckets
    """
    base_time = 1700000000
    events = []

    # Baseline: 3 hours, 2 dests per hour
    for i in range(3):
        t = base_time + (i * 3600)
        events.append({"_time": t + 10, "host": "hostA", "dest_ip": "10.0.0.10"})
        events.append({"_time": t + 20, "host": "hostA", "dest_ip": "10.0.0.11"})

    # Observation: 3 hours with increasing unique internal dests
    growth_sets = [
        ["10.0.0.20", "10.0.0.21", "10.0.0.22", "10.0.0.23"],
        ["10.0.0.30", "10.0.0.31", "10.0.0.32", "10.0.0.33", "10.0.0.34", "10.0.0.35"],
        ["10.0.0.40", "10.0.0.41", "10.0.0.42", "10.0.0.43", "10.0.0.44", "10.0.0.45", "10.0.0.46", "10.0.0.47"],
    ]
    for j, dests in enumerate(growth_sets):
        t = base_time + ((3 + j) * 3600)
        for k, d in enumerate(dests):
            events.append({"_time": t + (k * 5), "host": "hostA", "dest_ip": d})

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


def test_ns_p2_001_generates_signal():
    events = build_sample_events()
    bucketed = extract_fanout_bucket_features(events, bucket_seconds=3600)

    baseline_buckets, observation_buckets = split_baseline_vs_observation(bucketed, baseline_buckets=3)
    baselines = compute_host_baseline_stats(baseline_buckets)

    obs_with_baseline = apply_baseline_to_observation(
        observation_buckets,
        baselines,
        min_baseline_buckets=1,
    )

    signals = evaluate_ns_p2_001(
        obs_with_baseline,
        baselines,
        deviation_ratio_threshold=2.0,  # slightly lower for deterministic test
        sustained_buckets=2,
        min_new_targets=2,
        expected_baseline_buckets=3,
    )

    assert len(signals) >= 1, "Expected at least one signal for sustained fan-out growth."

    s = signals[0]
    assert s.entity_type == "host"
    assert s.entity_id == "hostA"
    assert 0 <= s.risk_score <= 100
    assert 0.0 <= s.confidence <= 1.0
    assert s.time_horizon in {"early", "emerging", "imminent"}


