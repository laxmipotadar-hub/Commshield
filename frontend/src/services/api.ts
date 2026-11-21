/**
 * CommShield Typed API Client
 * Base URL sourced from VITE_API_URL with default http://localhost:8000
 */

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

export function getAnalystToken(): string {
  return localStorage.getItem('commshield_analyst_token') || 'commshield-analyst-secret-v1';
}

export function setAnalystToken(token: string): void {
  localStorage.setItem('commshield_analyst_token', token);
}

// Generic fetch helper
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getAnalystToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options.headers as Record<string, string>) || {}),
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

export interface DemoKeyEvent {
  window_index: number;
  event_type: string;
  caption: string;
}

export interface DemoWindowRange {
  start_index: number;
  end_index: number;
  total_windows: number;
}

export interface DemoPreset {
  id: string;
  preset_number: number;
  name: string;
  description: string;
  data_label: string;
  source?: string;
  source_badge?: string;
  scenario?: string;
  dataset_id: string;
  best_attack_type?: string | null;
  window_range: DemoWindowRange;
  key_events: DemoKeyEvent[];
  three_arm_summary?: {
    scenario: string;
    source?: string;
    data_label?: string;
    arms: Record<string, {
      name: string;
      recall?: number | null;
      fpr: number;
      contamination: number;
      adaptations: number;
      quarantined: number;
    }>;
  };
  decision_trace?: {
    status?: string;
    candidate_version?: string;
    overall_status?: string;
    checks: Array<{
      name: string;
      status: string;
      detail: string;
    }>;
    conclusion: string;
  };
}

export interface DemoScenariosResponse {
  scenarios: DemoPreset[];
  source_attribution: string;
  fixed_seed: number;
}

export interface ReplayStartRequest {
  dataset_id: string;
  data_source?: string;
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
  data_label?: string;
  arms: Record<string, {
    name: string;
    precision?: number;
    recall?: number | null;
    f1?: number;
    false_alarm_rate?: number;
    contamination?: number;
    adaptations?: number;
    quarantined?: number;
    recovery_time?: number;
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

export interface ArmMetricsSummary {
  recall_mean: number | null;
  recall_std: number | null;
  recall_min?: number | null;
  recall_max?: number | null;
  fpr_mean: number;
  fpr_std: number;
  fpr_min?: number | null;
  fpr_max?: number | null;
  contamination_mean: number;
  contamination_std: number;
  contamination_min?: number | null;
  contamination_max?: number | null;
  adaptations_mean: number;
  adaptations_min?: number | null;
  adaptations_max?: number | null;
  quarantined_mean: number;
  quarantined_min?: number | null;
  quarantined_max?: number | null;
  recovery_time_mean: number;
  recovery_time_min?: number | null;
  recovery_time_max?: number | null;
}

export interface ScenarioSummaryData {
  num_seeds: number;
  seeds: number[];
  arms: {
    arm_a_static: ArmMetricsSummary;
    arm_b_naive: ArmMetricsSummary;
    arm_c_commshield: ArmMetricsSummary;
  };
}

export interface ExperimentSummaryResponse {
  config_version: string;
  generated_at: string;
  scenarios: string[];
  seeds: number[];
  summaries: Record<string, ScenarioSummaryData>;
  runs?: Array<{
    scenario: string;
    seed: number;
    config_version: string;
    num_windows: number;
    timestamp: string;
    arms: Record<string, {
      recall: number | null;
      fpr: number;
      baseline_contamination_final: number;
      baseline_contamination_over_time: number[];
      adaptations_count: number;
      quarantined_count: number;
      recovery_time_windows: number;
    }>;
  }>;
}

export interface ExperimentStatusResponse {
  status: 'IDLE' | 'RUNNING' | 'COMPLETED' | 'FAILED' | string;
  scenarios: string[];
  seeds: number[];
  progress: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

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

  // Centrepiece Three-Arm Experiments
  getExperimentResults: (dataSource = 'synthetic') =>
    request<ExperimentSummaryResponse>(`/api/experiments/results?data_source=${encodeURIComponent(dataSource)}`),
  getScenarioExperimentResults: (scenario: string, dataSource = 'synthetic') =>
    request<{ scenario: string; config_version: string; generated_at: string; summary: ScenarioSummaryData }>(
      `/api/experiments/results/${encodeURIComponent(scenario)}?data_source=${encodeURIComponent(dataSource)}`
    ),
  getExperimentStatus: () => request<ExperimentStatusResponse>('/api/experiments/status'),
  runExperiment: (payload: { scenarios?: string[]; seeds?: number[]; num_windows?: number }) =>
    request<{ status: string; message: string }>('/api/experiments/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  // Demo Mode
  getDemoScenarios: () => request<DemoScenariosResponse>('/api/demo/scenarios'),

  // Digital Twin
  getDigitalTwinData: (scenario = 'approved_onboarding', source?: string, timeStep = 15) => {
    const params = new URLSearchParams();
    if (scenario) params.set('scenario', scenario);
    if (source) params.set('source', source);
    if (timeStep !== undefined) params.set('time_step', timeStep.toString());
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request<DigitalTwinResponse>(`/api/digital-twin${qs}`);
  },

  // Real 5G-NIDD Endpoints
  getRealManifest: () => request<RealManifestResponse>('/api/real/manifest'),

  getRealOverview: () => request<RealOverviewResponse>('/api/real/overview'),

  getRealMonitoring: (params?: { slice_id?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.slice_id && params.slice_id !== 'ALL') qs.set('slice_id', params.slice_id);
    if (params?.limit !== undefined) qs.set('limit', String(params.limit));
    const str = qs.toString();
    return request<RealMonitoringResponse>(`/api/real/monitoring${str ? `?${str}` : ''}`);
  },

  getRealDetection: (params?: { slice_id?: string; threshold?: number }) => {
    const qs = new URLSearchParams();
    if (params?.slice_id && params.slice_id !== 'ALL') qs.set('slice_id', params.slice_id);
    if (params?.threshold !== undefined) qs.set('threshold', String(params.threshold));
    const str = qs.toString();
    return request<RealDetectionResponse>(`/api/real/detection${str ? `?${str}` : ''}`);
  },

  getRealWindows: (params?: { slice_id?: string; attack_label?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.slice_id && params.slice_id !== 'ALL') qs.set('slice_id', params.slice_id);
    if (params?.attack_label && params.attack_label !== 'ALL') qs.set('attack_label', params.attack_label);
    if (params?.limit !== undefined) qs.set('limit', String(params.limit));
    if (params?.offset !== undefined) qs.set('offset', String(params.offset));
    const str = qs.toString();
    return request<{ items: RealTelemetryWindow[]; total: number; limit: number; offset: number; source: string }>(
      `/api/real/windows${str ? `?${str}` : ''}`
    );
  },
};

export interface RealManifestResponse {
  dataset: string;
  version: string;
  total_windows: number;
  attack_distribution: Record<string, number>;
  slices: string[];
  window_duration_sec: number;
  time_span: {
    start?: string;
    end?: string;
  };
  features: string[];
}

export interface RealTelemetryWindow {
  window_id: string;
  timestamp: string;
  slice_id: string;
  uplink_mb: number;
  downlink_mb: number;
  total_packets: number;
  udp_ratio: number;
  tcp_ratio: number;
  icmp_ratio: number;
  unique_src_ips: number;
  unique_dst_ports: number;
  syn_flag_ratio: number;
  rst_flag_ratio: number;
  avg_inter_arrival_ms: number;
  inter_arrival_cv: number;
  attack_label: string;
}

export interface RealOverviewResponse {
  total_windows: number;
  total_traffic_mb: number;
  total_traffic_gb: number;
  total_packets: number;
  unique_slices: string[];
  active_slices_count: number;
  attack_windows_count: number;
  normal_windows_count: number;
  attack_distribution: Record<string, number>;
  traffic_timeline: Array<{
    timestamp: string;
    slice_id: string;
    uplink_mb: number;
    downlink_mb: number;
    total_mb: number;
    total_packets: number;
    attack_label: string;
  }>;
  source: string;
  dataset: string;
  version: string;
}

export interface RealMonitoringResponse {
  time_series: Array<{
    timestamp: string;
    slice_id: string;
    uplink_mb: number;
    downlink_mb: number;
    total_mb: number;
    total_packets: number;
    udp_ratio: number;
    tcp_ratio: number;
    icmp_ratio: number;
    syn_flag_ratio: number;
    rst_flag_ratio: number;
    avg_inter_arrival_ms: number;
    inter_arrival_cv: number;
    unique_src_ips: number;
    unique_dst_ports: number;
    attack_label: string;
  }>;
  slice_breakdown: Record<string, {
    slice_id: string;
    traffic_mb: number;
    total_packets: number;
    window_count: number;
    ratio: number;
  }>;
  protocol_summary: {
    tcp_ratio: number;
    udp_ratio: number;
    icmp_ratio: number;
  };
  total_traffic_mb: number;
  total_packets: number;
  source: string;
}

export interface RealDetectionResponse {
  scored_windows: Array<{
    window_id: string;
    timestamp: string;
    slice_id: string;
    attack_label: string;
    is_attack: boolean;
    anomaly_score: number;
    if_score: number;
    ae_error: number;
    verdict: string;
    uplink_mb: number;
    downlink_mb: number;
    total_packets: number;
    features: Record<string, number>;
  }>;
  threshold: number;
  detection_stats: {
    total_evaluated: number;
    true_positives: number;
    false_positives: number;
    true_negatives: number;
    false_negatives: number;
    precision: number;
    recall: number;
    f1_score: number;
  };
  source: string;
}

export interface DigitalTwinNode {
  id: string;
  label: string;
  type: string;
  x: number;
  y: number;
  role: string;
}

export interface DigitalTwinLink {
  source: string;
  target: string;
  label: string;
  type: string;
}

export interface DigitalTwinSliceZone {
  x: number;
  y: number;
  width: number;
  height: number;
  label: string;
}

export interface DigitalTwinSlice {
  slice_id: string;
  name: string;
  device_class: string;
  color: string;
  packet_rate_pps: number;
  zone: DigitalTwinSliceZone;
}

export interface DigitalTwinDevice {
  id: string;
  device_id_hash: string;
  device_class: 'sensor' | 'camera' | 'AGV' | string;
  slice_id: string;
  x: number;
  y: number;
  rate_pps: number;
  verdict: 'benign' | 'attack' | 'uncertain' | 'quarantined';
  action: 'none' | 'quarantine' | 'alert';
  status_label: string;
  is_onboarded: boolean;
  visible: boolean;
  is_provisioned: boolean;
}

export interface DigitalTwinBatchEvent {
  batch_id: string;
  start?: number;
  end?: number;
  count: number;
  slice: string;
}

export interface DigitalTwinProvisioningCard {
  total_catalog_sims: number;
  total_batches: number;
  batches: DigitalTwinBatchEvent[];
  provisioned_share: number;
  is_provisioned: boolean;
  matched_event: DigitalTwinBatchEvent | null;
  fitting_volume: boolean;
  verdict: string;
  action: string;
  action_description: string;
}

export interface ContaminationMeterData {
  name: string;
  contamination_mean: number;
  contamination_ci_95: [number, number];
  fpr_mean: number;
  onboardings_adapted: number;
}

export interface DigitalTwinDecisionStep {
  step: number;
  name: string;
  result: string;
  status: string;
}

export interface DigitalTwinResponse {
  generated_at: string;
  source: 'simulated_twin' | 'lab' | 'real_recorded' | string;
  source_badge: 'Simulated twin' | 'Live lab' | 'Real recorded' | string;
  lab_validated: boolean;
  scenario: string;
  available_scenarios: string[];
  time_step: number;
  topology: {
    nodes: DigitalTwinNode[];
    links: DigitalTwinLink[];
  };
  slices: DigitalTwinSlice[];
  devices: DigitalTwinDevice[];
  provisioning_card: DigitalTwinProvisioningCard;
  contamination_meters: {
    naive: ContaminationMeterData;
    commshield_base: ContaminationMeterData;
    commshield_twin: ContaminationMeterData;
  };
  decision_trace: DigitalTwinDecisionStep[];
  saved_metrics_reference: {
    summary_file: string;
    window_counts_file: string;
    provisioning_file: string;
    change_events_file: string;
    aggregate_windows: number;
    device_windows: number;
    slice_windows: number;
    aggregate_device_counts: Record<string, number>;
  };
}

export interface DataDatasetItem {
  name: string;
  display_name: string;
  source: string;
  seed: number;
  config_version: string;
  record_count: number;
  size_bytes: number;
  slices_assigned: boolean;
  description: string;
  metadata: Record<string, any>;
}

export interface DataPreviewResponse {
  name: string;
  source: string;
  seed: number;
  config_version: string;
  limit: number;
  total_records: number;
  metadata: Record<string, any>;
  windows: any[];
}

export async function fetchDataDatasets(): Promise<{ datasets: DataDatasetItem[]; total: number }> {
  try {
    return await request<{ datasets: DataDatasetItem[]; total: number }>('/api/data/datasets');
  } catch (err) {
    return {
      datasets: [
        {
          name: 'stable_benign',
          display_name: 'Stable Benign Core Telemetry (Offline Fallback)',
          source: 'simulated_twin',
          seed: 42,
          config_version: 'v1.0.0',
          record_count: 60,
          size_bytes: 84188,
          slices_assigned: false,
          description: 'Clean operational 5G telemetry across slices with stationary diurnal variations.',
          metadata: { anonymized: true, no_raw_identifiers: true, source: 'simulated_twin', seed: 42 },
        },
        {
          name: 'semi_synthetic_real_ramp',
          display_name: 'Real-Backbone Hidden Ramp (Offline Fallback)',
          source: 'semi_synthetic',
          seed: 42,
          config_version: 'v1.0.0-real-ramp',
          record_count: 40,
          size_bytes: 58000,
          slices_assigned: true,
          description: 'Semi-synthetic stream combining real 5G-NIDD test traffic with real SYNFlood attack injection.',
          metadata: { anonymized: true, no_raw_identifiers: true, source: 'semi_synthetic', seed: 42 },
        },
        {
          name: 'fiveg_nidd',
          display_name: 'Real 5G-NIDD Testbed Telemetry (Offline Fallback)',
          source: 'real_recorded',
          seed: 42,
          config_version: 'v1.0.0',
          record_count: 80,
          size_bytes: 110000,
          slices_assigned: true,
          description: 'Real recorded 5G testbed traffic with topology-assigned slices (BS1: eMBB, BS2: URLLC).',
          metadata: { anonymized: true, no_raw_identifiers: true, source: 'real_recorded', seed: 42 },
        },
      ],
      total: 3,
    };
  }
}

export async function fetchDataPreview(name: string, limit: number = 20): Promise<DataPreviewResponse> {
  return request<DataPreviewResponse>(`/api/data/${name}/preview?limit=${limit}`);
}

export function getDownloadUrl(name: string, seed?: number): string {
  const seedParam = seed !== undefined ? `?seed=${seed}` : '';
  return `${API_BASE_URL}/api/data/${name}/download${seedParam}`;
}

export async function generateDataStream(stream: string, seed: number): Promise<any> {
  return request<any>('/api/data/generate', {
    method: 'POST',
    body: JSON.stringify({ stream, seed }),
  });
}

