from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List

from src.engine.evaluator import Signal


def explain_ns_p2_001(signal: Signal) -> Dict[str, object]:
    """
    Convert a NS-P2-001 signal into an analyst-friendly explanation.

    Output includes:
      - headline
      - narrative (why it matters)
      - evidence bullets
      - recommended next steps
      - raw fields (for UI/debug)
    """
    headline = f"{signal.signal_name} on host {signal.entity_id}"

    # Keep narrative concise and consistent
    narrative = (
        f"Host behavior is drifting from historical norms. In the most recent observation bucket, "
        f"the host contacted {signal.internal_dest_count} unique internal destinations "
        f"with a baseline deviation ratio of {signal.baseline_deviation_ratio:.2f} "
        f"(relative to the host’s baseline average). This increase was sustained across "
        f"{signal.growth_hits} growth-hit buckets, which is consistent with early-stage lateral movement preparation."
        if signal.baseline_deviation_ratio is not None
        else
        f"Host behavior is drifting from historical norms. The host contacted {signal.internal_dest_count} "
        f"unique internal destinations and sustained growth across {signal.growth_hits} buckets, which can indicate "
        f"early-stage lateral movement preparation."
    )

    evidence: List[str] = [
        f"Unique internal destinations (current): {signal.internal_dest_count}",
        f"Internal connections (current): {signal.internal_conn_count}",
        f"Baseline avg unique destinations: {signal.baseline_avg_internal_dest_count if signal.baseline_avg_internal_dest_count is not None else 'unknown'}",
        f"Baseline deviation ratio: {signal.baseline_deviation_ratio if signal.baseline_deviation_ratio is not None else 'unknown'}",
        f"Sustained growth hits (rolling): {signal.growth_hits}",
        f"New internal targets (MVP proxy): {signal.new_internal_targets}",
        f"Risk score: {signal.risk_score}",
        f"Confidence: {signal.confidence:.2f}",
        f"Time horizon: {signal.time_horizon}",
    ]

    next_steps: List[str] = [
        "Validate expected activity: patching, deployment, scanning, monitoring, or backup tasks.",
        "Review the top internal destinations contacted and identify whether they are new or unusual for this host.",
        "Pivot to authentication telemetry for the same host and time window (failed logons, new logon types, remote logons).",
        "If endpoint telemetry is available, identify the process/user responsible for outbound connections.",
        "If this host is non-admin or non-management, treat as higher priority and broaden scope to adjacent hosts.",
    ]

    return {
        "headline": headline,
        "narrative": narrative,
        "evidence": evidence,
        "next_steps": next_steps,
        "raw": asdict(signal),
    }
