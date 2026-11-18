import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { api, DemoPreset, DemoKeyEvent } from '../services/api';
import { useReplay } from './ReplayContext';

// Hardcoded fallback presets matching backend CONTRACTS.md
const FALLBACK_PRESETS: DemoPreset[] = [
  {
    id: 'real_benign',
    preset_number: 1,
    name: 'Real Benign Traffic (5G-NIDD)',
    description: '40 consecutive 60s windows of authentic baseline benign traffic from 5G Standalone core tap points.',
    data_label: 'real',
    dataset_id: 'demo_real_benign',
    best_attack_type: null,
    window_range: { start_index: 0, end_index: 39, total_windows: 40 },
    key_events: [
      {
        window_index: 0,
        event_type: 'nominal_start',
        caption: 'Replay started: Nominal 5G core user-plane telemetry flowing through calibrated baseline.',
      },
      {
        window_index: 18,
        event_type: 'drift_alarm',
        caption: 'Natural variation detected: ADWIN triggers drift alarm; attribution confirms proportional composition.',
      },
      {
        window_index: 39,
        event_type: 'nominal_complete',
        caption: 'Replay completed: 0 attack windows injected, 0.0% baseline contamination, nominal 5% FPR.',
      },
    ],
  },
  {
    id: 'real_attack',
    preset_number: 2,
    name: 'Real Attack Traffic (SYNScan)',
    description: '20 clean baseline benign windows followed by an authentic 5G-NIDD SYNScan reconnaissance attack window.',
    data_label: 'real',
    dataset_id: 'demo_real_attack',
    best_attack_type: 'SYNScan',
    window_range: { start_index: 0, end_index: 20, total_windows: 21 },
    key_events: [
      {
        window_index: 0,
        event_type: 'baseline_lead_in',
        caption: 'Replay started: Clean benign traffic active on eMBB slice before reconnaissance onset.',
      },
      {
        window_index: 20,
        event_type: 'first_alert',
        caption: 'First Alert: SYNScan attack detected immediately (fused score p=0.999 >= 0.98, delay 0w).',
      },
      {
        window_index: 20,
        event_type: 'quarantine_isolation',
        caption: 'Quarantine Action: Malicious window isolated in quarantine; baseline contamination remains strictly 0.0%.',
      },
    ],
  },
  {
    id: 'scaled_growth',
    preset_number: 3,
    name: 'Real Benign Traffic Scaled 2x',
    description: 'Real benign 5G-NIDD traffic scaled 2.0x with composition preserved, modeling enterprise capacity expansion.',
    data_label: 'semi-synthetic',
    dataset_id: 'demo_scaled_growth',
    best_attack_type: null,
    window_range: { start_index: 0, end_index: 39, total_windows: 40 },
    key_events: [
      {
        window_index: 0,
        event_type: 'baseline_1x',
        caption: 'Replay started: 1x unscaled baseline benign traffic flowing normally.',
      },
      {
        window_index: 20,
        event_type: 'growth_onset',
        caption: 'Volume Surge: Traffic scales 2.0x; ADWIN drift detector fires across uplink and downlink counters.',
      },
      {
        window_index: 25,
        event_type: 'candidate_built',
        caption: 'Shadow Candidate Built: Proportional growth verified (JSD=0.0034 <= 0.035, per-UE deviation=0.167 <= 0.25).',
      },
      {
        window_index: 25,
        event_type: 'governance_failure',
        caption: 'Governance Gate Triggered: Clean candidate fails canary retention (recall drops to 25%) and drift budget (D_rms=6.65 > 2.5) -> Rejected.',
      },
    ],
  },
  {
    id: 'attack_in_growth',
    preset_number: 4,
    name: 'Real Attack Injected into Scaled Growth',
    description: 'An authentic 5G-NIDD attack window hidden inside 2.0x scaled benign growth traffic.',
    data_label: 'semi-synthetic',
    dataset_id: 'demo_attack_in_growth',
    best_attack_type: 'SYNScan',
    window_range: { start_index: 0, end_index: 20, total_windows: 21 },
    key_events: [
      {
        window_index: 0,
        event_type: 'scaled_growth_lead_in',
        caption: 'Replay started: 2.0x scaled high-volume traffic active across eMBB slice.',
      },
      {
        window_index: 20,
        event_type: 'attack_injected_alert',
        caption: 'Attack Injected: Real attack window detected instantly despite 2x volume expansion (p=0.999).',
      },
      {
        window_index: 20,
        event_type: 'quarantine_isolation',
        caption: 'Quarantine Isolation: Attack window isolated; candidate baseline training excludes attack traffic.',
      },
      {
        window_index: 20,
        event_type: 'governance_trace',
        caption: 'Decision Trace & Three-Arm Comparison: Arm C blocks contamination (0.0%), whereas naive Arm B is poisoned.',
      },
    ],
    three_arm_summary: {
      scenario: 'attack_in_scaled_growth',
      data_label: 'semi-synthetic',
      arms: {
        arm_a_static: {
          name: 'Static Anchor',
          recall: 1.0,
          fpr: 0.05,
          contamination: 0.0,
          adaptations: 0,
          quarantined: 0,
        },
        arm_b_naive: {
          name: 'Naive Retraining',
          recall: 0.0,
          fpr: 0.0,
          contamination: 0.0,
          adaptations: 1,
          quarantined: 0,
        },
        arm_c_commshield: {
          name: 'CommShield Gated',
          recall: 1.0,
          fpr: 0.05,
          contamination: 0.0,
          adaptations: 0,
          quarantined: 1,
        },
      },
    },
    decision_trace: {
      candidate_version: 'v1.1.0-real-demo-cand',
      overall_status: 'REJECTED',
      checks: [
        {
          name: 'normal_holdout_backtest',
          status: 'PASSED',
          detail: 'Normal-holdout FPR is 0.00% (0/20 windows flagged) <= limit 5.00%.',
        },
        {
          name: 'proportional_growth',
          status: 'PASSED',
          detail: 'JSD divergence is 0.0034 <= 0.0350 limit, per-UE session rate deviation is 0.167 <= 0.250 limit.',
        },
        {
          name: 'canary_retention_test',
          status: 'FAILED',
          detail: 'Candidate recall 25.0% vs active recall 100.0% (delta 75.0% exceeds allowed 5.0% limit).',
        },
        {
          name: 'drift_budget',
          status: 'FAILED',
          detail: 'D_rms(cand, active)=6.65 (limit <= 1.5) and D_max=16.90 (limit <= 3.0) exceeded.',
        },
      ],
      conclusion: 'Quarantine enforced: candidate baselines cannot be promoted while canary recall is degraded or distance exceeds anchor budget.',
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
    setSelectedDataSource(preset.data_label === 'real' ? '5g_nidd' : '5g_nidd');
    try {
      await api.startReplay({
        dataset_id: preset.dataset_id,
        data_source: '5g_nidd',
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
