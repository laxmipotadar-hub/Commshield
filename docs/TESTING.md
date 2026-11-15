# CommShield Testing Specification

## 1. Test Strategy & Runner Matrix

| Scope | Toolchain | Execution Command | Target Coverage |
| :--- | :--- | :--- | :--- |
| **Unit & Contract** | `pytest`, `pytest-cov`, `pytest-asyncio` | `pytest tests/unit tests/contracts` | $\ge 85\%$ line coverage on core ML & contracts |
| **Governance Gates** | `pytest` | `pytest tests/governance` | $100\%$ edge-case coverage on drift budgets & canary tests |
| **API Endpoints** | `httpx`, `pytest` | `pytest tests/api` | All endpoints tested for 200, 400, 404, 422 responses |
| **Frontend UI** | Vitest, React Testing Library | `npm test --run` | Component rendering, state transitions, replay controls |
| **Pipelines & Replay**| Python test harnesses | `python -m pytest tests/integration` | Verification of Arm A, Arm B, Arm C replay outputs |

---

## 2. Key Tests Per Module

### A. Preprocessing & Adapters (`ml_engine/preprocessing/`)

| Test File | Test Case Name | Input / Precondition | Expected Assertion / Outcome |
| :--- | :--- | :--- | :--- |
| `test_adapters.py` | `test_nidd_pseudonymization` | 5G-NIDD flow CSV with raw IPs & ports | SUPI/IP identifiers hashed; raw identities absent from output |
| `test_windowing.py`| `test_window_duration_aggregation` | Stream of 10s packet events | Strict aggregation into continuous non-overlapping 60s windows |
| `test_features.py` | `test_ratio_feature_zero_division` | Window with 0 active UEs, 0 PDU sessions | Robust handling via $\varepsilon$-smoothing; zero `NaN` or `Inf` values |
| `test_scaling.py`  | `test_robust_scaler_preservation` | Window vector + active baseline median/IQR | Correct log-transform followed by $(x - \text{med}) / \text{IQR}$ scaling |

### B. Baseline Learning (`ml_engine/baseline/`)

| Test File | Test Case Name | Input / Precondition | Expected Assertion / Outcome |
| :--- | :--- | :--- | :--- |
| `test_baseline.py` | `test_atomic_package_serialization`| Fitted models, scalers, schema, thresholds | Atomic bundle saves and restores identically; schema hashes match |
| `test_baseline.py` | `test_global_fallback_activation` | S-NSSAI slice with $< 50$ training windows | Global default baseline selected; fallback flag set to `True` |
| `test_baseline.py` | `test_anchor_immutability` | Attempt to overwrite `is_anchor=True` record | Mutation rejected with `ImmutableAnchorException` |

### C. Detection Engine (`ml_engine/detection/`)

| Test File | Test Case Name | Input / Precondition | Expected Assertion / Outcome |
| :--- | :--- | :--- | :--- |
| `test_iforest.py`  | `test_if_negated_score_ordering` | Benign vs high-volume anomaly windows | Score higher for anomalies; scores calibrated to $[0.0, 1.0]$ |
| `test_autoenc.py`  | `test_ae_reconstruction_error` | Structural correlation disruption window | Reconstruction MSE exceeds benign 98th percentile threshold |
| `test_fusion.py`   | `test_max_percentile_fusion_rule` | IF percentile: 0.99, AE percentile: 0.85 | Fused score equals 0.99; agreement state is `IF_ONLY` |
| `test_cusum.py`    | `test_cusum_drift_accumulation` | Sustained mild anomaly scores ($0.92$) | CUSUM accumulates steadily and triggers alarm within $N$ steps |
| `test_evasion.py`  | `test_sage5gc_slow_ramp_behavior`| Ramp scaling at $0.001$ per window | Detection delayed but eventually flagged before baseline drift |

### D. Drift Attribution & Abstention (`ml_engine/attribution/`)

| Test File | Test Case Name | Input / Precondition | Expected Assertion / Outcome |
| :--- | :--- | :--- | :--- |
| `test_adwin.py`    | `test_adwin_change_detection` | Step change in fused percentile stream | ADWIN emits drift trigger signal within bounded window count |
| `test_jsd.py`      | `test_proportional_growth_pass` | Scaled traffic $k=3.0$, identical composition | JSD divergence $<$ 99th percentile null threshold; test passes |
| `test_jsd.py`      | `test_small_count_smoothing` | Low session count composition ($< 10$ counts) | Pseudo-count smoothing prevents false divergence inflation |
| `test_abstain.py`  | `test_abstain_volume_composition_mismatch` | Volume up $3\times$, composition radically shifted | Verdict is `uncertain`; reason is `volume_composition_disagree` |
| `test_abstain.py`  | `test_all_five_named_reasons` | Synthetic scenarios matching 5 failure modes | Attributor returns the exact corresponding named reason string |

### E. Governance Engine (`ml_engine/governance/`)

| Test File | Test Case Name | Input / Precondition | Expected Assertion / Outcome |
| :--- | :--- | :--- | :--- |
| `test_quarantine.py`| `test_uncertain_window_exclusion` | Windows marked `uncertain` by attributor | Excluded from training set buffer for shadow candidate |
| `test_canary.py`    | `test_canary_recall_retention` | Candidate trained on poisoned ramp | Canary recall drops $> \delta$; test fails; promotion blocked |
| `test_canary.py`    | `test_canary_proportional_rescaling`| Canary replayed against $3\times$ organic growth | Attack volume rescaled proportionally; retains anomaly signature |
| `test_budget.py`    | `test_cumulative_drift_budget_rms` | Candidate $D_{\text{rms}} > B_{\text{rms}}$ | Promotion blocked with budget exceeded rejection trace |
| `test_budget.py`    | `test_single_feature_dmax_rejection` | Candidate with one runaway feature ($D_{\text{max}} > B_{\text{max}}$) | Rejected even though overall $D_{\text{rms}} \le B_{\text{rms}}$ |
| `test_rollback.py`  | `test_atomic_rollback_restoration` | Corrupted baseline promoted | Rollback restores model, scaler, schema, thresholds simultaneously |

### F. Backend API & Services (`backend/app/`)

| Test File | Test Case Name | Input / Precondition | Expected Assertion / Outcome |
| :--- | :--- | :--- | :--- |
| `test_replay_api.py`| `test_start_pause_resume_lifecycle` | POST `/api/v1/replay/{start,pause,resume,stop}` | Replay state transitions match `RUNNING` $\to$ `PAUSED` $\to$ `STOPPED` |
| `test_governance_api.py`| `test_candidate_approval_workflow` | POST `/api/v1/candidates/{id}/approve` | Status transitions from `PENDING` to `APPROVED`; audit logged |
| `test_explain_api.py`| `test_window_shap_explanation` | GET `/api/v1/windows/{id}/explain` | Returns SHAP feature dictionary and 5G hypothesis string |

### G. Frontend Components (`frontend/src/`)

| Test File | Test Case Name | Input / Precondition | Expected Assertion / Outcome |
| :--- | :--- | :--- | :--- |
| `ReplayControls.test.tsx` | `test_speed_and_scrub_actions` | User clicks $2\times$ speed button | Emits POST request to replay control API |
| `ModelHealthCard.test.tsx`| `test_budget_gauge_rendering` | Candidate with $D_{\text{rms}}=0.85$ | Renders budget consumption gauge with alert state color tokens |
| `DecisionTrace.test.tsx`  | `test_trace_audit_item_display` | Candidate JSON with 6 gate items | Renders all checks with distinct PASS/FAIL indicator badges |

---

## 3. Sample Test Fixtures

### Mock Replay Window Fixture (`fixture_window.json`)

```json
{
  "test_fixture_id": "fixture_window_benign_scaled",
  "window_payload": {
    "window_id": "t1e00000-0000-0000-0000-000000000001",
    "slice_id": "sst-1-sd-010203",
    "nf_id": "UPF-01",
    "duration_sec": 60,
    "raw_counters": {
      "active_ue_count": 3000,
      "pdu_sessions_established": 2980,
      "nas_failures": 2,
      "pfcp_failures": 0,
      "total_bytes_uplink": 300000000,
      "total_bytes_downlink": 1800000000,
      "total_packets": 1500000
    },
    "ratio_features": {
      "registrations_per_active_ue": 0.024,
      "nas_failure_ratio": 0.003,
      "pfcp_failure_ratio": 0.0,
      "pdu_session_rate_per_ue": 0.993,
      "bytes_per_session": 704697.9,
      "packets_per_session": 503.35,
      "gtpu_volume_per_ue": 700000.0,
      "ue_hash_entropy": 7.85,
      "new_ue_rate": 0.012
    },
    "composition_vector": {
      "registration_ratio": 0.078,
      "session_setup_ratio": 0.912,
      "failure_ratio": 0.004,
      "other_signalling_ratio": 0.006
    }
  },
  "expected_attributor_verdict": "likely_benign",
  "expected_detector_anomalous": false
}
```

---

## 4. Open Questions

| ID | Test Domain | Spec Section Reference | Question / Ambiguity | Temporary Testing Assumption |
| :--- | :--- | :--- | :--- | :--- |
| **OQ-T1** | Evaluation | F2 / Leave-one-out CI | Bootstrap sample count and confidence level definition. | 1,000 bootstrap iterations at 95% confidence intervals ($\alpha = 0.05$). |
| **OQ-T2** | Attributor | F3.B / Informal analyst check | Automated test representation for the informal 3-to-5 analyst validation check. | Mock survey response fixture with inter-rater agreement metric (Fleiss' Kappa $\ge 0.70$). |
| **OQ-T3** | Governance | F4.A / Dwell time | Specific default duration required between consecutive baseline promotions. | Default dwell time set to 3,600 seconds (1 hour of replay time). |
