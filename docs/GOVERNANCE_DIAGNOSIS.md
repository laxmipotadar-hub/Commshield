# Governance Diagnosis: Why the Clean Scaled Candidate Failed

**Investigation Target**: Clean candidate baseline `v1.1.0-real-clean` evaluated in `experiments/results/real/governance_evaluation.json`.  
**Failure Summary**: Rejected by both `canary_retention_test` (recall collapsed from 100.0% to 25.0%, recall delta 75.0% vs limit $\le 5.0\%$) and `drift_budget` ($D_{\text{rms}} = 6.65$ vs limit $\le 2.5$; $D_{\max} = 16.90$ vs limit $\le 3.0$).

---

## 1. Drift Budget Feature Analysis & $z_i$ Computation

### Ingress & Formula
* **Implementation**: `ml_engine/governance/checks.py`, class `DriftBudgetCheck.evaluate()` (lines 262–370).
* **Formula**:
  $$z_i = \frac{\text{median}_{\text{candidate}}(f) - \text{median}_{\text{anchor}}(f)}{s_{\text{anchor}}(f)}, \quad s_{\text{anchor}}(f) = \max\left(\frac{\text{IQR}_{\text{anchor}}(f)}{1.349}, 10^{-7}\right)$$
  $$D_{\text{rms}} = \sqrt{\frac{1}{d} \sum_{i=1}^d z_i^2}, \quad D_{\max} = \max_{i} |z_i|$$

### Feature Categorisation (9 Canonical Features)
| Feature Name | Feature Type | Units / Range | Numerator / Scaling Nature |
| :--- | :--- | :--- | :--- |
| `registrations_per_active_ue` | Ratio | $[0, \infty)$ | Control-plane rate per entity |
| `nas_failure_ratio` | Ratio | $[0, 1]$ | Bounded rate (failures / total) |
| `pfcp_failure_ratio` | Ratio | $[0, 1]$ | Bounded rate (failures / total) |
| `pdu_session_rate_per_ue` | Ratio | $[0, \infty)$ | Session establishment rate per entity |
| `bytes_per_session` | Volume-per-session | Bytes | Absolute byte volume in numerator |
| `packets_per_session` | Count-per-session | Packets | Absolute packet count in numerator |
| `gtpu_volume_per_ue` | Volume-per-UE | Bytes | Absolute byte volume in numerator |
| `ue_hash_entropy` | Statistical entropy | $[0, 8]$ | Shannon entropy of client identifiers |
| `new_ue_rate` | Ratio | $[0, 1]$ | Bounded rate (new UEs / total UEs) |

### Top 5 Features by $|z_i|$ for Clean Candidate ($v1.1.0\text{-real-clean}$)
Computed directly from `data/processed/candidates/sst-1-sd-010203_v1.1.0-real-clean.joblib` vs `data/processed/baselines/sst-1-sd-010203_v1.0.0-anchor-real.joblib`:

| Rank | Feature | Category | Cand Median ($c_{\text{med}}$) | Anchor Median ($a_{\text{med}}$) | Scale ($s_{\text{anc}}$) | $z_i$ Shift | $|z_i|$ |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **1** | `ue_hash_entropy` | Statistical entropy | 7.4200 | 2.4815 | 0.2923 | **+16.8980** | **16.8980** |
| **2** | `pdu_session_rate_per_ue` | Ratio | 55.5168 | 17.4278 | 4.1495 | **+9.1791** | **9.1791** |
| **3** | `packets_per_session` | Count-per-session | 9.1500 | 43.7350 | 8.8306 | **-3.9165** | **3.9165** |
| **4** | `bytes_per_session` | Volume-per-session | 12304.7750 | 49762.7800 | 10700.4133 | **-3.5006** | **3.5006** |
| **5** | `gtpu_volume_per_ue` | Volume-per-UE | 684940.9750 | 811904.3450 | 214005.5856 | **-0.5933** | **0.5933** |

*Remaining features*: `new_ue_rate` ($z = +0.4530$), `registrations_per_active_ue` ($z = +0.0422$), `nas_failure_ratio` ($z = 0.0$), `pfcp_failure_ratio` ($z = 0.0$).

### Comparison Across Growth Multipliers (1.5x, 2.0x, 3.0x)
When adaptation windows are scaled by 1.5x, 2.0x, and 3.0x, the top 5 features and their $|z_i|$ values remain virtually identical ($D_{\max} = 16.8980, D_{\text{rms}} = 6.6496$). The reason is that `build_shadow_candidate` pools 10 adaptation windows with 100 base training windows; the shift is entirely dominated by the base training set mismatch, not the scale multiplier.

---

## 2. Is $D_{\max}$ Driven by Absolute-Volume Features?

**No.** $D_{\max}$ is driven exclusively by `ue_hash_entropy` ($|z| = 16.8980$), followed by `pdu_session_rate_per_ue` ($|z| = 9.1791$). Both are ratio/statistical features, not absolute volume features.

### Side-by-Side Recomputation: All Features vs Ratio-Only Features
Excluding the two volume-denominated features (`bytes_per_session` and `gtpu_volume_per_ue`):

| Metric | All 9 Features | Ratio-Only Features (7 Features) | Gate Limit | Status |
| :--- | :---: | :---: | :---: | :---: |
| **$D_{\max}$ (Maximum single-feature shift)** | **16.8980** | **16.8980** | $\le 3.00$ | **FAILED** |
| **$D_{\text{rms}}$ (Cumulative distance from anchor)** | **6.6496** | **7.4195** | $\le 2.50$ | **FAILED** |
| **Top Driver** | `ue_hash_entropy` ($z = 16.90$) | `ue_hash_entropy` ($z = 16.90$) | - | - |
| **Second Driver** | `pdu_session_rate_per_ue` ($z = 9.18$) | `pdu_session_rate_per_ue` ($z = 9.18$) | - | - |

**Critical Observation**: Removing volume features causes $D_{\text{rms}}$ to **increase** from $6.65$ to $7.42$. This is because `gtpu_volume_per_ue` had a small shift ($z = -0.59$), which had been pulling the overall root-mean-square average downward. The drift explosion is entirely within the ratio and entropy features.

---

## 3. Canary Rescaling & Retention Evaluation

### Ingress & Rescaling Logic
* **Implementation**: `ml_engine/governance/canary.py`, `rescale_canary_window()` (lines 71–110).
* **Rescaling Mechanism**:
  1. Multiplies raw counters (`total_bytes_uplink`, `total_bytes_downlink`, `total_packets`, `active_ue_count`, `pdu_sessions_established`) by $k = \text{volume\_multiplier}$.
  2. Multiplies `ratio_features["gtpu_volume_per_ue"]` and `ratio_features["bytes_per_session"]` by $k$.
  3. Leaves all other ratio features (`ue_hash_entropy`, session rates, failure ratios) unchanged.
* **Evaluation Call**: `evaluate_canary_retention()` in `ml_engine/governance/canary.py:167-252`.

### Scoring Setup & Thresholds
* **Anchor Threshold**: `threshold_percentile = 95.0` (Isolation Forest fitted on clean 5G-NIDD baseline).
* **Candidate Threshold**: `threshold_percentile = 95.0` (Isolation Forest fitted on candidate baseline).
* **Canary Scoring Input**: In `canary.py:193-200`, `rescaled_canaries` is created once and passed to **both** `_score_windows_with_bundle(rescaled_canaries, active_bundle)` and `_score_windows_with_bundle(rescaled_canaries, candidate_bundle)`. **The anchor is evaluated on the exact same rescaled canaries as the candidate.**

### Per-Category Canary Recall Breakdown (40 Canaries Total)
Evaluated with the context used in `real_evaluator.py:381` ($k = 1.5$):

| Canary Category | Canary Count | Anchor (Active) Recall | Candidate Recall | Recall Delta ($\Delta$) | Category Gate |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `attack_in_growth` | 18 | 100.0% (18/18) | **11.11%** (2/18) | +88.89% | **FAILED** |
| `slow_attack_ramp` | 21 | 100.0% (21/21) | **33.33%** (7/21) | +66.67% | **FAILED** |
| `mimicry_attack` | 1 | 100.0% (1/1) | **100.0%** (1/1) | 0.0% | **PASSED** |
| **Total / Overall** | **40** | **100.0%** (40/40) | **25.0%** (10/40) | **+75.0%** | **FAILED** |

*Note on Scale Multipliers*:
* At $k = 1.0$: Anchor recall = 100.0%, Candidate recall = 40.0% ($\Delta = 60.0\%$, FAILED).
* At $k = 1.5$: Anchor recall = 100.0%, Candidate recall = 25.0% ($\Delta = 75.0\%$, FAILED).
* At $k = 2.0$: Anchor recall = 100.0%, Candidate recall = 100.0% ($\Delta = 0.0\%$, PASSED). When $k=2.0$, artificially doubling `bytes_per_session` pushes all canaries outside the candidate's envelope.

---

## 4. Threshold Recomputation & Calibration Mismatch

1. **Threshold Fitting Mechanism**:
   - `candidate.py:147-162`: When `build_shadow_candidate` trains the shadow detectors, it fits `IsolationForestDetector(contamination=0.05, threshold_percentile=95.0)` on the candidate's combined feature matrix $X$.
   - The candidate's decision score cutoff is recomputed at the 95th percentile of its own training score distribution.
   - Anchor's decision score cutoff was fixed at the 95th percentile of the anchor training distribution.
2. **The Mismatch**:
   - The threshold percentile is identical (95.0%), but the **training distributions are from entirely different domains**.
   - Anchor was calibrated on 24 real 5G-NIDD benign windows.
   - Candidate was calibrated on 100 synthetic windows from `training_embb.json` plus 10 real adaptation windows.
   - As a result, the candidate's decision boundary absorbed synthetic traffic characteristics as nominal.

---

## 5. Effect of Benign Scaling on Ratio Features

### Theoretical Expectation
In authentic proportional scaling where network capacity expands by $k$:
* Traffic volume scales: $\text{bytes} \to k \cdot \text{bytes}$, $\text{packets} \to k \cdot \text{packets}$.
* User base scales: $\text{active\_ues} \to k \cdot \text{active\_ues}$, $\text{sessions} \to k \cdot \text{sessions}$.
* **All ratio features remain invariant**:
  $$\frac{k \cdot \text{bytes}}{k \cdot \text{sessions}} = \frac{\text{bytes}}{\text{sessions}}, \quad \frac{k \cdot \text{bytes}}{k \cdot \text{active\_ues}} = \frac{\text{bytes}}{\text{active\_ues}}, \quad \frac{k \cdot \text{sessions}}{k \cdot \text{active\_ues}} = \frac{\text{sessions}}{\text{active\_ues}}$$

### Empirical Implementation Reality
1. **Canary Rescaling Bug**: `rescale_canary_window()` in `canary.py:105-108` explicitly forces ratio distortion:
   ```python
   ratios["gtpu_volume_per_ue"] = float(ratios["gtpu_volume_per_ue"]) * k
   ratios["bytes_per_session"] = float(ratios["bytes_per_session"]) * k
   ```
   This assumes "fat pipe" growth (same users consuming $k\times$ data), directly contradicting the proportional growth assumption ($k\times$ users generating nominal traffic).
2. **Attribution Growth Generator**: In `real_evaluator.py:310-315`, `raw_counters` are scaled by $k$, but `ratio_features` were left un-recalculated from the scaled raw values.

---

## 6. Root Cause Classification

The rejection of the clean candidate is a **combination of (b) a canary rescaling/dataset domain mismatch bug** and **(d) cross-domain training data pollution in candidate construction**.

### Evidence 1: Cross-Domain Data Pollution in `build_shadow_candidate` (Primary Drift Cause)
* **Code Trace**: `ml_engine/governance/candidate.py:106`:
  ```python
  base_windows = load_base_training_windows(slice_id) # Hardcoded to load SYNTHETIC training_embb.json!
  combined_windows = list(base_windows) + list(adaptation_windows)
  ```
* **Impact**: In real-data evaluations, `anchor_bundle` was trained on real 5G-NIDD traffic (`ue_hash_entropy` median **2.48**). But `build_shadow_candidate` merged 10 real adaptation windows with 100 synthetic windows from `training_embb.json` (`ue_hash_entropy` median **7.42**).
* **Proof**:
  $$z_{\text{entropy}} = \frac{7.4200 - 2.4815}{0.2923} = \mathbf{16.8980} \implies D_{\max} = 16.90$$
  This single line of code is 100% responsible for $D_{\max} = 16.90$ and $D_{\text{rms}} = 6.65$.
* **Empirical Verification**: When the candidate is built using the anchor's actual real training windows (`anchor_bundle["training_windows"]`), the drift budget **passes completely**:
  $$D_{\text{rms}} = \mathbf{0.5283} \le 2.50 \text{ (PASSED)}, \quad D_{\max} = \mathbf{1.0761} \le 3.00 \text{ (PASSED)}$$

### Evidence 2: Domain Mismatch in Canaries (Primary Canary Recall Cause)
* **Code Trace**: `load_canary_dataset()` in `canary.py:36` loads synthetic attack files (`slow_attack_ramp.json`, `attack_in_growth.json`).
* **Impact**: Synthetic canaries have `ue_hash_entropy \approx 7.4`.
  - To the **real anchor baseline** (entropy 2.48), synthetic canaries are $+12\sigma$ outliers simply because they are synthetic! The anchor scores 100% recall effortlessly.
  - To the **candidate baseline**, which was trained on synthetic `training_embb.json` (entropy 7.42), entropy 7.4 is nominal benign traffic. The synthetic attacks lose their domain anomaly advantage and fall inside the candidate's 95% nominal envelope.
* **Rescaling Bug**: `rescale_canary_window()` multiplies `bytes_per_session` by $k$. At $k=1.5$, the distortion places synthetic attack samples in an ambiguous intermediate score zone where candidate recall drops to 25.0%.

---

## 7. Smallest Fixes (Without Modifying Gate Thresholds)

In ascending order of implementation effort:

1. **Fix Candidate Base Training Window Ingress** (*Effort: Minimal, 3 lines of code*):
   - **Where**: `ml_engine/governance/candidate.py:106`.
   - **Fix**: Use `active_bundle.get("training_windows")` as `base_windows` if available, falling back to `load_base_training_windows(slice_id)` only when `active_bundle` has no training windows.
   - **Result**: Instantly eliminates synthetic cross-contamination. $D_{\max}$ drops from **16.90 to 1.08** (limit 3.0), and $D_{\text{rms}}$ drops from **6.65 to 0.53** (limit 2.5). The clean candidate **passes the drift budget completely**.

2. **Domain-Consistent Canary Selection** (*Effort: Low, 15 lines of code*):
   - **Where**: `ml_engine/governance/canary.py:load_canary_dataset()`.
   - **Fix**: Accept `data_source` or `domain` parameter. If `domain == "real"`, load held-out real attack windows from `data/raw/5g-nidd/BS1_each_attack_csv/` (e.g. real SYNScan, UDPFlood, Slowloris) instead of synthetic scenario files.
   - **Result**: Eliminates the synthetic domain anomaly advantage for the anchor, aligning anchor and candidate evaluations to the actual traffic domain.

3. **Ratio-Consistent Canary Rescaling** (*Effort: Medium, 20 lines of code*):
   - **Where**: `ml_engine/governance/canary.py:rescale_canary_window()`.
   - **Fix**: Distinguish between entity-expansion growth (scaling UEs and sessions proportionally) vs payload-expansion growth. In proportional growth mode, keep `bytes_per_session` and `gtpu_volume_per_ue` invariant, rescaling only absolute flow/byte counters.
   - **Result**: Eliminates artificial distortion of ratio features during canary backtesting.
