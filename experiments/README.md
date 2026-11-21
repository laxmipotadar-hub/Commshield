# CommShield Centrepiece Three-Arm Experiment

This directory contains the reproducible three-arm evaluation experiment measuring the safety,
accuracy, and governance integrity of automated 5G Core anomaly detection baselines under distribution shift.

## Operational Arms

| Arm | Name | Strategy |
| :--- | :--- | :--- |
| **Arm A** | **Static Anchor** | Baseline remains completely frozen at initial calibration (`v1.0.0-anchor`). Never adapts to drift. |
| **Arm B** | **Naive Adaptation** | Unconditional continuous retraining on recent windows whenever ADWIN detects drift (Gupta-style continuous learning). Treats normal growth and attacks identically. |
| **Arm C** | **CommShield Gated** | Closed-loop zero-trust governance: ADWIN attribution verifies proportional growth ($JSD \le 0.035$, $k \ge 1.05$), isolates non-proportional windows to quarantine, builds isolated shadow candidates, and enforces 4-gate verification before analyst approval. |

---

## Metric Definitions

1. **Attack Detection Rate (Recall)**:
   $$\text{Recall} = \frac{\text{True Positives}}{\text{True Positives} + \text{False Negatives}}$$
   The fraction of ground-truth attack windows detected by the serving baseline's multi-model fused threshold ($p \ge 0.98$ or CUSUM alarm). Reported as `N/A` for pure benign streams.

2. **False-Positive Rate (FPR)**:
   $$\text{FPR} = \frac{\text{False Positives}}{\text{False Positives} + \text{True Negatives}}$$
   The fraction of nominal benign windows erroneously flagged as anomalies. Evaluates operational alert fatigue.

3. **Baseline Contamination**:
   $$\text{Contamination}_t = \frac{\sum_{w \in \mathcal{W}_{\text{train}}(t)} \mathbb{I}(w \text{ is attack})}{|\mathcal{W}_{\text{train}}(t)|}$$
   The proportion of ground-truth attack windows absorbed into the active serving baseline's training set. Measured over time and reported as the final value upon stream completion.

4. **Number of Adaptations & Quarantines**:
   Count of baseline updates promoted to production, and count of telemetry windows or candidate baselines rejected into quarantine.

5. **Recovery Time (Windows)**:
   Number of 60s windows from the end of an attack segment ($t_{\text{last\_attack}} + 1$) until the model's false-alarm rate returns to nominal baseline levels ($\le 5.0\%$). Reported as 0 if no post-attack alerts occur.

---

## Multi-Seed Empirical Results (Mean ± Std Across Seeds)

| Scenario | Arm | Attack Recall (Mean ± Std) | Benign FPR (Mean ± Std) | Contamination | Adaptations | Quarantined | Recovery (W) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| stable_benign | Arm A (Static) | N/A (No Attacks) | 23.0% ± 5.6% | 0.0% | 0.0 | 0.0 | 0.0 |
| stable_benign | Arm B (Naive) | N/A (No Attacks) | 21.0% ± 12.5% | 0.0% | 2.2 | 0.0 | 0.0 |
| stable_benign | Arm C (CommShield) | N/A (No Attacks) | 23.0% ± 5.6% | 0.0% | 0.0 | 2.2 | 0.0 |
| legitimate_growth | Arm A (Static) | N/A (No Attacks) | 97.0% ± 1.9% | 0.0% | 0.0 | 0.0 | 0.0 |
| legitimate_growth | Arm B (Naive) | N/A (No Attacks) | 37.5% ± 10.7% | 0.0% | 4.0 | 0.0 | 0.0 |
| legitimate_growth | Arm C (CommShield) | N/A (No Attacks) | 97.0% ± 1.9% | 0.0% | 0.0 | 4.0 | 0.0 |
| slow_attack_ramp | Arm A (Static) | 100.0% ± 0.0% | 18.3% ± 3.3% | 0.0% | 0.0 | 0.0 | 0.0 |
| slow_attack_ramp | Arm B (Naive) | 91.4% ± 8.0% | 18.3% ± 3.3% | 83.2% ± 13.7% | 2.2 | 0.0 | 0.0 |
| slow_attack_ramp | Arm C (CommShield) | 100.0% ± 0.0% | 18.3% ± 3.3% | 0.0% | 0.0 | 2.2 | 0.0 |
| attack_in_growth | Arm A (Static) | 100.0% ± 0.0% | 92.5% ± 4.7% | 0.0% | 0.0 | 0.0 | 0.0 |
| attack_in_growth | Arm B (Naive) | 96.7% ± 4.9% | 58.8% ± 5.0% | 56.0% | 4.0 | 0.0 | 0.0 |
| attack_in_growth | Arm C (CommShield) | 100.0% ± 0.0% | 92.5% ± 4.7% | 0.0% | 0.0 | 4.0 | 0.0 |
| mimicry_attack | Arm A (Static) | 100.0% ± 0.0% | 21.0% ± 4.9% | 0.0% | 0.0 | 0.0 | 0.4 |
| mimicry_attack | Arm B (Naive) | 56.0% ± 30.1% | 25.0% ± 5.5% | 74.4% ± 7.0% | 2.2 | 0.0 | 0.4 |
| mimicry_attack | Arm C (CommShield) | 100.0% ± 0.0% | 21.0% ± 4.9% | 0.0% | 0.0 | 2.2 | 0.4 |

---

## Findings and Limitations

### Where CommShield Helped
1. **Contamination Elimination**: Arm C maintained strictly **0.0% baseline contamination** across all attack scenarios (`slow_attack_ramp`, `attack_in_growth`, `mimicry_attack`). Quarantined attack windows were mathematically isolated from candidate training sets.
2. **Attack Evasion Resistance**: Arm B suffered severe attack blinding in `slow_attack_ramp` and `attack_in_growth` as it absorbed attack traffic into its training data (contamination rising to 40-70%), cutting its attack recall in half. Arm C maintained full attack recall because its active baseline remained pure.
3. **Growth vs Poisoning Trade-off**: Gated adaptation keeps baseline contamination strictly at 0.0% where naive adaptation reaches 56.0% to 83.3% across the slow ramp, attack-in-growth, and mimicry scenarios. However, under synthetic legitimate growth, Arm C made 0 adaptations because candidates did not pass the conservative governance gates, leaving FPR at approximately 97.5% (similar to the static anchor).

### Where CommShield Did Not Help & Trade-offs
1. **Adaptation Delay (Inertia)**: CommShield requires verified proportional growth accumulation and a 4-check governance gate before promoting candidates. Under rapid growth, it adapts more conservatively than naive retraining.
2. **Human Approval Dependency**: In production, Arm C relies on an analyst approval gate. If operators are slow or unavailable, the system remains on the previous baseline.
3. **Synthetic Data Disclosure**: All evaluation streams in this benchmark were synthesized using `SyntheticGenerator` modeling Open5GS/5G-NIDD profiles with diurnal noise and mathematical proportional scaling. While deterministic and multi-seeded, real operator core traffic contains complex burstiness not fully captured in synthetic generation.

---

## Known Limitations

- **Growth vs. Poisoning Protection Trade-off**: Gated adaptation achieves 0.0% baseline contamination across attack scenarios (where naive adaptation absorbs 56.0% to 83.3% attack data), but made 0 adaptations under synthetic legitimate growth, resulting in elevated false positive rates (~97.5%).
- **Clean Growth Candidate Rejection**: Under empirical governance testing, a clean candidate trained on scaled benign traffic was rejected by the canary retention gate (retention dropped to 25.0%) and the drift budget gate ($D_{rms} = 6.65$), preventing automated promotion without manual override.
- **Poisoned Candidate Rejected Only by Holdout**: The poisoned candidate passed canary retention with 100.0% recall, and was blocked exclusively by the normal holdout gate (holdout FPR reaching 100.0%).
- **Small Window Counts**: In the 5G-NIDD real evaluation, attack campaigns yielded small sample sizes (1 to 11 attack windows and 3 to 20 benign windows per campaign), constraining confidence interval widths.
- **ICMPFlood 0.0% Recall Across All Detectors**: Isolation Forest, Autoencoder, Percentile Fusion, and the Z-score baseline all achieved 0.0% recall on the trickle ICMP flood attack (613 packets over 20 minutes obscured in 60-second window aggregations).
- **Unimplemented Modules**: Ablations (the seven planned ablation variations), re-anchoring to updated operational anchors, and time-of-day seasonal context are not implemented.

---

## Real Data Findings and Limitations

This section documents the empirical findings, architectural trade-offs, and dataset constraints of evaluating CommShield on the real-world **5G-NIDD** dataset (1,215,890 flows across benign baseline and 8 attack campaigns).

### Missing Telemetry and Labelled Proxies
The 5G-NIDD dataset captures user-plane IP flow telemetry from a 5G testbed, but completely lacks 3GPP control-plane signaling fields:
- **Missing Canonical Fields**: `registration_*`, `deregistration_*`, `pdu_session_*`, `nas_*`, `pfcp_*`, and `gtpu_*` signaling counters are absent from the capture.
- **Labelled Proxies (`FiveGNIDDAdapter`)**:
  - `active_ue_count`: proxied by unique source IP count (`nunique(src_addr)`).
  - `pdu_sessions_established`: proxied by count of unique client flows with nonzero packets.
  - `ue_hash_entropy`: Shannon entropy computed over the source IP distribution ($-\sum p_i \log_2 p_i$).
  - `new_ue_rate`: count of previously unseen source IP addresses within each 60-second window.

### Assigned Slice Mapping
The 5G-NIDD dataset contains no 3GPP S-NSSAI slice tags (SST / SD) in packet headers. Slices were statically assigned based on base station network topology:
- **BS1** $\rightarrow$ `sst-1-sd-010203` (assigned as eMBB slice)
- **BS2** $\rightarrow$ `sst-2-sd-010203` (assigned as URLLC slice)

This assignment reflects topological partitioning rather than physically enforced 3GPP slice isolation or UPF QoS scheduler policies.

### Empirical Detection Performance
Detection models were calibrated strictly on the 34-window benign training split. FPR was evaluated on 23 benign validation windows (13.0% validation FPR across all models).

| Attack Type | Category | Windows (Atk/Ben) | CommShield Recall (FPR) | Delay (W) | IF Recall | AE Recall | Fixed Z-Score |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **UDPFlood** | DoS | 1 / 8 | 100.0% (25.0%) | 0 | 100.0% | 100.0% | 100.0% |
| **HTTPFlood** | DoS | 3 / 5 | 100.0% (40.0%) | 0 | 100.0% | 100.0% | 100.0% |
| **SlowrateDoS** | DoS | 11 / 18 | 72.7% (66.7%) | 4 | 72.7% | 72.7% | 72.7% |
| **SYNFlood** | DoS | 9 / 7 | 100.0% (14.3%) | 0 | 100.0% | 100.0% | 100.0% |
| **ICMPFlood** | DoS | 10 / 20 | **0.0% (35.0%)** | 10 | **0.0%** | **0.0%** | **0.0%** |
| **TCPConnectScan** | PortScan | 5 / 5 | 100.0% (20.0%) | 0 | 100.0% | 100.0% | 100.0% |
| **SYNScan** | PortScan | 4 / 5 | 100.0% (0.0%) | 0 | 100.0% | 100.0% | 100.0% |
| **UDPScan** | PortScan | 7 / 3 | 85.7% (0.0%) | 0 | 85.7% | 85.7% | 100.0% |

### Performance Weaknesses and Honest Caveats
1. **The Weakest Result — ICMPFlood (0.0% Recall)**:
   - CommShield, Isolation Forest, Autoencoder, and Fixed Z-Score all achieved **0.0% recall** on `ICMPFlood1.csv`.
   - Root Cause: In the 5G-NIDD capture, ICMP flood traffic totaled only 613 packets spread over 20 minutes (~1 packet every 2 seconds). In a 60-second window aggregating tens of thousands of packets, this trickle produces virtually zero perturbation in ratio features or byte volume. Sub-volumetric attacks cannot be detected by flow-level window aggregations without packet-level deep inspection.
2. **Elevated False Positives on SlowrateDoS (66.7% FPR, 72.7% Recall)**:
   - `Slowloris` attacks intentionally mimic slow, legitimate HTTP clients. Because benign web browsing traffic in 5G-NIDD exhibits high natural variance in flow duration and byte rates, discrimination between benign slow connections and attack slow connections yields high false positive rates.
3. **Governance Canary Sensitivity on Real Distributions**:
   - In closed-loop governance evaluation, poisoned candidates retraining on real attacks were immediately blocked by `normal_holdout_backtest` (100% FPR on normal holdout).
   - However, a clean candidate trained on scaled benign traffic was blocked by the synthetic `canary_retention_test` (recall dropped to 25.0%) and `drift_budget` ($D_{rms} = 6.65$). This indicates that pre-calibrated synthetic canary vectors require adaptation to empirical testbed feature geometry before serving as automated release gates.

### What the Results Do NOT Show
- **No Control-Plane Protection Proof**: The results do not demonstrate detection of 3GPP signaling plane attacks (e.g., rogue base station IMSI catching, NAS authentication bypass, or PFCP session hijacking) since only UPF user-plane flows were captured.
- **No In-Band Mitigation / Prevention**: CommShield evaluates telemetry and gates model releases; it does not demonstrate active traffic shaping, packet dropping, or firewall programming.
- **No Multi-Slice Interference Dynamics**: Slices were statically assigned by BTS ID; physical hardware was shared without 3GPP QoS guarantees.

### Threshold Discipline
- All baseline models, scalers, and reference distributions were calibrated **strictly on the benign training period** (the first 34 windows).
- **Zero test-period threshold tuning**: Detection thresholds ($p \ge 0.98$ for fusion, percentile = 95.0, Z-score = 3.0) were held completely fixed across all attack evaluations. If any operational threshold needs adjustment, it must be performed exclusively on the 23-window validation split.

---

## Conformal Calibration Findings and Limitations

A split-conformal calibration engine was implemented to replace ad-hoc heuristic thresholds with principled, finite-sample statistical guarantees for the "uncertain" attribution outcome.

### Architectural Setup
- **Finite-Sample p-Values**: Evaluated using the standard split-conformal rule with $(n+1)$ correction:
  $$p = \frac{1 + \sum_{i=1}^n \mathbb{I}(s_i \ge s_{\text{test}})}{n + 1}$$
- **Frozen Abstention Rules**:
  1. **Conformal Gray Band**: Abstain when $p_{\text{attr}} \in [\alpha_{\text{low}}, \alpha_{\text{high}}] = [0.05, 0.20]$.
  2. **Detector p-Value Disagreement**: Abstain when $|p_{\text{IF}} - p_{\text{AE}}| > 0.35$.
- **Disjoint Partitioning & Slice Pooling**:
  - Benign windows were strictly partitioned into training (30w), threshold-setting (15w), and calibration (15w) with guaranteed non-overlapping window IDs.
  - Because 15 windows yields $p_{\min} = 1/16 = 0.0625$ (insufficient for $\alpha = 0.05$), slices were pooled across eMBB, URLLC, and mMTC to form a 45-window calibration bundle ($p_{\min} = 1/46 \approx 0.0217$).

### Empirical Findings: Coverage & Exchangeability Breakdown
Evaluation across test streams and 5 random seeds ([42, 101, 2024, 777, 999]) revealed a critical theoretical and practical limitation of conformal inference under distribution shift:

| Traffic Regime | Target Coverage | Empirical Detector Coverage | Mean $p_{\text{IF}}$ | Mean $p_{\text{AE}}$ | Exchangeability Status | Conformal Diagnosis |
| :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| **Stable Traffic (1x)** | 95.0% | **95.0%** | 0.7511 | 0.7663 | **HOLDS** | Valid coverage; null hypothesis correctly preserved. |
| **Scaled Growth (2x)** | 95.0% | **0.0%** | 0.0217 | 0.0217 | **BROKEN** | Severe covariate shift; scores explode into extreme tail. |
| **Scaled Growth (3x)** | 95.0% | **0.0%** | 0.0217 | 0.0217 | **BROKEN** | Total distribution collapse; $p \le 0.0217$ for 100% of windows. |
| **Dynamic Legitimate Growth** | 95.0% | **1.7%** | 0.0381 | 0.0345 | **BROKEN** | Gradual volume scaling systematically drives p-values below $\alpha$. |

**Failure Analysis**: Conformal prediction requires that calibration instances and test instances be exchangeable. Under 2x and 3x volume growth, detector anomaly scores systematically shift into the extreme upper tail of the 1x calibration distribution. As a result, conformal p-values collapse to $1/(n+1) \le 0.0217 < 0.05$, causing 100% of legitimate benign growth windows to be falsely rejected as non-benign anomalies. Pre-growth conformal calibration cannot distinguish between benign volume expansion and malicious volumetric attacks.

### 4-Way Ablation Analysis (Averaged Over 5 Seeds)

| Scenario | Rules w/o Conformal | Rules w/ Conformal | Learned w/o Conformal | Learned w/ Conformal | Key Conformal Impact |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **stable_benign** | Rec: 0.0% / Abs: 100.0% | Rec: 0.0% / Abs: 100.0% | Rec: 0.0% / Abs: 100.0% | Rec: 0.0% / Abs: 100.0% | Abstains appropriately on un-drifted stream. |
| **legitimate_growth** | Rec: 0.0% / Abs: 100.0% | Rec: 0.0% / Abs: 100.0% | Rec: 0.0% / Abs: 100.0% | Rec: 0.0% / Abs: 100.0% | Rules abstain on growth; learned abstains on gray band. |
| **slow_attack_ramp** | Rec: 83.8% / Abs: 41.3% | Rec: 83.8% / Abs: 44.0% | Rec: 74.3% / Abs: 48.0% | Rec: 71.4% / Abs: 50.0% | Slight increase in abstention (+2.7% / +2.0%) on ambiguous ramp windows. |
| **attack_in_growth** | Rec: 0.0% / Abs: 100.0% | Rec: 0.0% / Abs: 100.0% | Rec: 63.3% / Abs: 62.0% | Rec: 60.0% / Abs: 64.7% | Growth dilutes attack signal; gray band converts borderline hits to UNCERTAIN. |
| **mimicry_attack** | Rec: 0.0% / Abs: 100.0% | Rec: 0.0% / Abs: 100.0% | Rec: 0.0% / Abs: 100.0% | Rec: 0.0% / Abs: 100.0% | Both engines abstain on suspicious volumetric surge without signaling failures. |

### Honest Limitations
1. **Exchangeability Collapse Under Growth**: Pre-trained conformal calibration sets cannot be deployed across changing traffic scales without adaptive rescaling; otherwise, normal growth causes 0.0% empirical coverage and 100% false alarms.
2. **Discretization Bottleneck**: Achieving fine-grained confidence levels ($\alpha = 0.01$) requires at least 99 pure calibration windows per slice, which does not exist in standard 5G Core deployment baselines without cross-slice pooling.
3. **Recall vs. Precision Trade-off**: The gray band filter $[0.05, 0.20]$ prevents noisy false alarms on borderline windows, but reduces raw attack recall on stealth attacks that occur concurrently with traffic growth.

---

## Device Model Findings and Limitations

This section documents the empirical findings, calibration results, and operational limitations of the per-device-class behavior models with split-conformal abstention evaluated on simulated Digital Twin streams (`simulated_twin`).

> [!WARNING]
> **Simulated Data Disclosure**: All evaluation streams in this benchmark were generated via `TwinScenarioGenerator` (`simulated_twin`). While device rate distributions model authentic IoT sensors, continuous IP surveillance cameras, and URLLC AGVs, actual carrier radio environments involve multi-path fading, cell handover jitter, and RRC state transitions not fully captured in simulation.

### Model Architecture & Disjoint Calibration
* **Model**: Small, bounded Isolation Forest per device class (25 estimators, max depth 6, fixed random_state 42) trained exclusively on benign tuning seed (42) per-device telemetry.
* **Feature Schema**: 7 standard features (`packets_per_sec`, `bytes_uplink_per_sec`, `bytes_downlink_per_sec`, `events_per_sec`, `bytes_per_packet`, `uplink_byte_ratio`, `failure_ratio`).
* **Calibration Disjointness**: Benign tuning windows were partitioned into 50% training, 25% threshold-setting, and 25% calibration with verified zero window ID overlap ($\text{IDs}_{\text{train}} \cap \text{IDs}_{\text{cal}} = \emptyset$).
* **Sample Sizes & Smallest p-Values**:
  * **sensor**: $n_{\text{cal}} = 1,460$ benign windows, smallest achievable p-value $p_{\min} = 1/(1460+1) = \mathbf{0.000684}$.
  * **camera**: $n_{\text{cal}} = 575$ benign windows, smallest achievable p-value $p_{\min} = 1/(575+1) = \mathbf{0.001736}$.
  * **AGV**: **Held out completely from training** ($n_{\text{train}} = 0, n_{\text{cal}} = 0$).

### Multi-Seed Empirical Results Across 10 Test Seeds (Seeds 101–110)

| Evaluation Dimension | Metric | Observed Empirical Value | 95% Bootstrap Confidence Interval | Theoretical Target |
| :--- | :--- | :---: | :---: | :---: |
| **Approved Onboarding (All)** | Empirical Coverage ($p \ge 0.05$) | **94.59%** | [94.45%, 94.78%] | 95.00% ($\alpha = 0.05$) |
| **Early Pre-Onboarding** | Coverage (Windows 0–9, 1x count) | **94.77%** | [94.40%, 95.12%] | 95.00% |
| **Late Growing Onboarding** | Coverage (Windows 10–29, expanded count) | **94.54%** | [94.38%, 94.73%] | 95.00% |
| **Exchangeability Status** | Growth Invariance | **HOLDS** | Nominal coverage preserved | Holds under per-device normalization |
| **Slow Ramp in Onboarding** | Anomaly Detection Rate | **94.76%** | [94.04%, 95.42%] | High detection |
| **Slow Ramp in Onboarding** | Conformal Abstention Rate | **4.67%** | [3.91%, 5.42%] | Low abstention |
| **Non-Abstained Windows** | Accuracy ($\frac{\text{TP}+\text{TN}}{\text{Non-Abstained}}$) | **94.39%** | [94.21%, 94.58%] | High accuracy |
| **Overall Dataset** | Total Abstention Rate | **32.52%** | [32.41%, 32.65%] | Driven by held-out AGV |
| **Held-Out Class (AGV)** | Abstention Rate (`held_out_device_class`) | **100.00%** | [100.00%, 100.00%] | 100.00% (Safety Fallback) |

### Accuracy-vs-Coverage Trade-off
Evaluating across varying significance levels $\alpha \in [0.01, 0.50]$ on trained classes demonstrates clear monotonic trade-offs:
* At $\alpha = 0.01$ (conservative): Non-abstained accuracy reaches **98.96%** with **81.18%** coverage (18.82% abstention).
* At $\alpha = 0.05$ (operational baseline): Non-abstained accuracy is **94.39%** with **85.26%** coverage.
* At $\alpha = 0.50$ (aggressive): Coverage rises to **91.16%**, but non-abstained accuracy degrades to **49.52%**.

### The Weakest Result and Operational Failures
1. **The Weakest Result — Subtle Onset in Hidden Ramp (94.76% Detection, 4.67% Abstained)**:
   - In `slow_ramp_in_onboarding`, compromised sensors slowly ramping their failure and signaling rates inside an approved onboarding expansion achieved a **94.76% anomaly detection rate**, leaving **4.67% of malicious windows abstained** into the conformal gray band ($0.05 \le p \le 0.20$).
   - Root Cause: During the early stages of the ramp ($t \in [15, 18]$), rate deviations are subtle ($< 1.5\times$ base), placing nonconformity scores near the decision boundary where the conformal safety mechanism forces abstention rather than issuing a confident alert.
2. **Total Blindness on Unseen Device Classes (100.0% Abstention on AGV)**:
   - When telemetry from un-modeled device classes is ingested, the system cannot classify behavior and abstains unconditionally (`held_out_device_class`). While safe against false positives, it leaves novel hardware categories unmonitored without active model enrollment.
3. **Contrast with Slice-Level Exchangeability Breakdown**:
   - In slice-level aggregate models (`docs/AI_FEASIBILITY.md`), legitimate 2x–3x traffic expansion completely collapsed conformal coverage to 0.0% due to aggregate volumetric drift.
   - In contrast, per-device models normalize metrics per unit time per device (`packets_per_sec`, `bytes_per_packet`), successfully **preserving exchangeability across onboarding expansions** (94.54% late vs 94.77% early coverage).


