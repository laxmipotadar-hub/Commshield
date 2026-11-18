# CommShield Empirical Results Digest & Verification Audit

> **Audit Standard**: Every metric and number in this document is sourced directly from persisted JSON execution artifacts in `experiments/results/` (`real/metadata.json`, `real/detection_evaluation.json`, `real/growth_attribution.json`, `real/governance_evaluation.json`, `real/three_arm_summary.json`, `experiment_summary.json`, and individual run JSONs). No numbers are estimated or invented. Items not present in saved files are explicitly noted as `"not found"`.

---

## 1. Data Used (Real-Data Evaluation: 5G-NIDD)

* **Dataset Source**: `5g_nidd` (CIC / UNB 5G Standalone testbed flow capture).
* **Dataset Files Used**:
  * `data/raw/5g-nidd/BTS1_BTS2_fields_preserved.csv` (1,215,890 flows, primary baseline).
  * `data/raw/5g-nidd/BS1_each_attack_csv/UDPFlood1.csv`
  * `data/raw/5g-nidd/BS1_each_attack_csv/Goldeneye1.csv` (HTTPFlood)
  * `data/raw/5g-nidd/BS1_each_attack_csv/Slowloris1.csv` (SlowrateDoS)
  * `data/raw/5g-nidd/BS1_each_attack_csv/SYNFlood1.csv`
  * `data/raw/5g-nidd/BS1_each_attack_csv/ICMPFlood1.csv`
  * `data/raw/5g-nidd/BS1_each_attack_csv/TCPConnect1.csv`
  * `data/raw/5g-nidd/BS1_each_attack_csv/SYNScan1.csv`
  * `data/raw/5g-nidd/BS1_each_attack_csv/UDPScan1.csv`
* **Split Boundaries and Temporal Discipline**:
  * **Benign Training Split**: First 34 windows (`training_windows_count: 34`). Exclusively pure benign flows (`Label == "Benign"`) used to fit `RobustScaler`, `IsolationForest`, and `Autoencoder`.
  * **Validation Split**: Subsequent 23 windows (`validation_windows_count: 23`). Pure benign flows used for threshold calibration (fixed validation FPR: 13.04%). Zero test-period threshold tuning was performed.
  * **Test Split**: 8 attack campaigns evaluated individually over chronological window sequences:
    * `UDPFlood`: 9 windows total (1 attack, 8 benign)
    * `HTTPFlood`: 8 windows total (3 attack, 5 benign)
    * `SlowrateDoS`: 29 windows total (11 attack, 18 benign)
    * `SYNFlood`: 16 windows total (9 attack, 7 benign)
    * `ICMPFlood`: 30 windows total (10 attack, 20 benign)
    * `TCPConnectScan`: 10 windows total (5 attack, 5 benign)
    * `SYNScan`: 9 windows total (4 attack, 5 benign)
    * `UDPScan`: 10 windows total (7 attack, 3 benign)
    * **Test Total**: 121 windows total (50 attack windows, 71 benign windows across all test series).
* **Slice Assignment Methodology**:
  * `BS1` (Base Station 1) $\rightarrow$ `sst-1-sd-010203` (assigned as `eMBB`).
  * `BS2` (Base Station 2) $\rightarrow$ `sst-2-sd-010203` (assigned as `URLLC`).
  * **Transparency Disclosure**: Topology-assigned based on base station physical tap points. 5G-NIDD does **not** contain native 3GPP S-NSSAI slice headers.

---

## 2. Detection on Real Data (5G-NIDD)

* **Validation FPR on 23 Pure Benign Validation Windows**:
  * CommShield (Fusion): `0.1304` (13.04%)
  * Isolation Forest: `0.1304` (13.04%)
  * Autoencoder: `0.1304` (13.04%)
  * Fixed Z-Score Baseline: `0.1304` (13.04%)

* **Per-Attack Evaluation Summary**:

| Attack Type | Category | Total W | Atk W | Ben W | CommShield Fusion Recall / FPR (Delay) | Isolation Forest Recall / FPR (Delay) | Autoencoder Recall / FPR (Delay) | Fixed Z-Score Recall / FPR (Delay) | CommShield vs Z-Score Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **UDPFlood** | DoS | 9 | 1 | 8 | 100.0% / 25.0% (0 W) | 100.0% / 12.5% (0 W) | 100.0% / 12.5% (0 W) | 100.0% / 75.0% (0 W) | Superior FPR (25.0% vs 75.0%) |
| **HTTPFlood** | DoS | 8 | 3 | 5 | 100.0% / 40.0% (0 W) | 100.0% / 0.0% (0 W) | 100.0% / 0.0% (0 W) | 100.0% / 0.0% (0 W) | **Inferior FPR** (40.0% vs 0.0%) |
| **SlowrateDoS** | DoS | 29 | 11 | 18 | 72.73% / 66.67% (4 W) | 72.73% / 55.56% (4 W) | 72.73% / 66.67% (4 W) | 72.73% / 72.22% (4 W) | Comparable (both missed 3/11 atk) |
| **SYNFlood** | DoS | 16 | 9 | 7 | 100.0% / 14.29% (0 W) | 100.0% / 14.29% (0 W) | 100.0% / 14.29% (0 W) | 100.0% / 28.57% (0 W) | Superior FPR (14.29% vs 28.57%) |
| **ICMPFlood** | DoS | 30 | 10 | 20 | **0.0% / 35.0% (10 W)** | **0.0% / 30.0% (10 W)** | **0.0% / 35.0% (10 W)** | **0.0% / 30.0% (10 W)** | **Total failure across all models** |
| **TCPConnectScan** | Scan | 10 | 5 | 5 | 100.0% / 20.0% (0 W) | 100.0% / 20.0% (0 W) | 100.0% / 0.0% (0 W) | 100.0% / 0.0% (0 W) | **Inferior FPR** (20.0% vs 0.0%) |
| **SYNScan** | Scan | 9 | 4 | 5 | 100.0% / 0.0% (0 W) | 100.0% / 0.0% (0 W) | 100.0% / 0.0% (0 W) | 100.0% / 0.0% (0 W) | Equal |
| **UDPScan** | Scan | 10 | 7 | 3 | **85.71% / 0.0% (0 W)** | **85.71% / 0.0% (0 W)** | **85.71% / 0.0% (0 W)** | **100.0% / 0.0% (0 W)** | **WORSE RECALL** (85.71% vs 100.0%) |

* **Attack Types Where CommShield Does Worse Than Fixed Z-Score Baseline**:
  1. **`UDPScan` (Recall)**: CommShield achieves **85.71% recall** (missed 1 of 7 attack windows), whereas the simple Fixed Z-Score baseline achieves **100.0% recall** with identical 0.0% FPR.
  2. **`HTTPFlood` (False-Positive Rate)**: CommShield incurs a **40.0% FPR** on benign windows, whereas Fixed Z-Score incurs **0.0% FPR** with identical 100% recall.
  3. **`TCPConnectScan` (False-Positive Rate)**: CommShield incurs a **20.0% FPR** on benign windows, whereas Fixed Z-Score incurs **0.0% FPR** with identical 100% recall.

---

## 3. Growth and Attribution (Real-Data Evaluation)

* **Source File**: `experiments/results/real/growth_attribution.json`
* **Experimental Label**: `semi-synthetic` (real benign flow distribution mathematically scaled).
* **Outcome Summary**:

| Scaling Level | Composition Condition | Classified Likely Benign | Classified Likely Attack | Classified Uncertain | Proportional Test | Abstention Reason | JSD Divergence | Scaling Factor $k$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1.5x** | Preserved | 1 (profile episode) | 0 | 0 | PASSED (`true`) | None (`null`) | *not found* (`null`) | *not found* (`null`) |
| **1.5x** | Shifted | 0 | 1 (profile episode) | 0 | REJECTED (`false`) | None (`null`) | *not found* (`null`) | *not found* (`null`) |
| **2.0x** | Preserved | 1 (profile episode) | 0 | 0 | PASSED (`true`) | None (`null`) | *not found* (`null`) | *not found* (`null`) |
| **2.0x** | Shifted | 0 | 1 (profile episode) | 0 | REJECTED (`false`) | None (`null`) | *not found* (`null`) | *not found* (`null`) |
| **3.0x** | Preserved | 1 (profile episode) | 0 | 0 | PASSED (`true`) | None (`null`) | *not found* (`null`) | *not found* (`null`) |
| **3.0x** | Shifted | 0 | 1 (profile episode) | 0 | REJECTED (`false`) | None (`null`) | *not found* (`null`) | *not found* (`null`) |

* **Audit Notes on Growth Attribution Output**:
  * **Total Classifications**: Across the 6 evaluated growth conditions, 3 were classified as `likely_benign` (all composition-preserved conditions) and 3 were classified as `likely_attack` (all composition-shifted conditions).
  * **Uncertain & Abstentions**: 0 windows/episodes were classified as `uncertain`. Zero abstention reasons were recorded (`null` across all entries).
  * **Missing Metrics**: `jsd_divergence` and `scaling_factor_k` fields in `growth_attribution.json` are `null` (*not found*). Per-window breakdown counts are *not found* because the evaluator persisted only the episode-level verdict.

---

## 4. Governance Evaluation on Real Data

* **Source File**: `experiments/results/real/governance_evaluation.json`

### A. Benign-Growth Candidate (`v1.1.0-real-clean`)
Trained on scaled real benign traffic. Overall status: **REJECTED** (`all_mandatory_passed: false`).

| Check Name | Status | Metrics in JSON | Gate Result |
| :--- | :---: | :--- | :--- |
| `normal_holdout_backtest` | **PASSED** | $\text{FPR} = 0.0\%$ (0/20 windows flagged), limit $\le 5.0\%$ | Allowed |
| `proportional_growth` | **PASSED** | $\text{JSD} = 0.00342$ (limit $\le 0.0350$), Per-UE dev = 0.1673 (limit $\le 0.250$) | Allowed |
| `canary_retention_test` | **FAILED** | Active recall = 100.0%, Candidate recall = 25.0%, $\text{Recall Delta} = 75.0\%$ (limit $\le 5.0\%$). $\Delta_{\text{canary}} = 10.0$ (limit $\le 10.0$). Per-category: `attack_in_growth` recall 11.11% (18 canaries, FAILED); `slow_attack_ramp` recall 33.33% (21 canaries, FAILED); `mimicry_attack` recall 100.0% (1 canary, PASSED). | **REJECTED** |
| `drift_budget` | **FAILED** | $D_{\text{rms}}(\text{cand}, \text{active}) = 6.6496$ (limit $\le 1.5$, FAILED)<br>$D_{\text{rms}}(\text{cand}, \text{anchor}) = 6.6496$ (limit $\le 2.5$, FAILED)<br>$D_{\max}(\text{cand}, \text{anchor}) = 16.898$ (limit $\le 3.0$, FAILED)<br>$\Delta_{\text{canary}} = 10.0$ (limit $\le 10.0$, PASSED) | **REJECTED** |

* **Which checks rejected the clean candidate**: Rejected by **both** `canary_retention_test` (recall collapsed by 75%) and `drift_budget` (all distance checks failed: step limit $6.65 > 1.5$, cumulative budget $6.65 > 2.5$, max feature shift $16.90 > 3.0$).

### B. Poisoned Candidate (`v1.1.0-naive-poisoned`)
Training set injected with real attack windows. Overall status: **REJECTED** (`all_mandatory_passed: false`, `rejected_by_gates: ["normal_holdout_backtest"]`).

| Check Name | Status | Metrics in JSON | Gate Result |
| :--- | :---: | :--- | :--- |
| `normal_holdout_backtest` | **FAILED** | $\text{FPR} = 100.0\%$ (20/20 windows flagged), limit $\le 5.0\%$ | **REJECTED** |
| `proportional_growth` | **PASSED** | $\text{JSD} = 0.00031$ (limit $\le 0.0350$), Per-UE dev = 0.211 (limit $\le 0.250$) | Allowed |
| `canary_retention_test` | **PASSED** | Active recall = 100.0%, Candidate recall = 100.0%, $\text{Recall Delta} = 0.0\%$ (limit $\le 5.0\%$). Per category: all 40 canaries retained 100% recall. | Allowed |
| `drift_budget` | **PASSED** | $D_{\text{rms}}(\text{cand}, \text{active}) = 0.6114$ (limit $\le 1.5$, PASSED)<br>$D_{\text{rms}}(\text{cand}, \text{anchor}) = 0.6114$ (limit $\le 2.5$, PASSED)<br>$D_{\max}(\text{cand}, \text{anchor}) = 1.0761$ (limit $\le 3.0$, PASSED)<br>$\Delta_{\text{canary}} = 0.0$ (limit $\le 10.0$, PASSED) | Allowed |

* **Which check rejected the poisoned candidate**: Rejected **strictly and solely by `normal_holdout_backtest`**.
* **Critical Finding**: The poisoned candidate completely bypassed the `canary_retention_test` ($\Delta = 0.0\%$) and the `drift_budget` ($D_{\text{rms}} = 0.61 \le 2.5, D_{\max} = 1.08 \le 3.0$). Neither canary retention nor drift distance detected the poisoning.

---

## 5. Three-Arm Centrepiece Experiment Results

* **Seeds Evaluated**: 5 distinct seeds (`[42, 101, 2024, 777, 999]`).
* **Source Files**: `experiments/results/real/three_arm_summary.json` and `experiments/results/experiment_summary.json`.

### A. Real & Semi-Synthetic Scenarios (`experiments/results/real/three_arm_summary.json`)

| Scenario | Label | Total W (Atk W) | Arm | Attack Recall (Mean, Range) | Benign FPR (Mean, Range) | Contamination (Mean, Range) | Adaptations (Mean) | Quarantined (Mean) | Recovery (W) |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **real_benign** | Real | 40 (0) | **Arm A** (Static) | N/A | 5.0% [0.05, 0.05] | 0.0% [0.0, 0.0] | 0.0 | 0.0 | 0.0 |
| | | | **Arm B** (Naive) | N/A | **0.0% [0.0, 0.0]** | 0.0% [0.0, 0.0] | 2.0 | 0.0 | 0.0 |
| | | | **Arm C** (CommShield) | N/A | **5.0% [0.05, 0.05]** | 0.0% [0.0, 0.0] | 0.0 | 2.0 | 0.0 |
| **real_attacks** | Real | 21 (1) | **Arm A** (Static) | 100.0% [1.0, 1.0] | 5.0% [0.05, 0.05] | 0.0% [0.0, 0.0] | 0.0 | 0.0 | 0.0 |
| | | | **Arm B** (Naive) | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 1.0 | 0.0 | 0.0 |
| | | | **Arm C** (CommShield) | 100.0% [1.0, 1.0] | 5.0% [0.05, 0.05] | 0.0% [0.0, 0.0] | 0.0 | 1.0 | 0.0 |
| **scaled_benign_growth** | Semi-Synthetic | 40 (0) | **Arm A** (Static) | N/A | 5.0% [0.05, 0.05] | 0.0% [0.0, 0.0] | 0.0 | 0.0 | 0.0 |
| | | | **Arm B** (Naive) | N/A | 5.0% [0.05, 0.05] | 0.0% [0.0, 0.0] | 2.0 | 0.0 | 0.0 |
| | | | **Arm C** (CommShield) | N/A | 5.0% [0.05, 0.05] | 0.0% [0.0, 0.0] | **0.0** | 2.0 | 0.0 |
| **attack_in_scaled_growth** | Semi-Synthetic | 21 (1) | **Arm A** (Static) | 100.0% [1.0, 1.0] | 5.0% [0.05, 0.05] | 0.0% [0.0, 0.0] | 0.0 | 0.0 | 0.0 |
| | | | **Arm B** (Naive) | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 0.0% [0.0, 0.0] | 1.0 | 0.0 | 0.0 |
| | | | **Arm C** (CommShield) | 100.0% [1.0, 1.0] | 5.0% [0.05, 0.05] | 0.0% [0.0, 0.0] | 0.0 | 1.0 | 0.0 |

### B. Synthetic Scenarios (`experiments/results/experiment_summary.json` & run JSONs)

| Scenario | Label | Arm | Attack Recall (Mean ± Std, Range) | Benign FPR (Mean ± Std, Range) | Contamination (Mean ± Std, Range) | Adaptations (Mean) | Quarantined (Mean) | Recovery (W) |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **stable_benign** | Synthetic | **Arm A** | N/A | 23.00% ± 5.57% [12.5%, 27.5%] | 0.0% [0.0%, 0.0%] | 0.0 | 0.0 | 0.0 |
| | | **Arm B** | N/A | **21.00% ± 12.51% [5.0%, 40.0%]** | 0.0% [0.0%, 0.0%] | 2.2 | 0.0 | 0.0 |
| | | **Arm C** | N/A | **23.00% ± 5.57% [12.5%, 27.5%]** | 0.0% [0.0%, 0.0%] | 0.0 | 2.2 | 0.0 |
| **legitimate_growth** | Synthetic | **Arm A** | N/A | 97.00% ± 1.87% [95.0%, 100.0%] | 0.0% [0.0%, 0.0%] | 0.0 | 0.0 | 0.0 |
| | | **Arm B** | N/A | **37.50% ± 10.72% [27.5%, 55.0%]** | 0.0% [0.0%, 0.0%] | 4.0 | 0.0 | 0.0 |
| | | **Arm C** | N/A | **97.00% ± 1.87% [95.0%, 100.0%]** | 0.0% [0.0%, 0.0%] | **0.0** | 4.0 | 0.0 |
| **slow_attack_ramp** | Synthetic | **Arm A** | 100.0% ± 0.0% [100%, 100%] | 18.34% ± 3.33% [16.67%, 25.0%] | 0.0% [0.0%, 0.0%] | 0.0 | 0.0 | 0.0 |
| | | **Arm B** | 91.43% ± 8.02% [78.57%, 100%] | 18.34% ± 3.33% [16.67%, 25.0%] | 83.20% ± 13.72% [72.0%, 100%] | 2.2 | 0.0 | 0.0 |
| | | **Arm C** | 100.0% ± 0.0% [100%, 100%] | 18.34% ± 3.33% [16.67%, 25.0%] | 0.0% [0.0%, 0.0%] | 0.0 | 2.2 | 0.0 |
| **attack_in_growth** | Synthetic | **Arm A** | 100.0% ± 0.0% [100%, 100%] | 92.50% ± 4.68% [87.5%, 100.0%] | 0.0% [0.0%, 0.0%] | 0.0 | 0.0 | 0.0 |
| | | **Arm B** | 96.67% ± 4.86% [87.5%, 100%] | **58.75% ± 5.00% [50.0%, 62.5%]** | 56.00% ± 0.0% [56.0%, 56.0%] | 4.0 | 0.0 | 0.0 |
| | | **Arm C** | 100.0% ± 0.0% [100%, 100%] | **92.50% ± 4.68% [87.5%, 100.0%]** | 0.0% [0.0%, 0.0%] | 0.0 | 4.0 | 0.0 |
| **mimicry_attack** | Synthetic | **Arm A** | 100.0% ± 0.0% [100%, 100%] | 21.00% ± 4.90% [15.0%, 30.0%] | 0.0% [0.0%, 0.0%] | 0.0 | 0.0 | 0.4 |
| | | **Arm B** | 56.00% ± 30.07% [20.0%, 100%] | 25.00% ± 5.48% [15.0%, 30.0%] | 74.40% ± 6.97% [64.0%, 80.0%] | 2.2 | 0.0 | 0.4 |
| | | **Arm C** | 100.0% ± 0.0% [100%, 100%] | 21.00% ± 4.90% [15.0%, 30.0%] | 0.0% [0.0%, 0.0%] | 0.0 | 2.2 | 0.4 |

### C. Where Arm C is NOT Better Than Arm B
1. **`legitimate_growth` (Synthetic)**: Arm B adapted 4.0 times and reduced FPR to **37.50%**, whereas Arm C **completely failed to adapt (0.0 adaptations)** because candidate baselines were blocked by canary/budget gates, resulting in an extreme **97.00% FPR** (identical to static Arm A).
2. **`attack_in_growth` (Synthetic FPR)**: Arm B achieved an FPR of **58.75%**, whereas Arm C suffered an FPR of **92.50%** on benign windows during growth.
3. **`stable_benign` (Synthetic FPR)**: Arm B achieved a lower mean FPR (**21.00%**) than Arm C (**23.00%**).
4. **`real_benign` (Real Data FPR)**: Arm B achieved **0.0% FPR**, while Arm C incurred a **5.0% FPR** and quarantined 2 benign drift alerts.
5. **`scaled_benign_growth` (Semi-Synthetic Adaptation)**: Arm B adapted 2.0 times while Arm C failed to adapt (0.0 adaptations, identical 5.0% FPR).

---

## 6. The 5 Weakest or Least Convincing Results

1. **ICMPFlood Total Detection Blindness (0.0% Recall)**:
   CommShield, Isolation Forest, Autoencoder, and Fixed Z-Score all scored 0.0% recall across 30 windows because low-frequency ICMP packets (~1 packet every 2 seconds) produce zero measurable flow-level distortion in 60s ratio aggregates.
2. **Arm C Complete Failure to Adapt under Legitimate Growth (Synthetic 97.0% FPR, 0 Adaptations)**:
   In the centerpiece synthetic growth benchmark, Arm C made exactly 0 adaptations across all 5 seeds, leaving the system on a frozen baseline with a catastrophic 97.0% false positive rate.
3. **False Rejection of Clean Benign Growth Candidate by Canary & Budget Gates**:
   When given clean scaled benign real-data traffic, CommShield's governance layer rejected the clean candidate on both `canary_retention_test` (recall collapsed from 100% to 25.0%) and `drift_budget` ($D_{\text{rms}} = 6.65 > 2.5, D_{\max} = 16.90 > 3.0$).
4. **Complete Ineffectiveness of Canary Retention & Drift Budget against Poisoning**:
   The poisoned candidate trained on real attack traffic passed both `drift_budget` ($D_{\text{rms}} = 0.61 \le 2.5, D_{\max} = 1.08 \le 3.0$) and `canary_retention_test` ($\Delta = 0.0\%$), proving these two primary gates are blind to real poisoning.
5. **Inferior Recall on UDPScan Compared to Simple Z-Score Baseline**:
   On `UDPScan1.csv`, CommShield's multi-model fusion achieved only 85.71% recall (missing 1 of 7 attack windows), while a naive per-feature Fixed Z-Score baseline detected 100.0% of attack windows with 0.0% false alarms.

---

## 7. Gaps: Unsupported Claims & Placeholder Numbers

### A. Claims in `README.md` or UI Unsupported by Code
1. **Claim of MAWI Real-Growth Backbone and Open5GS Lab Telemetry**:
   * *Claim*: `README.md` (lines 12, 32) lists "Open5GS/UERANSIM testbed logs, real-growth backbones (MAWI)".
   * *Reality*: No MAWI capture files exist in `data/` or any ingestion pipeline. No Open5GS PCAPs or testbed logs exist. All non-5G-NIDD data is produced solely by `ml_engine/preprocessing/synthetic_generator.py`.
2. **Claim that CommShield Safely Adapted to Legitimate Growth**:
   * *Claim*: `experiments/README.md` (lines 65-66) states: *"Under legitimate_growth, Arm A suffered alert fatigue (elevated FPR) as traffic outgrew the frozen anchor, whereas Arm C safely adapted via approved shadow candidates once proportional growth was proven ($JSD \le 0.035$)."*
   * *Reality*: `experiments/results/experiment_summary.json` proves Arm C had **0.0 adaptations** across all 5 seeds, remaining frozen at **97.0% FPR**, identical to Arm A.
3. **Claim of SHAP Explanations for Isolation Forest**:
   * *Claim*: `docs/COMMSHIELD_SPEC_v9.md` (line 227) and frontend detail panels specify "SHAP for Isolation Forest".
   * *Reality*: In `backend/app/api/windows.py` (lines 112-118), the returned `shap_values` are simply per-feature robust z-scores: `(value - median) / iqr`. No TreeSHAP, KernelSHAP, or Shapley algorithm is executed.
4. **Claim of Dynamic Evasion Modeling**:
   * *Claim*: `docs/COMMSHIELD_SPEC_v9.md` (line 75) requires an evasion test where an attacker tracks scores and ramps below the threshold.
   * *Reality*: Evasion is only represented by static synthetic profiles with a fixed ramp parameter (`scenario_slow_attack_ramp`); closed-loop adaptive evasion does not exist.

### B. Numbers That Are Hard-Coded or Placeholder
1. **`ml_engine/evaluation/benchmark.py` (Lines 60-89 & 98-140)**:
   * Hard-coded fallback metrics: Arm A precision `0.941`, recall `0.722`, false alarm `0.085`; Arm B precision `0.778`, recall `0.444`, false alarm `0.021`; Arm C precision `0.963`, recall `0.926`, false alarm `0.012`.
   * Hard-coded simulation heuristics: `flagged = is_attack or (is_growth and not is_attack and hash(...) % 7 == 0)` for Arm A; `flagged = attack_count <= 4` for Arm B; `flagged = is_attack` for Arm C.
   * Hard-coded poisoning susceptibility: `metrics_c["poisoning_susceptibility"] = 0.020`.
2. **`ml_engine/attribution/rule_based.py` (Line 35)**:
   * `control_slice_concordant: bool = True` is hard-coded as a default parameter and never set dynamically from second-slice observations.
3. **`ml_engine/governance/config.py` (Line 77)**:
   * `DWELL_TIME_MIN_SECONDS: int = 0` is a placeholder constant unused by any candidate evaluation logic.

---

## 8. Status of Key Spec Items (With File and Function Evidence)

| Spec Item | Status | File and Function Evidence | What is Present / What is Absent |
| :--- | :---: | :--- | :--- |
| **Control-slice evidence** | **PARTIAL** | `ml_engine/attribution/rule_based.py:attribute()`<br>`ml_engine/attribution/metrics.py:evaluate_attribution_threat_indicators()` | **Present**: The function accepts `control_slice_concordant: bool = True` and tags `"NETWORK_WIDE_EXPANSION"` vs `"LOCALIZED_TO_SLICE_1"`.<br>**Absent**: Neither `backend/app/services/attribution.py` nor `ml_engine/evaluation/experiment.py` fetches or evaluates Slice 2 telemetry; the value is left at hard-coded default `True`. |
| **Time-of-day context** | **MISSING** | `ml_engine/baseline/trainer.py:train_slice_baseline()`<br>`ml_engine/preprocessing/windowing.py` | **Absent**: No hour-of-day or day-of-week bucketing or conditioning exists. Baselines pool all chronological training windows into a single global distribution. |
| **Re-anchoring procedure** | **MISSING** | `ml_engine/governance/`<br>`backend/app/api/governance.py` | **Absent**: Zero occurrences of `re_anchor` or re-anchoring logic in any Python file. No mechanism exists to reset drift budgets or establish a new anchor via offline review. |
| **Dwell time enforcement** | **MISSING** | `ml_engine/governance/config.py:77`<br>`backend/app/services/governance.py` | **Present**: Defined as an unused constant `DWELL_TIME_MIN_SECONDS: int = 0`.<br>**Absent**: Never checked in `ml_engine/governance/checks.py` or `candidate.py`. Consecutive promotions are not rate-limited. |
| **Lab attacks (Open5GS/UERANSIM)** | **MISSING** | `data/`<br>`backend/scripts/` | **Absent**: No Open5GS VM captures, UERANSIM flood recipes, or lab attack PCAPs exist in the project. |
| **Evasion boundary map** | **MISSING** | `ml_engine/evaluation/`<br>`experiments/` | **Absent**: No script, notebook, or output JSON evaluates or plots ramp speed vs detector sensitivity boundaries. |
| **Ablation 1**: Step limit alone vs step + budget | **MISSING** | `ml_engine/evaluation/` | **Absent**: No experiment runner isolates the step limit from the cumulative budget. |
| **Ablation 2**: With vs without canary retention | **MISSING** | `ml_engine/evaluation/` | **Absent**: No script evaluates Arm C with canary retention disabled. |
| **Ablation 3**: With vs without abstention | **MISSING** | `ml_engine/evaluation/` | **Absent**: No script generates coverage-accuracy trade-off curves without abstention. |
| **Ablation 4**: With vs without proportional growth test | **MISSING** | `ml_engine/evaluation/` | **Absent**: No script isolates the contribution of JSD proportional testing. |
| **Ablation 5**: With vs without control-slice evidence | **MISSING** | `ml_engine/evaluation/` | **Absent**: No ablation exists (and control-slice telemetry is not operational). |
| **Ablation 6**: Real backbone vs synthetic-only growth | **MISSING** | `ml_engine/evaluation/` | **Absent**: Real-data and synthetic runs were executed separately, but no controlled ablation isolates the backbone effect across matching conditions. |
| **Ablation 7**: Global vs per-slice baselines | **MISSING** | `ml_engine/evaluation/` | **Absent**: No experiment compares per-slice baselines against an aggregated single global model. |
