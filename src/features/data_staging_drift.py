from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class StagingBucketFeatures:
    """
    Feature record for a single entity (host) in a single time bucket.
    """
    host: str
    bucket_start: int  # epoch seconds aligned to bucket boundary
    staging_events_per_host: int
    unique_staging_artifacts: int

    # Computed later (needs multiple buckets / baseline)
    sustained_staging_growth: Optional[bool] = None
    staging_drift_ratio: Optional[float] = None


def bucket_epoch(ts: int, bucket_seconds: int) -> int:
    if bucket_seconds <= 0:
        raise ValueError("bucket_seconds must be > 0")
    return (ts // bucket_seconds) * bucket_seconds


def _is_staging_event(
    event: Dict,
    *,
    process_field: str,
    file_name_field: str,
    file_size_field: str,
    large_file_bytes: int,
    tool_keywords: Tuple[str, ...],
    archive_exts: Tuple[str, ...],
) -> bool:
    proc = str(event.get(process_field, "")).lower()
    fname = str(event.get(file_name_field, "")).lower()
    size_raw = event.get(file_size_field)

    if proc:
        for k in tool_keywords:
            if k in proc:
                return True

    if fname:
        for ext in archive_exts:
            if fname.endswith(ext):
                return True

    if size_raw is not None:
        try:
            size = int(size_raw)
            if size >= large_file_bytes:
                return True
        except Exception:
            pass

    return False


def extract_data_staging_bucket_features(
    events: Iterable[Dict],
    bucket_seconds: int = 3600,
    time_field: str = "_time",
    host_field: str = "host",
    process_field: str = "process_name",
    file_name_field: str = "file_name",
    file_path_field: str = "file_path",
    file_size_field: str = "file_size",
    large_file_bytes: int = 100_000_000,
    tool_keywords: Tuple[str, ...] = ("7z", "7za", "rar", "winzip", "zip", "tar", "gzip"),
    archive_exts: Tuple[str, ...] = (".zip", ".7z", ".rar", ".tar", ".gz"),
) -> List[StagingBucketFeatures]:
    counts: Dict[Tuple[str, int], int] = {}
    artifacts: Dict[Tuple[str, int], Set[str]] = {}

    for e in events:
        ts_raw = e.get(time_field)
        host = str(e.get(host_field, "")).strip()

        if ts_raw is None or not host:
            continue

        try:
            ts = int(ts_raw)
        except Exception:
            continue

        if not _is_staging_event(
            e,
            process_field=process_field,
            file_name_field=file_name_field,
            file_size_field=file_size_field,
            large_file_bytes=large_file_bytes,
            tool_keywords=tool_keywords,
            archive_exts=archive_exts,
        ):
            continue

        b = bucket_epoch(ts, bucket_seconds)
        key = (host, b)

        if key not in counts:
            counts[key] = 0
            artifacts[key] = set()

        counts[key] += 1

        artifact = (
            str(e.get(file_path_field) or "").strip()
            or str(e.get(file_name_field) or "").strip()
            or str(e.get(process_field) or "").strip()
            or "unknown_artifact"
        )
        artifacts[key].add(artifact)

    out: List[StagingBucketFeatures] = []
    for (host, b), c in counts.items():
        out.append(
            StagingBucketFeatures(
                host=host,
                bucket_start=b,
                staging_events_per_host=int(c),
                unique_staging_artifacts=len(artifacts[(host, b)]),
            )
        )

    out.sort(key=lambda r: (r.host, r.bucket_start))
    return out


def compute_growth_hits(
    per_bucket: List[StagingBucketFeatures],
    sustained_buckets: int = 3,
) -> Dict[Tuple[str, int], int]:
    if sustained_buckets <= 0:
        raise ValueError("sustained_buckets must be > 0")

    by_host: Dict[str, List[StagingBucketFeatures]] = {}
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
                flag = 1 if r.staging_events_per_host > prev else 0

            flags.append(flag)
            prev = r.staging_events_per_host

            window = flags[-sustained_buckets:]
            growth_hits[(host, r.bucket_start)] = int(sum(window))

    return growth_hits


if __name__ == "__main__":
    base = 1700000000
    events = [
        {"_time": base + 10, "host": "h1", "process_name": "7z.exe", "file_name": "a.zip", "file_size": 123},
        {"_time": base + 20, "host": "h1", "file_name": "b.7z", "file_size": 456},
        {"_time": base + 3600 + 10, "host": "h1", "file_name": "c.txt", "file_size": 200_000_000},
    ]
    feats = extract_data_staging_bucket_features(events, bucket_seconds=3600)
    hits = compute_growth_hits(feats, sustained_buckets=3)
    for f in feats:
        print(f, "growth_hits=", hits[(f.host, f.bucket_start)])
