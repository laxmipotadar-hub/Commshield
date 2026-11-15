"""Sample placeholder data adhering strictly to CONTRACTS.md specifications."""

from datetime import datetime, timezone
from typing import List

from ..schemas import (
    AttributionSummary,
    BaselineSummaryResponse,
    CanonicalTrafficWindow,
    CandidateResponse,
    DatasetInfo,
    DatasetListResponse,
    ExplainabilityResponse,
    PaginatedWindowsResponse,
    ReplayStatusResponse,
    RollbackResponse,
    ThreeArmComparisonResponse,
    WindowReplayEvent,
)


def get_sample_datasets() -> DatasetListResponse:
    datasets: List[DatasetInfo] = [
        DatasetInfo(
            dataset_id="5g_nidd_portscan_growth",
            name="5G-NIDD Port Scan with Proportional Growth",
            description="5G-NIDD testbed capture with benign proportional growth mixed with stealth port scans.",
            total_windows=1440,
            duration_sec=86400,
            attack_types=["portscan", "signalling_flood"],
        ),
        DatasetInfo(
            dataset_id="open5gs_pfcp_flood",
            name="Open5GS PFCP Association Flood",
            description="Open5GS core network trace demonstrating PFCP session teardown & flood attack.",
            total_windows=720,
            duration_sec=43200,
            attack_types=["pfcp_flood"],
        ),
        DatasetInfo(
            dataset_id="mawi_growth_baseline",
            name="MAWI Real Backbone Organic Growth",
            description="High-volume real-world backbone traffic exhibiting diurnal volume scaling.",
            total_windows=2880,
            duration_sec=172800,
            attack_types=[],
        ),
    ]
    return DatasetListResponse(
        datasets=datasets,
        total=len(datasets),
        is_placeholder=True,
    )


def get_sample_replay_status(
    status: str = "RUNNING",
    dataset_id: str = "5g_nidd_portscan_growth",
    speed_multiplier: float = 2.0,
) -> ReplayStatusResponse:
    return ReplayStatusResponse(
        status=status,
        dataset_id=dataset_id,
        current_window_index=420,
        total_windows=1440,
        speed_multiplier=speed_multiplier,
        current_timestamp=datetime(2026, 11, 15, 12, 7, 0, tzinfo=timezone.utc),
        is_placeholder=True,
    )


def get_sample_canonical_window(
    window_id: str = "c1f7a4d2-3c22-498b-967f-9e79432f41bb",
    slice_id: str = "sst-1-sd-010203",
    nf_id: str = "UPF-01",
) -> CanonicalTrafficWindow:
    return CanonicalTrafficWindow(
        window_id=window_id,
        slice_id=slice_id,
        nf_id=nf_id,
        window_start=datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc),
        window_end=datetime(2026, 11, 15, 12, 1, 0, tzinfo=timezone.utc),
        duration_sec=60,
        raw_counters={
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
            "gtpu_teid_count": 1410,
        },
        ratio_features={
            "registrations_per_active_ue": 0.0246,
            "nas_failure_ratio": 0.0044,
            "pfcp_failure_ratio": 0.0,
            "pdu_session_rate_per_ue": 0.993,
            "bytes_per_session": 735147.5,
            "packets_per_session": 553.19,
            "gtpu_volume_per_ue": 730181.7,
            "ue_hash_entropy": 7.421,
            "new_ue_rate": 0.015,
        },
        composition_vector={
            "registration_ratio": 0.0778,
            "session_setup_ratio": 0.9122,
            "failure_ratio": 0.0044,
            "other_signalling_ratio": 0.0056,
        },
        is_placeholder=True,
    )


def get_sample_paginated_windows(
    slice_id: str = "sst-1-sd-010203",
    limit: int = 50,
    offset: int = 0,
) -> PaginatedWindowsResponse:
    sample_window = get_sample_canonical_window(slice_id=slice_id)
    return PaginatedWindowsResponse(
        items=[sample_window],
        total=1,
        limit=limit,
        offset=offset,
        is_placeholder=True,
    )


def get_sample_explainability(
    window_id: str = "c1f7a4d2-3c22-498b-967f-9e79432f41bb",
    slice_id: str = "sst-1-sd-010203",
    nf_id: str = "UPF-01",
) -> ExplainabilityResponse:
    return ExplainabilityResponse(
        window_id=window_id,
        slice_id=slice_id,
        nf_id=nf_id,
        is_anomalous=True,
        fused_percentile=0.9982,
        shap_values={
            "nas_failure_ratio": 0.452,
            "bytes_per_session": 0.281,
            "pdu_session_rate_per_ue": -0.015,
            "ue_hash_entropy": 0.124,
        },
        hypothesis="Signalling flood with elevated NAS rejection rates during session establishment.",
        attribution_summary=AttributionSummary(
            verdict="likely_attack",
            abstain_reason=None,
        ),
        is_placeholder=True,
    )


def get_sample_baselines(slice_id: str = "sst-1-sd-010203") -> List[BaselineSummaryResponse]:
    return [
        BaselineSummaryResponse(
            id="b1f7a4d2-1111-498b-967f-9e79432f41aa",
            slice_id=slice_id,
            nf_id="UPF-01",
            version="v1.0.0-anchor",
            is_anchor=True,
            is_active=True,
            training_window_start=datetime(2026, 11, 14, 0, 0, 0, tzinfo=timezone.utc),
            training_window_end=datetime(2026, 11, 15, 0, 0, 0, tzinfo=timezone.utc),
            model_artifact_path="data/artifacts/baselines/v1.0.0-anchor.joblib",
            scaler_params={
                "medians": {"bytes_per_session": 720000.0, "ue_hash_entropy": 7.4},
                "iqrs": {"bytes_per_session": 150000.0, "ue_hash_entropy": 0.8},
            },
            threshold_params={
                "if_threshold": 0.98,
                "ae_threshold": 0.98,
                "cusum_threshold": 4.5,
            },
            feature_schema={
                "features": [
                    "registrations_per_active_ue",
                    "nas_failure_ratio",
                    "pfcp_failure_ratio",
                    "pdu_session_rate_per_ue",
                    "bytes_per_session",
                    "packets_per_session",
                    "gtpu_volume_per_ue",
                    "ue_hash_entropy",
                    "new_ue_rate",
                ]
            },
            created_at=datetime(2026, 11, 15, 0, 0, 0, tzinfo=timezone.utc),
            is_placeholder=True,
        )
    ]


def get_sample_candidates(status: str = "PENDING") -> List[CandidateResponse]:
    return [
        CandidateResponse(
            id="cand-9f88b0a1-7b55-46f9-bf51-11c750e3d220",
            slice_id="sst-1-sd-010203",
            candidate_version="v1.3.0-cand",
            active_baseline_id="b1f7a4d2-1111-498b-967f-9e79432f41aa",
            anchor_baseline_id="b1f7a4d2-1111-498b-967f-9e79432f41aa",
            status=status,
            gate_metrics={
                "d_rms": 0.35,
                "d_max": 1.45,
                "delta_can": 0.04,
                "canary_recall": 0.96,
            },
            decision_trace=[
                "Normal holdout FPR backtest: PASSED (0.009 <= 0.013)",
                "Canary retention test: PASSED (All categories within margin delta 0.03)",
                "Per-update step limit D_rms(cand, active): PASSED (0.35 <= 0.50)",
                "Cumulative drift budget D_rms(cand, anchor): PASSED (0.85 <= 1.20)",
                "Single-feature shift D_max(cand, anchor): PASSED (1.45 <= 2.00 on bytes_per_session)",
                "Canary percentile drop Delta_can: PASSED (0.04 <= 0.08)",
                "Analyst promotion gate: PENDING",
            ],
            reviewed_by=None,
            reviewed_at=None,
            created_at=datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc),
            is_placeholder=True,
        )
    ]


def get_sample_candidate_decision(
    candidate_id: str,
    status: str,
    analyst_id: str,
) -> CandidateResponse:
    candidates = get_sample_candidates(status=status)
    c = candidates[0]
    return CandidateResponse(
        id=candidate_id,
        slice_id=c.slice_id,
        candidate_version=c.candidate_version,
        active_baseline_id=c.active_baseline_id,
        anchor_baseline_id=c.anchor_baseline_id,
        status=status,
        gate_metrics=c.gate_metrics,
        decision_trace=c.decision_trace + [f"Analyst promotion gate: {status} by {analyst_id}"],
        reviewed_by=analyst_id,
        reviewed_at=datetime.now(timezone.utc),
        created_at=c.created_at,
        is_placeholder=True,
    )


def get_sample_rollback(
    slice_id: str = "sst-1-sd-010203",
    target_version: str = "v1.0.0-anchor",
) -> RollbackResponse:
    return RollbackResponse(
        status="COMPLETED",
        slice_id=slice_id,
        active_version=target_version,
        restored_artifacts=["model", "scaler", "thresholds", "schema"],
        timestamp=datetime.now(timezone.utc),
        is_placeholder=True,
    )


def get_sample_three_arm(dataset_id: str = "5g_nidd_portscan_growth") -> ThreeArmComparisonResponse:
    return ThreeArmComparisonResponse(
        dataset_id=dataset_id,
        arms={
            "arm_a_static": {
                "name": "Static Anchor",
                "precision": 0.94,
                "recall": 0.72,
                "f1": 0.815,
                "false_alarm_rate": 0.085,
                "poisoning_susceptibility": 0.0,
            },
            "arm_b_naive": {
                "name": "Naive Retraining",
                "precision": 0.78,
                "recall": 0.45,
                "f1": 0.57,
                "false_alarm_rate": 0.02,
                "poisoning_susceptibility": 0.65,
            },
            "arm_c_commshield": {
                "name": "CommShield Gated Adaptation",
                "precision": 0.96,
                "recall": 0.93,
                "f1": 0.945,
                "false_alarm_rate": 0.012,
                "poisoning_susceptibility": 0.02,
            },
        },
        is_placeholder=True,
    )


def get_sample_window_event() -> WindowReplayEvent:
    sample_window = get_sample_canonical_window()
    return WindowReplayEvent(
        event_type="window",
        arm="arm_c_commshield",
        window=sample_window.model_dump(mode="json"),
        detector_output={
            "isolation_forest": {
                "raw_score_negated": 0.684,
                "benign_percentile": 0.985,
                "threshold_percentile": 0.980,
                "is_flagged": True,
            },
            "autoencoder": {
                "reconstruction_mse": 0.0412,
                "benign_percentile": 0.991,
                "threshold_percentile": 0.980,
                "is_flagged": True,
            },
            "fusion": {
                "primary_rule": "MAX_PERCENTILE",
                "fused_percentile": 0.991,
                "secondary_mean_percentile": 0.988,
                "agreement_state": "BOTH_FIRE",
                "is_anomalous": True,
            },
            "cusum": {
                "accumulated_statistic": 4.82,
                "alarm_threshold": 4.50,
                "is_alarm": True,
            },
        },
        attribution_output={
            "drift_detected": True,
            "verdict": "likely_attack",
            "abstain_reason": None,
            "action_recommendation": "Maintain active anchor; flag window for analyst review",
        },
        timestamp=datetime.now(timezone.utc),
        is_placeholder=True,
    )
