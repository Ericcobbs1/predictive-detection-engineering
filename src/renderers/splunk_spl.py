from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class SplunkSPLResult:
    search: str
    notes: str


class SplunkSPLRenderer:
    """
    MVP SPL renderer for NextSigma Phase 2 detections.
    Focused on NS-P2-001 (Emerging Lateral Movement Preparation).
    """

    def render_ns_p2_001(self, detection: Dict[str, Any], params: Dict[str, Any]) -> SplunkSPLResult:
        """
        Renders SPL for NS-P2-001.

        Tunable params (with defaults):
          - index: Splunk index name (optional; user may prepend externally)
          - earliest_baseline: default '-30d@d'
          - earliest_obs: default '-72h@h'
          - bucket_span: default '1h'
          - deviation_ratio: default 2.5
          - min_new_targets: default 3
          - sustained_buckets: default 3

        Required normalized fields:
          - host
          - dest_ip (or dest_host if you map it)
          - _time
        """

        index = params.get("index")
        earliest_baseline = params.get("earliest_baseline", "-30d@d")
        earliest_obs = params.get("earliest_obs", "-72h@h")
        bucket_span = params.get("bucket_span", "1h")

        deviation_ratio = float(params.get("deviation_ratio", 2.5))
        min_new_targets = int(params.get("min_new_targets", 3))
        sustained_buckets = int(params.get("sustained_buckets", 3))

        # RFC1918 internal predicate (MVP; environment-specific refinement later)
        internal_predicate = (
            '(cidrmatch("10.0.0.0/8", dest_ip) OR '
            'cidrmatch("172.16.0.0/12", dest_ip) OR '
            'cidrmatch("192.168.0.0/16", dest_ip))'
        )

        # --- Baseline (30d) ---
        baseline = f"""
search {f"index={index}" if index else ""} earliest={earliest_baseline}
| eval is_internal=if({internal_predicate},1,0)
| where is_internal=1
| bucket _time span={bucket_span}
| stats dc(dest_ip) as internal_dest_count_baseline by host _time
| stats avg(internal_dest_count_baseline) as baseline_avg
        stdev(internal_dest_count_baseline) as baseline_std
        by host
""".strip()

        # --- Observation (72h) with sustained growth ---
        observation = f"""
search {f"index={index}" if index else ""} earliest={earliest_obs}
| eval is_internal=if({internal_predicate},1,0)
| where is_internal=1
| bucket _time span={bucket_span}
| stats dc(dest_ip) as internal_dest_count
        count as internal_conn_count
        values(dest_ip) as dests
        by host _time
| sort 0 host _time
| streamstats current=f window=2 last(internal_dest_count) as prev_count by host
| eval growth_flag=if(internal_dest_count>prev_count,1,0)
| streamstats window={sustained_buckets} sum(growth_flag) as growth_hits by host
""".strip()

        # --- Join + Evaluate ---
        spl = f"""
/* NextSigma P2: {detection.get("id")} */
/* {detection.get("title")} */
/* Baseline: 30d | Observation: 72h | Bucket: {bucket_span} */
/* Conditions: deviation_ratio>={deviation_ratio}, sustained_buckets>={sustained_buckets}, min_new_targets>={min_new_targets} */

| noop
| append [{baseline}]
| append [{observation}]
| stats latest(internal_dest_count) as internal_dest_count
        latest(internal_conn_count) as internal_conn_count
        latest(growth_hits) as growth_hits
        latest(baseline_avg) as baseline_avg
        latest(baseline_std) as baseline_std
        by host
| eval baseline_deviation_ratio=if(baseline_avg>0, internal_dest_count / baseline_avg, null())
| eval sustained_growth=if(growth_hits>={sustained_buckets}, 1, 0)

/* MVP novelty proxy: replace with true set-diff in Phase 2.2 */
| eval new_internal_targets=internal_dest_count

| where baseline_deviation_ratio>={deviation_ratio}
        AND sustained_growth=1
        AND new_internal_targets>={min_new_targets}

| eval signal_name="Emerging Lateral Movement Preparation"
| table host signal_name internal_dest_count internal_conn_count baseline_avg
        baseline_deviation_ratio growth_hits new_internal_targets
""".strip()

        notes = (
            "MVP renderer uses RFC1918 to classify internal traffic and a novelty proxy "
            "(new_internal_targets=internal_dest_count). "
            "Phase 2.2: replace proxy with true novelty via 30d dest set-diff "
            "(summary index or lookup)."
        )

        return SplunkSPLResult(search=spl, notes=notes)
