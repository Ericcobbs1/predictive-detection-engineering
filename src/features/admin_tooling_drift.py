from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class AdminToolingBucketFeatures:
    """
    Feature record for a single entity (host) in a single time bucket.
    """
    host: str
    bucket_start: int  # epoch seconds aligned to bucket boundary
    admin_tool_events_per_host: int
    unique_admin_tools: int

    # Computed later (needs multiple buckets / baseline)
    sustained_admin_tool_growth: Optional[bool] = None
    admin_tool_drift_ratio: Optional[float] = None


def bucket_epoch(ts: int, bucket_seconds: int) -> int:
    if bucket_seconds <= 0:
        raise ValueError("bucket_seconds must be > 0")
    return (ts // bucket_seconds) * bucket_seconds


def _classify_tool(process_name: str, command_line: str = "") -> Optional[str]:
    """
    MVP tool classifier based on process/command indicators.
    Tune this list to your environment as you onboard sources.

    Returns a normalized tool name or None if not considered admin tooling.
    """
    p = (process_name or "").lower()
    c = (command_line or "").lower()

    # PsExec variants
    if "psexec" in p or "paexec" in p or "psexec" in c or "paexec" in c:
        return "psexec"

    # WMI / WMIC
    if "wmic" in p or "wmiprvse" in p or "wmic" in c:
        return "wmi"

    # WinRM / WinRS
    if "winrm" in p or "winrs" in p or "winrm" in c or "winrs" in c:
        return "winrm"

    # schtasks and sc.exe are common LoLBins used for remote exec/persistence
    if "schtasks" in p or "schtasks" in c:
        return "schtasks"

    if p.endswith("sc.exe") or " sc " in f" {c} " or "\\sc.exe" in c:
        return "sc"

    # PowerShell often noisy; keep in scope but can be refined later
    if p.endswith("powershell.exe") or "powershell" in c:
        return "powershell"

    return None


def extract_admin_tooling_bucket_features(
    events: Iterable[Dict],
    bucket_seconds: int = 3600,  # 1h default
    time_field: str = "_time",
    host_field: str = "host",
    process_field: str = "process_name",
    cmd_field: str = "command_line",
) -> List[AdminToolingBucketFeatures]:
    """
    MVP feature extraction for suspicious admin tooling drift (PDE-SPL-0405).

    Expected normalized event fields:
      - _time (epoch seconds)
      - host
      - process_name (string)
      - command_line (optional)

    Computes per host per bucket:
      - admin_tool_events_per_host: count of classified tool executions
      - unique_admin_tools: distinct tools observed
    """
    counts: Dict[Tuple[str, int], int] = {}
    tools: Dict[Tuple[str, int], Set[str]] = {}

    for e in events:
        ts_raw = e.get(time_field)
        host = str(e.get(host_field, "")).strip()

        if ts_raw is None or not host:
            continue

        try:
            ts = int(ts_raw)
        except Exception:
            continue

        proc = str(e.get(process_field, "") or "").strip()
        cmd = str(e.get(cmd_field, "") or "").strip()

        tool = _classify_tool(proc, cmd)
        if tool is None:
            continue

        b = bucket_epoch(ts, bucket_seconds)
        key = (host, b)

        if key not in counts:
            counts[key] = 0
            tools[key] = set()

        counts[key] += 1
        tools[key].add(tool)

    out: List[AdminToolingBucketFeatures] = []
    for (host, b), c in counts.items():
        out.append(
            AdminToolingBucketFeatures(
                host=host,
                bucket_start=b,
                admin_tool_events_per_host=int(c),
                unique_admin_tools=len(tools[(host, b)]),
            )
        )

    out.sort(key=lambda r: (r.host, r.bucket_start))
    return out


def compute_growth_hits(
    per_bucket: List[AdminToolingBucketFeatures],
    sustained_buckets: int = 3,
) -> Dict[Tuple[str, int], int]:
    """
    Rolling count of growth events (tool event count increasing vs previous bucket) per host.
    Returns:
      (host, bucket_start) -> growth_hits over last N buckets.
    """
    if sustained_buckets <= 0:
        raise ValueError("sustained_buckets must be > 0")

    by_host: Dict[str, List[AdminToolingBucketFeatures]] = {}
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
                flag = 1 if r.admin_tool_events_per_host > prev else 0

            flags.append(flag)
            prev = r.admin_tool_events_per_host

            window = flags[-sustained_buckets:]
            growth_hits[(host, r.bucket_start)] = int(sum(window))

    return growth_hits


if __name__ == "__main__":
    base = 1700000000
    events = [
        {"_time": base + 10, "host": "h1", "process_name": "psexec.exe", "command_line": "psexec \\\\10.0.0.5 cmd"},
        {"_time": base + 20, "host": "h1", "process_name": "wmic.exe", "command_line": "wmic /node:10.0.0.6 process call create"},
        {"_time": base + 3600 + 10, "host": "h1", "process_name": "winrm.cmd", "command_line": "winrm quickconfig"},
        {"_time": base + 7200 + 10, "host": "h1", "process_name": "powershell.exe", "command_line": "powershell -enc AAAA"},
    ]
    feats = extract_admin_tooling_bucket_features(events, bucket_seconds=3600)
    hits = compute_growth_hits(feats, sustained_buckets=3)
    for f in feats:
        print(f, "growth_hits=", hits[(f.host, f.bucket_start)])
