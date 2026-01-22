# Phase 2 Predictive Detections (Implemented)

This document summarizes the predictive detections implemented in Phase 2.
Each detection includes a validated YAML definition, feature extraction,
evaluator logic, explainability, and deterministic tests.

These detections form the core baseline used to design the WebUI, API,
and first SIEM (Splunk) integration.

---

## PDE-SPL-0401 — Emerging Lateral Movement Preparation
**Family:** Lateral Movement  
**Model:** Baseline drift + true novelty (Phase 2.2)

Detects sustained increases in internal network fan-out relative to historical
baselines, with true novelty calculated via destination set-difference.

---

## PDE-SPL-0402 — Password Spray Drift (Low-and-Slow)
**Family:** Credential Abuse  
**Model:** Drift + trajectory

Identifies distributed password spraying by tracking authentication failure
drift and breadth of targeted users over time.

---

## PDE-SPL-0403 — Persistence Mechanism Drift
**Family:** Persistence  
**Model:** Drift + artifact diversity

Detects abnormal creation of scheduled tasks, services, and persistence
mechanisms relative to host baselines.

---

## PDE-SPL-0404 — Data Staging Drift
**Family:** Data Staging & Exfil Preparation  
**Model:** Drift + trajectory

Identifies early data staging behavior through compression activity,
large file writes, and staging artifact diversity.

---

## PDE-SPL-0405 — Suspicious Admin Tooling Drift
**Family:** Administrative Tooling  
**Model:** Drift + tool diversity

Detects abnormal usage of remote administration and management tools
outside expected host baselines.

---

## Phase 2 Coverage Summary

Phase 2 provides predictive coverage for:
- Lateral movement preparation
- Credential abuse
- Persistence establishment
- Data staging and exfil preparation
- Living-off-the-land admin tooling

These detections validate the engine architecture and establish
the baseline feature set for future expansion.

---

## Phase 2.2 Enhancements

Phase 2.2 introduces hardening across detections, including:
- True novelty detection (set-diff)
- Allowlists and suppression logic
- Baseline transparency
- Standardized explainability templates

---

## Status

- All Phase 2 detections are implemented and tested
- Phase 2.2 novelty implemented for PDE-SPL-0401
- Remaining Phase 2.2 enhancements will be applied uniformly
