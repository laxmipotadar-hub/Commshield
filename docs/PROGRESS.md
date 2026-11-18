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
