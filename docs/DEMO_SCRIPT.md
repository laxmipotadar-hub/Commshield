# CommShield Presentation Demo Script: Four-Scene Replay

This script provides an exact step-by-step presentation walkthrough for evaluators, judges, and operators. The four-scene demo runs deterministically with auto-pause at key events, one-line event captions, and source tags on every scene.

Scene 3 uses the lab clip only if it exists; otherwise it falls back to the simulated unprovisioned burst.

---

## Quickstart & CLI Replay Commands

To verify and run the demo suite locally:

### PowerShell (Windows)
```powershell
python -m unittest backend\tests\test_demo.py -v
cd frontend; npm run build
```

### Bash (Ubuntu / Linux / macOS)
```bash
python3 -m unittest backend/tests/test_demo.py -v
npm --prefix frontend run build
```

---

## Scene 1: Baseline Steady-State Telemetry

### What to Click
1. In the top navigation header bar, click the **Demo Mode** toggle button to turn it **ON**.
2. Confirm the dropdown selects **Scene 1: 1. Baseline Steady-State Telemetry**.
3. When the replay auto-pauses at Window #5 (`periodic_audit`), read the one-line caption and click **Continue Replay** (or **Next scene** to advance).

### Two Sentences to Say
"Here we observe nominal 5G standalone telemetry flowing across eMBB, URLLC, and mMTC slices with zero drift and zero false alarms. Every active device is cryptographically authenticated against our zero-trust provisioning catalog, establishing an uncontaminated anchor baseline."

### Which Numbers to Point At
* **200 Catalog SIMs** (100 sensors, 50 cameras, 50 AGVs) verified from `data/twin/provisioning.json`.
* **Nominal Telemetry Packet Rates**: **41.25 pps** on camera slice (`sst-1-sd-010203`), **80.0 pps** on AGV slice (`sst-2-sd-020304`), and **10.0 pps** on sensor slice (`sst-3-sd-030405`).
* **0.0% Baseline Contamination** and **0 Security Alerts** under steady-state operation.

---

## Scene 2: Approved Onboarding (Batch OB-01 & OB-02)

### What to Click
1. Click the **Next scene** button in the header bar or in the pause banner to load **Scene 2: Approved Onboarding**.
2. Watch the telemetry replay advance through Window #10 where newly onboarded devices join the network.
3. When auto-pause triggers at Window #14 (`governance_approval`), inspect the Governance Decision Trace card and click **Next scene**.

### Two Sentences to Say
"A planned deployment batch arrives on the sensor slice, scaling traffic volume by $k=1.48$ while preserving slice composition with a JSD divergence of $0.018 \le 0.045$. CommShield's governance gate cross-references the carrier provisioning schedule, confirms zero anomalous devices in split-conformal inference, and promotes the adapted candidate baseline without manual intervention."

### Which Numbers to Point At
* **30 Onboarded Sensors** matching scheduled change event `BATCH-OB-20261115-01` from `data/twin/change_events.json`.
* **Volume Multiplier $k=1.48$** and **JSD Composition Divergence $0.018$** (well within the $0.045$ null-hypothesis tolerance).
* **0.0% CommShield Twin Contamination** [95% CI: 0.0%, 0.0%] with **2.0 Onboardings Successfully Adapted** (from `experiments/results/twin/three_arm_twin_summary.json`).

---

## Scene 3: Unprovisioned Device Burst Flagged

### What to Click
1. Click the **Next scene** button to advance to **Scene 3: Unprovisioned Device Burst Flagged**.
2. Notice the source badge: displays **"Live lab"** when `data/lab/windows.jsonl` is present, or **"Simulated twin"** when running offline without the lab file.
3. When the replay auto-pauses at Window #10 (`first_alert`) and Window #11 (`quarantine_isolation`), observe the purple quarantine perimeter rings around the rogue devices on the floor map.

### Two Sentences to Say
"A sudden surge of 40 rogue SIM cards bursts onto the network, causing the active provisioned share to plummet from 100.0% to 57.1%. CommShield's Rule 1 immediately flags the uncatalogued subscriber IDs and enforces network quarantine, shielding downstream retraining from a 50.0% poisoning surge."

### Which Numbers to Point At
* **57.1% Active Provisioned Share** (dropping below the 95.0% zero-trust threshold due to unprovisioned devices).
* **Naive Retraining Contamination: 50.0%** [95% CI: 50.0%, 50.0%] with **13.3% FPR** (from `experiments/results/twin/three_arm_twin_summary.json`).
* **CommShield Twin Contamination: strictly 0.0%** [95% CI: 0.0%, 0.0%] with **1 Quarantined Batch** and **0.0 Poisoning Absorbed**.

---

## Scene 4: Hidden Ramp (Naive Poisoned vs CommShield Quarantines Excess)

### What to Click
1. Click the **Next scene** button to advance to **Scene 4: Hidden Ramp**.
2. Replay begins with approved onboarding active; at Window #10 subtle creeping rate increases begin.
3. When auto-pause triggers at Window #15 (`conformal_gray_band`) and Window #16 (`governance_divergence`), expand the **Three-Arm Comparison** and **Decision Trace** panels to compare Naive Retraining against CommShield Twin.

### Two Sentences to Say
"An adversary attempts a stealth attack by slowly ramping transmission rates on 15 provisioned devices hidden inside an approved onboarding envelope. While naive retraining absorbs the attack with 33.3% baseline contamination, CommShield's split-conformal model flags the creeping devices in the gray band and quarantines the excess, slashing contamination to 1.7%."

### Which Numbers to Point At
* **Naive Retraining Contamination: 33.3%** [95% CI: 33.3%, 33.3%], completely poisoned by the stealth ramp.
* **CommShield Base Failure**: achieves 0.0% contamination but suffers a catastrophic **100.0% False Positive Rate** by rejecting all legitimate onboardings.
* **CommShield Twin (Gated)**: limits contamination to **1.7%** [95% CI: 0.0%, 5.0%] while maintaining a low **2.7% False Positive Rate** [95% CI: 1.5%, 4.0%].
* **Conformal Gray Band**: point at **>30.0% uncertain share** in split-conformal bounds ($p \in [0.01, 0.05]$) triggering quarantine of excess devices.
