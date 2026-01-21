from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class FanoutBucketFeatures:
    """
    Feature record for a single entity (host) in a single time bucket.
    """
    host: str
    bucket_start: int  # epoch seconds aligned to bucket boundary
    internal_dest_count: int
    internal_conn_count: int

    # Computed later in pipeline stages (not required for raw extraction)
    fanout_growth_rate: Optional[float] = None
    new_internal_targets: Optional[int] = None
    baseline_deviation_ratio: Optional[float] = None


RFC1918_PREFIXES: Tuple[str, ...] = (
    "10.",
    "192.168.",
    # 172.16.0.0/12 handled separately
)


def is_internal_ip(ip: str) -> bool:
    if not ip:
        return False

    ip = ip.strip()
    if ip.startswith(RFC1918_PREFIXES):
        return True

    if ip.startswith("172."):
        parts = ip.split(".")
        if len(parts) < 2:
            return False
        try:
            second = int(parts[1])
        except ValueError:
            return False
        return 16 <= second <= 31

    return False


def bucket_epoch(ts: int, bucket_seconds: int) -> int:
    if bucket_seconds <= 0:
        raise ValueError("bucket_seconds must be > 0")
    return (ts // bucket_seconds) * bucket_seconds


def extract_fanout_bucket_features(
    events: Iterable[Dict],
    bucket_seconds: int = 3600,
    host_field: str = "host",
    dest_ip_field: str = "dest_ip",
    time_field: str = "_time",
) -> List[FanoutBucketFeatures]:
    """
    Computes per-host per-bucket:
      - internal_dest_count (dc internal dest_ip)
      - internal_conn_count (count internal events)
    """
    dest_sets: Dict[Tuple[str, int], Set[str]] = {}
    conn_counts: Dict[Tuple[str, int], int] = {}

    for e in events:
        host = str(e.get(host_field, "")).strip()
        dest_ip = str(e.get(dest_ip_field, "")).strip()
        ts_raw = e.get(time_field)

        if not host or not dest_ip or ts_raw is None:
            continue

        try:
            ts = int(ts_raw)
        except Exception:
            continue

        if not is_internal_ip(dest_ip):
            continue

        b = bucket_epoch(ts, bucket_seconds)
        key = (host, b)

        if key not in dest_sets:
            dest_sets[key] = set()
            conn_counts[key] = 0

        dest_sets[key].add(dest_ip)
        conn_counts[key] += 1

    out: List[FanoutBucketFeatures] = []
    for (host, b), dests in dest_sets.items():
        out.append(
            FanoutBucketFeatures(
                host=host,
                bucket_start=b,
                internal_dest_count=len(dests),
                internal_conn_count=int(conn_counts[(host, b)]),
            )
        )

    out.sort(key=lambda r: (r.host, r.bucket_start))
    return out


def compute_growth_hits(
    per_bucket: List[FanoutBucketFeatures],
    sustained_buckets: int = 3,
) -> Dict[Tuple[str, int], int]:
    if sustained_buckets <= 0:
        raise ValueError("sustained_buckets must be > 0")

    by_host: Dict[str, List[FanoutBucketFeatures]] = {}
    for r in per_bucket:
        by_host.setdefault(r.host, []).append(r)

    growth_hits: Dict[Tuple[str, int], int] = {}
    for host, rows in by_host.items():
        rows.sort(key=lambda r: r.bucket_start)
        flags: List[int] = []
        prev: Optional[int] = None

        for r in rows:
            flag = 0 if prev is None else (1 if r.internal_dest_count > prev else 0)
            flags.append(flag)
            prev = r.internal_dest_count

            window = flags[-sustained_buckets:]
            growth_hits[(host, r.bucket_start)] = int(sum(window))

    return growth_hits


def compute_new_internal_targets_proxy(internal_dest_count: int) -> int:
    return int(internal_dest_count)


if __name__ == "__main__":
    sample_events = [
        {"_time": 1700000000, "host": "host1", "dest_ip": "10.0.0.5"},
        {"_time": 1700000100, "host": "host1", "dest_ip": "10.0.0.6"},
        {"_time": 1700000200, "host": "host1", "dest_ip": "8.8.8.8"},
        {"_time": 1700003600, "host": "host1", "dest_ip": "10.0.0.7"},
        {"_time": 1700007200, "host": "host1", "dest_ip": "10.0.0.8"},
    ]

    feats = extract_fanout_bucket_features(sample_events, bucket_seconds=3600)
    hits = compute_growth_hits(feats, sustained_buckets=3)

    for f in feats:
        print(f)
        print("growth_hits:", hits[(f.host, f.bucket_start)])
