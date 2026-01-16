# JR Analyst Implementation SOP (Splunk Starter Pack)

## Purpose
This SOP enables a junior analyst to implement the Splunk starter-pack detections as Saved Searches/Alerts with consistent scheduling, throttling, and basic tuning.

## What you are deploying
Detections live here:
- `detections/splunk/reactive/` (PDE-SPL-0001 to 0005)
- `detections/splunk/predictive_adjacent/` (PDE-SPL-0101 to 0105)
- `detections/splunk/predictive/` (PDE-SPL-0201 to 0203)

Each file contains:
- SPL query
- alert condition (results > 0)
- tuning knobs
- triage steps
- governance mappings (MITRE, NIST, PCI, Kill Chain)

---

## Step 0: Confirm required data exists (do this first)
You must know your indexes/sourcetypes.

Run these quick checks and confirm you get events:

### Windows auth
`index=<win_index> (EventCode=4624 OR EventCode=4625) | head 5`

### Sysmon process creation
`index=<sysmon_index> sourcetype=Sysmon:Operational EventCode=1 | head 5`

### Windows scheduled task creation
`index=<win_index> EventCode=4698 | head 5`

### Windows service installation
`index=<win_index> (sourcetype=WinEventLog:System OR sourcetype=XmlWinEventLog:System) EventCode=7045 | head 5`

### DNS (if applicable)
`index=<dns_index> sourcetype=*dns* | head 5`

### AWS CloudTrail (if applicable)
`index=<cloud_index> sourcetype=aws:cloudtrail | head 5`

---

## Step 1: Create Saved Search for a detection
For each detection YAML file:
1. Open the YAML in VS Code
2. Copy the SPL under:
   - `query:`
   - `language: spl`
   - `text: |`
3. Paste into Splunk Search and run.
4. If it returns “no results,” widen the time picker to “Last 7 days” and re-run.
5. Save:
   - **Save As → Report**
   - Name format: `PDE-SPL-XXXX - <Detection Name>`

---

## Step 2: Convert to Alert
From the saved report:
1. **Edit → Edit Alert**
2. Trigger condition:
   - **Number of results > 0**

### Scheduling defaults (use these)
**Reactive (0001–0005)**
- Schedule: Every **5 minutes**
- Time range: **Last 5 minutes**

**Predictive-adjacent (0101–0105)**
- Schedule: Every **10 minutes**
- Time range: **Last 60 minutes**

**Predictive (0201–0203)**
- PDE-SPL-0201 (license forecast)
  - Schedule: **Daily** (or every 6 hours)
  - Time range: **Last 30 days**
- PDE-SPL-0202 (auth failure forecast)
  - Schedule: Every **10 minutes**
  - Time range: **Last 6 hours**
- PDE-SPL-0203 (risk trajectory)
  - Schedule: Every **10 minutes**
  - Time range: **Last 2 hours**

---

## Step 3: Throttling (required to prevent alert storms)
Enable throttling for all alerts.

Use the throttle field by detection type:
- Endpoint/process detections: `host`
- Auth detections: `user`
- DNS: `host`
- Cloud API: `principal`
- License forecast: no throttle needed (runs daily), but you may throttle on "first_exceed_time"

Throttle windows:
- Reactive: **30 minutes**
- Predictive-adjacent: **30 minutes**
- Predictive: **60 minutes** (except 0201)

---

## Step 4: Permissions (safe defaults)
- Start with: **App** sharing, not Global
- Only make Global after tuning and approval

---

## Step 5: Tuning loop (must do after deployment)
For each alert over 7 days:
1. Record alert volume/day
2. List top triggering entities (host/user/principal)
3. Add allowlists or threshold adjustments (use YAML tuning knobs)
4. Update the detection YAML in Git and bump version:
   - 0.1.0 → 0.1.1 for thresholds/allowlists
   - 0.1.x → 0.2.0 for structural query changes

---

## Step 6: Escalation and triage
Use the `triage.steps` in each detection YAML as the analyst runbook.
If a detection triggers repeatedly, treat it as:
- tuning required OR
- an incident requiring containment and deeper investigation
