from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class AuthBucketFeatures:
    """
    Feature record for a single entity (src_ip) in a single time bucket.
    """
    src_ip: str
    bucket_start: int  # epoch seconds aligned to bucket boundary
    auth_failures_per_src: int
    unique_users_targeted: int

    # Computed later (needs multiple buckets / baseline)
    sustained_failure_growth: Optional[bool] = None
    failure_drift_ratio: Optional[float] = None


def bucket_epoch(ts: int, bucket_seconds: int) -> int:
    if bucket_seconds <= 0:
        raise ValueError("bucket_seconds must be > 0")
    return (ts // bucket_seconds) * bucket_seconds


def extract_auth_failure_bucket_features(
    events: Iterable[Dict],
    bucket_seconds: int = 900,  # 15m default
    time_field: str = "_time",
    src_ip_field: str = "src_ip",
    user_field: str = "user",
    outcome_field: str = "outcome",
    failure_values: Tuple[str, ...] = ("failure", "failed", "fail"),
) -> List[AuthBucketFeatures]:
    """
    MVP feature extraction for password spray drift (PDE-SPL-0402).

    Required event fields (normalized):
      - _time (epoch seconds)
      - src_ip
      - user
      - outcome (string): one of failure_values indicates auth failure

    Output per src_ip per bucket:
      - auth_failures_per_src: count of failures
      - unique_users_targeted: distinct users receiving failures
    """
    # (src_ip, bucket) -> (fail_count, user_set)
    fail_counts: Dict[Tuple[str, int], int] = {}
    user_sets: Dict[Tuple[str, int], Set[str]] = {}

    for e in events:
        ts_raw = e.get(time_field)
        src_ip = str(e.get(src_ip_field, "")).strip()
        user = str(e.get(user_field, "")).strip()
        outcome = str(e.get(outcome_field, "")).strip().lower()

        if ts_raw is None or not src_ip or not user or not outcome:
            continue

        if outcome not in failure_values:
            continue

        try:
            ts = int(ts_raw)
        except Exception:
            continue

        b = bucket_epoch(ts, bucket_seconds)
        key = (src_ip, b)

        if key not in fail_counts:
            fail_counts[key] = 0
            user_sets[key] = set()

        fail_counts[key] += 1
        user_sets[key].add(user)

    out: List[AuthBucketFeatures] = []
    for (src_ip, b), c in fail_counts.items():
        out.append(
            AuthBucketFeatures(
                src_ip=src_ip,
                bucket_start=b,
                auth_failures_per_src=int(c),
                unique_users_targeted=len(user_sets[(src_ip, b)]),
            )
        )

    out.sort(key=lambda r: (r.src_ip, r.bucket_start))
    return out


def compute_growth_hits(
    per_bucket: List[AuthBucketFeatures],
    sustained_buckets: int = 3,
) -> Dict[Tuple[str, int], int]:
    """
    Rolling count of growth events (failures increasing vs previous bucket) per src_ip.

    Returns:
      (src_ip, bucket_start) -> growth_hits over the last N buckets.
    """
    if sustained_buckets <= 0:
        raise ValueError("sustained_buckets must be > 0")

    by_src: Dict[str, List[AuthBucketFeatures]] = {}
    for r in per_bucket:
        by_src.setdefault(r.src_ip, []).append(r)

    growth_hits: Dict[Tuple[str, int], int] = {}

    for src, rows in by_src.items():
        rows.sort(key=lambda r: r.bucket_start)
        flags: List[int] = []
        prev: Optional[int] = None

        for r in rows:
            if prev is None:
                flag = 0
            else:
                flag = 1 if r.auth_failures_per_src > prev else 0

            flags.append(flag)
            prev = r.auth_failures_per_src

            window = flags[-sustained_buckets:]
            growth_hits[(src, r.bucket_start)] = int(sum(window))

    return growth_hits


if __name__ == "__main__":
    # Tiny self-test
    base = 1700000000
    events = [
        {"_time": base + 10, "src_ip": "1.2.3.4", "user": "a", "outcome": "failure"},
        {"_time": base + 20, "src_ip": "1.2.3.4", "user": "b", "outcome": "failure"},
        {"_time": base + 900 + 10, "src_ip": "1.2.3.4", "user": "c", "outcome": "failure"},
        {"_time": base + 900 + 20, "src_ip": "1.2.3.4", "user": "d", "outcome": "failure"},
        {"_time": base + 2 * 900 + 10, "src_ip": "1.2.3.4", "user": "e", "outcome": "failure"},
        {"_time": base + 2 * 900 + 20, "src_ip": "1.2.3.4", "user": "f", "outcome": "failure"},
    ]
    feats = extract_auth_failure_bucket_features(events, bucket_seconds=900)
    hits = compute_growth_hits(feats, sustained_buckets=3)
    for f in feats:
        print(f, "growth_hits=", hits[(f.src_ip, f.bucket_start)])
