# Splunk Deployment Guide (Starter Pack)

## Purpose
This guide shows how to deploy the starter-pack detections as Saved Searches/Alerts in Splunk using SPL from the detection YAML files.

## Prerequisites
- You have Splunk search access to the required data sources (Windows logs, Sysmon, DNS, CloudTrail, etc.).
- You know or can confirm the correct indexes/sourcetypes in your environment.
- Optional but recommended: CIM normalization for endpoint/authentication/network data.

---

## Step 1: Identify data availability
For each detection, confirm:
- index
- sourcetype(s)
- key fields (host, user, Image, CommandLine, src_ip)

### Quick checks
- Windows auth:
  - Search: `index=<win_index> (EventCode=4624 OR EventCode=4625) | head 5`
- Sysmon:
  - Search: `index=<sysmon_index> sourcetype=Sysmon:Operational EventCode=1 | head 5`
- DNS:
  - Search: `index=<dns_index> sourcetype=*dns* | head 5`
- CloudTrail:
  - Search: `index=<cloud_index> sourcetype=aws:cloudtrail | head 5`

---

## Step 2: Create a Saved Search
For each detection YAML:
1. Open the detection file under `detections/splunk/...`
2. Copy the SPL block under:
   - `query:`
   - `language: "spl"`
   - `text: |`

3. In Splunk:
   - Go to **Search & Reporting**
   - Paste the query
   - Run it
   - Confirm it returns expected fields and volumes

4. Save it:
   - Click **Save As → Report**
   - Name: use the detection id + name (example: `PDE-SPL-0001 PowerShell with EncodedCommand`)
   - Set **Permissions**:
     - Owner: your user
     - App: choose the app context you want (Search is fine for labs)
     - Sharing: start with “App” or “Global” depending on your model

---

## Step 3: Convert report to an Alert (Correlation Search style)
1. Open the saved report
2. Click **Edit → Edit Alert**
3. Configure:

### Schedule
Use these defaults unless you have a reason to change:

- Reactive detections (0001–0005):
  - Run every **5 minutes**
  - Time range: **Last 5 minutes**
- Predictive-adjacent (0101–0105):
  - Run every **10 minutes**
  - Time range: **Last 60 minutes**
- Predictive (0201–0203):
  - 0201 (license forecast): Run **daily** (or every 6h)
    - Time range: **Last 30 days** (recommended for forecast stability)
  - 0202 (auth forecast): Run every **10 minutes**
    - Time range: **Last 6 hours**
  - 0203 (risk trajectory): Run every **10 minutes**
    - Time range: **Last 2 hours**

### Trigger condition
- Most detections already filter to only “alert-worthy” results.
- Use: **Trigger alert when: Number of Results > 0**

### Throttling (noise control)
- Set throttling by a stable entity:
  - Endpoint/process detections: `host`
  - Identity detections: `user`
  - DNS: `host`
  - Cloud: `principal`
- Default throttle window:
  - **30 minutes** for reactive and predictive-adjacent
  - **60 minutes** for predictive

---

## Step 4: Alert actions (lab-friendly defaults)
Choose at least one:
- Add to Triggered Alerts
- Email (optional)
- Webhook (optional)

Recommended in labs:
- Start with “Triggered Alerts” only.
- Add email/webhook after you tune.

---

## Step 5: Tuning workflow (required)
For each detection:
1. Run it for a week (or replay sample logs)
2. Record:
   - Alert volume/day
   - Top entities triggering
   - False positives and root causes
3. Apply tuning knobs documented in the YAML:
   - allowlists
   - threshold adjustment
   - scope constraints (servers, VIP accounts)
4. Re-run and confirm the change reduces noise without losing coverage

---

## Step 6: Version control
Whenever you tune a detection:
- Update the YAML file in this repo:
  - threshold changes
  - allowlist notes
  - false positives learned
- Bump version:
  - 0.1.0 → 0.1.1 for small tuning
  - 0.1.x → 0.2.0 for structural change

Commit message example:
- `Tune PDE-SPL-0004 thresholds and add allowlist guidance`
