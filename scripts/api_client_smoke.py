from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict, List


BASE_URL = "http://127.0.0.1:8000"


def post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode("utf-8")
        return json.loads(body)


def sample_0401() -> Dict[str, Any]:
    # baseline: 3 buckets, 2 dests each
    baseline = [
        {"host": "hostA", "bucket_start": 0, "internal_dest_count": 2, "internal_conn_count": 2},
        {"host": "hostA", "bucket_start": 3600, "internal_dest_count": 2, "internal_conn_count": 2},
        {"host": "hostA", "bucket_start": 7200, "internal_dest_count": 2, "internal_conn_count": 2},
    ]
    # observation: increasing fan-out (2 -> 4 -> 6)
    observation = [
        {"host": "hostA", "bucket_start": 10800, "internal_dest_count": 2, "internal_conn_count": 10},
        {"host": "hostA", "bucket_start": 14400, "internal_dest_count": 4, "internal_conn_count": 20},
        {"host": "hostA", "bucket_start": 18000, "internal_dest_count": 6, "internal_conn_count": 30},
    ]
    return {
        "baseline": baseline,
        "observation": observation,
        "deviation_ratio_threshold": 1.5,
        "sustained_buckets": 2,
        "min_new_targets": 1,
        "expected_baseline_buckets": 3,
    }


def sample_0402() -> Dict[str, Any]:
    baseline = [
        {"src_ip": "203.0.113.10", "bucket_start": 0, "auth_failures_per_src": 2, "unique_users_targeted": 2},
        {"src_ip": "203.0.113.10", "bucket_start": 900, "auth_failures_per_src": 2, "unique_users_targeted": 2},
        {"src_ip": "203.0.113.10", "bucket_start": 1800, "auth_failures_per_src": 2, "unique_users_targeted": 2},
    ]
    observation = [
        {"src_ip": "203.0.113.10", "bucket_start": 2700, "auth_failures_per_src": 8, "unique_users_targeted": 8},
        {"src_ip": "203.0.113.10", "bucket_start": 3600, "auth_failures_per_src": 12, "unique_users_targeted": 12},
        {"src_ip": "203.0.113.10", "bucket_start": 4500, "auth_failures_per_src": 16, "unique_users_targeted": 16},
    ]
    return {
        "baseline": baseline,
        "observation": observation,
        "drift_ratio_threshold": 1.5,
        "sustained_buckets": 2,
        "min_users": 5,
        "expected_baseline_buckets": 3,
        "min_baseline_buckets": 1,
    }


def sample_0403() -> Dict[str, Any]:
    baseline = [
        {"host": "hostA", "bucket_start": 0, "persistence_events_per_host": 1, "unique_persistence_artifacts": 1},
        {"host": "hostA", "bucket_start": 3600, "persistence_events_per_host": 1, "unique_persistence_artifacts": 1},
        {"host": "hostA", "bucket_start": 7200, "persistence_events_per_host": 1, "unique_persistence_artifacts": 1},
    ]
    observation = [
        {"host": "hostA", "bucket_start": 10800, "persistence_events_per_host": 2, "unique_persistence_artifacts": 2},
        {"host": "hostA", "bucket_start": 14400, "persistence_events_per_host": 3, "unique_persistence_artifacts": 2},
        {"host": "hostA", "bucket_start": 18000, "persistence_events_per_host": 4, "unique_persistence_artifacts": 3},
    ]
    return {
        "baseline": baseline,
        "observation": observation,
        "drift_ratio_threshold": 1.5,
        "sustained_buckets": 2,
        "min_unique_artifacts": 2,
        "expected_baseline_buckets": 3,
        "min_baseline_buckets": 1,
    }


def sample_0404() -> Dict[str, Any]:
    baseline = [
        {"host": "hostA", "bucket_start": 0, "staging_events_per_host": 1, "unique_staging_artifacts": 1},
        {"host": "hostA", "bucket_start": 3600, "staging_events_per_host": 1, "unique_staging_artifacts": 1},
        {"host": "hostA", "bucket_start": 7200, "staging_events_per_host": 1, "unique_staging_artifacts": 1},
    ]
    observation = [
        {"host": "hostA", "bucket_start": 10800, "staging_events_per_host": 2, "unique_staging_artifacts": 2},
        {"host": "hostA", "bucket_start": 14400, "staging_events_per_host": 4, "unique_staging_artifacts": 4},
        {"host": "hostA", "bucket_start": 18000, "staging_events_per_host": 6, "unique_staging_artifacts": 6},
    ]
    return {
        "baseline": baseline,
        "observation": observation,
        "drift_ratio_threshold": 1.5,
        "sustained_buckets": 2,
        "min_unique_artifacts": 2,
        "expected_baseline_buckets": 3,
        "min_baseline_buckets": 1,
    }


def sample_0405() -> Dict[str, Any]:
    baseline = [
        {"host": "hostA", "bucket_start": 0, "admin_tool_events_per_host": 1, "unique_admin_tools": 1},
        {"host": "hostA", "bucket_start": 3600, "admin_tool_events_per_host": 1, "unique_admin_tools": 1},
        {"host": "hostA", "bucket_start": 7200, "admin_tool_events_per_host": 1, "unique_admin_tools": 1},
    ]
    observation = [
        {"host": "hostA", "bucket_start": 10800, "admin_tool_events_per_host": 2, "unique_admin_tools": 2},
        {"host": "hostA", "bucket_start": 14400, "admin_tool_events_per_host": 4, "unique_admin_tools": 3},
        {"host": "hostA", "bucket_start": 18000, "admin_tool_events_per_host": 6, "unique_admin_tools": 4},
    ]
    return {
        "baseline": baseline,
        "observation": observation,
        "drift_ratio_threshold": 1.5,
        "sustained_buckets": 2,
        "min_unique_tools": 2,
        "expected_baseline_buckets": 3,
        "min_baseline_buckets": 1,
    }


def main() -> None:
    # health check
    with urllib.request.urlopen(f"{BASE_URL}/health", timeout=10) as resp:
        print("GET /health:", resp.read().decode("utf-8"))

    calls = [
        ("/evaluate/0401", sample_0401()),
        ("/evaluate/0402", sample_0402()),
        ("/evaluate/0403", sample_0403()),
        ("/evaluate/0404", sample_0404()),
        ("/evaluate/0405", sample_0405()),
    ]

    for path, payload in calls:
        print(f"\nPOST {path}")
        res = post(path, payload)
        print("count:", res.get("count"))
        if res.get("signals"):
            print("first_signal:", res["signals"][0])


if __name__ == "__main__":
    main()
