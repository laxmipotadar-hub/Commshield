# CommShield Data Presentation Scan & Audit Report

**Generated:** 2026-11-21T15:37:36.440826+00:00

## Audit Counts: Before vs After Remediation

- **Raw Assets Flagged (Before):** 104 items
- **Unhandled Presentation Defects (After):** 0 items
- **Remediation Status:** Complete across DP1, DP2, DP4; DP3 stopped per strict switch rule (Windows difference 0.0084 > 1e-6; existing results preserved).

### Scope & Cut Line Notes
- **DP1 (Scan & Report):** DONE (104 items identified across 4 core pages).
- **DP2 (Display Fixes):** DONE (Missing data formatted as 'no data', percentiles show raw-to-threshold log ratio, proportions show Wilson CI).
- **DP4 (Scenario Charts & Captions):** DONE (Stable benign band, approved growth volume vs ratio & JSD bar, slow ramp CUSUM, bullet bars, 2x2 agreement matrix; all charts have title, units, n, source badge, and two-line captions).
- **DP3 (Regenerated Data):** PARTIAL / STOPPED (Windows re-run produced max diff 0.0084 > 1e-6 vs Ubuntu results; per switch rule, stopped step, kept old results in use).
- **DP5 (Guard Tests):** DONE (`tools/test_data_presentation_guard.py` verifies zero hardcoded literals, captions, badges, and statistical intervals).

## Consolidated Findings and Remediation Table

| Page | Field | Problem | Likely Cause | Planned Fix |
| :--- | :--- | :--- | :--- | :--- |
| Anomaly Detection | `validation_fpr (all 4 detectors)` | Zero variance series: identical 0.1304 across all detectors | Identical threshold percentile or uniform reference split mapping | Compute detector-specific empirical validation FPR from distinct score distributions |
| Anomaly Detection | `UDPFlood total_windows` | Sample size n=9 < 10 | Too few evaluation windows in short real-data slice burst | Show n={count} and mark interval too wide; regenerate with more windows |
| Anomaly Detection | `UDPFlood attack_windows` | Attack window count n=1 < 10 | Sparse real attack frames in test recording | Display count n with Wilson score confidence interval |
| Anomaly Detection | `UDPFlood [commshield] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `UDPFlood [isolation_forest] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `UDPFlood [autoencoder] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `UDPFlood [fixed_zscore] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `HTTPFlood total_windows` | Sample size n=8 < 10 | Too few evaluation windows in short real-data slice burst | Show n={count} and mark interval too wide; regenerate with more windows |
| Anomaly Detection | `HTTPFlood attack_windows` | Attack window count n=3 < 10 | Sparse real attack frames in test recording | Display count n with Wilson score confidence interval |
| Anomaly Detection | `HTTPFlood [commshield] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `HTTPFlood [isolation_forest] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `HTTPFlood [autoencoder] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `HTTPFlood [fixed_zscore] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `SYNFlood attack_windows` | Attack window count n=9 < 10 | Sparse real attack frames in test recording | Display count n with Wilson score confidence interval |
| Anomaly Detection | `SYNFlood [commshield] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `SYNFlood [isolation_forest] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `SYNFlood [autoencoder] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `SYNFlood [fixed_zscore] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `ICMPFlood [commshield] recall` | Exact boundary recall=0.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `ICMPFlood [isolation_forest] recall` | Exact boundary recall=0.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `ICMPFlood [autoencoder] recall` | Exact boundary recall=0.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `ICMPFlood [fixed_zscore] recall` | Exact boundary recall=0.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `TCPConnectScan attack_windows` | Attack window count n=5 < 10 | Sparse real attack frames in test recording | Display count n with Wilson score confidence interval |
| Anomaly Detection | `TCPConnectScan [commshield] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `TCPConnectScan [isolation_forest] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `TCPConnectScan [autoencoder] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `TCPConnectScan [fixed_zscore] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `SYNScan total_windows` | Sample size n=9 < 10 | Too few evaluation windows in short real-data slice burst | Show n={count} and mark interval too wide; regenerate with more windows |
| Anomaly Detection | `SYNScan attack_windows` | Attack window count n=4 < 10 | Sparse real attack frames in test recording | Display count n with Wilson score confidence interval |
| Anomaly Detection | `SYNScan [commshield] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `SYNScan [isolation_forest] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `SYNScan [autoencoder] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `SYNScan [fixed_zscore] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Anomaly Detection | `UDPScan attack_windows` | Attack window count n=7 < 10 | Sparse real attack frames in test recording | Display count n with Wilson score confidence interval |
| Anomaly Detection | `UDPScan [fixed_zscore] recall` | Exact boundary recall=1.0 | Small sample size (1/1 or 0/1 attack windows detected) | Annotate with n={atk_win}, Wilson 95% CI, and explain binary window evaluation |
| Baseline Governance | `clean_candidate.holdout_fpr` | Exact 0.0 FPR (0/20) | Perfect holdout rejection on benign validation slice | Show n=20, Wilson 95% CI [0.00, 0.16], reason: zero false positives in benign holdout |
| Baseline Governance | `clean_candidate.canary_active_recall` | Exact 1.0 (100%) canary active recall | Canary suite designed with conspicuous anchor attacks | Annotate with canary count n=40 and Wilson CI |
| Baseline Governance | `clean_candidate.canary_mimicry_attack_count` | Canary category count n=1 < 10 | Limited canary pool for rare evasion categories (e.g. mimicry) | Show 'n={count}, interval too wide' badge |
| Baseline Governance | `clean_candidate.delta_canary` | Metric saturated exactly at budget cap (10.0 == 10.0) | Threshold clamping in test harness | Show raw uncapped distance ratio and log-scale comparison to limit |
| Baseline Governance | `poisoned_candidate.canary_active_recall` | Exact 1.0 (100%) canary active recall | Canary suite designed with conspicuous anchor attacks | Annotate with canary count n=40 and Wilson CI |
| Baseline Governance | `poisoned_candidate.canary_mimicry_attack_count` | Canary category count n=1 < 10 | Limited canary pool for rare evasion categories (e.g. mimicry) | Show 'n={count}, interval too wide' badge |
| Experiment Matrix | `real_benign.arm_a_static.fpr_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `real_benign.arm_a_static.contamination_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `real_benign.arm_a_static.contamination_mean` | Exact boundary contamination=0.0 | Unprovisioned burst cleanly blocked (0.0) or completely ingested (0.5) | Show n seeds, CI interval, and scenario mechanism caption |
| Experiment Matrix | `real_benign.arm_b_naive.fpr_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `real_benign.arm_b_naive.contamination_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `real_benign.arm_b_naive.contamination_mean` | Exact boundary contamination=0.0 | Unprovisioned burst cleanly blocked (0.0) or completely ingested (0.5) | Show n seeds, CI interval, and scenario mechanism caption |
| Experiment Matrix | `real_benign.arm_c_commshield.fpr_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `real_benign.arm_c_commshield.contamination_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `real_benign.arm_c_commshield.contamination_mean` | Exact boundary contamination=0.0 | Unprovisioned burst cleanly blocked (0.0) or completely ingested (0.5) | Show n seeds, CI interval, and scenario mechanism caption |
| Experiment Matrix | `real_attacks.arm_a_static.recall_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `real_attacks.arm_a_static.fpr_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `real_attacks.arm_a_static.contamination_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `real_attacks.arm_a_static.contamination_mean` | Exact boundary contamination=0.0 | Unprovisioned burst cleanly blocked (0.0) or completely ingested (0.5) | Show n seeds, CI interval, and scenario mechanism caption |
| Experiment Matrix | `real_attacks.arm_a_static.recall_mean` | Exact boundary recall=1.0 | Static detector either wholly flags or wholly misses scenario pattern | Add n seeds and Wilson CI per arm |
| Experiment Matrix | `real_attacks.arm_b_naive.recall_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `real_attacks.arm_b_naive.fpr_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `real_attacks.arm_b_naive.contamination_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `real_attacks.arm_b_naive.contamination_mean` | Exact boundary contamination=0.0 | Unprovisioned burst cleanly blocked (0.0) or completely ingested (0.5) | Show n seeds, CI interval, and scenario mechanism caption |
| Experiment Matrix | `real_attacks.arm_b_naive.recall_mean` | Exact boundary recall=0.0 | Static detector either wholly flags or wholly misses scenario pattern | Add n seeds and Wilson CI per arm |
| Experiment Matrix | `real_attacks.arm_c_commshield.recall_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `real_attacks.arm_c_commshield.fpr_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `real_attacks.arm_c_commshield.contamination_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `real_attacks.arm_c_commshield.contamination_mean` | Exact boundary contamination=0.0 | Unprovisioned burst cleanly blocked (0.0) or completely ingested (0.5) | Show n seeds, CI interval, and scenario mechanism caption |
| Experiment Matrix | `real_attacks.arm_c_commshield.recall_mean` | Exact boundary recall=1.0 | Static detector either wholly flags or wholly misses scenario pattern | Add n seeds and Wilson CI per arm |
| Experiment Matrix | `scaled_benign_growth.arm_a_static.fpr_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `scaled_benign_growth.arm_a_static.contamination_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `scaled_benign_growth.arm_a_static.contamination_mean` | Exact boundary contamination=0.0 | Unprovisioned burst cleanly blocked (0.0) or completely ingested (0.5) | Show n seeds, CI interval, and scenario mechanism caption |
| Experiment Matrix | `scaled_benign_growth.arm_b_naive.fpr_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `scaled_benign_growth.arm_b_naive.contamination_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `scaled_benign_growth.arm_b_naive.contamination_mean` | Exact boundary contamination=0.0 | Unprovisioned burst cleanly blocked (0.0) or completely ingested (0.5) | Show n seeds, CI interval, and scenario mechanism caption |
| Experiment Matrix | `scaled_benign_growth.arm_c_commshield.fpr_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `scaled_benign_growth.arm_c_commshield.contamination_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `scaled_benign_growth.arm_c_commshield.contamination_mean` | Exact boundary contamination=0.0 | Unprovisioned burst cleanly blocked (0.0) or completely ingested (0.5) | Show n seeds, CI interval, and scenario mechanism caption |
| Experiment Matrix | `attack_in_scaled_growth.arm_a_static.recall_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `attack_in_scaled_growth.arm_a_static.fpr_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `attack_in_scaled_growth.arm_a_static.contamination_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `attack_in_scaled_growth.arm_a_static.contamination_mean` | Exact boundary contamination=0.0 | Unprovisioned burst cleanly blocked (0.0) or completely ingested (0.5) | Show n seeds, CI interval, and scenario mechanism caption |
| Experiment Matrix | `attack_in_scaled_growth.arm_a_static.recall_mean` | Exact boundary recall=1.0 | Static detector either wholly flags or wholly misses scenario pattern | Add n seeds and Wilson CI per arm |
| Experiment Matrix | `attack_in_scaled_growth.arm_b_naive.recall_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `attack_in_scaled_growth.arm_b_naive.fpr_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `attack_in_scaled_growth.arm_b_naive.contamination_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `attack_in_scaled_growth.arm_b_naive.contamination_mean` | Exact boundary contamination=0.0 | Unprovisioned burst cleanly blocked (0.0) or completely ingested (0.5) | Show n seeds, CI interval, and scenario mechanism caption |
| Experiment Matrix | `attack_in_scaled_growth.arm_b_naive.recall_mean` | Exact boundary recall=0.0 | Static detector either wholly flags or wholly misses scenario pattern | Add n seeds and Wilson CI per arm |
| Experiment Matrix | `attack_in_scaled_growth.arm_c_commshield.recall_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `attack_in_scaled_growth.arm_c_commshield.fpr_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `attack_in_scaled_growth.arm_c_commshield.contamination_std` | Zero variance series (std == 0.0) | Evaluation run across limited identical seeds or deterministic replay | Regenerate multi-seed experiments with >= 10 seeds and diverse noise |
| Experiment Matrix | `attack_in_scaled_growth.arm_c_commshield.contamination_mean` | Exact boundary contamination=0.0 | Unprovisioned burst cleanly blocked (0.0) or completely ingested (0.5) | Show n seeds, CI interval, and scenario mechanism caption |
| Experiment Matrix | `attack_in_scaled_growth.arm_c_commshield.recall_mean` | Exact boundary recall=1.0 | Static detector either wholly flags or wholly misses scenario pattern | Add n seeds and Wilson CI per arm |
| Digital Twin | `twin_approved_onboarding.naive.fpr` | Saturated boundary FPR=0.0 | commshield_base without twin updates saturates to 100% on valid growth | Show raw score ratio on log scale alongside 100% saturation badge |
| Digital Twin | `twin_approved_onboarding.commshield_base.onboardings_adapted` | Exact 0 adaptations (0.0) | Quarantine policy correctly blocked poison or static arm has no updates | Display n=0 with explicit reason badge 'Policy blocked adaptation' |
| Digital Twin | `twin_unprovisioned_burst.naive.onboardings_adapted` | Exact 0 adaptations (0.0) | Quarantine policy correctly blocked poison or static arm has no updates | Display n=0 with explicit reason badge 'Policy blocked adaptation' |
| Digital Twin | `twin_unprovisioned_burst.commshield_base.fpr` | Saturated boundary FPR=1.0 | commshield_base without twin updates saturates to 100% on valid growth | Show raw score ratio on log scale alongside 100% saturation badge |
| Digital Twin | `twin_unprovisioned_burst.commshield_base.onboardings_adapted` | Exact 0 adaptations (0.0) | Quarantine policy correctly blocked poison or static arm has no updates | Display n=0 with explicit reason badge 'Policy blocked adaptation' |
| Digital Twin | `twin_unprovisioned_burst.commshield_twin.onboardings_adapted` | Exact 0 adaptations (0.0) | Quarantine policy correctly blocked poison or static arm has no updates | Display n=0 with explicit reason badge 'Policy blocked adaptation' |
| Digital Twin | `twin_provisioned_burst_no_event.naive.onboardings_adapted` | Exact 0 adaptations (0.0) | Quarantine policy correctly blocked poison or static arm has no updates | Display n=0 with explicit reason badge 'Policy blocked adaptation' |
| Digital Twin | `twin_provisioned_burst_no_event.commshield_base.fpr` | Saturated boundary FPR=1.0 | commshield_base without twin updates saturates to 100% on valid growth | Show raw score ratio on log scale alongside 100% saturation badge |
| Digital Twin | `twin_provisioned_burst_no_event.commshield_base.onboardings_adapted` | Exact 0 adaptations (0.0) | Quarantine policy correctly blocked poison or static arm has no updates | Display n=0 with explicit reason badge 'Policy blocked adaptation' |
| Digital Twin | `twin_provisioned_burst_no_event.commshield_twin.onboardings_adapted` | Exact 0 adaptations (0.0) | Quarantine policy correctly blocked poison or static arm has no updates | Display n=0 with explicit reason badge 'Policy blocked adaptation' |
| Digital Twin | `twin_slow_ramp_in_onboarding.naive.fpr` | Saturated boundary FPR=0.0 | commshield_base without twin updates saturates to 100% on valid growth | Show raw score ratio on log scale alongside 100% saturation badge |
| Digital Twin | `twin_slow_ramp_in_onboarding.naive.onboardings_adapted` | Exact 0 adaptations (0.0) | Quarantine policy correctly blocked poison or static arm has no updates | Display n=0 with explicit reason badge 'Policy blocked adaptation' |
| Digital Twin | `twin_slow_ramp_in_onboarding.commshield_base.fpr` | Saturated boundary FPR=1.0 | commshield_base without twin updates saturates to 100% on valid growth | Show raw score ratio on log scale alongside 100% saturation badge |
| Digital Twin | `twin_slow_ramp_in_onboarding.commshield_base.onboardings_adapted` | Exact 0 adaptations (0.0) | Quarantine policy correctly blocked poison or static arm has no updates | Display n=0 with explicit reason badge 'Policy blocked adaptation' |
| Digital Twin | `twin_slow_ramp_in_onboarding.commshield_twin.onboardings_adapted` | Exact 0 adaptations (0.0) | Quarantine policy correctly blocked poison or static arm has no updates | Display n=0 with explicit reason badge 'Policy blocked adaptation' |

## Summary by Page

- **Anomaly Detection**: 35 flagged items
- **Baseline Governance**: 6 flagged items
- **Digital Twin**: 15 flagged items
- **Experiment Matrix**: 48 flagged items
<!-- CommShield AI Core -->
