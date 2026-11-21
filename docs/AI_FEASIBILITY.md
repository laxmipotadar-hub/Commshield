# Feasibility Analysis: Learned Attributor with Conformal Abstention

## 1. Executive Summary

This document evaluates whether a learned statistical or machine learning classifier equipped with conformal prediction abstention can feasibly replace CommShield's existing rule-based drift attributor (`RuleBasedAttributor`) without requiring new UI pages, database schema migrations, or additional feature pipelines.

**Verdict**:
* **Learned Classifier Feasibility**: **NO**. The dataset lacks sufficient sample volume, episode diversity, and class balance (0 real growth/mimicry episodes; exactly 1 synthetic episode per class from a single generator family). Any supervised classifier would catastrophically overfit to generator artifacts.
* **Conformal Calibration Feasibility**: **NO**. The available calibration pool ($n = 23$ benign validation windows in real data) yields a minimum p-value resolution of $p_{\min} = 1/(n+1) = 0.0417$ (4.17%), making statistical control at $\alpha \le 0.01$ mathematically impossible. Crucially, benign traffic growth severely violates the foundational **exchangeability** assumption: detector anomaly scores on scaled benign traffic shift into the extreme upper tail (100th percentile), collapsing conformal validity.
* **Recommendation**: Retain the interpretable rule-based structure and augment it with margin-based score smoothing rather than a learned model.

---

## 2. Attribution Signals Inventory

CommShield's attribution engine evaluates 7 primary signals across drift and anomaly events:
* **Implementation Source**: `ml_engine/attribution/rule_based.py` (`RuleBasedAttributor.attribute()`) and `ml_engine/attribution/metrics.py`.

| Signal Name | Source Function & File | Description / Formula | Real 5G-NIDD Availability | Synthetic Telemetry Availability |
| :--- | :--- | :--- | :---: | :---: |
| **JSD (Jensen-Shannon Divergence)** | `compute_jsd()` & `evaluate_proportional_growth()` (`metrics.py:10-85`) | Symmetric divergence between current composition vector and baseline reference with pseudo-count smoothing ($10^{-5}$) and null threshold ($\le 0.035$). | **Available** (Layer-4 protocols: TCP, UDP, ICMP, other) | **Available** (Signalling events: registration, PDU setup, failure, other) |
| **Growth Factor ($k$)** | `compute_volume_multiplier()` (`metrics.py:41-62`) | Ratio of current total byte volume ($\text{UL} + \text{DL}$) to baseline mean volume: $k = V_{\text{cur}} / V_{\text{base}}$. | **Available** (Derived from flow byte counters) | **Available** (Derived from aggregated session bytes) |
| **UE Hash Entropy Shift ($\Delta H$)** | `evaluate_threat_indicators()` (`metrics.py:145-200`) | Difference between current window client identifier Shannon entropy and baseline median ($H_{\text{cur}} - H_{\text{base}}$). Suppressed to $-1.0$ when active UEs $< 5$. | **Available** (Shannon entropy of HMAC-pseudonymised client IPs) | **Available** (Parametric entropy generator, nominal $\approx 7.42$) |
| **New-UE Arrival Rate** | `evaluate_threat_indicators()` (`metrics.py:145-200`) | Ratio of previously unseen UE identifiers to total active UEs in the current window. Flagged when $> 0.15$. | **Available** (Tracked via `_previous_ues_by_slice` across sliding windows) | **Available** (Generated Poisson arrival process) |
| **Control-Plane Failure Ratios** | `evaluate_threat_indicators()` (`metrics.py:145-200`) | Ratios of failed signalling procedures: `nas_failure_ratio` and `pfcp_failure_ratio`. Flagged when $> 0.02$. | **Unavailable** (Fixed to `0.0` / labelled proxy; control-plane absent from NetFlow logs) | **Available** (Parametric signalling failure counts) |
| **Detector Agreement State** | `evaluate_threat_indicators()` (`metrics.py:170-173`) | Consensus state between Isolation Forest and Autoencoder (`both_fired`, `only_isolation_forest`, `only_autoencoder`, `neither`). | **Available** (Evaluated from dual detector percentiles) | **Available** (Evaluated from dual detector percentiles) |
| **Control-Slice Concordance** | `compute_control_slice_concordance()` (`metrics.py:111-143`) | Concordance boolean verifying if Slice 2 (URLLC) composition and session rate deviate in tandem with Slice 1 (eMBB). | **Available** (BS2 vs BS1 comparative evaluation) | **Available** (Multi-slice synthetic streams) |

---

## 3. Training Data Audit for a Learned Classifier

To train a multi-class or one-class supervised classifier (e.g. Random Forest, Gradient Boosted Trees, MLP) to classify window events into `benign_growth`, `attack`, `attack_during_growth`, or `mimicry`, the dataset must contain distinct, diverse episodes.

### A. Real Data Stream (5G-NIDD)
* **Tuning Streams**: None. Only a single 23-window validation split exists.
* **Test Streams**: 8 individual attack campaign files.

| Class | Labelled Episodes | Total Windows | Attack Windows | Benign Windows | Generator / Capture Family |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Stable Benign (Train)** | 1 | 34 | 0 | 34 | Real 5G testbed capture (`BTS1_BTS2_fields_preserved.csv`) |
| **Stable Benign (Validation)** | 1 | 23 | 0 | 23 | Real 5G testbed capture (`BTS1_BTS2_fields_preserved.csv`) |
| **Benign Growth** | **0** | **0** | 0 | 0 | **None** (Only semi-synthetic static multiplier available) |
| **Attack (DoS / PortScan)** | 8 | 121 | 50 | 71 | Real 5G testbed attacks (`BS1_each_attack_csv/`) |
| **Attack During Growth** | **0** | **0** | 0 | 0 | **None** |
| **Mimicry Attack** | **0** | **0** | 0 | 0 | **None** |

### B. Synthetic Data Streams (`data/synthetic/`)
* **Tuning Streams**: **0** (No separate tuning stream files exist; all files are test scenarios).
* **Generator Families**: **1** (`SyntheticGenerator` in `ml_engine/preprocessing/synthetic_generator.py`). Zero held-out generator families.

| Class | Scenario File | Labelled Episodes | Total Windows | Attack Windows | Benign Windows | Growth Windows |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Clean Baseline (eMBB)** | `training_embb.json` | 1 | 60 | 0 | 60 | 0 |
| **Clean Baseline (URLLC)** | `training_urllc.json` | 1 | 60 | 0 | 60 | 0 |
| **Clean Baseline (mMTC)** | `training_mmtc.json` | 1 | 60 | 0 | 60 | 0 |
| **Stable Benign** | `stable_benign.json` | 1 | 60 | 0 | 60 | 0 |
| **Benign Growth** | `legitimate_growth.json` | 1 | 60 | 0 | 2 | 58 |
| **Slow Attack Ramp** | `slow_attack_ramp.json` | 1 | 60 | 42 | 18 | 0 |
| **Attack During Growth** | `attack_in_growth.json` | 1 | 60 | 36 | 2 | 22 (growth + attack) |
| **Mimicry Attack** | `mimicry_attack.json` | 1 | 60 | 30 | 30 | 0 |

### Audit Summary
Across both real and synthetic sources, there is **exactly 1 synthetic episode per dynamic class** and **0 real episodes** for growth or mimicry. Training a machine learning classifier on 1 episode per class guarantees catastrophic overfitting to arbitrary parameter constants (such as synthetic noise standard deviations or specific diurnal phases) rather than genuine traffic dynamics.

---

## 4. Detector Scores to p-Values & Calibration Constraints

### Current Percentile Mapping Mechanism
* **Implementation**: `IsolationForestDetector.score_percentile()` (`ml_engine/detection/isolation_forest.py:66-73`) and `AutoencoderDetector.score_percentile()` (`ml_engine/detection/autoencoder.py:169-176`).
* **Reference Windows**:
  ```python
  idx = np.searchsorted(self.train_scores_, raw_score, side="right")
  percentile = (float(idx) / float(self.n_train_samples_)) * 100.0
  ```
  The reference windows are the **training windows** used to fit the model (`self.train_scores_`), not a held-out calibration set. This represents an in-sample empirical cumulative distribution function (eCDF), not a conformal p-value.

### Conformal Prediction Mathematical Requirement
In split conformal prediction, given $n$ held-out benign calibration non-conformity scores $\{s_1, \dots, s_n\}$, the valid p-value for a new test score $s_{n+1}$ is:
$$p(s_{n+1}) = \frac{1 + \sum_{i=1}^n \mathbf{1}(s_i \ge s_{n+1})}{n + 1}$$
The minimum non-zero p-value resolution is bounded from below by:
$$p_{\min} = \frac{1}{n + 1}$$

### Per-Slice Window Breakdown & Minimum p-Value Resolution

| Slice ID / Description | Source Domain | Training Windows ($n_{\text{train}}$) | Available Benign Validation Windows ($n_{\text{val}}$) | Benign Test Windows ($n_{\text{test}}$) | Potential Calibration Size ($n$) | Smallest Possible p-Value ($1/(n+1)$) | Can Support $\alpha = 0.01$? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`sst-1-sd-010203` (eMBB)** | Real 5G-NIDD | 34 | 23 | 71 | 23 | **0.04167 (4.17%)** | **NO** |
| **`sst-2-sd-010203` (URLLC)** | Real 5G-NIDD | 34 | 23 | 71 | 23 | **0.04167 (4.17%)** | **NO** |
| **`sst-3-sd-010203` (mMTC)** | Real 5G-NIDD | 0 | 0 | 0 | 0 | **N/A** | **NO** |
| **`sst-1-sd-010203` (eMBB)** | Synthetic | 60 | 0 (or 30 split) | 120 | 30 | **0.03226 (3.23%)** | **NO** |
| **`sst-2-sd-010203` (URLLC)** | Synthetic | 60 | 0 (or 30 split) | 0 | 30 | **0.03226 (3.23%)** | **NO** |
| **`sst-3-sd-010203` (mMTC)** | Synthetic | 60 | 0 (or 30 split) | 0 | 30 | **0.03226 (3.23%)** | **NO** |

**Conclusion on Sample Size**: With only 23 benign validation windows in real data, the smallest attainable p-value is **4.17%**. An operator cannot set a standard 1% or 0.1% false-discovery rate under split conformal prediction without hundreds of additional benign calibration windows.

---

## 5. Exchangeability Breakdown Under Benign Growth

Conformal prediction guarantees finite-sample coverage **if and only if** the calibration data and test data are **exchangeable** (i.i.d. or permutation-invariant).

To verify whether exchangeability holds when traffic expands, we scored real 5G-NIDD calibration windows against scaled benign windows (2.0x and 3.0x growth) using the frozen real anchor baseline (`v1.0.0-anchor-real`):

### Score Distribution Comparison (Real 5G-NIDD)

| Telemetry Condition | Sample Count ($n$) | Isolation Forest Raw Median | Isolation Forest Raw 95th | Autoencoder Reconstruction Median | Autoencoder Reconstruction 95th | Ensemble Fused Percentile Median | Ensemble Fused Percentile 95th |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Calibration (Val Baseline)** | 23 | **0.4573** | **0.6258** | **0.0919** | **7.7812** | **76.5%** | **100.0%** |
| **2.0x Scaled Benign Traffic** | 23 | **0.5838** | **0.6258** | **1.2899** (+1,304%) | **7.7519** | **100.0%** | **100.0%** |
| **3.0x Scaled Benign Traffic** | 23 | **0.5838** | **0.6258** | **3.5476** (+3,760%) | **8.0559** | **100.0%** | **100.0%** |

### Synthetic Telemetry Comparison (`legitimate_growth.json`)
* **Synthetic Training Baseline ($n=60$)**: Isolation Forest median = `0.5557`, 95th = `0.5627`.
* **Legitimate Growth Stream ($n=60$)**: Under unadapted baseline evaluation, 100.0% of legitimate growth windows receive fused percentiles of `100.0%`.

### Analytical Implication
Under traffic growth, absolute packet/byte volumes shift feature distributions. Even when composition is strictly preserved, non-linear deep reconstruction error (Autoencoder MSE) increases by **13x to 38x**, shifting scores directly into the extreme upper tail of the calibration distribution.
* **Exchangeability is completely broken**: $P(S_{\text{test}} \mid \text{growth}) \ne P(S_{\text{cal}} \mid \text{nominal})$.
* Consequently, conformal p-values for legitimate benign growth collapse to $p = \frac{1}{n+1} \approx 0.0417$. A conformal predictor would classify legitimate growth as a statistically significant anomaly ($p < 0.05$), failing to distinguish growth from attacks.

---

## 6. Current Abstention Architecture

CommShield's abstention mechanism is implemented in:
* **File**: `ml_engine/attribution/rule_based.py`
* **Function**: `RuleBasedAttributor.attribute()` (lines 78–130)

### Inputs Evaluated
1. `recent_windows`: Sequence history length $N$. If $N < 3$ during an active ADWIN drift alarm, the system abstains immediately with `INSUFFICIENT_WINDOWS`.
2. `scaling_factor_k`: Current volume expansion multiplier.
3. `prop_growth["passed"]`: Boolean indicating whether JSD divergence $\le 0.035$.
4. `per_ue_eval`: Per-UE session rate deviation ($|r_{\text{cur}}/r_{\text{base}} - 1| \le 0.25$).
5. `threat_eval`: Domain threat signals (NAS failure $> 0.02$, PFCP failure $> 0.02$, entropy drop $< -0.80$, new-UE rate $> 0.15$).
6. `detector_agreement_state`: Consensus state between Isolation Forest and Autoencoder.

### Abstention Taxonomy (Strict Order)
When evidence does not satisfy `likely_benign` (Check 1) or `likely_attack` (Check 2), the system assigns `verdict = UNCERTAIN`, sets `action = QUARANTINE`, and maps the conflict to one of five explicit, auditable failure modes:
1. `VOLUME_COMPOSITION_DISAGREE`: Volume expanded ($k \ge 1.2$) but protocol composition shifted ($JSD > 0.035$) without triggering threat indicators.
2. `MIMICRY_SUSPECTED`: Composition preserved ($JSD \le 0.035$) but specific threat indicators (entropy drop or signalling failures) fired.
3. `INDICATOR_CONFLICT`: Disagreement among threat signals (e.g. NAS failure ratio spike without corresponding entropy drop).
4. `DETECTORS_DISAGREE`: Single-detector split (`only_isolation_forest` or `only_autoencoder`).
5. `INCONCLUSIVE_GROWTH_PATTERN`: Marginal drift failing both stability and attack criteria.

---

## 7. Recommendations & Implementation Effort

### Summary Recommendations
* **(a) Enough data for a learned classifier?** **NO.** There are 0 real growth/mimicry episodes and only 1 synthetic episode per class. Supervised classifiers cannot generalize on this sample size.
* **(b) Enough data for conformal calibration?** **NO.** $n = 23$ calibration windows limits p-value resolution to $4.17\%$, and benign growth destroys the exchangeability assumption, causing legitimate growth to fail conformal validation.
* **(c) Smallest change that would work**:
  Retain the rule-based decision tree and add **margin-based score smoothing** across the two primary continuous statistics:
  1. Define a continuous growth confidence:
     $$C_{\text{growth}} = 1.0 - \min\left(1.0, \frac{\text{JSD}}{0.035}\right)$$
  2. Define an attack indicator score:
     $$S_{\text{threat}} = \max\left(\frac{\text{nas\_fail}}{0.02}, \frac{-\Delta H}{0.80}\right)$$
  3. Abstain when $|C_{\text{growth}} - S_{\text{threat}}| < \epsilon$ (ambiguity margin $\epsilon = 0.20$), outputting the existing named abstention reasons.

### Effort Estimate
* **Implementation**: 1 engineer, ~1.5 days.
* **Scope**: Modifies ~50 lines within `ml_engine/attribution/rule_based.py` and `ml_engine/attribution/metrics.py`.
* **Zero Disruption**: Requires **0** database migrations, **0** API contract changes, and **0** frontend updates (preserves `CONTRACTS.md` `AttributionOutput` and decision trace formats).
