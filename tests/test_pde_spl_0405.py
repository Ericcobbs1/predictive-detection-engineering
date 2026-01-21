from __future__ import annotations

from src.engine.evaluator_admin_tooling import compute_admin_tooling_baseline_stats, evaluate_pde_spl_0405
from src.features.admin_tooling_drift import extract_admin_tooling_bucket_features


def build_sample_admin_tool_events():
    """
    Deterministic synthetic admin tooling events:
      - baseline: low admin tooling activity (1 event per bucket) so baseline stats exist
      - observation: increasing activity with multiple unique tools per bucket
    """
    base = 1700000000
    host = "hostA"
    events = []

    # Baseline: 3 buckets, 1 tool event per bucket (powershell)
    for i in range(3):
        t = base + i * 3600
        events.append(
            {
                "_time": t + 10,
                "host": host,
                "process_name": "powershell.exe",
                "command_line": "powershell -nop -w hidden",
            }
        )

    # Observation: increasing counts (2 -> 4 -> 6) with tool variety
    t4 = base + 3 * 3600
    events.extend(
        [
            {"_time": t4 + 10, "host": host, "process_name": "psexec.exe", "command_line": "psexec \\\\10.0.0.5 cmd"},
            {"_time": t4 + 20, "host": host, "process_name": "wmic.exe", "command_line": "wmic /node:10.0.0.6 process call create"},
        ]
    )

    t5 = base + 4 * 3600
    events.extend(
        [
            {"_time": t5 + 10, "host": host, "process_name": "psexec.exe", "command_line": "psexec \\\\10.0.0.7 cmd"},
            {"_time": t5 + 20, "host": host, "process_name": "winrm.cmd", "command_line": "winrm quickconfig"},
            {"_time": t5 + 30, "host": host, "process_name": "schtasks.exe", "command_line": "schtasks /create /tn X"},
            {"_time": t5 + 40, "host": host, "process_name": "sc.exe", "command_line": "sc.exe create svc binPath= C:\\Temp\\a.exe"},
        ]
    )

    t6 = base + 5 * 3600
    events.extend(
        [
            {"_time": t6 + 10, "host": host, "process_name": "psexec.exe", "command_line": "psexec \\\\10.0.0.8 cmd"},
            {"_time": t6 + 20, "host": host, "process_name": "wmic.exe", "command_line": "wmic /node:10.0.0.9 process call create"},
            {"_time": t6 + 30, "host": host, "process_name": "winrm.cmd", "command_line": "winrm enumerate"},
            {"_time": t6 + 40, "host": host, "process_name": "schtasks.exe", "command_line": "schtasks /run /tn X"},
            {"_time": t6 + 50, "host": host, "process_name": "sc.exe", "command_line": "sc.exe start svc"},
            {"_time": t6 + 60, "host": host, "process_name": "powershell.exe", "command_line": "powershell -enc AAAA"},
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


def test_pde_spl_0405_generates_signal():
    events = build_sample_admin_tool_events()
    bucketed = extract_admin_tooling_bucket_features(events, bucket_seconds=3600)

    baseline_buckets, observation_buckets = split_baseline_vs_observation(bucketed, baseline_buckets=3)
    baselines = compute_admin_tooling_baseline_stats(baseline_buckets)

    signals = evaluate_pde_spl_0405(
        observation_buckets,
        baselines,
        drift_ratio_threshold=2.0,   # lower for deterministic test
        sustained_buckets=2,
        min_unique_tools=2,
        expected_baseline_buckets=3,
        min_baseline_buckets=1,
    )

    assert len(signals) >= 1, "Expected at least one suspicious admin tooling drift signal."

    s = signals[0]
    assert s.entity_type == "host"
    assert s.entity_id == "hostA"
    assert 0 <= s.risk_score <= 100
    assert 0.0 <= s.confidence <= 1.0
    assert s.time_horizon in {"early", "emerging", "imminent"}
    assert s.unique_admin_tools >= 2
    assert s.admin_tool_drift_ratio is not None
