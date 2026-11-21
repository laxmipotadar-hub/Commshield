import React from 'react';
import { useDemo } from '../context/DemoContext';
import { ChevronRight, FastForward, Presentation, Shield, Timer, Zap } from 'lucide-react';

export const DemoControlBar: React.FC = () => {
  const {
    isDemoMode,
    setIsDemoMode,
    presets,
    activePreset,
    activePresetIndex,
    selectPreset,
    nextPreset,
    skipScene,
    timeRemaining,
    autoAdvanceEnabled,
    isOfflineFallback,
    reducedMotion,
    setReducedMotion,
  } = useDemo();

  return (
    <div className="flex items-center gap-2.5 flex-wrap">
      {/* 1. Presentation Demo Mode Toggle Button */}
      <button
        onClick={() => setIsDemoMode(!isDemoMode)}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all shadow-sm ${
          isDemoMode
            ? 'bg-gradient-to-r from-blue to-teal text-white shadow-blue/20 ring-1 ring-blue/50'
            : 'bg-card border border-border text-muted hover:text-text hover:bg-slate/30'
        }`}
        title="Toggle Judge Presentation Demo Mode (Zero Randomness)"
      >
        <Presentation className="w-3.5 h-3.5" />
        <span>Demo Mode</span>
        <span
          className={`text-[9px] uppercase font-bold px-1.5 py-0.2 rounded ${
            isDemoMode ? 'bg-black/30 text-white' : 'bg-border text-muted'
          }`}
        >
          {isDemoMode ? 'ON' : 'OFF'}
        </span>
      </button>

      {/* 2. Controls visible when Demo Mode is ON */}
      {isDemoMode && (
        <>
          {/* Source Tag Badge */}
          <div
            className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold shadow-sm border ${
              activePreset.source === 'lab' || activePreset.source_badge === 'Live lab'
                ? 'bg-purple-500/15 border-purple-500/40 text-purple-300'
                : activePreset.source === 'real_recorded' || activePreset.source_badge === 'Real recorded'
                ? 'bg-blue/15 border-blue/40 text-blue'
                : 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
            }`}
          >
            <Shield className="w-3.5 h-3.5" />
            <span className="whitespace-nowrap">
              Source: {activePreset.source_badge || (activePreset.source === 'lab' ? 'Live lab' : 'Simulated twin')}
            </span>
          </div>

          {/* Offline Snapshot Fallback Badge if active */}
          {isOfflineFallback && (
            <span
              className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40"
              title="Replaying from frozen offline snapshots in experiments/snapshot/"
            >
              Snapshot Fallback
            </span>
          )}

          {/* Clear Scene Step Indicator */}
          <span className="text-xs font-bold text-white px-2 py-1 bg-card rounded-lg border border-border shadow-xs">
            Scene {activePresetIndex + 1} of {presets.length}
          </span>

          {/* Scenario Selector Dropdown */}
          <div className="flex items-center gap-1.5 bg-bg px-2 py-1 rounded-lg border border-border">
            <select
              value={activePresetIndex}
              onChange={(e) => selectPreset(Number(e.target.value))}
              className="bg-transparent text-xs font-bold text-text focus:outline-none cursor-pointer max-w-[200px] truncate"
            >
              {presets.map((p, idx) => (
                <option key={p.id} value={idx}>
                  {idx + 1}. {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Low Motion Toggle Button */}
          <button
            onClick={() => setReducedMotion(!reducedMotion)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold border transition-colors ${
              reducedMotion
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                : 'bg-bg text-muted hover:text-text border-border'
            }`}
            title="Toggle low-motion (respects prefers-reduced-motion)"
          >
            <Zap className="w-3 h-3" />
            <span>{reducedMotion ? 'Low-Motion: ON' : 'Low-Motion: OFF'}</span>
          </button>

          {/* 30-Second Auto-Advancement Countdown with Progress Indicator */}
          <div
            className="flex items-center gap-2 px-2.5 py-1 bg-card rounded-lg border border-border shadow-xs text-xs font-mono"
            title={autoAdvanceEnabled ? `Auto-advancing to next scene in ${timeRemaining}s` : 'Auto-advance paused'}
          >
            <Timer className={`w-3.5 h-3.5 ${timeRemaining <= 5 ? 'text-attack animate-pulse' : 'text-teal'}`} />
            <div className="flex items-center gap-1.5">
              <span className="text-muted text-[10px] hidden sm:inline">Auto-advance:</span>
              <span className="font-bold text-text">{timeRemaining}s</span>
            </div>
            {/* Visual mini progress bar */}
            <div className="w-12 bg-bg rounded-full h-1.5 overflow-hidden border border-border">
              <div
                className={`h-full transition-all duration-1000 ${timeRemaining <= 5 ? 'bg-attack' : 'bg-teal'}`}
                style={{ width: `${(timeRemaining / 30) * 100}%` }}
              />
            </div>
          </div>

          {/* Skip Scene Button */}
          <button
            onClick={skipScene}
            className="flex items-center gap-1 px-2.5 py-1 bg-teal/15 hover:bg-teal/25 text-teal border border-teal/30 rounded-lg text-xs font-bold transition-colors cursor-pointer"
            title="Skip current scene and immediately advance to next"
          >
            <FastForward className="w-3 h-3" />
            <span>Skip Scene</span>
          </button>

          {/* Next Scene Button with Key Indicator */}
          <button
            onClick={nextPreset}
            className="flex items-center gap-1 px-3 py-1 bg-blue hover:bg-blue/90 text-white rounded-lg text-xs font-bold shadow-sm transition-colors cursor-pointer"
            title="Advance to next presentation scene (Hotkey: 'N' or Right Arrow)"
          >
            <span>Next scene (N)</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </>
      )}
    </div>
  );
};
