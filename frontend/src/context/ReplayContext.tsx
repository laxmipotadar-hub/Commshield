import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import { api, ReplayStatusResponse } from '../services/api';

export const SCENARIOS = [
  { id: 'stable_benign', label: 'Stable Benign' },
  { id: 'legitimate_growth', label: 'Legitimate Growth' },
  { id: 'slow_attack_ramp', label: 'Slow Attack Ramp' },
  { id: 'attack_in_growth', label: 'Attack in Growth' },
  { id: 'mimicry_attack', label: 'Mimicry Attack' },
] as const;

export type ScenarioId = (typeof SCENARIOS)[number]['id'];

interface ReplayContextType {
  selectedScenario: ScenarioId;
  setSelectedScenario: (scenario: ScenarioId) => void;
  speed: number;
  setSpeed: (speed: number) => void;
  status: 'STOPPED' | 'RUNNING' | 'PAUSED' | 'COMPLETED' | string;
  currentIndex: number;
  totalWindows: number;
  pollTick: number;
  activeBaselineVersion: string;
  selectedSlice: string;
  setSelectedSlice: (slice: string) => void;
  handleStart: () => Promise<void>;
  handlePause: () => Promise<void>;
  handleResume: () => Promise<void>;
  handleStop: () => Promise<void>;
  refreshStatus: () => Promise<void>;
}

const ReplayContext = createContext<ReplayContextType | undefined>(undefined);

export const ReplayProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedScenario, setSelectedScenario] = useState<ScenarioId>('stable_benign');
  const [speed, setSpeed] = useState<number>(2.0);
  const [status, setStatus] = useState<string>('STOPPED');
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [totalWindows, setTotalWindows] = useState<number>(60);
  const [pollTick, setPollTick] = useState<number>(0);
  const [activeBaselineVersion, setActiveBaselineVersion] = useState<string>('v1.0.0-anchor');
  const [selectedSlice, setSelectedSlice] = useState<string>('sst-1-sd-010203');

  const pollIntervalRef = useRef<number | null>(null);

  const applyStatus = (res: ReplayStatusResponse) => {
    if (!res) return;
    setStatus(res.status);
    setCurrentIndex(res.current_window_index ?? 0);
    setTotalWindows(res.total_windows ?? 0);
  };

  const refreshStatus = async () => {
    try {
      const res = await api.getReplayStatus();
      applyStatus(res);
    } catch (e) {
      console.warn('Failed to fetch replay status:', e);
    }
  };

  // Fetch initial active baseline
  useEffect(() => {
    api
      .getBaselines()
      .then((baselines) => {
        if (baselines && baselines.length > 0) {
          const active = baselines.find((b) => b.is_active) || baselines[0];
          if (active?.version) {
            setActiveBaselineVersion(active.version);
          }
        }
      })
      .catch((e) => console.warn('Could not fetch active baseline:', e));

    refreshStatus();
  }, []);

  const handleStart = async () => {
    try {
      const res = await api.startReplay({
        dataset_id: selectedScenario,
        speed_multiplier: speed,
      });
      applyStatus(res);
      setPollTick((t) => t + 1);
    } catch (e) {
      console.error('Failed to start replay:', e);
    }
  };

  const handlePause = async () => {
    try {
      const res = await api.pauseReplay();
      applyStatus(res);
    } catch (e) {
      console.error('Failed to pause replay:', e);
    }
  };

  const handleResume = async () => {
    try {
      const res = await api.resumeReplay();
      applyStatus(res);
      setPollTick((t) => t + 1);
    } catch (e) {
      console.error('Failed to resume replay:', e);
    }
  };

  const handleStop = async () => {
    try {
      const res = await api.stopReplay();
      applyStatus(res);
    } catch (e) {
      console.error('Failed to stop replay:', e);
    }
  };

  // Poll data endpoints and status every 2 seconds while replay is running
  useEffect(() => {
    if (status === 'RUNNING') {
      pollIntervalRef.current = window.setInterval(async () => {
        try {
          const res = await api.getReplayStatus();
          applyStatus(res);
          // Increment poll tick to notify pages to re-query data endpoints
          setPollTick((t) => t + 1);

          if (res.status !== 'RUNNING') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
          }
        } catch (e) {
          console.warn('Replay polling error:', e);
        }
      }, 2000);
    } else {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [status]);

  return (
    <ReplayContext.Provider
      value={{
        selectedScenario,
        setSelectedScenario,
        speed,
        setSpeed,
        status,
        currentIndex,
        totalWindows,
        pollTick,
        activeBaselineVersion,
        selectedSlice,
        setSelectedSlice,
        handleStart,
        handlePause,
        handleResume,
        handleStop,
        refreshStatus,
      }}
    >
      {children}
    </ReplayContext.Provider>
  );
};

export const useReplay = () => {
  const context = useContext(ReplayContext);
  if (!context) {
    throw new Error('useReplay must be used within a ReplayProvider');
  }
  return context;
};
