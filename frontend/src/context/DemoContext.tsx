import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { api, DemoPreset, DemoKeyEvent } from '../services/api';
import { useReplay } from './ReplayContext';

// Hardcoded fallback presets matching backend canonical four-scene demo
const FALLBACK_PRESETS: DemoPreset[] = [
  {
    id: 'baseline',
    preset_number: 1,
    name: '1. Baseline Steady-State Telemetry',
    description: 'Calibrated nominal baseline telemetry flowing across eMBB, URLLC, and mMTC slices with 100% catalog-provisioned SIMs.',
    data_label: 'simulated_twin',
    source: 'simulated_twin',
    source_badge: 'Simulated twin',
    scenario: 'approved_onboarding',
    dataset_id: 'baseline',
    best_attack_type: null,
    window_range: { start_index: 0, end_index: 9, total_windows: 10 },
    key_events: [
      {
        window_index: 0,
        event_type: 'nominal_start',
        caption: 'Replay started: Nominal 5G core telemetry flowing through calibrated baseline on all slices.',
      },
      {
        window_index: 5,
        event_type: 'periodic_audit',
        caption: 'Periodic audit: 200/200 devices catalog provisioned; JSD=0.000, zero drift, 0.0% false alarms.',
      },
      {
        window_index: 9,
        event_type: 'nominal_complete',
        caption: 'Baseline complete: Zero security alerts; contamination strictly 0.0%; nominal baseline sustained.',
      },
    ],
    three_arm_summary: {
      scenario: 'baseline',
      source: 'simulated_twin',
      arms: {
        naive: { name: 'Naive Retraining', contamination: 0.0, fpr: 0.0, adaptations: 0, quarantined: 0 },
        commshield_twin: { name: 'CommShield Twin', contamination: 0.0, fpr: 0.0, adaptations: 0, quarantined: 0 },
      },
    },
    decision_trace: {
      status: 'APPROVED',
      conclusion: 'Nominal baseline traffic verified; no adaptation required; all devices provisioned.',
      checks: [
        { name: 'volume_scale', status: 'PASSED', detail: 'k = 1.00 nominal volume across all slices.' },
        { name: 'composition_jsd', status: 'PASSED', detail: 'JSD = 0.000 <= 0.045 limit.' },
        { name: 'provisioning_check', status: 'PASSED', detail: '100.0% provisioned in catalog (200 SIMs verified).' },
      ],
    },
  },
  {
    id: 'approved_onboarding',
    preset_number: 2,
    name: '2. Approved Onboarding (Batch OB-01 & OB-02)',
    description: 'Legitimate onboarding surge matching scheduled change events (BATCH-OB-20261115-01) with 100% catalog-verified SIMs.',
    data_label: 'simulated_twin',
    source: 'simulated_twin',
    source_badge: 'Simulated twin',
    scenario: 'approved_onboarding',
    dataset_id: 'approved_onboarding',
    best_attack_type: null,
    window_range: { start_index: 0, end_index: 19, total_windows: 20 },
    key_events: [
      {
        window_index: 0,
        event_type: 'baseline_lead_in',
        caption: 'Replay started: Steady-state baseline telemetry before scheduled onboarding window.',
      },
      {
        window_index: 10,
        event_type: 'batch_arrival',
        caption: 'Batch Ingress: 30 new sensors join mMTC slice; traffic scales by k=1.48 matching BATCH-OB-20261115-01.',
      },
      {
        window_index: 14,
        event_type: 'governance_approval',
        caption: 'Governance Approved: JSD=0.018 <= 0.045, 100% provisioned, device anomalous share 0.0% -> Candidate promoted.',
      },
    ],
    three_arm_summary: {
      scenario: 'approved_onboarding',
      source: 'simulated_twin',
      arms: {
        naive: { name: 'Naive Retraining', contamination: 0.0, fpr: 0.0, adaptations: 2.0, quarantined: 0 },
        commshield_twin: { name: 'CommShield Twin', contamination: 0.0, fpr: 0.027, adaptations: 2.0, quarantined: 0 },
      },
    },
    decision_trace: {
      status: 'APPROVED',
      conclusion: 'Approved onboarding adapted; 100% provisioned; volume fits scheduled batch; conformal check clear.',
      checks: [
        { name: 'volume_scale', status: 'PASSED', detail: 'k = 1.48 expansion fits batch size (30 sensors).' },
        { name: 'composition_jsd', status: 'PASSED', detail: 'JSD = 0.018 <= 0.045 limit.' },
        { name: 'provisioning_catalog', status: 'PASSED', detail: '100.0% provisioned; matches BATCH-OB-20261115-01.' },
        { name: 'conformal_evaluation', status: 'PASSED', detail: 'Device anomalous share: 0.0% <= 10.0%, uncertain: 4.8% <= 30.0%.' },
      ],
    },
  },
  {
    id: 'unprovisioned_device',
    preset_number: 3,
    name: '3. Unprovisioned Device Burst Flagged',
    description: 'Sudden surge of unprovisioned rogue SIM IDs flagged and quarantined by zero-trust catalog lookup.',
    data_label: 'simulated_twin',
    source: 'simulated_twin',
    source_badge: 'Simulated twin',
    scenario: 'unprovisioned_burst',
    dataset_id: 'unprovisioned_device',
    best_attack_type: 'Unprovisioned_Burst',
    window_range: { start_index: 0, end_index: 19, total_windows: 20 },
    key_events: [
      {
        window_index: 0,
        event_type: 'rogue_lead_in',
        caption: 'Replay started: Clean telemetry before sudden unprovisioned traffic ingress.',
      },
      {
        window_index: 10,
        event_type: 'first_alert',
        caption: 'Security Alert: Rogue devices detected; catalog provisioned share drops to 57.1% < 95.0% threshold.',
      },
      {
        window_index: 11,
        event_type: 'quarantine_isolation',
        caption: 'Quarantine Enforced: Rule 1 isolates unprovisioned devices; baseline contamination prevented (0.0%).',
      },
    ],
    three_arm_summary: {
      scenario: 'unprovisioned_burst',
      source: 'simulated_twin',
      arms: {
        naive: { name: 'Naive Retraining', contamination: 0.50, fpr: 0.133, adaptations: 0, quarantined: 0 },
        commshield_twin: { name: 'CommShield Twin', contamination: 0.0, fpr: 0.025, adaptations: 0, quarantined: 1 },
      },
    },
    decision_trace: {
      status: 'QUARANTINED',
      conclusion: 'Quarantine enforced: unprovisioned rogue devices present without catalog registration.',
      checks: [
        { name: 'volume_scale', status: 'FAILED', detail: 'k = 2.15 sudden anomalous surge.' },
        { name: 'composition_jsd', status: 'FAILED', detail: 'JSD = 0.142 > 0.045 limit.' },
        { name: 'provisioning_catalog', status: 'FAILED', detail: 'Provisioned share: 57.1% < 95.0%; 40 rogue SIMs detected.' },
        { name: 'conformal_evaluation', status: 'FAILED', detail: 'Rogue devices anomaly rate: 99.3% in split conformal test.' },
      ],
    },
  },
  {
    id: 'hidden_ramp',
    preset_number: 4,
    name: '4. Hidden Ramp (Naive Poisoned vs CommShield Quarantines Excess)',
    description: 'Subtle creeping rate increases hidden inside an approved onboarding where naive retraining is poisoned and CommShield quarantines the excess.',
    data_label: 'simulated_twin',
    source: 'simulated_twin',
    source_badge: 'Simulated twin',
    scenario: 'slow_ramp_in_onboarding',
    dataset_id: 'hidden_ramp',
    best_attack_type: 'Conformal_Gray_Band',
    window_range: { start_index: 0, end_index: 19, total_windows: 20 },
    key_events: [
      {
        window_index: 0,
        event_type: 'ramp_lead_in',
        caption: 'Replay started: Approved onboarding baseline active with scheduled batch event.',
      },
      {
        window_index: 10,
        event_type: 'ramp_onset',
        caption: 'Hidden Ramp Onset: 15 devices subtly ramp rate inside approved onboarding volume ($k=1.55$).',
      },
      {
        window_index: 15,
        event_type: 'conformal_gray_band',
        caption: 'Conformal Abstention: Creeping devices fall into split-conformal gray band ($p in [0.01, 0.05]$); uncertain share exceeds 30.0%.',
      },
      {
        window_index: 16,
        event_type: 'governance_divergence',
        caption: 'Governance Divergence: Naive retraining absorbs attack (33.3% contamination); CommShield quarantines excess (1.7% contamination).',
      },
    ],
    three_arm_summary: {
      scenario: 'slow_ramp_in_onboarding',
      source: 'simulated_twin',
      arms: {
        naive: { name: 'Naive Retraining', contamination: 0.333, fpr: 0.0, adaptations: 0, quarantined: 0 },
        commshield_twin: { name: 'CommShield Twin', contamination: 0.017, fpr: 0.027, adaptations: 0, quarantined: 1 },
      },
    },
    decision_trace: {
      status: 'QUARANTINED',
      conclusion: 'Quarantine excess enforced: split-conformal gray band detected ramping anomalous behavior despite valid batch.',
      checks: [
        { name: 'volume_scale', status: 'PASSED', detail: 'k = 1.55 volume growth initially matches batch envelope.' },
        { name: 'composition_jsd', status: 'PASSED', detail: 'JSD = 0.038 <= 0.045 limit.' },
        { name: 'provisioning_catalog', status: 'PASSED', detail: '100.0% provisioned in catalog.' },
        { name: 'conformal_evaluation', status: 'FAILED', detail: '15 ramping sensors fall into conformal gray band (uncertain share > 30.0%).' },
      ],
    },
  },
];

interface DemoContextType {
  isDemoMode: boolean;
  setIsDemoMode: (enabled: boolean) => void;
  presets: DemoPreset[];
  activePreset: DemoPreset;
  activePresetIndex: number;
  selectPreset: (indexOrId: number | string) => Promise<void>;
  nextPreset: () => Promise<void>;
  injectAttack: () => Promise<void>;
  scaleTraffic2x: () => Promise<void>;
  activeKeyEvent: DemoKeyEvent | null;
  pausedAtEvent: boolean;
  resumeFromKeyEvent: () => Promise<void>;
}

const DemoContext = createContext<DemoContextType | undefined>(undefined);

export const DemoProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isDemoMode, setIsDemoMode] = useState<boolean>(false);
  const [presets, setPresets] = useState<DemoPreset[]>(FALLBACK_PRESETS);
  const [activePresetIndex, setActivePresetIndex] = useState<number>(0);
  const [activeKeyEvent, setActiveKeyEvent] = useState<DemoKeyEvent | null>(null);
  const [pausedAtEvent, setPausedAtEvent] = useState<boolean>(false);

  const acknowledgedEventsRef = useRef<Set<number>>(new Set());
  const { currentIndex, status, handlePause, handleResume, setSelectedDataSource, speed } = useReplay();

  // Load presets from backend API on mount
  useEffect(() => {
    api
      .getDemoScenarios()
      .then((res) => {
        if (res?.scenarios?.length > 0) {
          setPresets(res.scenarios);
        }
      })
      .catch((err) => {
        console.warn('Could not fetch demo scenarios from API, using fallback presets:', err);
      });
  }, []);

  const activePreset = presets[activePresetIndex] || FALLBACK_PRESETS[0];

  // Start replay for a given preset
  const playPreset = async (preset: DemoPreset) => {
    acknowledgedEventsRef.current.clear();
    setActiveKeyEvent(null);
    setPausedAtEvent(false);
    const ds = preset.source === 'lab' ? 'open5gs_lab' : 'synthetic';
    setSelectedDataSource(ds);
    try {
      await api.startReplay({
        dataset_id: preset.dataset_id,
        data_source: preset.source === 'lab' ? 'lab' : 'simulated_twin',
        speed_multiplier: speed,
      });
    } catch (e) {
      console.warn('Failed to start demo preset replay:', e);
    }
  };

  const selectPreset = async (indexOrId: number | string) => {
    let targetIndex = 0;
    if (typeof indexOrId === 'number') {
      targetIndex = Math.max(0, Math.min(presets.length - 1, indexOrId));
    } else {
      const found = presets.findIndex((p) => p.id === indexOrId || p.dataset_id === indexOrId);
      if (found >= 0) targetIndex = found;
    }
    setActivePresetIndex(targetIndex);
    const targetPreset = presets[targetIndex];
    if (targetPreset) {
      await playPreset(targetPreset);
    }
  };

  const nextPreset = async () => {
    const nextIdx = (activePresetIndex + 1) % presets.length;
    await selectPreset(nextIdx);
  };

  const injectAttack = async () => {
    // Switch to Scenario 2 (Real Attack)
    await selectPreset(1);
  };

  const scaleTraffic2x = async () => {
    // Switch to Scenario 3 (Scaled Benign Traffic 2x)
    await selectPreset(2);
  };

  // Monitor currentIndex against activePreset key_events for auto-pause
  useEffect(() => {
    if (!isDemoMode || status !== 'RUNNING') return;

    const matchedEvent = activePreset.key_events.find(
      (ev) => ev.window_index === currentIndex && !acknowledgedEventsRef.current.has(ev.window_index)
    );

    if (matchedEvent) {
      acknowledgedEventsRef.current.add(matchedEvent.window_index);
      setActiveKeyEvent(matchedEvent);
      setPausedAtEvent(true);
      handlePause();
    }
  }, [currentIndex, isDemoMode, status, activePreset, handlePause]);

  const resumeFromKeyEvent = async () => {
    setPausedAtEvent(false);
    await handleResume();
  };

  // When demo mode is toggled ON, automatically select and start Scenario 1 if not already running
  const handleToggleDemoMode = (enabled: boolean) => {
    setIsDemoMode(enabled);
    if (enabled) {
      selectPreset(activePresetIndex);
    } else {
      setActiveKeyEvent(null);
      setPausedAtEvent(false);
    }
  };

  return (
    <DemoContext.Provider
      value={{
        isDemoMode,
        setIsDemoMode: handleToggleDemoMode,
        presets,
        activePreset,
        activePresetIndex,
        selectPreset,
        nextPreset,
        injectAttack,
        scaleTraffic2x,
        activeKeyEvent,
        pausedAtEvent,
        resumeFromKeyEvent,
      }}
    >
      {children}
    </DemoContext.Provider>
  );
};

export const useDemo = () => {
  const context = useContext(DemoContext);
  if (!context) {
    throw new Error('useDemo must be used within a DemoProvider');
  }
  return context;
};
