import React from 'react';
import { useDemo } from '../context/DemoContext';
import { ChevronRight, Presentation, Shield, TrendingUp, Zap } from 'lucide-react';

export const DemoControlBar: React.FC = () => {
  const {
    isDemoMode,
    setIsDemoMode,
    presets,
    activePreset,
    activePresetIndex,
    selectPreset,
    nextPreset,
    injectAttack,
    scaleTraffic2x,
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
          {/* Persistent Real 5G-NIDD Replay Badge */}
          <div className="flex items-center gap-1 bg-amber-500/10 border border-amber-500/30 text-amber-400 px-2.5 py-1 rounded-lg text-xs font-semibold shadow-sm">
            <Shield className="w-3.5 h-3.5 text-amber-400" />
            <span className="whitespace-nowrap">Replay mode: real 5G-NIDD traffic</span>
          </div>

          {/* Semi-Synthetic Badge if applicable */}
          {activePreset.data_label === 'semi-synthetic' && (
            <div className="flex items-center gap-1 bg-purple-500/15 border border-purple-500/30 text-purple-300 px-2 py-1 rounded-lg text-xs font-bold">
              <span>semi-synthetic</span>
            </div>
          )}

          {/* Scenario Selector Dropdown (1 to 4) */}
          <div className="flex items-center gap-1.5 bg-bg px-2 py-1 rounded-lg border border-border">
            <span className="text-[11px] font-bold text-muted uppercase">Scenario:</span>
            <select
              value={activePresetIndex}
              onChange={(e) => selectPreset(Number(e.target.value))}
              className="bg-transparent text-xs font-bold text-text focus:outline-none cursor-pointer"
            >
              {presets.map((p, idx) => (
                <option key={p.id} value={idx}>
                  {idx + 1}. {p.name} ({p.data_label})
                </option>
              ))}
            </select>
          </div>

          {/* Next Scenario Button */}
          <button
            onClick={nextPreset}
            className="flex items-center gap-1 px-2.5 py-1 bg-card hover:bg-border/60 border border-border text-text rounded-lg text-xs font-semibold transition-colors"
            title="Advance to next presentation scenario"
          >
            <span>Next</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>

          {/* Live Judge Action Buttons (Only when on Scenario 1) */}
          {activePreset.preset_number === 1 && (
            <div className="flex items-center gap-1.5 pl-1.5 border-l border-border">
              <button
                onClick={injectAttack}
                className="flex items-center gap-1 px-2 py-1 rounded bg-attack/15 hover:bg-attack/25 border border-attack/40 text-attack text-[11px] font-bold transition-all shadow-sm"
                title="Switch replay to prepared SYNScan attack window"
              >
                <Zap className="w-3 h-3 text-attack fill-current" />
                <span>Inject attack</span>
              </button>
              <button
                onClick={scaleTraffic2x}
                className="flex items-center gap-1 px-2 py-1 rounded bg-teal/15 hover:bg-teal/25 border border-teal/40 text-teal text-[11px] font-bold transition-all shadow-sm"
                title="Switch replay to prepared 2.0x scaled growth stream"
              >
                <TrendingUp className="w-3 h-3 text-teal" />
                <span>Scale traffic 2x</span>
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
};
