from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class PersistenceBucketFeatures:
    """
    Feature record for a single entity (host) in a single time bucket.
    """
    host: str
    bucket_start: int  # epoch seconds aligned to bucket boundary
    persistence_events_per_host: int
    unique_persistence_artifacts: int

    # Computed later (needs multiple buckets / baseline)
    sustained_persistence_growth: Optional[bool] = None
    persistence_drift_ratio: Optional[float] = None


def bucket_epoch(ts: int, bucket_seconds: int) -> int:
    if bucket_seconds <= 0:
        raise ValueError("bucket_seconds must be > 0")
    return (ts // bucket_seconds) * bucket_seconds


def extract_persistence_bucket_features(
    events: Iterable[Dict],
    bucket_seconds: int = 3600,  # 1h default
    time_field: str = "_time",
    host_field: str = "host",
    eventcode_field: str = "EventCode",
    task_name_fields: Tuple[str, ...] = ("TaskName", "task_name"),
    service_name_fields: Tuple[str, ...] = ("ServiceName", "service_name"),
    persistence_eventcodes: Tuple[int, ...] = (4698, 7045),
) -> List[PersistenceBucketFeatures]:
    """
    MVP feature extraction for persistence drift (PDE-SPL-0403).

    Expected normalized event fields:
      - _time (epoch seconds)
      - host
      - EventCode (int) where 4698=scheduled task created, 7045=service created (common Windows)
      - TaskName/ServiceName fields may vary by source

    Computes per host per bucket:
      - persistence_events_per_host: count of matching persistence events
      - unique_persistence_artifacts: distinct task/service names (artifact ids)
    """
    counts: Dict[Tuple[str, int], int] = {}
    artifacts: Dict[Tuple[str, int], Set[str]] = {}

    for e in events:
        ts_raw = e.get(time_field)
        host = str(e.get(host_field, "")).strip()
        ec_raw = e.get(eventcode_field)

        if ts_raw is None or not host or ec_raw is None:
            continue

        try:
            ts = int(ts_raw)
        except Exception:
            continue

        try:
            ec = int(ec_raw)
        except Exception:
            continue

        if ec not in persistence_eventcodes:
            continue

        b = bucket_epoch(ts, bucket_seconds)
        key = (host, b)

        if key not in counts:
            counts[key] = 0
            artifacts[key] = set()

        counts[key] += 1

        # Determine artifact name
        artifact_val = None
        if ec == 4698:
            for f in task_name_fields:
                if e.get(f):
                    artifact_val = str(e.get(f)).strip()
                    break
            if not artifact_val:
                artifact_val = "unknown_task"
        elif ec == 7045:
            for f in service_name_fields:
                if e.get(f):
                    artifact_val = str(e.get(f)).strip()
                    break
            if not artifact_val:
                artifact_val = "unknown_service"
        else:
            artifact_val = "unknown_artifact"

        artifacts[key].add(artifact_val)

    out: List[PersistenceBucketFeatures] = []
    for (host, b), c in counts.items():
        out.append(
            PersistenceBucketFeatures(
                host=host,
                bucket_start=b,
                persistence_events_per_host=int(c),
                unique_persistence_artifacts=len(artifacts[(host, b)]),
            )
        )

    out.sort(key=lambda r: (r.host, r.bucket_start))
    return out


def compute_growth_hits(
    per_bucket: List[PersistenceBucketFeatures],
    sustained_buckets: int = 3,
) -> Dict[Tuple[str, int], int]:
    """
    Rolling count of growth events (event count increasing vs previous bucket) per host.
    Returns:
      (host, bucket_start) -> growth_hits over last N buckets.
    """
    if sustained_buckets <= 0:
        raise ValueError("sustained_buckets must be > 0")

    by_host: Dict[str, List[PersistenceBucketFeatures]] = {}
    for r in per_bucket:
        by_host.setdefault(r.host, []).append(r)

    growth_hits: Dict[Tuple[str, int], int] = {}

    for host, rows in by_host.items():
        rows.sort(key=lambda r: r.bucket_start)
        flags: List[int] = []
        prev: Optional[int] = None

        for r in rows:
            if prev is None:
                flag = 0
            else:
                flag = 1 if r.persistence_events_per_host > prev else 0

            flags.append(flag)
            prev = r.persistence_events_per_host

            window = flags[-sustained_buckets:]
            growth_hits[(host, r.bucket_start)] = int(sum(window))

    return growth_hits


if __name__ == "__main__":
    # Tiny self-test
    base = 1700000000
    events = [
        {"_time": base + 10, "host": "h1", "EventCode": 4698, "TaskName": "A"},
        {"_time": base + 20, "host": "h1", "EventCode": 7045, "ServiceName": "S1"},
        {"_time": base + 3600 + 10, "host": "h1", "EventCode": 7045, "ServiceName": "S2"},
        {"_time": base + 7200 + 10, "host": "h1", "EventCode": 4698, "TaskName": "B"},
        {"_time": base + 7200 + 20, "host": "h1", "EventCode": 7045, "ServiceName": "S3"},
    ]
    feats = extract_persistence_bucket_features(events, bucket_seconds=3600)
    hits = compute_growth_hits(feats, sustained_buckets=3)
    for f in feats:
        print(f, "growth_hits=", hits[(f.host, f.bucket_start)])
