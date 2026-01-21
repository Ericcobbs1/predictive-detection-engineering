from __future__ import annotations

from src.engine.evaluator_staging import compute_staging_baseline_stats, evaluate_pde_spl_0404
from src.features.data_staging_drift import extract_data_staging_bucket_features


def build_sample_staging_events():
    """
    Deterministic synthetic staging indicators:
      - baseline: low staging activity (1 archive event per bucket) so baseline stats exist
      - observation: sustained, increasing staging activity with multiple unique artifacts per bucket
    """
    base = 1700000000
    host = "hostA"
    events = []

    # Baseline: 3 buckets, 1 small archive per bucket
    for i in range(3):
        t = base + i * 3600
        events.append(
            {
                "_time": t + 10,
                "host": host,
                "process_name": "zip.exe",
                "file_name": f"base{i}.zip",
                "file_path": f"C:\\Temp\\base{i}.zip",
                "file_size": 10_000,
            }
        )

    # Observation: increasing counts per bucket (2 -> 4 -> 6)
    # Bucket 4: 2 events, 2 artifacts
    t4 = base + 3 * 3600
    events.extend(
        [
            {"_time": t4 + 10, "host": host, "process_name": "7z.exe", "file_name": "stage1.zip", "file_path": "C:\\Temp\\stage1.zip", "file_size": 10_000},
            {"_time": t4 + 20, "host": host, "process_name": "7z.exe", "file_name": "stage2.7z", "file_path": "C:\\Temp\\stage2.7z", "file_size": 20_000},
        ]
    )

    # Bucket 5: 4 events, 4 artifacts
    t5 = base + 4 * 3600
    events.extend(
        [
            {"_time": t5 + 10, "host": host, "process_name": "zip.exe", "file_name": "stage3.zip", "file_path": "C:\\Temp\\stage3.zip", "file_size": 30_000},
            {"_time": t5 + 20, "host": host, "process_name": "rar.exe", "file_name": "stage4.rar", "file_path": "C:\\Temp\\stage4.rar", "file_size": 40_000},
            {"_time": t5 + 30, "host": host, "process_name": "tar.exe", "file_name": "stage5.tar", "file_path": "C:\\Temp\\stage5.tar", "file_size": 50_000},
            {"_time": t5 + 40, "host": host, "process_name": "gzip.exe", "file_name": "stage6.gz", "file_path": "C:\\Temp\\stage6.gz", "file_size": 60_000},
        ]
    )

    # Bucket 6: 6 events, 6 artifacts
    t6 = base + 5 * 3600
    events.extend(
        [
            {"_time": t6 + 10, "host": host, "process_name": "7z.exe", "file_name": "stage7.zip", "file_path": "C:\\Temp\\stage7.zip", "file_size": 10_000},
            {"_time": t6 + 20, "host": host, "process_name": "7z.exe", "file_name": "stage8.7z", "file_path": "C:\\Temp\\stage8.7z", "file_size": 20_000},
            {"_time": t6 + 30, "host": host, "process_name": "rar.exe", "file_name": "stage9.rar", "file_path": "C:\\Temp\\stage9.rar", "file_size": 40_000},
            {"_time": t6 + 40, "host": host, "process_name": "tar.exe", "file_name": "stage10.tar", "file_path": "C:\\Temp\\stage10.tar", "file_size": 50_000},
            {"_time": t6 + 50, "host": host, "process_name": "gzip.exe", "file_name": "stage11.gz", "file_path": "C:\\Temp\\stage11.gz", "file_size": 60_000},
            {"_time": t6 + 60, "host": host, "process_name": "zip.exe", "file_name": "stage12.zip", "file_path": "C:\\Temp\\stage12.zip", "file_size": 30_000},
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


def test_pde_spl_0404_generates_signal():
    events = build_sample_staging_events()
    bucketed = extract_data_staging_bucket_features(events, bucket_seconds=3600, large_file_bytes=100_000_000)

    baseline_buckets, observation_buckets = split_baseline_vs_observation(bucketed, baseline_buckets=3)
    baselines = compute_staging_baseline_stats(baseline_buckets)

    signals = evaluate_pde_spl_0404(
        observation_buckets,
        baselines,
        drift_ratio_threshold=2.0,
        sustained_buckets=2,
        min_unique_artifacts=2,
        expected_baseline_buckets=3,
        min_baseline_buckets=1,
    )

    assert len(signals) >= 1, "Expected at least one data staging drift signal."

    s = signals[0]
    assert s.entity_type == "host"
    assert s.entity_id == "hostA"
    assert 0 <= s.risk_score <= 100
    assert 0.0 <= s.confidence <= 1.0
    assert s.time_horizon in {"early", "emerging", "imminent"}
    assert s.unique_staging_artifacts >= 2
    assert s.staging_drift_ratio is not None
