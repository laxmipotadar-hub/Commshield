import React from 'react';
import { useDemo } from '../context/DemoContext';
import { ChevronRight, Presentation, Shield } from 'lucide-react';

export const DemoControlBar: React.FC = () => {
  const {
    isDemoMode,
    setIsDemoMode,
    presets,
    activePreset,
    activePresetIndex,
    selectPreset,
    nextPreset,
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

          {/* Scenario Selector Dropdown (1 to 4) */}
          <div className="flex items-center gap-1.5 bg-bg px-2 py-1 rounded-lg border border-border">
            <span className="text-[11px] font-bold text-muted uppercase">Scene:</span>
            <select
              value={activePresetIndex}
              onChange={(e) => selectPreset(Number(e.target.value))}
              className="bg-transparent text-xs font-bold text-text focus:outline-none cursor-pointer"
            >
              {presets.map((p, idx) => (
                <option key={p.id} value={idx}>
                  {idx + 1}. {p.name} [{p.source_badge || (p.source === 'lab' ? 'Live lab' : 'Simulated twin')}]
                </option>
              ))}
            </select>
          </div>

          {/* Next Scene Button */}
          <button
            onClick={nextPreset}
            className="flex items-center gap-1 px-3 py-1 bg-blue hover:bg-blue/90 text-white rounded-lg text-xs font-bold shadow-sm transition-colors"
            title="Advance to next presentation scene"
          >
            <span>Next scene</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </>
      )}
    </div>
  );
};
