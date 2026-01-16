# Validation and Backtesting (Starter Pack)

## Purpose
Provide a repeatable way to validate each detection:
- returns expected results
- is tunable
- has stable behavior over time
- supports predictive claims (forecast/trajectory)

---

## General validation checklist (all detections)
For each detection:
1. Confirm data exists (index/sourcetype/fields).
2. Run the SPL query over an appropriate time window.
3. Confirm fields required for triage are present (host, user, command line, src_ip).
4. Measure baseline alert volume:
   - results per day
   - top triggering entities
5. Tune:
   - thresholds
   - allowlists
   - scoping (critical hosts/users)
6. Re-test after tuning.

---

## Reactive detections (0001–0005)
Goal: validate the detection fires on known suspicious patterns.

Backtest approach:
- Run the query over the last 7–30 days
- Capture:
  - count of hits by host/user
  - top command lines / task names / service paths
- Confirm FPs and add allowlists/tuning notes.

Suggested window:
- 7 days for process creation (high volume)
- 30 days for service/task creation (lower volume)

---

## Predictive-adjacent detections (0101–0105)
Goal: validate “leading indicator” behavior exists and can be tuned.

Backtest approach:
- Run the query over 14–30 days
- Confirm:
  - the baseline logic behaves consistently
  - alerts cluster around real incidents or test simulations
- Capture:
  - false positives
  - what thresholds reduce noise without losing signal

Specific notes:
- 0102 (rare parent-child):
  - validate baseline window is long enough (7–14d)
  - consider an allowlist for benign update chains
- 0104 (NXDOMAIN surge):
  - validate z-score window (6h) vs your DNS baseline
  - consider per-host thresholds for noisy systems
- 0105 (Cloud API spike):
  - exclude known automation roles first
  - consider a “sensitive API only” variant

---

## Predictive detections (0201–0203)

### 0201 License forecast exhaustion
Goal: verify forecast is stable and meaningful.

Validation:
- Run over the last 30–90 days
- Confirm daily_gb is not sparse (fillnull helps)
- Adjust:
  - timechart span (1d vs 1h)
  - future_timespan (7 vs 14 vs 30)

Backtesting:
- Compare forecast against actual for prior periods by:
  - running forecast daily
  - logging predicted vs actual (future improvement)

### 0202 Auth failure forecast
Goal: verify that forecast is not overly sensitive to short spikes.

Validation:
- Run over 6–24 hours of auth failures
- Tune:
  - span (5m vs 10m)
  - threshold
  - consider per-domain-controller or gateway scoping

Backtesting:
- Identify historical “spike events” and see if the forecast would have crossed threshold earlier.

### 0203 Risk trajectory (score acceleration)
Goal: verify that the score is explainable and the thresholds make sense.

Validation:
- Run over 7–30 days for a subset of users
- Identify:
  - normal ranges of risk_1h and risk_delta
  - known noisy accounts (service/shared)

Tuning:
- Adjust weights and thresholds based on baseline
- Separate service accounts into a dedicated detection variant

---

## Optional test simulation guidance
If you do not have real incidents:
- Use controlled test activity:
  - generate failed logons (lab users)
  - execute benign PowerShell encoded commands
  - create a scheduled task in a lab VM
- Confirm detections trigger as expected and document outcomes.
