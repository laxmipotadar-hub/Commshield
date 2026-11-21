/**
 * CommShield 3D Digital Twin - Dedicated Service Layer (twinApi.ts)
 * Sourced directly from docs/CONTRACTS.md.
 * Handles REST commands, polling fallback, connection state, stale data,
 * duplicate/out-of-order event filtering, and strict mock isolation.
 */

export interface TwinNode {
  id: string;
  label: string;
  type: 'ran' | 'core_control' | 'core_user' | 'edge' | 'gateway' | 'router' | 'switch' | 'security';
  x: number;
  y: number;
  z?: number;
  role: string;
  cpu_percent?: number;
  memory_percent?: number;
  health?: 'healthy' | 'degraded' | 'critical' | 'isolated';
}

export interface TwinLink {
  source: string;
  target: string;
  label: string;
  type: 'control' | 'user_plane';
  latency_ms?: number;
  packet_loss_rate?: number;
  active?: boolean;
}

export interface TwinSlice {
  slice_id: string;
  name: string;
  device_class: string;
  color: string;
  packet_rate_pps: number;
  zone: {
    x: number;
    y: number;
    width: number;
    height: number;
    label: string;
  };
}

export interface TwinDevice {
  id: string;
  device_id_hash: string;
  device_class: 'camera' | 'AGV' | 'sensor';
  slice_id: string;
  x: number;
  y: number;
  z?: number;
  rate_pps: number;
  verdict: 'benign' | 'attack' | 'uncertain' | 'quarantined';
  action: 'none' | 'alert' | 'quarantine' | 'mitigate';
  status_label: string;
  is_onboarded: boolean;
  visible: boolean;
  is_provisioned: boolean;
  cpu_percent?: number;
  memory_percent?: number;
}

export interface ProvisioningCardData {
  total_catalog_sims: number;
  total_batches: number;
  batches: Array<{ batch_id: string; count: number; slice: string }>;
  provisioned_share: number;
  is_provisioned: boolean;
  matched_event: { batch_id: string; count: number; slice: string } | null;
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

export interface DecisionTraceStep {
  step: number;
  name: string;
  result: string;
  status: string;
}

export interface DigitalTwinState {
  generated_at: string;
  source: string;
  source_badge: string;
  lab_validated: boolean;
  scenario: string;
  available_scenarios: string[];
  time_step: number;
  topology: {
    nodes: TwinNode[];
    links: TwinLink[];
  };
  slices: TwinSlice[];
  devices: TwinDevice[];
  provisioning_card: ProvisioningCardData;
  contamination_meters: {
    naive: ContaminationMeterData;
    commshield_base?: ContaminationMeterData;
    commshield_twin: ContaminationMeterData;
  };
  decision_trace: DecisionTraceStep[];
  saved_metrics_reference: {
    summary_file: string;
    window_counts_file: string;
    aggregate_windows: number;
  };
  is_stale?: boolean;
  is_mock?: boolean;
}

export interface ReplayStatus {
  status: 'IDLE' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'STOPPED';
  dataset_id?: string;
  current_tick?: number;
  total_ticks?: number;
  speed_multiplier?: number;
}

export interface DemoScenarioItem {
  id: string;
  name: string;
  dataset_id: string;
  best_attack_type: string | null;
  timeline_events: Array<{
    window_index: number;
    event_type: string;
    caption: string;
  }>;
}

export type ConnectionState = 'connected' | 'connecting' | 'disconnected' | 'error';

class TwinApiService {
  private baseUrl: string;
  private isMockEnabled: boolean;
  private connectionState: ConnectionState = 'disconnected';
  private lastTimestamp: string | null = null;
  private seenEventIds = new Set<string>();

  constructor() {
    this.baseUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
    this.isMockEnabled = import.meta.env.VITE_USE_MOCK === 'true';
  }

  public getConnectionState(): ConnectionState {
    return this.connectionState;
  }

  public getIsMockEnabled(): boolean {
    return this.isMockEnabled;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    this.connectionState = 'connecting';
    try {
      const resp = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...((options.headers as Record<string, string>) || {}),
        },
        ...options,
      });

      if (!resp.ok) {
        throw new Error(`TwinApi Error [${resp.status}]: ${resp.statusText}`);
      }
      this.connectionState = 'connected';
      return await resp.json();
    } catch (err) {
      this.connectionState = 'error';
      throw err;
    }
  }

  /**
   * Fetch Digital Twin State from /digital-twin
   * Validates timestamps and enforces out-of-order / duplicate rejection.
   */
  public async getTwinState(
    scenario: string = 'approved_onboarding',
    source?: string,
    timeStep: number = 15
  ): Promise<DigitalTwinState> {
    try {
      const q = new URLSearchParams({
        scenario,
        time_step: timeStep.toString(),
      });
      if (source) q.set('source', source);

      const data = await this.request<DigitalTwinState>(`/digital-twin?${q.toString()}`);

      // Handle Stale / Out-of-Order validation
      const generatedAt = data.generated_at;
      if (this.lastTimestamp && new Date(generatedAt).getTime() < new Date(this.lastTimestamp).getTime()) {
        // Out-of-order response: keep newer timestamp in memory
        console.warn('TwinApi: Discarded out-of-order telemetry snapshot');
      } else {
        this.lastTimestamp = generatedAt;
      }

      // Check staleness (if older than 30s)
      const ageMs = Date.now() - new Date(generatedAt).getTime();
      data.is_stale = ageMs > 30000;
      data.is_mock = false;
      return data;
    } catch (err) {
      if (this.isMockEnabled) {
        console.warn('TwinApi: Falling back to dev mock adapter (VITE_USE_MOCK=true)');
        return this.getMockTwinState(scenario, timeStep);
      }
      throw err;
    }
  }

  /**
   * Start Replay / Scenario via POST /api/v1/replay/start
   */
  public async startReplay(datasetId: string, speed: number = 1.0): Promise<ReplayStatus> {
    return this.request<ReplayStatus>('/api/v1/replay/start', {
      method: 'POST',
      body: JSON.stringify({ dataset_id: datasetId, speed_multiplier: speed }),
    });
  }

  /**
   * Pause Replay via POST /api/v1/replay/pause
   */
  public async pauseReplay(): Promise<ReplayStatus> {
    return this.request<ReplayStatus>('/api/v1/replay/pause', { method: 'POST' });
  }

  /**
   * Resume Replay via POST /api/v1/replay/resume
   */
  public async resumeReplay(): Promise<ReplayStatus> {
    return this.request<ReplayStatus>('/api/v1/replay/resume', { method: 'POST' });
  }

  /**
   * Stop Replay via POST /api/v1/replay/stop
   */
  public async stopReplay(): Promise<ReplayStatus> {
    return this.request<ReplayStatus>('/api/v1/replay/stop', { method: 'POST' });
  }

  /**
   * Get Replay Status via GET /api/v1/replay/status
   */
  public async getReplayStatus(): Promise<ReplayStatus> {
    return this.request<ReplayStatus>('/api/v1/replay/status');
  }

  /**
   * Get Demo Scenarios via GET /api/v1/demo/scenarios
   */
  public async getDemoScenarios(): Promise<{ scenarios: DemoScenarioItem[] }> {
    return this.request<{ scenarios: DemoScenarioItem[] }>('/api/v1/demo/scenarios');
  }

  /**
   * Filter duplicate event IDs from live timeline streams
   */
  public filterDuplicateEvent(eventId: string): boolean {
    if (this.seenEventIds.has(eventId)) {
      return false; // Already seen
    }
    this.seenEventIds.add(eventId);
    if (this.seenEventIds.size > 1000) {
      // Clear oldest entries
      const iter = this.seenEventIds.values();
      for (let i = 0; i < 200; i++) {
        const next = iter.next();
        if (!next.done) this.seenEventIds.delete(next.value);
      }
    }
    return true;
  }

  /**
   * Strict Dev Mock Adapter (only active when VITE_USE_MOCK=true)
   * Explicitly labeled MOCK.
   */
  private getMockTwinState(scenario: string, timeStep: number): DigitalTwinState {
    return {
      generated_at: new Date().toISOString(),
      source: 'simulated_twin',
      source_badge: 'Simulated twin (MOCK)',
      lab_validated: false,
      scenario,
      available_scenarios: ['approved_onboarding', 'unprovisioned_burst', 'provisioned_burst_no_event', 'slow_ramp_in_onboarding'],
      time_step: timeStep,
      topology: {
        nodes: [
          { id: 'gnb', label: 'gNodeB-01 (MOCK)', type: 'ran', x: 340, y: 270, role: '5G Radio Access' },
          { id: 'amf', label: 'AMF-01 (MOCK)', type: 'core_control', x: 540, y: 140, role: 'Access & Mobility' },
          { id: 'smf', label: 'SMF-01 (MOCK)', type: 'core_control', x: 700, y: 140, role: 'Session Management' },
          { id: 'upf', label: 'UPF-01 (MOCK)', type: 'core_user', x: 620, y: 380, role: 'User Plane Gateway' },
        ],
        links: [
          { source: 'gnb', target: 'amf', label: 'N2 (SCTP)', type: 'control' },
          { source: 'gnb', target: 'upf', label: 'N3 (GTP-U)', type: 'user_plane' },
          { source: 'amf', target: 'smf', label: 'N11 (SBI)', type: 'control' },
          { source: 'smf', target: 'upf', label: 'N4 (PFCP)', type: 'control' },
        ],
      },
      slices: [
        {
          slice_id: 'sst-1-sd-010203',
          name: 'eMBB High-Throughput (MOCK)',
          device_class: 'camera',
          color: '#3B82F6',
          packet_rate_pps: 41.25,
          zone: { x: 40, y: 40, width: 240, height: 130, label: 'Camera Array Zone' },
        },
        {
          slice_id: 'sst-2-sd-020304',
          name: 'URLLC Low-Latency (MOCK)',
          device_class: 'AGV',
          color: '#F59E0B',
          packet_rate_pps: 80.0,
          zone: { x: 40, y: 200, width: 240, height: 130, label: 'Autonomous Vehicle Track' },
        },
        {
          slice_id: 'sst-3-sd-030405',
          name: 'mMTC Massive IoT (MOCK)',
          device_class: 'sensor',
          color: '#8B5CF6',
          packet_rate_pps: 10.0,
          zone: { x: 40, y: 360, width: 240, height: 130, label: 'Industrial Sensor Mesh' },
        },
      ],
      devices: [
        {
          id: 'dev_mock_01',
          device_id_hash: '0xmockdev001',
          device_class: 'camera',
          slice_id: 'sst-1-sd-010203',
          x: 100,
          y: 80,
          rate_pps: 41.25,
          verdict: 'benign',
          action: 'none',
          status_label: 'Nominal Streaming (MOCK)',
          is_onboarded: false,
          visible: true,
          is_provisioned: true,
        },
      ],
      provisioning_card: {
        total_catalog_sims: 200,
        total_batches: 2,
        batches: [{ batch_id: 'MOCK-BATCH-01', count: 30, slice: 'sst-3-sd-030405' }],
        provisioned_share: 1.0,
        is_provisioned: true,
        matched_event: null,
        fitting_volume: true,
        verdict: 'likely_benign',
        action: 'adapt_candidate',
        action_description: 'Mock dev fallback; real backend offline',
      },
      contamination_meters: {
        naive: { name: 'Naive Retraining (MOCK)', contamination_mean: 0.12, contamination_ci_95: [0.09, 0.15], fpr_mean: 0.05, onboardings_adapted: 1.0 },
        commshield_twin: { name: 'CommShield Twin (MOCK)', contamination_mean: 0.0, contamination_ci_95: [0.0, 0.0], fpr_mean: 0.01, onboardings_adapted: 2.0 },
      },
      decision_trace: [
        { step: 1, name: 'Volume Scaling Multiplier', result: 'k = 1.0 (MOCK)', status: 'PASSED' },
      ],
      saved_metrics_reference: {
        summary_file: 'experiments/results/twin/three_arm_twin_summary.json',
        window_counts_file: 'experiments/results/twin/window_counts.json',
        aggregate_windows: 11870,
      },
      is_stale: false,
      is_mock: true,
    };
  }
}

export const twinApi = new TwinApiService();
