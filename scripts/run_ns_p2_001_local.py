from __future__ import annotations

import argparse
from dataclasses import asdict
from typing import Dict, List

from src.baselines.rolling import apply_baseline_to_observation, compute_host_baseline_stats
from src.engine.evaluator import evaluate_ns_p2_001
from src.engine.explain import explain_ns_p2_001
from src.features.network_fanout import FanoutBucketFeatures, extract_fanout_bucket_features


def split_baseline_vs_observation(
    bucket_features: List[FanoutBucketFeatures],
    baseline_buckets: int,
) -> (List[FanoutBucketFeatures], List[FanoutBucketFeatures]):
    """
    MVP splitter:
      - takes the earliest N buckets per host as baseline
      - uses the remainder as observation

    In production you will use actual time windows (30d baseline, 72h observation).
    """
    by_host: Dict[str, List[FanoutBucketFeatures]] = {}
    for r in bucket_features:
        by_host.setdefault(r.host, []).append(r)

    baseline: List[FanoutBucketFeatures] = []
    observation: List[FanoutBucketFeatures] = []

    for host, rows in by_host.items():
        rows.sort(key=lambda x: x.bucket_start)
        baseline.extend(rows[:baseline_buckets])
        observation.extend(rows[baseline_buckets:])

    baseline.sort(key=lambda x: (x.host, x.bucket_start))
    observation.sort(key=lambda x: (x.host, x.bucket_start))
    return baseline, observation


def build_sample_events() -> List[dict]:
    """
    Generates synthetic events to demonstrate a gradual fan-out increase.
    Assumes RFC1918 internal addressing for dest_ip.
    """
    base_time = 1700000000  # arbitrary epoch
    events: List[dict] = []

    # Baseline: low fan-out
    for i in range(3):
        t = base_time + (i * 3600)
        # 2 internal destinations per hour
        events.append({"_time": t + 10, "host": "hostA", "dest_ip": "10.0.0.10"})
        events.append({"_time": t + 20, "host": "hostA", "dest_ip": "10.0.0.11"})

    # Observation: sustained growth in fan-out
    # Hour 4: 4 dests, Hour 5: 6 dests, Hour 6: 8 dests
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Local end-to-end runner for NS-P2-001 (MVP).")
    parser.add_argument("--bucket-seconds", type=int, default=3600, help="Bucket size in seconds (default: 3600)")
    parser.add_argument("--baseline-buckets", type=int, default=3, help="How many earliest buckets to treat as baseline (default: 3)")
    parser.add_argument("--min-baseline-buckets", type=int, default=1, help="Minimum baseline buckets required (default: 1)")
    parser.add_argument("--deviation-ratio", type=float, default=2.5, help="Deviation ratio threshold (default: 2.5)")
    parser.add_argument("--sustained-buckets", type=int, default=3, help="Sustained growth buckets (default: 3)")
    parser.add_argument("--min-new-targets", type=int, default=3, help="Minimum new targets threshold (default: 3)")
    args = parser.parse_args()

    # 1) Create sample events (replace with real data loader later)
    events = build_sample_events()

    # 2) Feature extraction (bucketized)
    bucketed = extract_fanout_bucket_features(events, bucket_seconds=args.bucket_seconds)

    # 3) Split into baseline and observation (MVP)
    baseline_buckets, observation_buckets = split_baseline_vs_observation(bucketed, baseline_buckets=args.baseline_buckets)

    # 4) Compute baseline stats
    baselines = compute_host_baseline_stats(baseline_buckets)

    # 5) Apply baseline ratio to observation buckets
    observation_with_baseline = apply_baseline_to_observation(
        observation_buckets,
        baselines,
        min_baseline_buckets=args.min_baseline_buckets,
    )

    # 6) Evaluate detection
    signals = evaluate_ns_p2_001(
        observation_with_baseline,
        baselines,
        deviation_ratio_threshold=args.deviation_ratio,
        sustained_buckets=args.sustained_buckets,
        min_new_targets=args.min_new_targets,
        expected_baseline_buckets=args.baseline_buckets,
    )

    # 7) Explain results
    if not signals:
        print("\nNo signals generated (tune thresholds or sample data).\n")
        return

    print("\n=== Signals ===\n")
    for s in signals:
        print(asdict(s))

    print("\n=== Explanations ===\n")
    for s in signals:
        exp = explain_ns_p2_001(s)
        print("\n---")
        print("Headline:", exp["headline"])
        print("Narrative:", exp["narrative"])
        print("Evidence:")
        for e in exp["evidence"]:
            print(" -", e)
        print("Next steps:")
        for n in exp["next_steps"]:
            print(" -", n)


if __name__ == "__main__":
    main()

