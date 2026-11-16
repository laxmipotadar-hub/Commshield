# CommShield Contracts Specification

## 1. Database Schema (SQLAlchemy Portable: SQLite & PostgreSQL)

All tables use standard SQLAlchemy types with `JSON` column abstractions (stored as `TEXT` in SQLite, `JSONB` in PostgreSQL). Foreign keys and compound indices enforce referential integrity.

### Table Definitions

| Table Name | Column Name | SQLAlchemy Type | Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`baselines`** | `id` | `String(36)` | PK, UUID | Unique baseline package ID |
| | `slice_id` | `String(64)` | Indexed, NOT NULL | S-NSSAI identifier (e.g. `sst-1-sd-010203`) |
| | `nf_id` | `String(64)` | Indexed, NOT NULL | Network function tag (e.g. `AMF-01`, `UPF-01`) |
| | `version` | `String(32)` | NOT NULL | Semantic version (e.g. `v1.0.0-anchor`) |
| | `is_anchor` | `Boolean` | NOT NULL, Default False | Immutable trusted anchor flag |
| | `is_active` | `Boolean` | NOT NULL, Default False | Currently active serving baseline flag |
| | `training_window_start` | `DateTime(timezone=True)` | NOT NULL | Benign training start boundary |
| | `training_window_end` | `DateTime(timezone=True)` | NOT NULL | Benign training end boundary |
| | `model_artifact_path` | `String(255)` | NOT NULL | Path to serialized models (IF + AE) |
| | `scaler_params` | `JSON` | NOT NULL | Medians and IQRs for robust scaling |
| | `threshold_params` | `JSON` | NOT NULL | Calibration percentiles and CUSUM thresholds |
| | `feature_schema` | `JSON` | NOT NULL | Ordered feature list and ratio definitions |
| | `created_at` | `DateTime(timezone=True)` | NOT NULL | Creation timestamp |
| **`canonical_windows`** | `id` | `String(36)` | PK, UUID | Unique window ID |
| | `slice_id` | `String(64)` | Indexed, NOT NULL | Slice identifier |
| | `nf_id` | `String(64)` | Indexed, NOT NULL | NF identifier |
| | `window_start` | `DateTime(timezone=True)` | Indexed, NOT NULL | Window start time |
| | `window_end` | `DateTime(timezone=True)` | NOT NULL | Window end time |
| | `duration_sec` | `Integer` | NOT NULL | Aggregation scale (10, 60, or 300) |
| | `raw_counters` | `JSON` | NOT NULL | Raw counts (bytes, packets, sessions) |
| | `ratio_features` | `JSON` | NOT NULL | Computed ratio and rate features |
| | `composition_vector` | `JSON` | NOT NULL | Normalized distribution for JSD testing |
| | `created_at` | `DateTime(timezone=True)` | NOT NULL | Ingestion timestamp |
| **`detection_results`** | `id` | `String(36)` | PK, UUID | Unique detection record ID |
| | `window_id` | `String(36)` | FK(`canonical_windows.id`), Indexed | Referenced window ID |
| | `slice_id` | `String(64)` | Indexed, NOT NULL | Slice identifier |
| | `baseline_id` | `String(36)` | FK(`baselines.id`), NOT NULL | Evaluated baseline version |
| | `if_score` | `Float` | NOT NULL | Isolation Forest raw score (negated) |
| | `if_percentile` | `Float` | NOT NULL | Benign reference percentile [0.0 - 1.0] |
| | `ae_recon_error` | `Float` | NOT NULL | Autoencoder reconstruction MSE |
| | `ae_percentile` | `Float` | NOT NULL | Benign reference percentile [0.0 - 1.0] |
| | `fused_percentile` | `Float` | NOT NULL | Fused score (e.g. max of percentiles) |
| | `cusum_score` | `Float` | NOT NULL | Cumulative sum anomaly statistic |
| | `agreement_state` | `String(32)` | NOT NULL | `BOTH_FIRE`, `IF_ONLY`, `AE_ONLY`, `NONE` |
| | `is_anomalous` | `Boolean` | NOT NULL | True if fused percentile exceeds threshold |
| | `created_at` | `DateTime(timezone=True)` | NOT NULL | Evaluation timestamp |
| **`attribution_results`** | `id` | `String(36)` | PK, UUID | Unique attribution record ID |
| | `window_id` | `String(36)` | FK(`canonical_windows.id`), Indexed | Referenced window ID |
| | `slice_id` | `String(64)` | Indexed, NOT NULL | Slice identifier |
| | `drift_detected` | `Boolean` | NOT NULL | True if ADWIN triggered |
| | `verdict` | `String(32)` | NOT NULL | `likely_benign`, `likely_attack`, `uncertain` |
| | `abstain_reason` | `String(64)` | Nullable | Named reason if verdict is `uncertain` |
| | `jsd_divergence` | `Float` | NOT NULL | Jensen-Shannon Divergence score |
| | `scaling_factor_k` | `Float` | NOT NULL | Estimated volume scale factor |
| | `evidence_signals` | `JSON` | NOT NULL | Supporting signals (entropy, cross-slice, etc.) |
| | `created_at` | `DateTime(timezone=True)` | NOT NULL | Creation timestamp |
| **`candidate_baselines`** | `id` | `String(36)` | PK, UUID | Unique candidate ID |
| | `slice_id` | `String(64)` | Indexed, NOT NULL | Target slice ID |
| | `candidate_version`| `String(32)` | NOT NULL | Candidate version string |
| | `active_baseline_id` | `String(36)` | FK(`baselines.id`), NOT NULL | Currently active baseline compared |
| | `anchor_baseline_id` | `String(36)` | FK(`baselines.id`), NOT NULL | Immutable anchor baseline compared |
| | `status` | `String(32)` | NOT NULL | `PENDING`, `APPROVED`, `REJECTED`, `ROLLED_BACK` |
| | `gate_metrics` | `JSON` | NOT NULL | Holds $D_{\text{rms}}, D_{\text{max}}, \Delta_{\text{can}}$, canary recall |
| | `decision_trace` | `JSON` | NOT NULL | Array of audit check strings |
| | `reviewed_by` | `String(64)` | Nullable | Analyst identifier |
| | `reviewed_at` | `DateTime(timezone=True)` | Nullable | Approval / Rejection timestamp |
| | `created_at` | `DateTime(timezone=True)` | NOT NULL | Candidate generation timestamp |
| **`quarantine_windows`** | `id` | `String(36)` | PK, UUID | Unique quarantine item ID |
| | `window_id` | `String(36)` | FK(`canonical_windows.id`), NOT NULL | Quarantined window ID |
| | `slice_id` | `String(64)` | Indexed, NOT NULL | Slice identifier |
| | `reason` | `String(64)` | NOT NULL | Isolation reason (`UNCERTAIN_ATTRIBUTION`, etc.) |
| | `quarantined_at` | `DateTime(timezone=True)` | NOT NULL | Timestamp quarantined |
| **`audit_events`** | `id` | `String(36)` | PK, UUID | Unique audit record ID |
| | `event_type` | `String(64)` | Indexed, NOT NULL | `PROMOTION`, `ROLLBACK`, `REANCHOR`, `APPROVAL` |
| | `slice_id` | `String(64)` | NOT NULL | Slice identifier |
| | `actor` | `String(64)` | NOT NULL | User ID or system service |
| | `details` | `JSON` | NOT NULL | Event parameters, before/after diffs |
| | `timestamp` | `DateTime(timezone=True)` | NOT NULL | Audit timestamp |
| **`experiment_results`** | `id` | `String(36)` | PK, UUID | Unique experiment run ID |
| | `scenario` | `String(64)` | Indexed, NOT NULL | Scenario name (`stable_benign`, etc.) |
| | `seed` | `Integer` | Indexed, NOT NULL | Random generator seed |
| | `arm` | `String(32)` | Indexed, NOT NULL | `arm_a_static`, `arm_b_naive`, `arm_c_commshield` |
| | `config_version` | `String(32)` | NOT NULL | Evaluation configuration version |
| | `recall` | `Float` | Nullable | Attack detection rate (recall) |
| | `fpr` | `Float` | NOT NULL | False-positive rate on benign windows |
| | `contamination_final` | `Float` | NOT NULL | Final attack fraction in active baseline |
| | `adaptations_count` | `Integer` | NOT NULL | Number of promoted baseline adaptations |
| | `quarantined_count` | `Integer` | NOT NULL | Number of quarantined windows/candidates |
| | `recovery_time_windows` | `Integer` | Nullable | Post-attack recovery time in windows |
| | `metrics` | `JSON` | NOT NULL | Full run metrics and contamination history |
| | `timestamp` | `DateTime(timezone=True)` | NOT NULL | Experiment execution timestamp |

---

## 2. API Endpoints

### Replay & Dataset Endpoints

| Method | Route | Description | Request Payload | Response Payload |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/datasets` | List available public & testbed traces | None | `DatasetListResponse` |
| `POST` | `/api/v1/replay/start` | Start replay stream across 3 arms | `ReplayStartRequest` | `ReplayStatusResponse` |
| `POST` | `/api/v1/replay/pause` | Pause active replay | None | `ReplayStatusResponse` |
| `POST` | `/api/v1/replay/resume` | Resume paused replay | None | `ReplayStatusResponse` |
| `POST` | `/api/v1/replay/stop` | Terminate active replay | None | `ReplayStatusResponse` |
| `GET` | `/api/v1/replay/status` | Current tick and replay state | None | `ReplayStatusResponse` |
| `GET` | `/api/v1/replay/stream` | Server-Sent Events stream of replay windows | None (SSE query params: `speed=1`) | Event Stream (`WindowReplayEvent`) |

#### Replay API JSON Schemas

```json
{
  "ReplayStartRequest": {
    "dataset_id": "5g_nidd_portscan_growth",
    "speed_multiplier": 2.0,
    "active_arms": ["arm_a_static", "arm_b_naive", "arm_c_commshield"],
    "window_scale_sec": 60
  },
  "ReplayStatusResponse": {
    "status": "RUNNING",
    "dataset_id": "5g_nidd_portscan_growth",
    "current_window_index": 420,
    "total_windows": 1440,
    "speed_multiplier": 2.0,
    "current_timestamp": "2026-11-15T12:07:00Z"
  }
}
```

### Detection & Windows Endpoints

| Method | Route | Description | Request Payload | Response Payload |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/windows` | Paginated canonical windows | Query params: `slice_id, limit, offset` | `PaginatedWindowsResponse` |
| `GET` | `/api/v1/windows/{window_id}/explain` | SHAP feature attributions for window | None | `ExplainabilityResponse` |

#### Explainability API JSON Schema

```json
{
  "ExplainabilityResponse": {
    "window_id": "c1f7a4d2-3c22-498b-967f-9e79432f41bb",
    "slice_id": "sst-1-sd-010203",
    "nf_id": "UPF-01",
    "is_anomalous": true,
    "fused_percentile": 0.9982,
    "shap_values": {
      "nas_failure_ratio": 0.452,
      "bytes_per_session": 0.281,
      "pdu_session_rate_per_ue": -0.015,
      "ue_hash_entropy": 0.124
    },
    "hypothesis": "Signalling flood with elevated NAS rejection rates during session establishment.",
    "attribution_summary": {
      "verdict": "likely_attack",
      "abstain_reason": null
    }
  }
}
```

### Governance & Baselines Endpoints

| Method | Route | Description | Request Payload | Response Payload |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/baselines` | List active & anchor baselines | Query params: `slice_id` | `List[BaselineSummaryResponse]` |
| `GET` | `/api/v1/candidates` | List pending shadow candidate baselines | Query params: `status` | `List[CandidateResponse]` |
| `POST` | `/api/v1/candidates/{id}/approve` | Operator approves promotion | `ApprovalActionRequest` | `CandidateResponse` |
| `POST` | `/api/v1/candidates/{id}/reject` | Operator rejects candidate | `ApprovalActionRequest` | `CandidateResponse` |
| `POST` | `/api/v1/baselines/rollback` | Atomic rollback to designated baseline | `RollbackRequest` | `RollbackResponse` |
| `GET` | `/api/v1/experiments/three-arm` | Compare metrics across arms A/B/C | Query params: `dataset_id` | `ThreeArmComparisonResponse` |
| `POST` | `/api/v1/experiments/run` | Trigger multi-seed 3-arm benchmark in background | `ExperimentRunRequest` | `Dict[str, Any]` |
| `GET` | `/api/v1/experiments/status` | Execution status & progress of benchmark | None | `Dict[str, Any]` |
| `GET` | `/api/v1/experiments/results` | Aggregated multi-seed experiment benchmark results | None | `Dict[str, Any]` |
| `GET` | `/api/v1/experiments/results/{scenario}` | Single-scenario benchmark results | None | `Dict[str, Any]` |

#### Governance Action JSON Schemas

```json
{
  "ApprovalActionRequest": {
    "analyst_id": "analyst_sec_09",
    "notes": "Verified organic marketing campaign traffic surge matches change-event log."
  },
  "RollbackRequest": {
    "slice_id": "sst-1-sd-010203",
    "nf_id": "UPF-01",
    "target_baseline_version": "v1.0.0-anchor",
    "reason": "Detection degradation observed post candidate canary evaluation",
    "analyst_id": "analyst_sec_09"
  },
  "RollbackResponse": {
    "status": "COMPLETED",
    "slice_id": "sst-1-sd-010203",
    "active_version": "v1.0.0-anchor",
    "restored_artifacts": ["model", "scaler", "thresholds", "schema"],
    "timestamp": "2026-11-15T12:15:30Z"
  }
}
```

---

## 3. Canonical JSON Contracts

### A. Canonical Traffic Window (`CanonicalTrafficWindow`)

```json
{
  "window_id": "c1f7a4d2-3c22-498b-967f-9e79432f41bb",
  "slice_id": "sst-1-sd-010203",
  "nf_id": "UPF-01",
  "window_start": "2026-11-15T12:00:00Z",
  "window_end": "2026-11-15T12:01:00Z",
  "duration_sec": 60,
  "raw_counters": {
    "active_ue_count": 1420,
    "registration_attempts": 35,
    "registration_failures": 1,
    "pdu_sessions_established": 1410,
    "nas_messages_total": 450,
    "nas_failures": 2,
    "pfcp_association_messages": 85,
    "pfcp_failures": 0,
    "total_bytes_uplink": 142058000,
    "total_bytes_downlink": 894500000,
    "total_packets": 780000,
    "gtpu_teid_count": 1410
  },
  "ratio_features": {
    "registrations_per_active_ue": 0.0246,
    "nas_failure_ratio": 0.0044,
    "pfcp_failure_ratio": 0.0,
    "pdu_session_rate_per_ue": 0.993,
    "bytes_per_session": 735147.5,
    "packets_per_session": 553.19,
    "gtpu_volume_per_ue": 730181.7,
    "ue_hash_entropy": 7.421,
    "new_ue_rate": 0.015
  },
  "composition_vector": {
    "registration_ratio": 0.0778,
    "session_setup_ratio": 0.9122,
    "failure_ratio": 0.0044,
    "other_signalling_ratio": 0.0056
  }
}
```

### B. Detector Output (`DetectorOutput`)

```json
{
  "window_id": "c1f7a4d2-3c22-498b-967f-9e79432f41bb",
  "slice_id": "sst-1-sd-010203",
  "nf_id": "UPF-01",
  "evaluated_at": "2026-11-15T12:01:02Z",
  "baseline_version": "v1.2.0-candidate",
  "isolation_forest": {
    "raw_score_negated": 0.684,
    "benign_percentile": 0.985,
    "threshold_percentile": 0.980,
    "is_flagged": true
  },
  "autoencoder": {
    "reconstruction_mse": 0.0412,
    "benign_percentile": 0.991,
    "threshold_percentile": 0.980,
    "is_flagged": true
  },
  "fusion": {
    "primary_rule": "MAX_PERCENTILE",
    "fused_percentile": 0.991,
    "secondary_mean_percentile": 0.988,
    "agreement_state": "BOTH_FIRE",
    "is_anomalous": true
  },
  "cusum": {
    "accumulated_statistic": 4.82,
    "alarm_threshold": 4.50,
    "is_alarm": true
  }
}
```

### C. Attribution Output with Abstention (`AttributionOutput`)

#### Case 1: Likely Benign (Proportional Growth)
```json
{
  "window_id": "d2a8b5e3-4d33-5a9c-878e-0f80543f52cc",
  "slice_id": "sst-1-sd-010203",
  "drift_detected": true,
  "verdict": "likely_benign",
  "abstain_reason": null,
  "proportional_growth_test": {
    "scaling_factor_k": 2.85,
    "jsd_divergence": 0.0124,
    "jsd_null_threshold_99th": 0.0350,
    "passed": true
  },
  "supporting_signals": {
    "ue_entropy_delta": 0.12,
    "new_ue_rate": 0.042,
    "nas_failure_ratio": 0.003,
    "control_slice_concordance": "NETWORK_WIDE_EXPANSION",
    "change_log_match": true
  },
  "action_recommendation": "Quarantine clear; queue windows for shadow candidate training"
}
```

#### Case 2: Uncertain (Abstained with Named Reason)
```json
{
  "window_id": "e3b9c6f4-5e44-6b0d-989f-1a91654a63dd",
  "slice_id": "sst-1-sd-010203",
  "drift_detected": true,
  "verdict": "uncertain",
  "abstain_reason": "volume_composition_disagree",
  "proportional_growth_test": {
    "scaling_factor_k": 1.25,
    "jsd_divergence": 0.145,
    "jsd_null_threshold_99th": 0.0350,
    "passed": false
  },
  "supporting_signals": {
    "ue_entropy_delta": -1.85,
    "new_ue_rate": 0.008,
    "nas_failure_ratio": 0.082,
    "control_slice_concordance": "LOCALIZED_TO_SLICE_1",
    "change_log_match": false
  },
  "action_recommendation": "Abstain from adaptation; quarantine window; notify analyst"
}
```

### D. Candidate Baseline Package (`CandidateBaselinePackage`)

```json
{
  "candidate_id": "cand-9f88b0a1-7b55-46f9-bf51-11c750e3d220",
  "slice_id": "sst-1-sd-010203",
  "nf_id": "UPF-01",
  "candidate_version": "v1.3.0-cand",
  "active_version": "v1.2.0",
  "anchor_version": "v1.0.0-anchor",
  "training_metadata": {
    "window_count": 720,
    "quarantined_windows_excluded": 34,
    "start_time": "2026-11-15T00:00:00Z",
    "end_time": "2026-11-15T12:00:00Z"
  },
  "gate_evaluations": {
    "normal_holdout_fpr": {
      "anchor_fpr": 0.008,
      "candidate_fpr": 0.009,
      "allowed_margin_delta": 0.005,
      "passed": true
    },
    "canary_retention_test": {
      "passed": true,
      "category_results": [
        {
          "category": "pfcp_flood",
          "anchor_recall": 0.96,
          "candidate_recall": 0.95,
          "delta": 0.01,
          "margin_limit": 0.03,
          "passed": true
        },
        {
          "category": "syn_flood",
          "anchor_recall": 0.98,
          "candidate_recall": 0.97,
          "delta": 0.01,
          "margin_limit": 0.03,
          "passed": true
        }
      ]
    },
    "step_limit": {
      "metric": "D_rms(candidate, active)",
      "observed": 0.35,
      "limit_b_step": 0.50,
      "passed": true
    },
    "cumulative_drift_budget": {
      "metric_d_rms": {
        "observed": 0.85,
        "limit_B_rms": 1.20,
        "passed": true
      },
      "metric_d_max": {
        "feature": "bytes_per_session",
        "observed": 1.45,
        "limit_B_max": 2.00,
        "passed": true
      },
      "metric_delta_can": {
        "observed": 0.04,
        "limit_B_can": 0.08,
        "passed": true
      }
    }
  },
  "overall_governance_decision": "PENDING_APPROVAL",
  "decision_trace": [
    "Normal holdout FPR backtest: PASSED (0.009 <= 0.013)",
    "Canary retention test: PASSED (All categories within margin delta 0.03)",
    "Per-update step limit D_rms(cand, active): PASSED (0.35 <= 0.50)",
    "Cumulative drift budget D_rms(cand, anchor): PASSED (0.85 <= 1.20)",
    "Single-feature shift D_max(cand, anchor): PASSED (1.45 <= 2.00 on bytes_per_session)",
    "Canary percentile drop Delta_can: PASSED (0.04 <= 0.08)",
    "Analyst promotion gate: PENDING"
  ]
}
```

---

## 4. Open Questions

| ID | Contract Domain | Spec Section Reference | Question / Ambiguity | Temporary Contract Assumption |
| :--- | :--- | :--- | :--- | :--- |
| **OQ-C1** | Database | F4.A / Candidate versioning | Version naming convention across automated canary candidates. | Auto-increment format `v<major>.<minor>.<patch>-cand.<hash>`. |
| **OQ-C2** | API | F5 / Dashboard SHAP | Real-time calculation latency of SHAP values for high-frequency windows. | Pre-compute KernelSHAP/TreeSHAP asynchronously only for windows where `is_anomalous == True`. |
| **OQ-C3** | JSON | F3.B / JSD Null Threshold | Null distribution calculation window size for benign-vs-benign comparisons. | Store fixed calibration parameters `(mean, 99th_percentile)` calculated during tuning stream preprocessing. |
