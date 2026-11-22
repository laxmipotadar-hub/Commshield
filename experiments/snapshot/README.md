# CommShield Offline Experiment Snapshots

This directory contains standalone, committed offline snapshots of the latest empirical evaluation summaries for CommShield.

## Contents

- **`experiment_summary.json`**:
  Aggregated results of the multi-seed centerpiece three-arm experiment across the 5 canonical synthetic scenarios (`stable_benign`, `legitimate_growth`, `slow_attack_ramp`, `attack_in_growth`, `mimicry_attack`) evaluated over 5 random seeds (42, 101, 2024, 777, 999).
- **`real/three_arm_summary.json`**:
  Aggregated results of the three-arm experiment executed on real 5G-NIDD telemetry across 4 scenarios (`real_benign`, `real_attacks`, `scaled_benign_growth`, `attack_in_scaled_growth`) evaluated over 5 random seeds.
- **`real/detection_evaluation.json`**:
  Per-attack detection metrics (recall, benign FPR, detection delay in windows) across all 5G-NIDD DoS and port scan categories for CommShield, Isolation Forest, Autoencoder, and the Fixed Z-Score baseline.
- **`real/growth_attribution.json`**:
  Attribution classification outcomes (JSD divergence and scaling factor $k$) under 1.5x, 2.0x, and 3.0x scale growth with composition preserved vs. shifted.
- **`real/governance_evaluation.json`**:
  Closed-loop 4-gate evaluation results (Normal Holdout Backtest, Proportional Growth, Canary Retention, Drift Budget) comparing a clean candidate baseline against a poisoned candidate baseline.
- **`real/metadata.json`**:
  Audit trace capturing raw dataset files used, split boundaries, temporal discipline parameters, and assigned slice mappings.

## Purpose

These snapshots allow the CommShield dashboard (specifically the **Experiment Comparison** view) to function immediately out-of-the-box without requiring live background model retraining or an active populated SQLite/PostgreSQL database. If the database has no experiment run records, the backend and frontend automatically fall back to these verified snapshots.

## How to Regenerate Snapshots

To rerun the empirical evaluations from scratch and refresh the snapshot files:

### 1. Synthetic Three-Arm Benchmark
Run the synthetic evaluation runner:
```bash
# Using Python CLI directly:
python experiments/run_experiments.py

# Or trigger asynchronously through the backend API:
curl -X POST http://localhost:8000/api/experiments/run \
  -H "Content-Type: application/json" \
  -d '{"scenarios": ["stable_benign", "legitimate_growth", "slow_attack_ramp", "attack_in_growth", "mimicry_attack"], "seeds": [42, 101, 2024, 777, 999], "num_windows": 40}'
```
This produces `experiments/results/experiment_summary.json`.

### 2. Real 5G-NIDD Empirical Evaluation
Ensure raw 5G-NIDD datasets are present in `data/raw/5g-nidd/`, then run:
```bash
python experiments/run_real_experiments.py
```
This produces `experiments/results/real/*.json`.

### 3. Copy to Snapshot Directory
Update the snapshot directory with the freshly generated results:
```bash
# On Linux/macOS:
cp experiments/results/experiment_summary.json experiments/snapshot/
cp experiments/results/real/* experiments/snapshot/real/

# On Windows (PowerShell):
Copy-Item experiments/results/experiment_summary.json experiments/snapshot/ -Force
Copy-Item experiments/results/real/* experiments/snapshot/real/ -Force
```
Commit the updated JSON files along with any documentation changes.
<!-- CommShield AI Core -->
