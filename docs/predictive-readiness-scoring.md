# Predictive Readiness Scoring

This repository tags every detection with a “predictive readiness” label to guide conversion work.

## Labels
- reactive_only (no useful time-series / leading indicator value)
- predictive_adjacent (has time-window aggregation, rarity, correlation, or rate-based logic)
- predictive_ready (has clear leading indicators and can produce a forecast/score/trajectory)

## Heuristics
A detection is usually predictive_adjacent if it includes:
- counts over time windows
- distinct counts (new entities, rare events)
- thresholds with sliding windows
- correlations across sources within a time window

A detection is often predictive_ready if it includes:
- sequences (ordered event logic)
- multi-stage kill chain behaviors
- repeated precursor activity with escalation patterns
- anomaly / baseline references (even implicit)
- risk scoring or weighted signals

## Output
We store the label as:
- predictive_readiness: reactive_only | predictive_adjacent | predictive_ready
