# WebUI Requirements — Predictive Detection Control Plane (Hybrid UI)

This document defines the functional requirements for the Predictive Detection Control Plane WebUI.
It is built directly from:
- `docs/detection_roadmap.md` (12 families / ~100 detections)
- `docs/detection_intake_template.md` (intake guardrails)
- `docs/p2/phase2_predictive_detections.md` (implemented baseline)
- `docs/webui_style_guide.md` (hybrid look & feel + light/dark/system)

The WebUI is a control plane, not a SIEM replacement.

---

## 1) Goals

### Primary goals
1. Provide a modern, durable UI that supports predictive detection operations at scale (100+ detections).
2. Enable tuning and preview workflows before deployment into Splunk (Splunk-first integration).
3. Provide explainability and baseline transparency to build analyst trust.
4. Provide governance controls (allowlists, maintenance windows) to reduce noise without killing sensitivity.
5. Provide deployment packaging, promotion, and rollback.

### Non-goals
- Replace Splunk dashboards or raw log search.
- Become an incident response console.
- Duplicate Splunk ES alert queue behavior.

---

## 2) Target Users and Primary Workflows

### Roles
- Detection Engineer (primary)
- SOC Analyst (secondary)
- Security Manager (secondary)

### Core workflows
- Browse detections by family → open details → tune → preview → deploy
- Review predictive signals → understand why → pivot to Splunk → tune/suppress if noisy
- Manage allowlists and maintenance windows
- Track changes (audit), versions, and deployments across environments

---

## 3) Theme and Visual Requirements

The WebUI must follow `docs/webui_style_guide.md`:
- Hybrid control-plane look
- Left nav + main content + right-side inspector panel
- Light / Dark / System theme support
- Token-based theming (CSS variables), no “dashboard tile” UI

Theme behavior:
- User can select Light / Dark / System
- Preference persists across sessions
- Theme applied before first paint to avoid flash

---

## 4) Information Architecture (Navigation)

Top-level navigation:
1. Detections
2. Tuning
3. Baselines
4. Signals
5. Deployments
6. Governance
7. Settings
8. Audit

---

## 5) Screen Requirements

### 5.1 Detections (Catalog)
Purpose: Organize detections by family and status (planned vs implemented).

Must support:
- Group by family (12 families)
- Filter by:
  - implemented/planned
  - readiness (p2 / p2.2 hardened)
  - model type (drift / novelty / trajectory / composite)
  - entity type (host/user/src_ip)
  - data source availability
- Search by ID/name/tags

Table columns (minimum):
- ID
- Name
- Family
- Status (implemented/planned)
- Readiness (p2/p2.2)
- Entity
- Last updated (version)
- Enabled/disabled (per environment)

Actions:
- Open details (right inspector or details page)
- Open tuning workspace
- Add to deployment package
- Clone as variant (tier/environment/entity)

---

### 5.2 Detection Details
Purpose: Single source of truth for a detection.

Tabs/sections:
1. Overview
   - intent (plain language)
   - family
   - model type
   - entities and scope
   - data sources
2. Tunables
   - defaults and allowed ranges
   - current environment overrides
3. Preview
   - run preview evaluation (see Tuning)
   - show “would have fired” summary
4. Explainability
   - template preview
   - evidence requirements
5. Mappings
   - ATT&CK / NIST / PCI
6. Tests (optional UI)
   - last pass/fail status and timestamp
7. Changelog
   - versions + changes

---

### 5.3 Tuning Workspace (Flagship)
Purpose: Tune predictive detections before deployment.

Inputs:
- Detection selection (or open from Details)
- Environment selector (e.g., dev/test/prod)
- Time window selector (24h/72h/7d/custom)
- Scope selector:
  - by entity group (server/workstation/jump host)
  - by Splunk index/sourcetype (if configured)
  - by allowlist exclusions toggle

Controls (tunables):
- drift ratio threshold
- sustained buckets
- novelty threshold (where applicable)
- min unique artifacts/users/tools
- large file bytes (where applicable)
- sensitivity preset: Conservative / Balanced / Aggressive

Outputs:
- Would-have-fired count (entities)
- Risk distribution
- Confidence distribution
- Top entities by risk
- Most common evidence patterns
- Example signal detail (inspector panel)

Actions:
- Save tuning profile (per environment)
- Reset to defaults
- Compare profiles (before/after)
- Promote tuning to deployment package

---

### 5.4 Baselines
Purpose: Trust and transparency in predictive models.

Must show:
- baseline window and bucket size
- baseline completeness score
- baseline freshness (last updated)
- baseline values (avg, std) per entity (sampled or pageable)
- novelty baseline set size (Phase 2.2+)

Actions:
- rebuild baseline (manual trigger)
- export baseline summary
- flag unstable baselines (variance too high)

---

### 5.5 Signals
Purpose: Review predictive signals (not a SIEM alert queue).

List view must show:
- time
- detection ID + name
- entity
- risk score
- confidence
- time horizon (early/emerging/imminent)
- short explanation snippet

Signal detail (inspector panel):
- narrative explanation
- evidence bullets
- baseline vs current summary
- recommended next steps
- “Open in Splunk” link (deep link)

Actions:
- mark expected / suppress candidate
- open tuning for this detection
- add entity to allowlist (with reason)
- promote to incident (optional integration hook)

---

### 5.6 Deployments (Splunk-first)
Purpose: Promote tuned detections into Splunk.

Deployment modes:
- SPL-native deployment (saved searches/macros)
- API-backed deployment (Splunk builds buckets → API scores → Splunk stores signals)

Must support:
- deployment packages (group detections)
- environment targeting
- dry run validation
- deploy + rollback
- deployment history and status

---

### 5.7 Governance
Purpose: Reduce noise while preserving sensitivity.

Must support:
- allowlists:
  - hosts
  - tools
  - service accounts
  - src_ip ranges
- maintenance windows:
  - recurring
  - one-off
- suppression rules:
  - by family
  - by entity role

Actions:
- add/remove allowlist entries
- import/export allowlists
- apply allowlists to preview and deployments
- audit who changed what

---

### 5.8 Settings
Purpose: Configure integrations.

Must include:
- API base URL (if WebUI is separate from API host)
- Splunk connection settings (Hec/search endpoints or app-based integration)
- Field mapping / normalization (optional)
- Default tuning presets

---

### 5.9 Audit
Purpose: Change tracking and compliance.

Audit events:
- tuning profile changes
- deployment actions
- allowlist changes
- detection enable/disable
- version changes

Must include:
- actor
- timestamp
- object changed
- previous vs new value

---

## 6) Integration Requirements

### 6.1 API integration
WebUI must call API endpoints for:
- preview evaluation
- returning signals with risk/confidence/horizon
- explainability payloads

API failures must be handled gracefully:
- show “API unreachable” state
- retry
- do not crash UI

### 6.2 Splunk integration (first SIEM)
WebUI must support Splunk-first deployment workflows:
- preview based on Splunk-sourced buckets (or file upload in dev)
- deploy as saved searches/macros or API-backed scheduled jobs
- deep links to Splunk for pivoting

---

## 7) Data Contracts (MVP)
The UI and API must standardize on:
- baseline buckets payload
- observation buckets payload
- response with:
  - count
  - signals list
  - per-signal evidence fields
  - explainability fields

Signals must include at minimum:
- detection_id
- entity_type + entity_id
- risk_score
- confidence
- time_horizon
- summary evidence fields

---

## 8) Acceptance Criteria (MVP)
The WebUI MVP is complete when:
1. Detections catalog supports grouping and filtering across families.
2. Tuning workspace can preview and tune at least 5 implemented detections (0401–0405).
3. Signals list shows scored results with explainability and Splunk pivots.
4. Deployments screen supports packaging and deployment tracking (SPL-native mode minimum).
5. Governance supports allowlists and maintenance windows.
6. Light/Dark/System theme works without flicker and persists preference.

---

## 9) Future Enhancements (Phase 2.2+)
- True novelty visualization (baseline set growth + novelty trends)
- Composite detection builder UI
- Role-based access controls
- Multi-tenant support (if SaaS)
- Detection marketplace/import tooling

