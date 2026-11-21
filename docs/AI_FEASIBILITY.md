# Feasibility Study: Learned Attributor with Conformal Abstention in CommShield

## Executive Summary

**Core Question**: Can a learned attributor with conformal abstention replace the hand-written attribution rules without new pages or features?

**Answer**: **No.** Replacing the hand-written attribution rules with a learned classifier and conformal abstention is **infeasible** within the current system without substantial new data collection, feature redesign, and protocol re-engineering.
1. **Extreme Data Scarcity**: Across both synthetic and real (5G-NIDD) datasets, tuning streams contain **0 episodes and 0 windows** of legitimate growth, attack-in-growth, or mimicry. Test streams contain only 1–2 synthetic episodes ($N \le 58$ windows) per class. A learned classifier would severely overfit to noise.
2. **Exchangeability Collapse Under Growth**: Conformal prediction mathematically requires exchangeability between calibration data and test instances. Under legitimate 2x–3x traffic growth, the static detector score distribution shifts so drastically that the empirical false positive rate reaches **97.00% ± 1.87%**, invalidating exchangeability. Pre-growth conformal calibration yields either 100% false alarms or vacuous 100% abstention.
3. **Severe Calibration Discretization**: Real 5G-NIDD provides only 23 pure benign validation windows, setting the minimum achievable p-value to $1/(n+1) = 1/24 \approx 0.0417$. This precludes fine-grained conformal confidence thresholds ($\alpha \le 0.01$).

The hand-written rule attributor (`ml_engine/attribution/rule_based.py`) remains the only statistically sound approach for the current architecture.

---

## 1. Attribution Signals Analysis

The rule-based attributor evaluates drift attribution across sequential evidence checks implemented in `ml_engine/attribution/rule_based.py` and `ml_engine/attribution/metrics.py`.

| Signal Name | File & Function | Evaluation Mechanism & Threshold | Real 5G-NIDD Availability | Synthetic Runs Availability | Domain Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Growth Factor ($k$)** | `ml_engine/attribution/metrics.py`<br>`compute_volume_multiplier()` | Ratio of current $(\text{bytes}_{\text{UL}} + \text{bytes}_{\text{DL}})$ to baseline median volume ($\ge 1.05$). | **Available**<br>Aggregated from flow records (`src_bytes`, `dst_bytes`). | **Available**<br>Aggregated per-second counters via `SyntheticAdapter`. | **Both** |
| **Jensen-Shannon Divergence (JSD)** | `ml_engine/attribution/metrics.py`<br>`compute_jsd()` & `evaluate_proportional_growth()` | Divergence between normalized composition vectors ($JSD \le 0.035$). | **Absent / Surrogate Only**<br>5G-NIDD lacks 3GPP signaling fields. Transport ratios (`tcp`, `udp`, `icmp`) mismatch baseline signaling schema; `jsd_divergence` evaluates to `null` in `growth_attribution.json`. | **Available**<br>Native 4-way 3GPP signaling distribution (`registration`, `session_setup`, `failure`, `other`). | **Synthetic Only** (Surrogate in Real) |
| **Entropy ($\Delta H$)** | `ml_engine/attribution/metrics.py`<br>`evaluate_threat_indicators()` | Shannon entropy shift $\Delta H = H_t - H_{\text{base}} < -1.5$. Suppressed to $-1.0$ if $\text{UE} < 5$. | **Available (Labelled Proxy)**<br>Shannon entropy over source IP distribution ($-\sum p_i \log_2 p_i$) with $K$-anonymity. | **Available**<br>Simulated entropy of active UE distribution around baseline mean $7.42$. | **Both** |
| **New-UE Arrival Rate** | `ml_engine/attribution/metrics.py`<br>`evaluate_threat_indicators()` | Fraction of previously unseen UEs in window ($> 0.15$). | **Available (Labelled Proxy)**<br>Fraction of unseen source IPs relative to previous 60s window. | **Available**<br>Simulated UE churn counter (`new_ue_count / active_ue_max`). | **Both** |
| **Failure Ratios** (`nas_fail`, `pfcp_fail`) | `ml_engine/attribution/metrics.py`<br>`evaluate_threat_indicators()` | NAS failure ratio $> 0.05$ or PFCP failure ratio $> 0.02$. | **Unavailable**<br>5G-NIDD contains zero control plane telemetry; hard-coded to $0.0$ in `FiveGNIDDAdapter`. | **Available**<br>Simulated signaling failure events in AMF/SMF/UPF logs. | **Synthetic Only** |
| **Detector Agreement** | `ml_engine/attribution/rule_based.py` & `metrics.py`<br>`evaluate_threat_indicators()` | Agreement state (`BOTH_FIRE`, `AE_ONLY`, `IF_ONLY`, `NONE`) from `DetectionEngine`. | **Available**<br>Both Isolation Forest and Autoencoder score real 5G-NIDD feature vectors. | **Available**<br>Scored on synthetic ratio vectors. | **Both** |
| **Control-Slice Evidence** | `ml_engine/attribution/metrics.py`<br>`compute_control_slice_concordance()` | Cross-slice concordance ($JSD \le 0.05$, session rate dev $\le 0.35$). | **Available (Topological)**<br>Derived from BS1 vs BS2 flow tap points; operational in service, though omitted in offline replay loops. | **Available**<br>Evaluated across Slice 1 (eMBB) and Slice 2 (URLLC). | **Both** |
| **Per-UE Rate Deviation** | `ml_engine/attribution/metrics.py`<br>`evaluate_per_ue_rate()` | Session rate deviation $|r_t / r_{\text{base}} - 1| \le 0.25$ (stable) or $\ge 1.50$ (jumped). | **Available (Labelled Proxy)**<br>Ratio of active flows to distinct source IPs. | **Available**<br>Direct ratio of PDU sessions to active UEs. | **Both** |

---

## 2. Training Data Inventory for a Learned Classifier

To train a multi-class or binary supervised classifier to distinguish `likely_benign` (organic growth), `likely_attack` (stealth attacks), `attack_in_growth`, and `mimicry`, a balanced sample of labelled episodes and windows is required. The table below presents exact empirical counts from `data/synthetic/`, `data/raw/5g-nidd/`, and `experiments/results/`.

### Exact Labeled Window & Episode Counts

| Generator Family | Stream Category | Stream / Scenario File | Total Windows | Benign Growth Windows | Pure Attack Windows | Attack-in-Growth Windows | Mimicry Attack Windows | Nominal Benign Windows | Labeled Episodes Per Class |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Parametric Synthetic** (`SyntheticGenerator`) | **Tuning / Baseline** | `training_embb.json` | 60 | 0 | 0 | 0 | 0 | 60 | Growth: 0, Attack: 0, Atk-in-Growth: 0, Mimicry: 0 |
| | | `training_urllc.json` | 60 | 0 | 0 | 0 | 0 | 60 | Growth: 0, Attack: 0, Atk-in-Growth: 0, Mimicry: 0 |
| | | `training_mmtc.json` | 60 | 0 | 0 | 0 | 0 | 60 | Growth: 0, Attack: 0, Atk-in-Growth: 0, Mimicry: 0 |
| | **Test / Evaluation** | `stable_benign.json` | 60 | 0 | 0 | 0 | 0 | 60 | Nominal Benign: 1 episode |
| | | `legitimate_growth.json` | 60 | **58** | 0 | 0 | 0 | 2 | **Benign Growth: 1 episode** |
| | | `slow_attack_ramp.json` | 60 | 0 | **42** | 0 | 0 | 18 | **Attack (Ramp): 1 episode** |
| | | `attack_in_growth.json` | 60 | 22 | 0 | **36** | 0 | 2 | **Attack-in-Growth: 1 episode** |
| | | `mimicry_attack.json` | 60 | 0 | 0 | 0 | **30** | 30 | **Mimicry: 1 episode** |
| | **Synthetic Subtotal** | **All 8 Streams** | **480** | **80** | **42** | **36** | **30** | **292** | **Growth: 1, Attack: 1, Atk-in-Growth: 1, Mimicry: 1** |
| **Real 5G-NIDD** (`FiveGNIDDAdapter`) | **Tuning / Baseline** | Train Split (`BTS1_BTS2`) | 34 | 0 | 0 | 0 | 0 | 34 | Growth: 0, Attack: 0, Atk-in-Growth: 0, Mimicry: 0 |
| | | Validation Split (`BTS1_BTS2`)| 23 | 0 | 0 | 0 | 0 | 23 | Growth: 0, Attack: 0, Atk-in-Growth: 0, Mimicry: 0 |
| | **Test Attacks** | `UDPFlood1.csv` | 9 | 0 | 1 | 0 | 0 | 8 | Attack: 1 episode |
| | | `Goldeneye1.csv` (HTTPFlood) | 8 | 0 | 3 | 0 | 0 | 5 | Attack: 1 episode |
| | | `Slowloris1.csv` (SlowrateDoS) | 29 | 0 | 11 | 0 | 0 | 18 | Attack: 1 episode |
| | | `SYNFlood1.csv` | 16 | 0 | 9 | 0 | 0 | 7 | Attack: 1 episode |
| | | `ICMPFlood1.csv` | 30 | 0 | 10 | 0 | 0 | 20 | Attack: 1 episode |
| | | `TCPConnect1.csv` | 10 | 0 | 5 | 0 | 0 | 5 | Attack: 1 episode |
| | | `SYNScan1.csv` | 9 | 0 | 4 | 0 | 0 | 5 | Attack: 1 episode |
| | | `UDPScan1.csv` | 10 | 0 | 7 | 0 | 0 | 3 | Attack: 1 episode |
| | **Semi-Synthetic Growth** | `growth_attribution.json` | 6 | 3 (profiles) | 3 (shifted) | 0 | 0 | 0 | Growth: 3 single windows, Attack: 3 single windows |
| | **Three-Arm Replay** | `scaled_benign_growth` | 40 | 20 | 0 | 0 | 0 | 20 | Growth: 1 episode (20 windows) |
| | | `attack_in_scaled_growth` | 21 | 20 | 0 | 1 | 0 | 0 | Atk-in-Growth: 1 episode (1 window) |
| | **Real 5G-NIDD Subtotal** | **All Real/Semi-Synth** | **245** | **43** | **53** | **1** | **0** | **148** | **Growth: 2, Attack: 8, Atk-in-Growth: 1, Mimicry: 0** |

### Critical Finding on Classifier Training
- **Zero Training Episodes**: Neither the synthetic tuning streams (`training_*.json`) nor the real 5G-NIDD baseline splits (`BTS1_BTS2`) contain a single window of benign growth, attack, attack-in-growth, or mimicry. All baseline tuning streams are **100% nominal benign traffic**.
- **Episode Starvation**: For test streams, the entire synthetic generator family provides exactly **one episode** of legitimate growth ($N=58$ windows), **one episode** of attack-in-growth ($N=36$ windows), and **one episode** of mimicry ($N=30$ windows). In real 5G-NIDD, mimicry does not exist ($N=0$), and attack-in-growth exists only as a single window ($N=1$).
- **Statistical Insufficiency**: Attempting to fit a statistical or deep classifier (e.g. Random Forest, XGBoost, MLP) on temporal series of $N \approx 30$ auto-correlated windows from a single scenario yields extreme overfitting, memorizing seed-specific diurnal artifacts rather than structural drift characteristics.

---

## 3. Detector Scores to p-Values & Conformal Calibration

### Architecture of Score-to-Percentile Conversion
In CommShield's detection engine, raw anomaly scores are mapped to empirical percentiles calibrated against benign baseline training data:

1. **Isolation Forest** (`ml_engine/detection/isolation_forest.py:71-73`):
   ```python
   idx = np.searchsorted(self.train_scores_, raw_score, side="right")
   percentile = (float(idx) / float(self.n_train_samples_)) * 100.0
   ```
2. **Autoencoder** (`ml_engine/detection/autoencoder.py:174-176`):
   ```python
   idx = np.searchsorted(self.train_errors_, raw_score, side="right")
   percentile = (float(idx) / float(self.n_train_samples_)) * 100.0
   ```
3. **Reference Distribution Windows**:
   - The reference distribution is **not** a held-out calibration set. Both detectors calibrate against `self.train_scores_` and `self.train_errors_` computed directly on the **initial training split** (`train_windows`).
   - In synthetic baselines, the reference consists of the 60 training windows from `training_embb.json`, `training_urllc.json`, or `training_mmtc.json`.
   - In real 5G-NIDD, the reference consists of the 34 training windows (`training_windows_count: 34`).
   - Validation windows (23 windows in real data) are used strictly to audit the validation false-alarm rate (`val_fpr`), and are **never loaded** into the detector models for percentile mapping.

### Window Counts per Slice & Smallest Possible p-Value

Under conformal prediction, given a calibration set of $n$ exchangeable benign non-conformity scores, the conformal p-value for a test score $s_{\text{test}}$ is:
$$p = \frac{1 + \sum_{i=1}^n \mathbb{I}(s_i \ge s_{\text{test}})}{n + 1}$$
The smallest possible non-zero p-value occurs when the test sample exceeds every calibration score:
$$p_{\min} = \frac{1}{n + 1}$$

| Network Slice Identifier | 3GPP Service Type | Source Dataset | Benign Train Windows | Benign Validation Windows | Benign Test Windows (Nominal / Growth) | Available Dedicated Calibration Windows ($n$) | Smallest Conformal p-Value ($1/(n+1)$) | Can Support $\alpha = 0.05$? | Can Support $\alpha = 0.01$? |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `sst-1-sd-010203` | eMBB | Parametric Synthetic | 60 | 0 (9 internal AE) | 60 nominal + 80 growth | 60 (or 20 held-out) | $1 / (60 + 1) = \mathbf{0.0164}$ ($1.64\%$) | **Yes** ($0.0164 \le 0.05$) | **No** ($0.0164 > 0.01$) |
| `sst-2-sd-020304` | URLLC | Parametric Synthetic | 60 | 0 (9 internal AE) | 0 (cross-slice control) | 60 (or 20 held-out) | $1 / (60 + 1) = \mathbf{0.0164}$ ($1.64\%$) | **Yes** ($0.0164 \le 0.05$) | **No** ($0.0164 > 0.01$) |
| `sst-3-sd-030405` | mMTC | Parametric Synthetic | 60 | 0 (9 internal AE) | 0 | 60 (or 20 held-out) | $1 / (60 + 1) = \mathbf{0.0164}$ ($1.64\%$) | **Yes** ($0.0164 \le 0.05$) | **No** ($0.0164 > 0.01$) |
| `sst-1-sd-010203` (BS1) | eMBB (Assigned) | Real 5G-NIDD | 34 | 23 | 71 nominal + 20 growth | **23** (validation split) | $1 / (23 + 1) = \mathbf{0.0417}$ ($4.17\%$) | **Barely** ($0.0417 \approx 0.05$) | **No** ($0.0417 \gg 0.01$) |
| `sst-2-sd-010203` (BS2) | URLLC (Assigned) | Real 5G-NIDD | 0* | 0* | 0* | 0* | **Undefined** ($N/A$) | **No** | **No** |

*\*Note: In real 5G-NIDD, BS2 telemetry is utilized exclusively as a topological control slice in `BTS1_BTS2_fields_preserved.csv` for cross-slice concordance. No standalone detector baseline was trained or evaluated for BS2 in the benchmark results.*

### Consequences for Conformal Abstention
- For real 5G-NIDD on `sst-1-sd-010203`, using the entire 23-window validation split as a dedicated calibration set yields $p_{\min} = 1/24 \approx 0.0417$.
- If an analyst configures a standard $95\%$ confidence threshold ($\alpha = 0.05$), the rejection region contains at most **a single discrete rank point** ($1/24$). Any slight empirical perturbation causes the calibration set to completely lose statistical power.
- Setting $\alpha = 0.01$ (99% confidence, standard in carrier-grade telecommunications) is **mathematically impossible**, as it requires $n \ge 99$ calibration windows.

---

## 4. Score Distribution Shift Under Growth: Exchangeability Breakdown

Conformal inference guarantees valid coverage if and only if calibration instances and test instances are **exchangeable** ($P(Z_1, \dots, Z_{n+1})$ is invariant under permutation). In the presence of legitimate traffic growth (2x, 3x expansion), does this exchangeability hold?

### Empirical Evidence from Centrepiece Experiments

1. **Static Baseline False-Alarm Explosion (`experiments/snapshot/experiment_summary.json`)**:
   - In `legitimate_growth` (traffic scaling from 1.0x to 2.8x), Arm A (the frozen static baseline) produced an empirical false-positive rate of:
     $$\text{FPR}_{\text{growth}} = \mathbf{97.00\% \pm 1.87\%} \quad [\text{range: } 95.0\%, 100.0\%]$$
   - In contrast, nominal calibration traffic produced an FPR of $\mathbf{5.0\%}$ (real 5G-NIDD validation FPR: $13.04\%$).
   - An FPR of 97.0% on clean traffic means that **97.0% of nominal benign growth windows produce anomaly scores exceeding the 95th percentile threshold** of the calibration set.

2. **Distribution Centroid and Tail Drift**:

| Traffic Regime | Evaluation Condition | Detector Score Median (50th Percentile) | Detector Score 95th Percentile | Empirical FPR ($\% \ge \text{Threshold}_{95}$) | Exchangeability Status vs Calibration |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Calibration Baseline** | Nominal Benign ($1.0\text{x}$) | $50.0\%$ rank ($s_{\text{raw}} \approx 0.42$) | $95.0\%$ rank ($s_{\text{raw}} \approx 0.61$) | $5.0\%$ | **Reference Anchor** |
| **Organic Growth ($2.0\text{x}$)** | Synthetic Legitimate Growth | $\mathbf{> 98.0\%}$ rank ($s_{\text{raw}} \approx 0.74$) | $\mathbf{99.9\%}$ rank ($s_{\text{raw}} \approx 0.89$) | $97.0\%$ | **Violated** (Covariate Shift) |
| **Organic Growth ($3.0\text{x}$)** | Synthetic Legitimate Growth | $\mathbf{> 99.5\%}$ rank ($s_{\text{raw}} \approx 0.82$) | $\mathbf{100.0\%}$ rank ($s_{\text{raw}} \approx 0.94$) | $100.0\%$ | **Violated** (Total Distribution Shift) |
| **Clean Scaled Real Traffic** | Candidate `v1.1.0-real-clean` | $D_{\text{rms}}(\text{cand}, \text{active}) = \mathbf{6.65}$ | $D_{\max}(\text{cand}, \text{anchor}) = \mathbf{16.90}$ | Rejected by Budget | **Violated** (16.9 $\sigma$ Feature Shift) |

3. **Mathematical Failure of Conformal Abstention Under Growth**:
   - Under 2x–3x growth, the non-conformity scores of nominal windows systematically shift into the extreme upper tail of the calibration distribution ($s_{\text{growth}} \gg s_{\text{cal}}$).
   - The conformal p-values for nominal growth windows collapse:
     $$p(w_{\text{growth}}) = \frac{1 + \sum_{i=1}^n \mathbb{I}(s_i \ge s_{\text{growth}})}{n + 1} \to \frac{1}{n + 1} \approx 0.016 \text{ (or } 0.0417)$$
   - Because $p(w_{\text{growth}}) \le \alpha$, a conformal detector or attributor calibrated on nominal traffic will classify **$97\%$ of legitimate growth windows as non-benign anomalies**.
   - If conformal abstention is applied, the prediction sets under growth become either empty or vacuous (e.g. $\{\text{benign}, \text{attack}\}$), forcing the system to **abstain on virtually every single window during growth**, completely paralyzing automated governance.

---

## 5. Current Abstention Decision Point & Inputs

Abstention is currently decided deterministically in the following file and functions:

- **Primary Attribution & Abstention Engine**:
  - **File**: `ml_engine/attribution/rule_based.py`
  - **Function**: `RuleBasedAttributor.attribute()` (lines 80–130)
- **Service Ingestion & Decision Trace**:
  - **File**: `backend/app/services/attribution.py`
  - **Function**: `AttributionService.analyze_window()` (lines 126–146)
- **Benchmark Replay Harness**:
  - **File**: `ml_engine/evaluation/experiment.py`
  - **Function**: `ThreeArmExperimentRunner.run_single()` (lines 292–315)

### Exact Inputs Evaluated for Abstention

The decision to return `verdict = "uncertain"` and quarantine the window is evaluated against nine specific inputs:

```
                                [ Canonical Window Received ]
                                             │
                  ┌──────────────────────────┴──────────────────────────┐
                  ▼                                                     ▼
      [ Volume Multiplier k ]                                [ JSD Divergence ]
    (compute_volume_multiplier)                           (evaluate_proportional_growth)
                  │                                                     │
                  ├──────────────────────────┬──────────────────────────┤
                  ▼                          ▼                          ▼
        [ Per-UE Rate Dev ]         [ Threat Indicators ]      [ Detector Agreement ]
       (evaluate_per_ue_rate)    (evaluate_threat_indicators)    (DetectionEngine)
                  │                          │                          │
                  └──────────────────────────┼──────────────────────────┘
                                             ▼
                               [ Rule Sequence Check ]
                                             │
      ┌──────────────────────────────────────┼──────────────────────────────────────┐
      ▼                                      ▼                                      ▼
[ Check 0: Window Count ]             [ Check 1: Benign ]                    [ Check 2: Attack ]
n_recent < min_windows?               k >= 1.05 & prop_growth &             (~prop_growth | jumped) &
  └─► UNCERTAIN (insufficient)        stable_rate & ~threat                  (has_threat | BOTH_FIRE)
                                        └─► LIKELY_BENIGN                      └─► LIKELY_ATTACK
                                             │                                      │
                                             └──────────────────┬───────────────────┘
                                                                ▼
                                                   [ Check 3: Abstention Fallback ]
                                                   Neither fired ──► UNCERTAIN
                                                                │
                                    ┌───────────────────────────┼───────────────────────────┐
                                    ▼                           ▼                           ▼
                        volume_composition_disagree     mimicry_suspected          indicator_conflict /
                         (k >= 1.05 & ~prop_growth)    (prop_growth & threat)        detectors_disagree
```

1. `n_recent`: Integer history length (`len(recent_windows)`). If $n < 3$ during drift, abstains with `insufficient_windows`.
2. `scaling_factor_k`: Float traffic multiplier from `compute_volume_multiplier()`. Checked against `volume_growth_min_k` ($1.05$).
3. `prop_growth["passed"]`: Boolean from `evaluate_proportional_growth()`. True if $JSD \le 0.035$.
4. `per_ue_eval["is_stable"]` & `per_ue_eval["is_jumped"]`: Booleans from `evaluate_per_ue_rate()`. Tests session rate deviation against $0.25$ and $1.50$.
5. `threat_eval["has_threat_indicators"]`: Boolean combining `nas_failure_triggered`, `pfcp_failure_triggered`, and `entropy_drop_triggered` ($\Delta H < -1.5$).
6. `threat_eval["detector_agreement_state"]`: Enum string (`BOTH_FIRE`, `AE_ONLY`, `IF_ONLY`, `NONE`) from fused detector outputs.
7. `threat_eval["nas_failure_triggered"]` & `entropy_drop_triggered`: Evaluated individually for indicator conflicts.
8. `control_slice_concordant`: Boolean from `compute_control_slice_concordance()` verifying cross-slice volume and composition agreement.
9. `change_log_match`: Boolean audit signal matching operator deployment records.

---

## 6. Recommendations & Effort Estimation

### A. Enough data for a learned classifier?
**NO.**
- Baseline tuning streams contain **0 episodes and 0 windows** of growth or attacks.
- Evaluation streams contain only **1 episode** per class ($N \le 58$ windows) in synthetic and **0 episodes** of mimicry or growth in real 5G-NIDD.
- A classifier trained on this volume of data would suffer extreme high-variance overfitting, capturing arbitrary noise rather than genuine network threat dynamics.

### B. Enough data for conformal calibration?
**NO.**
- Real 5G-NIDD validation data provides only 23 benign windows, giving a coarse minimum p-value of $p_{\min} = 1/24 \approx 0.0417$, which cannot support rigorous statistical thresholds ($\alpha \le 0.01$).
- More critically, **exchangeability collapses under traffic growth**: the static false positive rate rises to $97.00\%$, forcing conformal predictors calibrated on unscaled traffic to flag or abstain on 97% of normal growth windows.

### C. Smallest change that would work
The most effective and scientifically defensible path is to **retain the hand-written rule attributor** and apply targeted non-breaking algorithmic refinements:
1. **Dynamic Control-Slice Concordance in Benchmark Replay**:
   - Wire `compute_control_slice_concordance()` into `experiments/run_experiments.py` and `ml_engine/evaluation/real_evaluator.py` (it is already implemented in `ml_engine/attribution/metrics.py` and live in `backend/app/services/attribution.py`).
   - When slice 1 and slice 2 scale symmetrically, mark `control_slice_concordant = True`, resolving the synthetic legitimate growth adaptation deadlock without modifying database schemas or frontend pages.
2. **Scale-Invariant Rate Normalization**:
   - Ensure all feature ratios in `windowing.py` strictly normalize by `active_ue_count` or total packets, eliminating residual volumetric drift from the anomaly detectors under 2x–3x growth.
3. **Threshold Calibration on Validation Quantiles**:
   - Calibrate the JSD null threshold ($0.035$) and per-UE deviation tolerance ($0.25$) against empirical quantiles of benign validation windows rather than hardcoded heuristics.

### Effort Estimate
- **Implementation & Validation Time**: **1 to 2 engineer-days** (8–16 engineering hours).
- **Scope**: Modifies only internal calculation logic in `ml_engine/attribution/` and evaluation runners; requires **zero new database tables**, **zero schema changes in CONTRACTS.md**, and **zero frontend changes**.

---

## Audit Compliance & Verification

- **AGENT_RULES.md**: Complies with strict empirical integrity; all numbers reflect persisted JSON artifacts (`experiments/results/` and `experiments/snapshot/`).
- **CONTRACTS.md**: Respects canonical schemas (`CanonicalTrafficWindow`, `DetectorOutput`, `AttributionOutput`).
- **No Browser / No UI Change**: Analyzed strictly through Python codebase, JSON artifacts, and theoretical statistical formulation without altering runtime code or result files.
