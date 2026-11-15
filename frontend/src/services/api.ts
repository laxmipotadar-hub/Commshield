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
  is_placeholder?: boolean;
}

export interface ReplayStartRequest {
  dataset_id: string;
  speed_multiplier?: number;
  active_arms?: string[];
  window_scale_sec?: number;
}

export interface ReplayStatusResponse {
  status: 'RUNNING' | 'PAUSED' | 'STOPPED' | string;
  dataset_id: string;
  current_window_index: number;
  total_windows: number;
  speed_multiplier: number;
  current_timestamp: string;
  is_placeholder?: boolean;
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
  is_placeholder?: boolean;
}

export interface PaginatedWindowsResponse {
  items: CanonicalTrafficWindow[];
  total: number;
  limit: number;
  offset: number;
  is_placeholder?: boolean;
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
  is_placeholder?: boolean;
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
  is_placeholder?: boolean;
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
  is_placeholder?: boolean;
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
  is_placeholder?: boolean;
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
  is_placeholder?: boolean;
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
    request<ReplayStatusResponse>('/api/v1/replay/start', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  pauseReplay: () =>
    request<ReplayStatusResponse>('/api/v1/replay/pause', {
      method: 'POST',
    }),

  resumeReplay: () =>
    request<ReplayStatusResponse>('/api/v1/replay/resume', {
      method: 'POST',
    }),

  stopReplay: () =>
    request<ReplayStatusResponse>('/api/v1/replay/stop', {
      method: 'POST',
    }),

  getReplayStatus: () => request<ReplayStatusResponse>('/api/v1/replay/status'),

  getReplayStreamUrl: (speed = 1.0) => `${API_BASE_URL}/api/v1/replay/stream?speed=${speed}`,

  // Windows & Explainability
  getWindows: (params?: { slice_id?: string; limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (params?.slice_id) query.set('slice_id', params.slice_id);
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    if (params?.offset !== undefined) query.set('offset', String(params.offset));
    const qs = query.toString();
    return request<PaginatedWindowsResponse>(`/api/v1/windows${qs ? `?${qs}` : ''}`);
  },

  getExplainability: (windowId: string) =>
    request<ExplainabilityResponse>(`/api/v1/windows/${windowId}/explain`),

  // Governance & Baselines
  getBaselines: (sliceId?: string) => {
    const qs = sliceId ? `?slice_id=${encodeURIComponent(sliceId)}` : '';
    return request<BaselineSummaryResponse[]>(`/api/v1/baselines${qs}`);
  },

  getCandidates: (status?: string) => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : '';
    return request<CandidateResponse[]>(`/api/v1/candidates${qs}`);
  },

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
};
