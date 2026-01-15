# Detection Standard

## Purpose
Provide a consistent, reviewable format for detections in this repository, including predictive detections.

## Detection types
- reactive
- predictive_adjacent
- predictive

## Required fields (minimum)
- id
- name
- version
- status (draft | experimental | production)
- description
- detection_type (reactive | predictive_adjacent | predictive)
- severity (informational | low | medium | high | critical)
- data_sources (list)
- log_source (platform + product + category)
- query (language + text)
- tags (attack tactics/techniques, domains)
- false_positives
- triage (steps)
- tuning (knobs)
- references

## Predictive-only requirements
If detection_type is `predictive`, also include:
- prediction.target
- prediction.horizon
- prediction.method
- features (list of feature definitions)
- alert_condition (how prediction output becomes an alert)
- validation (backtest window + metrics)
- drift_monitoring (what to watch, how often)

## Naming and IDs
- Use stable IDs (UUID or deterministic slug + hash).
- Names should be human-readable and action-oriented.
