/**
 * CommShield Typed API Client
 * Base URL sourced from VITE_API_URL with default http://localhost:8000
 */

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

// Generic fetch helper
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API Error [${response.status}] ${response.statusText}: ${errorBody}`);
  }
  return response.json();
}

// -------------------------------------------------------------
// Type Definitions matching CONTRACTS.md
// -------------------------------------------------------------

export interface HealthResponse {
  status: string;
}

export interface DatasetInfo {
  dataset_id: string;
  name: string;
  description?: string;
  total_windows?: number;
  duration_sec?: number;
  attack_types?: string[];
}

export interface DatasetListResponse {
  datasets: DatasetInfo[];
  total: number;
}

export interface ReplayStartRequest {
  dataset_id: string;
  speed_multiplier?: number;
  active_arms?: string[];
  window_scale_sec?: number;
}

export interface ReplayStatusResponse {
  status: 'RUNNING' | 'PAUSED' | 'STOPPED' | 'COMPLETED' | string;
  dataset_id: string;
  current_window_index: number;
  total_windows: number;
  speed_multiplier: number;
  current_timestamp: string;
}

export interface CanonicalTrafficWindow {
  window_id: string;
  slice_id: string;
  nf_id: string;
  window_start: string;
  window_end: string;
  duration_sec: number;
  raw_counters: Record<string, number>;
  ratio_features: Record<string, number>;
  composition_vector: Record<string, number>;
}

export interface PaginatedWindowsResponse {
  items: CanonicalTrafficWindow[];
  total: number;
  limit: number;
  offset: number;
}

export interface IsolationForestScore {
  raw_score_negated: number;
  benign_percentile: number;
  threshold_percentile: number;
  is_flagged: boolean;
}

export interface ProportionalGrowthTest {
  scaling_factor_k: number;
  jsd_divergence: number;
  jsd_null_threshold_99th: number;
  passed: boolean;
}

export interface AttributionOutput {
  window_id: string;
  slice_id: string;
  drift_detected: boolean;
  verdict: 'likely_benign' | 'likely_attack' | 'uncertain' | string;
  abstain_reason?: string | null;
  confidence_type: string;
  proportional_growth_test: ProportionalGrowthTest;
  supporting_signals: Record<string, unknown>;
  action?: string | null;
  action_recommendation: string;
  decision_trace_id?: string | null;
}

export interface DriftEventItem {
  id: string;
  window_id: string;
  slice_id: string;
  event_time: string;
  volume_multiplier: number;
  drift_detected: boolean;
  verdict: 'likely_benign' | 'likely_attack' | 'uncertain' | string;
  abstain_reason?: string | null;
  action: string;
  decision_trace_id?: string | null;
  attribution?: Record<string, unknown> | null;
}

export interface DecisionTraceResponse {
  id: string;
  window_id: string;
  slice_id: string;
  alert_id?: string | null;
  drift_event_id?: string | null;
  verdict: string;
  action: string;
  steps: Array<{
    step_name: string;
    description: string;
    timestamp: string;
    details: Record<string, unknown>;
  }>;
  created_at: string;
}

export interface QuarantineWindowItem {
  id: string;
  window_id: string;
  slice_id: string;
  reason: string;
  scenario?: string | null;
  quarantined_at: string;
}

export interface AutoencoderScore {
  reconstruction_mse?: number | null;
  benign_percentile?: number | null;
  threshold_percentile?: number | null;
  is_flagged?: boolean | null;
}

export interface FusionScore {
  primary_rule: string;
  fused_percentile: number;
  secondary_mean_percentile: number;
  agreement_state: string;
  is_anomalous: boolean;
}

export interface CusumScore {
  accumulated_statistic?: number | null;
  alarm_threshold?: number | null;
  is_alarm?: boolean | null;
  status?: 'idle' | 'accumulating' | 'triggered' | string;
}

export interface DetectorOutput {
  window_id: string;
  slice_id: string;
  nf_id: string;
  evaluated_at: string;
  baseline_version: string;
  isolation_forest: IsolationForestScore;
  autoencoder?: AutoencoderScore | null;
  fusion: FusionScore;
  cusum?: CusumScore | null;
}

export interface AlertItem {
  id: string;
  window_id: string;
  slice_id: string;
  nf_id: string;
  detector_output: DetectorOutput;
  is_anomalous: boolean;
  fused_score?: number | null;
  created_at: string;
  is_candidate?: boolean;
  candidate_status?: string;
}

export interface DashboardOverviewResponse {
  total_traffic_bytes: number;
  active_slices_count: number;
  anomaly_alerts_count: number;
  drift_status: string;
  quarantined_windows_count: number;
  active_baseline_version: string;
  pending_updates_count: number;
  recent_alerts: Array<Record<string, unknown>>;
  traffic_over_time: Array<{
    timestamp: string;
    total_bytes: number;
    packets: number;
    slice_id?: string;
  }>;
}

export interface ExplainabilityResponse {
  window_id: string;
  slice_id: string;
  nf_id: string;
  is_anomalous: boolean;
  fused_percentile: number;
  shap_values: Record<string, number>;
  hypothesis: string;
  attribution_summary: {
    verdict: string;
    abstain_reason: string | null;
  };
}

export interface BaselineSummaryResponse {
  id: string;
  slice_id: string;
  nf_id: string;
  version: string;
  is_anchor: boolean;
  is_active: boolean;
  training_window_start: string;
  training_window_end: string;
  model_artifact_path: string;
  scaler_params: Record<string, unknown>;
  threshold_params: Record<string, unknown>;
  feature_schema: Record<string, unknown>;
  created_at: string;
  is_candidate?: boolean;
  candidate_status?: string;
}

export interface CandidateResponse {
  id: string;
  slice_id: string;
  candidate_version: string;
  active_baseline_id: string;
  anchor_baseline_id: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'ROLLED_BACK' | string;
  gate_metrics: Record<string, unknown>;
  decision_trace: string[];
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  created_at: string;
  is_candidate?: boolean;
  candidate_status?: string;
}

export interface ApprovalActionRequest {
  analyst_id: string;
  notes: string;
}

export interface RollbackRequest {
  slice_id: string;
  nf_id: string;
  target_baseline_version: string;
  reason: string;
  analyst_id: string;
}

export interface RollbackResponse {
  status: string;
  slice_id: string;
  active_version: string;
  restored_artifacts: string[];
  timestamp: string;
}

export interface ThreeArmComparisonResponse {
  dataset_id: string;
  arms: Record<string, {
    name: string;
    precision?: number;
    recall?: number;
    f1?: number;
    false_alarm_rate?: number;
    poisoning_susceptibility?: number;
    [key: string]: unknown;
  }>;
}

export interface InvestigationDetailsResponse {
  alert_header: {
    id: string;
    window_id: string;
    slice_id: string;
    nf_id: string;
    timestamp: string;
    severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
    final_decision: 'Alert' | 'Quarantine' | 'Abstain' | 'Normal';
    baseline_version: string;
  };
  traffic_series: Array<{
    window_id: string;
    time: string;
    observed_packets: number;
    observed_bytes_mb: number;
    expected_min: number;
    expected_max: number;
    expected_median: number;
    is_current: boolean;
    is_deviated: boolean;
  }>;
  evidence: {
    detector_scores: {
      isolation_forest: {
        score: number;
        percentile: number;
        threshold: number;
        flagged: boolean;
      };
      autoencoder: {
        reconstruction_mse: number;
        percentile: number;
        threshold: number;
        flagged: boolean;
      };
      fusion: {
        fused_percentile: number;
        threshold: number;
        flagged: boolean;
      };
    };
    cusum: {
      score: number;
      allowance_k: number;
      threshold_h: number;
      is_alarm: boolean;
    };
    js_divergence: {
      value: number;
      threshold: number;
      is_pass: boolean;
      interpretation: string;
    };
    volume_multiplier: {
      multiplier: number;
      expected_baseline: number;
      is_proportional: boolean;
    };
    threat_indicators: Array<{
      feature: string;
      observed_value: number;
      baseline_median: number;
      iqr_deviation: number;
      status: 'danger' | 'warn' | 'ok';
    }>;
  };
  timeline_steps: Array<{
    step_number: number;
    title: string;
    explanation: string;
    outcome: 'pass' | 'warn' | 'fail';
    timestamp: string;
  }>;
  why_explanation: {
    verdict: string;
    summary: string;
    key_reasons: string[];
    quarantine_reason: string | null;
    abstain_reason: string | null;
  };
  governance_link: {
    candidate_id: string;
    candidate_version: string;
    status: string;
    href: string;
  } | null;
  feedback_history: Array<{
    id: string;
    analyst_id: string;
    classification: string;
    notes: string;
    timestamp: string;
  }>;
}

export interface AnalystFeedbackPayload {
  analyst_id: string;
  classification: 'TRUE_POSITIVE' | 'FALSE_POSITIVE' | 'NOTE';
  notes: string;
}

// -------------------------------------------------------------
// API Client Methods
// -------------------------------------------------------------

export const api = {
  // Health
  getHealth: () => request<HealthResponse>('/api/health'),

  // Datasets
  getDatasets: () => request<DatasetListResponse>('/api/v1/datasets'),

  // Replay
  startReplay: (payload: ReplayStartRequest) =>
    request<ReplayStatusResponse>('/api/replay/start', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  pauseReplay: () =>
    request<ReplayStatusResponse>('/api/replay/pause', {
      method: 'POST',
    }),

  resumeReplay: () =>
    request<ReplayStatusResponse>('/api/replay/resume', {
      method: 'POST',
    }),

  stopReplay: () =>
    request<ReplayStatusResponse>('/api/replay/stop', {
      method: 'POST',
    }),

  getReplayStatus: () => request<ReplayStatusResponse>('/api/replay/status'),

  getReplayStreamUrl: (speed = 1.0) => `${API_BASE_URL}/api/v1/replay/stream?speed=${speed}`,

  // Windows & Explainability
  getWindows: (params?: { slice_id?: string; limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.slice_id) query.set('slice_id', params.slice_id);
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    const qs = query.toString();
    return request<PaginatedWindowsResponse>(`/api/traffic/windows${qs ? `?${qs}` : ''}`);
  },

  getExplainability: (windowId: string) =>
    request<ExplainabilityResponse>(`/api/v1/windows/${windowId}/explain`),

  // Detection & Alerts
  analyzeWindow: (payload: {
    window_id?: string;
    window?: unknown;
    slice_id?: string;
    ratio_features?: Record<string, number>;
  }) =>
    request<DetectorOutput>('/api/detection/analyze', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getAlerts: (sliceId?: string, limit = 50) => {
    const qs = sliceId ? `?slice_id=${encodeURIComponent(sliceId)}&limit=${limit}` : `?limit=${limit}`;
    return request<AlertItem[]>(`/api/alerts${qs}`);
  },

  getDashboardOverview: () => request<DashboardOverviewResponse>('/api/dashboard/overview'),

  // Governance & Baselines
  getBaselines: (sliceId?: string) => {
    const qs = sliceId ? `?slice_id=${encodeURIComponent(sliceId)}` : '';
    return request<BaselineSummaryResponse[]>(`/api/baselines${qs}`);
  },

  getCandidates: (status?: string) => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : '';
    return request<CandidateResponse[]>(`/api/v1/candidates${qs}`);
  },

  evaluateCandidate: (payload: { candidate_id?: string; slice_id?: string; volume_multiplier?: number }) =>
    request<{
      candidate_id: string;
      slice_id: string;
      overall_passed: boolean;
      all_mandatory_passed: boolean;
      gate_metrics: Record<string, unknown>;
      check_results: Array<{
        name: string;
        passed: boolean;
        mandatory: boolean;
        metrics: Record<string, unknown>;
        explanation: string;
      }>;
    }>('/api/governance/evaluate', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  approveCandidate: (id: string, payload: ApprovalActionRequest) =>
    request<CandidateResponse>(`/api/v1/candidates/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  rejectCandidate: (id: string, payload: ApprovalActionRequest) =>
    request<CandidateResponse>(`/api/v1/candidates/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  rollbackBaseline: (payload: RollbackRequest) =>
    request<RollbackResponse>('/api/v1/baselines/rollback', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getThreeArmComparison: (datasetId = '5g_nidd_portscan_growth') =>
    request<ThreeArmComparisonResponse>(
      `/api/v1/experiments/three-arm?dataset_id=${encodeURIComponent(datasetId)}`
    ),

  // Attribution & Drift
  getDriftEvents: (sliceId?: string, limit = 50) => {
    const qs = sliceId ? `?slice_id=${encodeURIComponent(sliceId)}&limit=${limit}` : `?limit=${limit}`;
    return request<DriftEventItem[]>(`/api/drift/events${qs}`);
  },

  getDecisionTrace: (traceId: string) =>
    request<DecisionTraceResponse>(`/api/decision-traces/${encodeURIComponent(traceId)}`),

  getQuarantineWindows: (sliceId?: string, limit = 100) => {
    const qs = sliceId ? `?slice_id=${encodeURIComponent(sliceId)}&limit=${limit}` : `?limit=${limit}`;
    return request<QuarantineWindowItem[]>(`/api/quarantine/windows${qs}`);
  },

  analyzeAttribution: (payload: {
    window_id?: string;
    window?: unknown;
    scenario?: string;
    force_drift?: boolean;
  }) =>
    request<AttributionOutput>('/api/attribution/analyze', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Investigation & Analyst Feedback
  getInvestigationDetails: (targetId: string) =>
    request<InvestigationDetailsResponse>(`/api/investigation/${encodeURIComponent(targetId)}`),

  submitInvestigationFeedback: (targetId: string, payload: AnalystFeedbackPayload) =>
    request<{ status: string; feedback_id: string }>(
      `/api/investigation/${encodeURIComponent(targetId)}/feedback`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    ),
};
