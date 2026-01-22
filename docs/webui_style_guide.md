# WebUI Style Guide (Hybrid + Light/Dark/System)

This document defines the visual and interaction standards for the Predictive Detection Control Plane WebUI.
The goal is a modern, durable UI that feels like an engineering console while remaining analyst-friendly.

This is not a dashboard UI. It is a control plane UI.

---

## 1) Product Vibe: Hybrid

Hybrid means:
- Engineer-first workflows (tuning, deploy, governance)
- Analyst-friendly reading experience (signals, explainability)
- Clean, calm, minimal, and scalable to ~100+ detections

Avoid “cyber neon” aesthetics, heavy gradients, and widget grids.

---

## 2) Theme Requirements: Light / Dark / System

The UI must support:
- Light mode
- Dark mode
- System preference (default)

Behavior:
- Save user preference locally (persist across sessions)
- Apply theme before first paint to avoid flashing the wrong theme
- Theme controlled via tokens (CSS variables), not separate style sheets

Default:
- System

---

## 3) Layout Principles

### 3.1 App layout (control plane pattern)
Use a three-region layout:
- Left sidebar navigation (primary)
- Main content (lists, editors, previews)
- Right-side inspector panel (details, explainability, metadata)

Avoid “dashboard tiles” and multi-chart grids.

### 3.2 Progressive disclosure
Default views show essentials only.
Details appear in:
- right-side inspector panel
- expandable sections
- secondary pages only when necessary

---

## 4) Typography and Spacing

### 4.1 Typography
- Prefer modern sans-serif (Inter or system UI stack)
- Clear hierarchy:
  - Page title
  - Section heading
  - Table/list content
  - Metadata labels

Rules:
- Don’t bold everything
- Use font weight for hierarchy, not decoration
- Use readable line height (no cramped text)

### 4.2 Spacing
- Spacious enough for readability
- Avoid dense “SIEM table” look
- Consistent spacing scale across the app

---

## 5) Color System (Token-Based)

### 5.1 Neutral-first
The UI should be neutral by default.
Color is used only for meaning:
- risk
- confidence
- time horizon
- status

No decorative rainbow palettes.

### 5.2 Semantic color usage
Use semantic meaning consistently:

**Risk**
- low: subtle neutral or cool tone
- medium: amber
- high: restrained red (not bright)

**Confidence**
- Use opacity/intensity or labels
- Do not confuse confidence with risk

**Time horizon**
- early / emerging / imminent should be distinguishable, but not loud

**Status**
- enabled/disabled, healthy/degraded

### 5.3 Charts
- Charts exist to explain a decision, not decorate a page
- Use charts sparingly
- Prefer small inline charts (sparklines) over large dashboards

---

## 6) Components and Interaction Standards

### 6.1 Tables and Lists (primary UI primitive)
Tables must support:
- sorting
- filtering
- quick search
- column toggles (optional)
- row click → opens inspector panel

Lists must support:
- grouping by family
- tags (small pills)
- status indicators

### 6.2 Inspector Panel (right side)
Used for:
- detection detail summary
- tunables preview
- explainability narrative
- evidence bullets
- “open in Splunk” link

### 6.3 Buttons
- Primary action: one per view (e.g., Deploy)
- Secondary actions: subtle (Preview, Save tuning profile)
- Destructive actions: require confirmation (Disable, Rollback)

### 6.4 Forms
- Labels above inputs
- Inline validation
- Defaults visible
- “Reset to defaults” always available on tuning screens

### 6.5 Modals
Minimize modal usage.
Prefer inspector panel and inline expansions.

---

## 7) Key Screen Visual Rules

### 7.1 Detections catalog
- Group by family
- Show status pills + version
- Favor text clarity over visual noise

### 7.2 Tuning workspace
This is the flagship.
- Sliders with numeric input
- Before/after preview comparison
- “Would have fired” counts and distribution
- Save profile and promote to deployment

### 7.3 Signals view
Not an alert queue.
- Scannable list
- Clear explanation snippet
- Easy pivot back to tuning and Splunk

---

## 8) Accessibility and Usability (Non-negotiable)
- Contrast meets accessibility guidelines in both themes
- Keyboard navigation works for critical flows (tables, forms)
- Visible focus states
- Clear empty states (“No signals in this window”)
- Friendly error states (“API unreachable” with retry)

---

## 9) Branding Guidance
Branding should be subtle:
- Simple logo
- Minimal accent color
- No heavy gradients
- No “matrix” visuals

This UI should feel trustworthy to enterprise buyers.

---

## 10) Implementation Notes (for future build)
- React recommended
- Use a modern component approach (lightweight and token-based)
- Theme tokens (CSS variables) enable portability across hosting

This style guide is the source of truth for UI implementation.
