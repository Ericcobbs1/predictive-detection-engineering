from __future__ import annotations

from src.engine.evaluator_auth import compute_auth_baseline_stats, evaluate_pde_spl_0402
from src.features.auth_drift import extract_auth_failure_bucket_features


def build_sample_auth_events():
    """
    Deterministic synthetic auth failures:
      - baseline: low failures per bucket for src_ip
      - observation: sustained increasing failures and many unique users (spray)
    """
    base = 1700000000
    src = "203.0.113.10"
    events = []

    # Baseline: 3 buckets, 2 failures each, 2 unique users
    for i in range(3):
        t = base + i * 900  # 15m buckets
        events.append({"_time": t + 10, "src_ip": src, "user": f"base{i}a", "outcome": "failure"})
        events.append({"_time": t + 20, "src_ip": src, "user": f"base{i}b", "outcome": "failure"})

    # Observation: 3 buckets with increasing failures and many unique users
    # bucket 4: 12 users, bucket 5: 14 users, bucket 6: 16 users
    user_counts = [12, 14, 16]
    for j, n_users in enumerate(user_counts):
        t = base + (3 + j) * 900
        for k in range(n_users):
            events.append({"_time": t + k, "src_ip": src, "user": f"user{k:02d}", "outcome": "failure"})

    return events


def split_baseline_vs_observation(bucketed, baseline_buckets: int = 3):
    by_src = {}
    for r in bucketed:
        by_src.setdefault(r.src_ip, []).append(r)

    baseline = []
    obs = []
    for src, rows in by_src.items():
        rows.sort(key=lambda x: x.bucket_start)
        baseline.extend(rows[:baseline_buckets])
        obs.extend(rows[baseline_buckets:])

    baseline.sort(key=lambda x: (x.src_ip, x.bucket_start))
    obs.sort(key=lambda x: (x.src_ip, x.bucket_start))
    return baseline, obs


def test_pde_spl_0402_generates_signal():
    events = build_sample_auth_events()
    bucketed = extract_auth_failure_bucket_features(events, bucket_seconds=900)

    baseline_buckets, observation_buckets = split_baseline_vs_observation(bucketed, baseline_buckets=3)
    baselines = compute_auth_baseline_stats(baseline_buckets)

    signals = evaluate_pde_spl_0402(
        observation_buckets,
        baselines,
        drift_ratio_threshold=2.0,   # lower for deterministic test
        sustained_buckets=2,
        min_users=8,
        expected_baseline_buckets=3,
        min_baseline_buckets=1,
    )

    assert len(signals) >= 1, "Expected at least one password spray drift signal."

    s = signals[0]
    assert s.entity_type == "src_ip"
    assert s.entity_id == "203.0.113.10"
    assert 0 <= s.risk_score <= 100
    assert 0.0 <= s.confidence <= 1.0
    assert s.time_horizon in {"early", "emerging", "imminent"}
    assert s.unique_users_targeted >= 8
    assert s.failure_drift_ratio is not None
