# PDE Correlation 0001: Admin Trajectory + Endpoint Anomalies Escalation

## Purpose
Increase confidence and reduce false positives by correlating:
- Identity risk trajectory (admin remote logon risk) with
- Endpoint anomaly indicators (system binary path anomaly, DLL sideloading)

This correlation is designed to escalate severity when behaviors co-occur within a defined window.

---

## Inputs (detections)
Primary:
- PDE-SPL-0304: Admin remote logon risk trajectory (novelty + acceleration)

Supporting:
- PDE-SPL-0302: System binary execution from anomalous location (baseline rarity)
- PDE-SPL-0301: System DLL sideloading from non-system locations (baseline rarity)

Optional supporting:
- PDE-SPL-0003: Windows service creation detected
- PDE-SPL-0005: Scheduled task creation detected
- PDE-SPL-0002: Suspicious rundll32 execution patterns

---

## Correlation keys
- Preferred: host AND time proximity
- Secondary: user AND host proximity (if user-to-host relationship is available)

Recommended key mapping:
- PDE-SPL-0304: user, dest_hosts
- PDE-SPL-0302: host
- PDE-SPL-0301: host

---

## Correlation window
- 60 minutes is the default.
- Use 30 minutes for high-signal environments.
- Use 120 minutes for low-volume environments.

---

## Escalation logic
Escalate to CRITICAL when:
- PDE-SPL-0304 triggers for a user AND
- (PDE-SPL-0301 OR PDE-SPL-0302) triggers on any host in dest_hosts within 60 minutes

Escalate to HIGH when:
- PDE-SPL-0304 triggers AND
- (PDE-SPL-0003 OR PDE-SPL-0005 OR PDE-SPL-0002) triggers on any host in dest_hosts within 60 minutes

Remain HIGH (no escalation) when:
- PDE-SPL-0304 triggers alone but risk_6h and risk_delta exceed thresholds significantly

---

## Analyst workflow (triage sequence)
1. Confirm PDE-SPL-0304 context:
   - user
   - src_ips
   - dest_hosts
   - risk_6h, risk_delta, z-scores

2. For each dest_host:
   - Check for PDE-SPL-0302 and PDE-SPL-0301 hits near the same time
   - Check for persistence signals (service/task creation)

3. Validate legitimacy:
   - change tickets
   - incident response activity
   - known jump hosts/VPN ranges

4. If suspicious:
   - isolate affected dest_hosts
   - reset/revoke admin sessions
   - collect artifacts (binary, DLLs, scheduled task/service details)
   - initiate incident response

---

## Tuning notes
- Reduce noise by allowlisting:
  - known admin jump hosts and VPN CIDRs
  - known software updaters that trigger binary path anomalies
  - known DLL load paths in enterprise tooling
- Consider Tier-0 admin-only scope for PDE-SPL-0304.

