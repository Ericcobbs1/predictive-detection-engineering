# Predictive Readiness Classifier Rules

## Purpose
Assign a deterministic "predictive readiness" label to detections ingested from public sources (Sigma, Sentinel, Elastic, Chronicle, Panther, etc.). This helps prioritize which detections are best candidates for conversion into Splunk-first predictive detections.

## Output labels
- reactive_only
- predictive_adjacent
- predictive_ready

## Design principles
- Deterministic and explainable: scoring must be traceable.
- Source-agnostic: works across Sigma/KQL/EQL/YARA-L/Python.
- Splunk-aligned: scoring signals map cleanly to SPL patterns and feature engineering concepts.
- Conservative by default: "predictive_ready" requires strong leading-indicator evidence.

---

## Scoring model

### Total score → label
- 0–3  → reactive_only
- 4–7  → predictive_adjacent
- 8+   → predictive_ready

### Strong signals (high weight)
These strongly indicate the detection can be turned into a score/forecast/trajectory.

1) Ordered sequence / progression logic (+4)
Examples:
- EQL sequences
- multi-stage correlation where order matters
- Chronicle-style multi-event logic implying progression

Splunk mapping:
- transaction / stats by session keys
- streamstats ordering / state machines
- event sequence joins across time

2) Baseline / anomaly framing (+4)
Examples:
- explicit baseline / anomaly / ML job outputs
- dynamic thresholds derived from history

Splunk mapping:
- `predict`
- `anomalydetection`
- `streamstats` baselines (rolling mean/stddev)
- `eventstats` historical comparisons

---

## Medium signals (moderate weight)
3) Time-window aggregation (+2)
Examples:
- counts over X minutes/hours/days
- thresholding on windowed rates

Splunk mapping:
- `timechart`, `bin _time`
- `stats count by _time`
- `where count > N`

4) Distinct count / novelty / rare entity logic (+3)
Examples:
- "new user", "new host", "rare parent process"
- `dc(field)`/rarity approaches

Splunk mapping:
- `dc(user)`, `rare`, `stats count by field`
- lookup-based first_seen / last_seen
- "new entity" patterns

5) Multi-signal correlation across sources (+3)
Examples:
- authentication + endpoint + network correlation
- cloud audit + IAM + network correlation

Splunk mapping:
- `join`, `stats` across sourcetypes
- `tstats` across CIM models
- correlation search patterns

---

## Light signals (lower weight)
6) Risk scoring / weighted logic (+3)
Examples:
- explicit risk objects / weights / RBA concepts

Splunk mapping:
- Risk-based alerting style (risk_score, risk_object)
- accumulating score across detections

7) Repeated behavior / escalation language (+2)
Examples:
- brute force patterns
- repeated failures then success
- "increase", "spike", "surge" logic

Splunk mapping:
- `streamstats` rate-of-change
- slope/acceleration style measures
- success-after-fail sequences

8) Static IOC match only (+0)
Examples:
- hash/domain/IP match with no temporal logic

Splunk mapping:
- exact match lookups with no behavioral context

---

## Guardrails (label downgrades)
These reduce over-labeling.

- If detectio
