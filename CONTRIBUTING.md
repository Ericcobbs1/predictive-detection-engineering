# Contributing to Predictive Detection Engineering

Thank you for your interest in contributing. This repository focuses on **predictive detection engineering**: detections that move beyond static indicators and toward behavior, baselines, trajectories, and early warning signals.

This document defines **mandatory standards** for all contributions. Pull requests that do not meet these standards will not be merged.

---

## Repository philosophy

This repository prioritizes:

- Explainable detections over black-box alerts
- Behavioral and temporal signals over static IOCs
- Predictive readiness and maturity over sheer rule count
- Schema validation and governance over ad-hoc queries

AI may assist with authoring or analysis, but **AI-generated detections must still meet all standards below**.

---

## Detection structure (required)

All detections **must**:

- Be written in YAML
- Validate against `schemas/detection.schema.json`
- Pass `tools/validate_detections.py`
- Include governance mappings (MITRE, NIST, PCI, Kill Chain)

Detections live under:

detections/
splunk/
reactive/
predictive_adjacent/
predictive/


---

## Detection ID conventions (mandatory)

Detection IDs must follow this format:

PDE-SPL-XXXX


Where:

| Range | Meaning |
|------|--------|
| 0001–0099 | Baseline reactive detections |
| 0100–0199 | Predictive-adjacent detections |
| 0200–0299 | Predictive detections |
| 0300–0399 | Sigma-derived conversions |
| 0400+ | Reserved for future sources |

IDs are **never reused**.

---

## Versioning rules

Semantic versioning is required:

- `0.1.x` → tuning, allowlists, threshold changes
- `0.x.0` → logic or feature changes
- `1.0.0` → production-ready detection

Version bumps are required whenever detection behavior changes.

---

## Detection type vs predictive readiness

These fields serve different purposes and **must not be conflated**:

- `detection_type`
  - `reactive`
  - `predictive_adjacent`
  - `predictive`

- `predictive_readiness`
  - `reactive_only`
  - `predictive_adjacent`
  - `predictive_ready`

Valid example:

```yaml
detection_type: predictive_adjacent
predictive_readiness: predictive_ready


Required detection fields

Every detection must include:

id

name

version

status

description

detection_type

predictive_readiness

severity

log_source

data_sources

query

false_positives

triage

tuning

mappings

references

tags

Predictive detections must also include:

features

prediction

explainable alert logic

Each detection must include the full mappings block:

MITRE ATT&CK (tactics + techniques)

Cyber Kill Chain

NIST CSF + NIST 800-53

PCI DSS

Operational detections (for example, capacity forecasting) may leave ATT&CK arrays empty:

mitre_attack:
  tactics: []
  techniques: []
