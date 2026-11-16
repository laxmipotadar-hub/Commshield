"""API endpoints for deep investigation, explainability, evidence synthesis, and analyst actions."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    AnomalyAlert,
    ApprovalLog,
    AuditEvent,
    Baseline,
    CanonicalWindow,
    CandidateBaseline,
    DecisionTrace,
    DetectionResult,
    DriftEvent,
    QuarantineWindow,
)

router = APIRouter(prefix="/investigation", tags=["Investigation"])


class AnalystFeedbackRequest(BaseModel):
    analyst_id: str = Field(..., description="Analyst identifier")
    classification: str = Field(..., description="'TRUE_POSITIVE', 'FALSE_POSITIVE', or 'NOTE'")
    notes: str = Field(..., description="Analyst notes and rationale")


class AnalystFeedbackItem(BaseModel):
    id: str
    analyst_id: str
    classification: str
    notes: str
    timestamp: str


@router.get("/{target_id}")
def get_investigation_details(
    target_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve complete investigation dossier for an alert, drift event, or canonical window."""
    # 1. Resolve window_id and related entities
    target_alert = db.query(AnomalyAlert).filter(AnomalyAlert.id == target_id).first()
    target_drift = db.query(DriftEvent).filter(DriftEvent.id == target_id).first()
    target_window = db.query(CanonicalWindow).filter(CanonicalWindow.id == target_id).first()
    target_trace = db.query(DecisionTrace).filter(DecisionTrace.id == target_id).first()

    window_id = None
    if target_alert:
        window_id = target_alert.window_id
    elif target_drift:
        window_id = target_drift.window_id
    elif target_window:
        window_id = target_window.id
    elif target_trace:
        window_id = target_trace.window_id
    else:
        # Fallback: check if target_id starts with win-
        win = db.query(CanonicalWindow).filter(CanonicalWindow.id == target_id).first()
        if win:
            window_id = win.id

    if not window_id:
        raise HTTPException(
            status_code=404,
            detail=f"Investigation target '{target_id}' not found across alerts, drift events, or windows.",
        )

    db_window = db.query(CanonicalWindow).filter(CanonicalWindow.id == window_id).first()
    if not db_window:
        raise HTTPException(status_code=404, detail=f"Canonical window '{window_id}' not found.")

    # Fetch associated records
    alert_row = target_alert or db.query(AnomalyAlert).filter(AnomalyAlert.window_id == window_id).first()
    drift_row = target_drift or db.query(DriftEvent).filter(DriftEvent.window_id == window_id).first()
    quarantine_row = db.query(QuarantineWindow).filter(QuarantineWindow.window_id == window_id).first()
    det_row = db.query(DetectionResult).filter(DetectionResult.window_id == window_id).first()
    trace_row = target_trace or db.query(DecisionTrace).filter(DecisionTrace.window_id == window_id).order_by(DecisionTrace.created_at.desc()).first()

    # Active baseline for this slice
    active_base = (
        db.query(Baseline)
        .filter(Baseline.slice_id == db_window.slice_id, Baseline.is_active == True)
        .first()
    )
    scaler_params = active_base.scaler_params if active_base and active_base.scaler_params else {}
    medians = scaler_params.get("medians", {})
    iqrs = scaler_params.get("iqrs", {})

    # 2. Alert Header computation
    fused_p = float(det_row.fused_percentile) if det_row else (
        float(alert_row.fused_score) if alert_row and alert_row.fused_score is not None else 0.5
    )
    is_anom = det_row.is_anomalous if det_row else (alert_row.is_anomalous if alert_row else False)

    # Final decision determination
    attr_data = drift_row.attribution if drift_row and drift_row.attribution else {}
    attr_verdict = attr_data.get("verdict", "")
    abstain_reason = attr_data.get("abstain_reason")

    if quarantine_row:
        final_decision = "Quarantine"
    elif attr_verdict == "uncertain" or (trace_row and trace_row.action == "quarantine_abstain"):
        final_decision = "Abstain"
    elif is_anom or alert_row:
        final_decision = "Alert"
    else:
        final_decision = "Normal"

    if fused_p >= 0.99:
        severity = "CRITICAL"
    elif fused_p >= 0.98:
        severity = "HIGH"
    elif fused_p >= 0.95:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    alert_header = {
        "id": target_id,
        "window_id": db_window.id,
        "slice_id": db_window.slice_id,
        "nf_id": db_window.nf_id,
        "timestamp": db_window.window_end.isoformat(),
        "severity": severity,
        "final_decision": final_decision,
        "baseline_version": active_base.version if active_base else "v1.0.0-anchor",
    }

    # 3. Expected vs Observed Traffic Series
    # Fetch recent historical windows for this slice leading up to this window
    recent_windows = (
        db.query(CanonicalWindow)
        .filter(
            CanonicalWindow.slice_id == db_window.slice_id,
            CanonicalWindow.window_end <= db_window.window_end,
        )
        .order_by(CanonicalWindow.window_end.desc())
        .limit(12)
        .all()
    )
    recent_windows.reverse()
    if not recent_windows:
        recent_windows = [db_window]

    traffic_series = []
    base_packets_med = float(medians.get("total_packets", 500000))
    base_packets_iqr = float(max(10000, iqrs.get("total_packets", 150000)))
    expected_min = max(0, round(base_packets_med - (1.5 * base_packets_iqr)))
    expected_max = round(base_packets_med + (1.5 * base_packets_iqr))

    for w in recent_windows:
        raw = w.raw_counters or {}
        obs_pkts = int(raw.get("total_packets", raw.get("packets", 0)))
        obs_bytes = int(raw.get("total_bytes_downlink", raw.get("bytes_dl", 0))) + int(raw.get("total_bytes_uplink", raw.get("bytes_ul", 0)))
        is_curr = (w.id == db_window.id)
        is_dev = obs_pkts < expected_min or obs_pkts > expected_max

        traffic_series.append({
            "window_id": w.id,
            "time": w.window_end.strftime("%H:%M:%S") if hasattr(w.window_end, "strftime") else str(w.window_end)[11:19],
            "observed_packets": obs_pkts,
            "observed_bytes_mb": round(obs_bytes / (1024 * 1024), 2),
            "expected_min": expected_min,
            "expected_max": expected_max,
            "expected_median": round(base_packets_med),
            "is_current": is_curr,
            "is_deviated": is_dev,
        })

    # 4. Evidence Panel details
    raw_counters = db_window.raw_counters or {}
    ratio_features = db_window.ratio_features or {}
    comp_vector = db_window.composition_vector or {}

    det_output = alert_row.detector_output if alert_row and alert_row.detector_output else (
        det_row.model_outputs if det_row and det_row.model_outputs else {}
    )
    if_data = det_output.get("isolation_forest", {})
    ae_data = det_output.get("autoencoder", {})
    cusum_data = det_output.get("cusum", {})
    fusion_data = det_output.get("fusion", {})

    # Proportional growth & divergence data from attribution
    pg_test = attr_data.get("proportional_growth_test", {})
    jsd_val = float(pg_test.get("js_divergence", 0.012))
    vol_mult = float(pg_test.get("scaling_factor_k", drift_row.volume_multiplier if drift_row else 1.0))
    is_pg_pass = bool(pg_test.get("is_proportional", jsd_val <= 0.035))

    # Threat indicators: evaluate ratio deviations
    threat_indicators = []
    for k, v in ratio_features.items():
        med = float(medians.get(k, 0.0))
        iqr = float(max(0.0001, iqrs.get(k, 1.0)))
        dev = round((float(v) - med) / iqr, 3)
        threat_indicators.append({
            "feature": k,
            "observed_value": round(float(v), 4),
            "baseline_median": round(med, 4),
            "iqr_deviation": dev,
            "status": "danger" if abs(dev) > 2.5 else ("warn" if abs(dev) > 1.5 else "ok"),
        })
    threat_indicators.sort(key=lambda x: abs(x["iqr_deviation"]), reverse=True)

    evidence = {
        "detector_scores": {
            "isolation_forest": {
                "score": round(float(if_data.get("raw_score_negated", 0.5)), 4),
                "percentile": round(float(if_data.get("benign_percentile", 0.5)), 4),
                "threshold": round(float(if_data.get("threshold_percentile", 0.98)), 3),
                "flagged": bool(if_data.get("is_flagged", False)),
            },
            "autoencoder": {
                "reconstruction_mse": round(float(ae_data.get("reconstruction_mse", 0.01)), 5),
                "percentile": round(float(ae_data.get("benign_percentile", 0.5)), 4),
                "threshold": round(float(ae_data.get("threshold_percentile", 0.98)), 3),
                "flagged": bool(ae_data.get("is_flagged", False)),
            },
            "fusion": {
                "fused_percentile": round(fused_p, 4),
                "threshold": 0.980,
                "flagged": is_anom,
            },
        },
        "cusum": {
            "score": round(float(cusum_data.get("score", 0.0)), 3),
            "allowance_k": round(float(cusum_data.get("allowance", 0.5)), 3),
            "threshold_h": round(float(cusum_data.get("alarm_threshold", 5.0)), 2),
            "is_alarm": bool(cusum_data.get("is_alarm", False)),
        },
        "js_divergence": {
            "value": round(jsd_val, 4),
            "threshold": 0.035,
            "is_pass": is_pg_pass,
            "interpretation": "Signaling composition preserved" if is_pg_pass else "Signaling composition structurally distorted",
        },
        "volume_multiplier": {
            "multiplier": round(vol_mult, 2),
            "expected_baseline": 1.0,
            "is_proportional": is_pg_pass,
        },
        "threat_indicators": threat_indicators[:6],
    }

    # 5. Vertical Decision Trace Timeline
    timeline_steps = []
    if trace_row and trace_row.steps:
        # Structured or array steps
        for idx, s in enumerate(trace_row.steps):
            if isinstance(s, dict):
                timeline_steps.append({
                    "step_number": idx + 1,
                    "title": s.get("step", f"Step {idx + 1}"),
                    "explanation": s.get("detail", str(s)),
                    "outcome": s.get("status", "pass").lower(),
                    "timestamp": s.get("timestamp", trace_row.created_at.strftime("%H:%M:%S")),
                })
            else:
                str_s = str(s)
                outcome = "fail" if ("reject" in str_s.lower() or "quarantine" in str_s.lower() or "fail" in str_s.lower() or "alert" in str_s.lower()) else "pass"
                timeline_steps.append({
                    "step_number": idx + 1,
                    "title": str_s.split(":")[0] if ":" in str_s else f"Evaluation Stage {idx + 1}",
                    "explanation": str_s,
                    "outcome": outcome,
                    "timestamp": trace_row.created_at.strftime("%H:%M:%S"),
                })
    else:
        # Synthesize real steps based on pipeline outcome
        t_str = db_window.window_end.strftime("%H:%M:%S")
        timeline_steps = [
            {
                "step_number": 1,
                "title": "Canonical Window Ingestion",
                "explanation": f"Normalized 60s telemetry window for slice {db_window.slice_id} across {raw_counters.get('total_packets', 0):,} packets.",
                "outcome": "pass",
                "timestamp": t_str,
            },
            {
                "step_number": 2,
                "title": "Dual-Model Anomaly Scoring",
                "explanation": f"Isolation Forest: {if_data.get('benign_percentile', 0.5):.1%} %ile | Autoencoder MSE: {ae_data.get('reconstruction_mse', 0.01):.4f}. Fused percentile: {fused_p:.1%}.",
                "outcome": "fail" if is_anom else "pass",
                "timestamp": t_str,
            },
            {
                "step_number": 3,
                "title": "ADWIN Drift Attribution & JSD Test",
                "explanation": f"Jensen-Shannon Divergence: {jsd_val:.4f} (threshold: 0.035). Volume scaling factor: {vol_mult:.2f}x. Verdict: {attr_verdict or 'stable'}.",
                "outcome": "pass" if is_pg_pass else "fail",
                "timestamp": t_str,
            },
            {
                "step_number": 4,
                "title": "Zero-Trust Governance Enforcement",
                "explanation": f"Action enforced: {final_decision.upper()}. Window isolated from baseline training data." if final_decision in ["Quarantine", "Alert", "Abstain"] else "Traffic classified as nominal.",
                "outcome": "fail" if final_decision in ["Quarantine", "Alert"] else "pass",
                "timestamp": t_str,
            },
        ]

    # 6. Plain-language "Why did the system decide this?" card
    why_explanation = {
        "verdict": final_decision,
        "summary": "",
        "key_reasons": [],
        "quarantine_reason": quarantine_row.reason if quarantine_row else None,
        "abstain_reason": abstain_reason,
    }

    if final_decision == "Quarantine":
        why_explanation["summary"] = (
            f"The system quarantined window {db_window.id[:8]} because the traffic shift failed proportional growth validation. "
            f"Reason: {quarantine_row.reason if quarantine_row else 'Potential stealth poisoning or unverified signaling deviation'}."
        )
        why_explanation["key_reasons"] = [
            f"Traffic volume grew by {vol_mult:.2f}x but signalling distribution diverged (JSD: {jsd_val:.4f} > 0.035 limit).",
            "Non-proportional signaling indicates potential resource exhaustion or stealthy baseline poisoning.",
            "Zero-trust rule strictly forbids using quarantined telemetry in future baseline retraining.",
        ]
    elif final_decision == "Abstain":
        why_explanation["summary"] = (
            f"The system abstained from automated classification. "
            f"Reason: {abstain_reason or 'Ambiguous sample volume or intermediate divergence'}."
        )
        why_explanation["key_reasons"] = [
            f"Abstention trigger: {abstain_reason or 'Drift detected without sufficient evidence of legitimate proportional growth'}.",
            "System prioritized zero-trust safety: abstained windows are quarantined and require operator review.",
        ]
    elif final_decision == "Alert":
        why_explanation["summary"] = (
            f"The system raised a security alert because the fused anomaly percentile ({fused_p:.1%}) "
            f"exceeded the calibrated safety threshold (98.0th percentile)."
        )
        top_threat = threat_indicators[0] if threat_indicators else None
        why_explanation["key_reasons"] = [
            f"Fused detection score: {fused_p:.1%} (calibrated nominal threshold: 98.0%).",
            f"Leading anomaly contributor: '{top_threat['feature']}' with {top_threat['iqr_deviation']:+.2f} IQR deviation." if top_threat else "Composite shift across multiple signaling metrics.",
            f"CUSUM cumulative deviation score: {cusum_data.get('score', 0):.2f} (alarm threshold: {cusum_data.get('alarm_threshold', 5.0):.1f}).",
        ]
    else:
        why_explanation["summary"] = "The system determined this window operates within calibrated baseline nominal bounds."
        why_explanation["key_reasons"] = [
            f"Fused anomaly percentile ({fused_p:.1%}) remains strictly below the 98.0% threshold.",
            f"Signaling ratio distribution matches active baseline {active_base.version if active_base else 'v1.0.0-anchor'}.",
        ]

    # 7. Governance link
    governance_link = None
    # Check if this slice has a pending shadow candidate
    cand = (
        db.query(CandidateBaseline)
        .filter(CandidateBaseline.slice_id == db_window.slice_id)
        .order_by(CandidateBaseline.created_at.desc())
        .first()
    )
    if cand:
        governance_link = {
            "candidate_id": cand.id,
            "candidate_version": cand.candidate_version,
            "status": cand.status,
            "href": "/governance",
        }

    # 8. Analyst feedback history
    audit_rows = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.event_type == "ANALYST_INVESTIGATION_FEEDBACK",
            AuditEvent.slice_id == db_window.slice_id,
        )
        .order_by(AuditEvent.timestamp.desc())
        .all()
    )
    feedback_history = []
    for ev in audit_rows:
        details = ev.details or {}
        if details.get("window_id") == db_window.id or details.get("target_id") == target_id:
            feedback_history.append(
                AnalystFeedbackItem(
                    id=ev.id,
                    analyst_id=ev.actor,
                    classification=details.get("classification", "NOTE"),
                    notes=details.get("notes", ""),
                    timestamp=ev.timestamp.isoformat(),
                )
            )

    return {
        "alert_header": alert_header,
        "traffic_series": traffic_series,
        "evidence": evidence,
        "timeline_steps": timeline_steps,
        "why_explanation": why_explanation,
        "governance_link": governance_link,
        "feedback_history": [f.model_dump() for f in feedback_history],
    }


@router.post("/{target_id}/feedback")
def submit_investigation_feedback(
    target_id: str,
    payload: AnalystFeedbackRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Store analyst actions (mark true positive, mark false positive, add note) in approval_logs and audit_events."""
    # Find slice_id and window_id
    win = db.query(CanonicalWindow).filter(CanonicalWindow.id == target_id).first()
    alert = db.query(AnomalyAlert).filter(AnomalyAlert.id == target_id).first()
    drift = db.query(DriftEvent).filter(DriftEvent.id == target_id).first()

    window_id = win.id if win else (alert.window_id if alert else (drift.window_id if drift else target_id))
    slice_id = win.slice_id if win else (alert.slice_id if alert else (drift.slice_id if drift else "unknown"))

    now = datetime.now(timezone.utc)

    # 1. Store in audit_events
    audit_ev = AuditEvent(
        event_type="ANALYST_INVESTIGATION_FEEDBACK",
        slice_id=slice_id,
        actor=payload.analyst_id,
        details={
            "target_id": target_id,
            "window_id": window_id,
            "classification": payload.classification,
            "notes": payload.notes,
        },
        timestamp=now,
    )
    db.add(audit_ev)

    # 2. Also store in approval_logs for persistent governance record
    appr_log = ApprovalLog(
        candidate_id=target_id,
        slice_id=slice_id,
        action=f"INVESTIGATION_{payload.classification}",
        analyst_id=payload.analyst_id,
        notes=payload.notes,
        created_at=now,
    )
    db.add(appr_log)

    db.commit()

    return {
        "status": "RECORDED",
        "feedback_id": audit_ev.id,
        "target_id": target_id,
        "window_id": window_id,
        "classification": payload.classification,
        "analyst_id": payload.analyst_id,
        "notes": payload.notes,
        "timestamp": now.isoformat(),
    }
