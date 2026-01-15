# Sigma Ingestion Plan

## Purpose
Use SigmaHQ/sigma as a baseline public detection corpus. We will not modify upstream rules.
We will index and normalize metadata, then translate selected rules into Splunk SPL.

## Ingestion scope
- All rule directories matching `rules*` in the Sigma repo
- YAML rule files

## Outputs produced in this repo
1. inventory index (normalized metadata)
2. Splunk translations for selected rules
3. predictive readiness labels
4. conversion notes and tuning guidance

## Storage approach
- Upstream content referenced as a submodule or external mirror (build-phase decision)
- This repo stores only:
  - normalized inventory rows
  - translation outputs
  - predictive enhancements

## Splunk-first note
Predictive detections authored in this repo will be implemented in Splunk SPL first.
