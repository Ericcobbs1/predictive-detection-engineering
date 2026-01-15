# Vision: Predictive Detection Engineering

## Working definitions

**Reactive detection**
- Alerts on known-bad indicators, signatures, or confirmed suspicious events.

**Predictive-adjacent detection**
- Uses aggregations over time, thresholds, rarity, or correlations that hint at escalation, but still mostly reacts to what already happened.

**Predictive detection**
- Uses leading indicators to estimate likelihood of a future event (or a trend crossing a boundary), then alerts when predicted risk exceeds a defined threshold within a defined horizon.

## Core principles
- Explainable: outputs are interpretable (forecast, score, trajectory).
- Testable: backtesting and measurable performance are required.
- Operational: includes tuning knobs, triage steps, and suppression guidance.
- Versioned: predictive logic is a versioned artifact, not ad-hoc reasoning.

## Where AI fits
AI is used to accelerate:
- query authoring assistance
- feature brainstorming
- documentation and runbooks
- normalization and mapping (CIM/ECS-like abstractions)

AI is not used as the final decision-maker for alerting.
