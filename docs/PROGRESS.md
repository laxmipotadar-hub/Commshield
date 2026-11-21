# CommShield Project Progress & Implementation Status

## Milestone Status: Empirical Rigour & Audit Alignment

All hard-coded fallback metrics and placeholder heuristics have been removed. Every number and claim displayed across the dashboard and documented in reports is derived strictly from real runtime evaluations or persisted experiment output files (`experiments/results/` and `experiments/snapshot/`).

### Completed Work

1. **Benchmark Engine Clean-up (`ml_engine/evaluation/benchmark.py`)**:
   - Removed all hard-coded metrics: the fallback dictionary (precision: 0.941/0.778/0.963, recall: 0.722/0.444/0.926, false alarm rate: 0.085/0.021/0.012) and simulated hash-based mock rules (`hash(w) % 7 == 0`).
   - Wired the Experiment Comparison API (`/api/v1/governance/experiments/three-arm`) directly to persisted JSON result files (`experiments/results/three_arm_summary.json`, `experiments/results/experiment_summary.json`, and `experiments/results/real/three_arm_summary.json`).
   - Completely eliminated `poisoning_susceptibility` metric from schemas, backend responses, and frontend interfaces.

2. **Dynamic Control-Slice Evidence**:
   - Implemented `compute_control_slice_concordance()` in `ml_engine/attribution/metrics.py` using real second-slice data (BS2 vs BS1 in real 5G-NIDD; slice 2 vs slice 1 in synthetic data).
   - Removed hardcoded `control_slice_concordant = True`.
   - Updated `AttributionView.tsx` to conditionally display the Control Slice Concordance panel only when second-slice telemetry is present, cleanly hiding it for scenarios lacking control-slice data.

3. **Real SHAP Attribution (`backend/app/api/windows.py`)**:
   - Integrated `shap.TreeExplainer` on the fitted `IsolationForestDetector` model to compute true SHAP values exclusively on flagged anomalous windows.
   - Retained the "SHAP" label and ensured full mathematical additivity ($\text{expected\_value} + \sum \text{shap\_values} = \text{model\_prediction}$).
   - Set `shap_values = {}` on non-anomalous nominal windows.

4. **Data Sources Alignment (`README.md`)**:
   - Removed MAWI and Open5GS/UERANSIM testbed claims.
   - Documented the exact empirical data pipeline: 5G-NIDD real flow captures and parametric synthetic stream generators.

5. **Empirical Factuality & Known Limitations (`experiments/README.md`)**:
   - Corrected the Arm C growth narrative to reflect empirical measurements: gated adaptation keeps baseline contamination at 0.0% across attack scenarios (where naive adaptation absorbs 56.0% to 83.3% attack data), but made 0 adaptations under synthetic legitimate growth due to strict drift gates (yielding ~97.5% FPR).
   - Added a dedicated "Known Limitations" section detailing: the growth-adaptation trade-off, clean candidate rejection by canary and budget gates, poisoned candidate rejection solely by holdout, small sample window counts, 0.0% recall on trickle ICMP flood across all detectors, and unimplemented modules (ablations, re-anchoring, time-of-day).

6. **Dwell Time Enforcement (`backend/app/services/governance.py` & `ml_engine/governance/config.py`)**:
   - Configured `DWELL_TIME_MIN_SECONDS = 300` in governance config.
   - Enforced dwell time check in `governance_service.approve_and_promote()`, checking the timestamp of the last approved baseline for that slice in `ApprovalLog`.
   - Added explicit dwell time decision trace entry (`Dwell time check: PASSED` or `Dwell time check: FAILED`) and raised HTTP 409 conflict upon rapid successive promotion attempts.

7. **Verification & Tests (`backend/tests/test_audit_verification.py`)**:
   - Verified that the benchmark endpoint returns only numbers present in saved result files.
   - Verified that control-slice concordance is dynamically computed, not constant.
   - Verified that SHAP values sum consistently on flagged anomalous windows.
   - Verified that dwell time blocks a second promotion inside the configured interval.

## Milestone Status: Privacy by Design & Zero-Trust Governance

CommShield has enforced end-to-end privacy by design across the pipeline, verified by automated unit and integration tests:

1. **Cryptographic Pseudonymisation**:
   - Replaced identifier hashing with keyed `HMAC-SHA256` (`COMMSHIELD_HMAC_KEY`) in `ml_engine/preprocessing/adapters/base.py`.
   - Verified that Shannon entropy of identifier frequencies is invariant under deterministic pseudonymisation.

2. **Aggregate-Only Boundary**:
   - Defined strict allowlists (`CANONICAL_WINDOW_ALLOWLIST`, `RAW_COUNTERS_ALLOWLIST`, `RATIO_FEATURES_ALLOWLIST`, `COMPOSITION_VECTOR_ALLOWLIST`) enforced via `enforce_aggregate_boundary()`.
   - Guaranteed that raw IP addresses, port numbers, or subscriber traces are stripped before reaching detectors, database, or API responses.

3. **Small-Group Suppression ($K$-Anonymity)**:
   - When a slice window contains fewer than $K$ distinct active UEs ($K=5$), `ue_hash_entropy` is set to `-1.0` (`SUPPRESSED_ENTROPY_VALUE`).
   - Attribution engine handles suppressed entropy as missing evidence without tripping false alarms or altering gate thresholds.

4. **Access Control & Authorization**:
   - Enforced `Authorization: Bearer <analyst_token>` (`COMMSHIELD_ANALYST_TOKEN`) on all state-mutating candidate approval, rejection, and rollback endpoints.
   - Maintained read-only access for demo mode and added operator token management in the frontend Settings modal.

5. **Privacy Documentation & Verification**:
   - Documented retention policies (30-day sliding telemetry window, immutable anchor/audit trails) and carrier private-network requirements in `docs/PRIVACY.md`.
   - Created comprehensive privacy test suite in `backend/tests/test_privacy.py` covering IP redaction, keyed HMAC, small-group suppression, and 401 unauthorized access controls.

## Milestone Status: Learned Drift Attributor Beside Rules Baseline

A small, regularized learned drift attributor has been introduced beside the existing hand-crafted rules attributor, maintaining rules as the baseline and graceful fallback without introducing new UI pages.

1. **Signals & No-Leakage Feature Extraction (`ml_engine/attribution/learned.py`)**:
   - Strictly restricted features to the 9 canonical attribution signals audited in `docs/AI_FEASIBILITY.md`: `scaling_factor_k`, `jsd_divergence`, `ue_entropy_delta`, `new_ue_rate`, `nas_failure_ratio`, `pfcp_failure_ratio`, `detector_agreement_numeric`, `control_slice_concordant`, and `per_ue_rate_deviation`.
   - Zero raw identifiers (`imsi`, `src_ip`), zero window labels, and zero ground truth enter the feature extractor or model.

2. **Small Regularized Model (`ml_engine/attribution/learned.py`)**:
   - Implemented an L2-regularized linear classifier (9 weights + 1 bias) with fixed random seed (42) using SciPy L-BFGS-B optimization.
   - Bounded model capacity prevents overfitting to diurnal patterns or single synthetic growth curves while preserving mathematical interpretability and monotonic regularization.
   - Enforced a standard deviation floor ($\ge 0.05$) to guarantee numerical stability across low-variance features.

3. **Tuning Streams Training (`ml_engine/attribution/trainer.py`)**:
   - Trained exclusively on synthetic tuning streams generated with dedicated isolated seed (8888).
   - Test streams (seeds 42, 101, 2024, 777, 999) and the entire real 5G-NIDD generator family were held out strictly.
   - Binary classes: benign growth ($y=0$) vs attack ($y=1$), with attack-during-growth windows labeled strictly by individual window ground truth. Model parameters persisted to `ml_engine/attribution/learned_model.json`.

4. **Sequential Evidence Accumulation ($N=3$)**:
   - Implemented sequential smoothing over horizon $N=3$ windows before issuing a verdict, preventing single noisy or transitional windows from prematurely flipping verdicts.

5. **Decision Categories & Backend Integration (`backend/app/services/attribution.py`, `docs/CONTRACTS.md`)**:
   - Output restricted to evidence categories: `likely_benign`, `likely_attack`, `uncertain` (no raw probabilities exposed to operators).
   - Added configuration flag `attributor = "rules" | "learned"` (default `"rules"`).
   - Exposed `attributor_configured`, `produced_by`, and `fallback_used` in the `evidence_evaluated` step of `DecisionTrace`.

6. **Comparative Evaluation (`experiments/results/attribution/learned_vs_rules_summary.json`)**:
   - Evaluated across 5 test seeds and held-out real 5G-NIDD family with 1000-iteration bootstrap 95% confidence intervals.
   - Synthetic attack recall: `slow_attack_ramp` (Rules: 83.8%, Learned: 74.3%), `attack_in_growth` (Rules: 88.9%, Learned: 63.3%). Precision remained 100.0% for both.
   - Held-out real 5G-NIDD: 100.0% attack recall across SYNFlood, HTTPFlood, UDPScan, SlowrateDoS for both engines.
   - **Weakest Result**: Synthetic `attack_in_growth` attack recall dropped by 25.6% (88.9% down to 63.3%, with abstention rising from 46.7% to 62.0%) due to sequential lag ($N=3$) and legitimate growth volume dampening anomaly ratios into the ambiguous zone ($0.40 - 0.60$).

7. **Verification & Tests (`backend/tests/test_learned_attribution.py`)**:
   - 7 automated test cases passing: no label leakage, feature schema order matching, bitwise determinism, held-out family isolation, sequential decision accumulation, graceful fallback, and backend decision trace verification.

## Milestone Status: Split Conformal Calibration & Principled Abstention

Split-conformal calibration has been integrated into the attribution layer to provide finite-sample statistical guarantees for the "uncertain" classification outcome.

1. **Finite-Sample Conformal p-Values (`ml_engine/attribution/conformal.py`)**:
   - Implemented exact split-conformal rule with $(n+1)$ correction:
     $$p = \frac{1 + \sum_{i=1}^n \mathbb{I}(s_i \ge s_{\text{test}})}{n + 1}$$
   - Evaluated for Isolation Forest negated score ($p_{\text{IF}}$), Autoencoder reconstruction MSE ($p_{\text{AE}}$), and Learned Attributor attack probability ($p_{\text{attr}}$).

2. **Disjoint Calibration Sets & Slice Pooling (`ml_engine/attribution/conformal.py`)**:
   - Benign baseline windows were strictly partitioned into training (30w), threshold-setting (15w), and calibration (15w) with guaranteed non-overlapping window IDs.
   - Due to per-slice sample limits (15 windows yields $p_{\min} = 1/16 = 0.0625$, which cannot support carrier significance $\alpha = 0.05$), global pooling across eMBB, URLLC, and mMTC slices was implemented to form an effective 45-window calibration set ($p_{\min} = 1/46 \approx 0.0217$).

3. **Frozen Abstention Rules**:
   - Pre-registered on tuning streams and frozen:
     - **Conformal Gray Band**: Abstain when $p_{\text{attr}} \in [\alpha_{\text{low}}, \alpha_{\text{high}}] = [0.05, 0.20]$.
     - **Detector Disagreement**: Abstain when $|p_{\text{IF}} - p_{\text{AE}}| > 0.35$.
   - Directly exposes named reasons `"conformal gray band"` and `"detector p-value disagreement"` in output schemas and decision traces.

4. **Empirical Findings: Coverage & Exchangeability Breakdown (`experiments/results/conformal/conformal_calibration_summary.json`)**:
   - **Stable Traffic (1x)**: Empirical detector coverage reached **95.0%** (target: 95.0%, mean $p_{\text{IF}} = 0.7511$, mean $p_{\text{AE}} = 0.7663$). Exchangeability holds.
   - **Scaled Growth Traffic (2x, 3x)**: Empirical detector coverage collapsed to **0.0%** (target: 95.0%, mean $p_{\text{IF}} = p_{\text{AE}} = 0.0217$). Exchangeability is completely broken because volume scaling shifts nonconformity scores into the extreme upper tail of the 1x calibration distribution, causing 100% false rejections of benign growth windows.
   - **Accuracy-vs-Coverage Curves**: Generated across $\alpha \in [0.01, 0.50]$ for stable traffic, scaled 2x traffic, and attack-in-growth.

5. **4-Way Ablation Benchmark**:
   - Conducted multi-seed benchmark (5 seeds: [42, 101, 2024, 777, 999]) across rules vs learned attributor, with and without conformal abstention.
   - In `slow_attack_ramp`: Rules achieved 83.8% recall (abstain 41.3% w/o vs 44.0% w/ conformal); Learned achieved 74.3% recall w/o vs 71.4% w/ conformal (abstain 48.0% -> 50.0%).
   - In `attack_in_growth`: Rules abstained 100% on volume composition disagreement; Learned achieved 63.3% recall w/o vs 60.0% w/ conformal (abstain 62.0% -> 64.7%).
   - Conformal abstention prevents borderline false alarms, elevating non-abstained precision at the cost of slight recall reduction on stealth attacks diluted by concurrent volume growth.

6. **Backend Integration & Configuration**:
   - Added `conformal_calibration` flag (default `false` initially, toggled to `true` post-experiment).
   - Exposed p-values, calibration slice size, and fallback status in `DecisionTrace` step `evidence_evaluated`.
   - Updated `docs/CONTRACTS.md` with conformal parameters and schemas.

7. **Verification & Tests (`backend/tests/test_conformal_attribution.py`)**:
   - 6 automated unit tests passing: exact p-value correctness on toy example, bitwise determinism, calibration disjointness audit, named abstention reasons, calibration size and pooling fallback, and decision trace persistence.

## Milestone Status: Cross-Platform & Agent Rules Verification

1. **Protocol & Contract Audit**:
   - Reviewed `docs/AGENT_RULES.md`, `docs/CONTRACTS.md`, `docs/PROGRESS.md`, and `docs/AI_FEASIBILITY.md`.
   - Verified cross-platform constraints (Windows primary, Ubuntu secondary; pure Python scripts; pathlib paths; UTF-8 LF encoding; explicit random states; environment-backed secrets).
   - Confirmed strict empirical integrity: no hardcoded numbers, no changes to existing detector code, thresholds, or governance gates.

