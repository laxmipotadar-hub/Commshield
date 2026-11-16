import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from ..database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Baseline(Base):
    __tablename__ = "baselines"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    slice_id = Column(String(64), nullable=False, index=True)
    nf_id = Column(String(64), nullable=False, index=True)
    version = Column(String(32), nullable=False)
    is_anchor = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=False)
    training_window_start = Column(DateTime(timezone=True), nullable=False)
    training_window_end = Column(DateTime(timezone=True), nullable=False)
    model_artifact_path = Column(String(255), nullable=False)
    scaler_params = Column(JSON, nullable=False)
    threshold_params = Column(JSON, nullable=False)
    feature_schema = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class CanonicalWindow(Base):
    __tablename__ = "canonical_windows"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    slice_id = Column(String(64), nullable=False, index=True)
    nf_id = Column(String(64), nullable=False, index=True)
    window_start = Column(DateTime(timezone=True), nullable=False, index=True)
    window_end = Column(DateTime(timezone=True), nullable=False)
    duration_sec = Column(Integer, nullable=False)
    raw_counters = Column(JSON, nullable=False)
    ratio_features = Column(JSON, nullable=False)
    composition_vector = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    detection_results = relationship("DetectionResult", back_populates="window", cascade="all, delete-orphan")
    attribution_results = relationship("AttributionResult", back_populates="window", cascade="all, delete-orphan")
    quarantine_windows = relationship("QuarantineWindow", back_populates="window", cascade="all, delete-orphan")


class DetectionResult(Base):
    __tablename__ = "detection_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    window_id = Column(String(36), ForeignKey("canonical_windows.id", ondelete="CASCADE"), nullable=False, index=True)
    slice_id = Column(String(64), nullable=False, index=True)
    baseline_id = Column(String(36), ForeignKey("baselines.id"), nullable=False)
    if_score = Column(Float, nullable=False)
    if_percentile = Column(Float, nullable=False)
    ae_recon_error = Column(Float, nullable=False)
    ae_percentile = Column(Float, nullable=False)
    fused_percentile = Column(Float, nullable=False)
    cusum_score = Column(Float, nullable=False)
    agreement_state = Column(String(32), nullable=False)
    is_anomalous = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    window = relationship("CanonicalWindow", back_populates="detection_results")
    baseline = relationship("Baseline")


class AttributionResult(Base):
    __tablename__ = "attribution_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    window_id = Column(String(36), ForeignKey("canonical_windows.id", ondelete="CASCADE"), nullable=False, index=True)
    slice_id = Column(String(64), nullable=False, index=True)
    drift_detected = Column(Boolean, nullable=False)
    verdict = Column(String(32), nullable=False)
    abstain_reason = Column(String(64), nullable=True)
    jsd_divergence = Column(Float, nullable=False)
    scaling_factor_k = Column(Float, nullable=False)
    evidence_signals = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    window = relationship("CanonicalWindow", back_populates="attribution_results")


class CandidateBaseline(Base):
    __tablename__ = "candidate_baselines"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    slice_id = Column(String(64), nullable=False, index=True)
    candidate_version = Column(String(32), nullable=False)
    parent_version = Column(String(32), nullable=True)
    active_baseline_id = Column(String(36), ForeignKey("baselines.id"), nullable=False)
    anchor_baseline_id = Column(String(36), ForeignKey("baselines.id"), nullable=False)
    status = Column(String(32), nullable=False)
    gate_metrics = Column(JSON, nullable=False)
    decision_trace = Column(JSON, nullable=False)
    training_window_ids = Column(JSON, nullable=True)
    model_artifact_path = Column(String(255), nullable=True)
    reviewed_by = Column(String(64), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    active_baseline = relationship("Baseline", foreign_keys=[active_baseline_id])
    anchor_baseline = relationship("Baseline", foreign_keys=[anchor_baseline_id])


class DriftBudget(Base):
    __tablename__ = "drift_budgets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    candidate_id = Column(String(36), nullable=False, index=True)
    slice_id = Column(String(64), nullable=False, index=True)
    d_rms_active = Column(Float, nullable=False)
    d_rms_anchor = Column(Float, nullable=False)
    d_max_anchor = Column(Float, nullable=False)
    delta_canary = Column(Float, nullable=False)
    metrics = Column(JSON, nullable=False)
    passed = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class CanaryResult(Base):
    __tablename__ = "canary_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    candidate_id = Column(String(36), nullable=False, index=True)
    slice_id = Column(String(64), nullable=False, index=True)
    active_recall = Column(Float, nullable=False)
    candidate_recall = Column(Float, nullable=False)
    recall_delta = Column(Float, nullable=False)
    category_recalls = Column(JSON, nullable=False)
    passed = Column(Boolean, nullable=False)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class ApprovalLog(Base):
    __tablename__ = "approval_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    candidate_id = Column(String(36), nullable=False, index=True)
    slice_id = Column(String(64), nullable=False, index=True)
    action = Column(String(32), nullable=False)  # APPROVED or REJECTED
    analyst_id = Column(String(64), nullable=False)
    notes = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class QuarantineWindow(Base):
    __tablename__ = "quarantine_windows"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    window_id = Column(String(36), ForeignKey("canonical_windows.id", ondelete="CASCADE"), nullable=False)
    slice_id = Column(String(64), nullable=False, index=True)
    reason = Column(String(64), nullable=False)
    scenario = Column(String(64), nullable=True)
    quarantined_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    window = relationship("CanonicalWindow", back_populates="quarantine_windows")


class DriftEvent(Base):
    __tablename__ = "drift_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    window_id = Column(String(36), nullable=False, index=True)
    slice_id = Column(String(64), nullable=False, index=True)
    event_time = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    volume_multiplier = Column(Float, nullable=False, default=1.0)
    drift_detected = Column(Boolean, nullable=False, default=True)
    attribution_id = Column(String(36), nullable=True)
    decision_trace_id = Column(String(36), nullable=True)
    attribution = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class DecisionTrace(Base):
    __tablename__ = "decision_traces"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    window_id = Column(String(36), nullable=False, index=True)
    slice_id = Column(String(64), nullable=False, index=True)
    alert_id = Column(String(36), nullable=True)
    drift_event_id = Column(String(36), nullable=True)
    steps = Column(JSON, nullable=False)
    verdict = Column(String(32), nullable=False)
    action = Column(String(32), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_type = Column(String(64), nullable=False, index=True)
    slice_id = Column(String(64), nullable=False)
    actor = Column(String(64), nullable=False)
    details = Column(JSON, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class BaselineRegistry(Base):
    __tablename__ = "baseline_registry"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    slice_id = Column(String(64), nullable=False, index=True)
    nf_id = Column(String(64), nullable=False, default="UPF-01")
    version = Column(String(32), nullable=False)
    is_anchor = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=False)
    training_window_count = Column(Integer, nullable=False, default=0)
    training_window_start = Column(DateTime(timezone=True), nullable=True)
    training_window_end = Column(DateTime(timezone=True), nullable=True)
    model_artifact_path = Column(String(255), nullable=False)
    scaler_params = Column(JSON, nullable=False)
    threshold_params = Column(JSON, nullable=False)
    feature_schema = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class AnomalyAlert(Base):
    __tablename__ = "anomaly_alerts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    window_id = Column(String(36), nullable=False, index=True)
    slice_id = Column(String(64), nullable=False, index=True)
    nf_id = Column(String(64), nullable=False, default="UPF-01")
    detector_output = Column(JSON, nullable=False)
    is_anomalous = Column(Boolean, nullable=False, default=True)
    fused_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    scenario = Column(String(64), nullable=False, index=True)
    seed = Column(Integer, nullable=False, index=True)
    arm = Column(String(32), nullable=False, index=True)  # arm_a_static, arm_b_naive, arm_c_commshield
    config_version = Column(String(32), nullable=False, default="v1.0.0")
    recall = Column(Float, nullable=True)
    fpr = Column(Float, nullable=False)
    contamination_final = Column(Float, nullable=False, default=0.0)
    adaptations_count = Column(Integer, nullable=False, default=0)
    quarantined_count = Column(Integer, nullable=False, default=0)
    recovery_time_windows = Column(Integer, nullable=True)
    metrics = Column(JSON, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now)


