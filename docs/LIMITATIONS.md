# CommShield: Known Limitations & Constraints

This document provides a strictly factual, transparent inventory of the known limitations of the CommShield platform, its datasets, models, and governance gates.

---

## 1. Telemetry and Data Provenance

1. **Topology-Assigned Slices (5G-NIDD)**:
   - In the real testbed dataset (5G-NIDD), network slice identifiers (`S-NSSAI`) are not present in raw protocol headers.
   - Slices are assigned by base station topology (BS1 $\rightarrow$ `sst-1-sd-010203` eMBB, BS2 $\rightarrow$ `sst-2-sd-020304` URLLC).
   - This serves as a realistic proxy, but does not reflect dynamic multi-slice multiplexing over a single gNB.

2. **Simulated Core Telemetry**:
   - The digital twin generator produces parametric 5G core telemetry (NAS registration counters, PFCP session messages, GTP-U volumes).
   - While generated with deterministic seeds and realistic diurnal patterns, it is a synthetic simulation and does not capture all nuances of production carrier-grade 3GPP release-17 core traffic.

3. **Attack Representation & Sample Size**:
   - In 5G-NIDD flow captures, specific attack categories (such as ICMP flood) contain very few flows (small window sample sizes), resulting in wide bootstrap confidence intervals and lower statistical power for rare attack types.
   - Zero-day attacks outside the feature subspace (e.g., control plane application-layer exploits not affecting packet/byte ratios or UE session dynamics) cannot be detected by volume/ratio telemetry alone.

---

## 2. Model & Detector Limitations

1. **Static Baseline Degradation (Arm A)**:
   - The static anchor baseline has a false positive rate of 83%–97% under sustained 2x–2.5x volume expansion, because volume features scale beyond anchor IQR bounds even when traffic is benign.

2. **Naive Retraining Vulnerability (Arm B)**:
   - Naive unconditional retraining adapts to growth, but absorbs attack traffic: in the hidden ramp scenario, naive retrain experiences 46.7% contamination.
   - Under creeping poisoning (boiling frog), a step-limit-only check accepts 10 out of 10 attack steps, allowing gradual baseline corruption.

3. **Ratio Feature Scale Invariance**:
   - CommShield ratio features (`registrations_per_active_ue`, `nas_failure_ratio`, `pfcp_failure_ratio`, `pdu_session_rate_per_ue`, `new_ue_rate`) achieve provable scale invariance ($D_{\max} = 0.0, D_{\text{rms}} = 0.0$) under strictly proportional growth.
   - However, if legitimate growth involves non-proportional user behavior shifts (e.g., changes in user application mix), the ratio drift budget will reject candidate baselines, requiring operator manual intervention.

---

## 3. Governance and Human Oversight

1. **Analyst Gating Required**:
   - CommShield governance gates (holdout FPR, proportional growth test, canary retention, cumulative drift budget) provide automated candidate rejection, but promotion to active baseline requires an authenticated analyst token (`COMMSHIELD_ANALYST_TOKEN`).
   - The system intentionally does not execute autonomous unverified baseline promotion.

2. **Open5GS Live Lab Prerequisites**:
   - The live lab adapter requires an operational Open5GS core and UERANSIM deployment on Linux. On Windows or environments without a running core, the adapter falls back to pre-recorded sample logs (`lab/sample_logs/`).
<!-- CommShield AI Core -->
