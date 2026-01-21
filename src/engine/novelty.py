from __future__ import annotations

from typing import Dict, Set, Tuple


def compute_true_novelty_count(
    *,
    current_set: Set[str],
    baseline_set: Set[str],
) -> int:
    """
    True novelty = |current_set - baseline_set|
    """
    if not current_set:
        return 0
    if not baseline_set:
        return len(current_set)
    return len(current_set.difference(baseline_set))


def build_baseline_set_by_host(
    baseline_dest_sets: Dict[Tuple[str, int], Set[str]],
) -> Dict[str, Set[str]]:
    """
    Build a baseline destination set per host by unioning all baseline bucket sets.
    Input: (host, bucket_start) -> set(dest_ip)
    Output: host -> union(set(dest_ip))
    """
    out: Dict[str, Set[str]] = {}
    for (host, _bucket), dests in baseline_dest_sets.items():
        if host not in out:
            out[host] = set()
        out[host].update(dests)
    return out
