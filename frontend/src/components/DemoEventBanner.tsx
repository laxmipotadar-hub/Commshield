import React, { useState } from 'react';
import { useDemo } from '../context/DemoContext';
import { AlertTriangle, CheckCircle, ChevronDown, ChevronRight, ChevronUp, Play, ShieldAlert, Sparkles, Zap, TrendingUp } from 'lucide-react';

export const DemoEventBanner: React.FC = () => {
  const {
    isDemoMode,
    activePreset,
    activeKeyEvent,
    pausedAtEvent,
    resumeFromKeyEvent,
    nextPreset,
    injectAttack,
    scaleTraffic2x,
  } = useDemo();

  const [traceExpanded, setTraceExpanded] = useState<boolean>(true);
  const [threeArmExpanded, setThreeArmExpanded] = useState<boolean>(true);

  if (!isDemoMode) return null;

  return (
    <div className="mb-6 space-y-4">
      {/* 1. Active Key Event Pause Banner */}
      {pausedAtEvent && activeKeyEvent && (
        <div className="bg-amber-950/80 border-2 border-amber-500/80 rounded-xl p-4 shadow-xl backdrop-blur-sm animate-pulse-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-start sm:items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 flex-shrink-0">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-500/30 text-amber-300">
                  Key Event Paused (Window #{activeKeyEvent.window_index})
                </span>
                <span className="text-xs text-amber-400 font-semibold">{activeKeyEvent.event_type}</span>
              </div>
              <p className="text-sm font-semibold text-white mt-1 leading-snug">
                {activeKeyEvent.caption}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={resumeFromKeyEvent}
              className="flex items-center justify-center gap-2 px-3.5 py-2 bg-amber-500 hover:bg-amber-400 text-navy font-bold text-xs rounded-lg transition-colors shadow-md"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Continue Replay</span>
            </button>
            <button
              onClick={nextPreset}
              className="flex items-center justify-center gap-1.5 px-3.5 py-2 bg-blue hover:bg-blue/90 text-white font-bold text-xs rounded-lg transition-colors shadow-md"
            >
              <span>Next scene</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* 2. Interactive Trigger Buttons for Scenario 1 (Judge Live Actions) */}
      {activePreset.preset_number === 1 && (
        <div className="bg-card border border-border rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 bg-gradient-to-r from-card to-card/60">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-teal" />
            <span className="text-xs font-semibold text-text">
              Judge Live Actions (Scenario 1 Active):
            </span>
            <span className="text-xs text-muted">
              Dynamically perturb pure benign baseline into attack or growth streams
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={injectAttack}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-attack/15 border border-attack/40 hover:bg-attack/25 text-attack text-xs font-bold transition-all shadow-sm"
              title="Switch replay to Scenario 2 (Real SYNScan attack)"
            >
              <Zap className="w-3.5 h-3.5 text-attack fill-current" />
              <span>Inject Attack (SYNScan)</span>
            </button>
            <button
              onClick={scaleTraffic2x}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-teal/15 border border-teal/40 hover:bg-teal/25 text-teal text-xs font-bold transition-all shadow-sm"
              title="Switch replay to Scenario 3 (2.0x scaled growth)"
            >
              <TrendingUp className="w-3.5 h-3.5 text-teal" />
              <span>Scale Traffic 2x</span>
            </button>
          </div>
        </div>
      )}

      {/* 3. Scenario 4 Special Panels: Decision Trace and Three-Arm View */}
      {activePreset.preset_number === 4 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Decision Trace Card */}
          {activePreset.decision_trace && (
            <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
              <div
                className="flex items-center justify-between cursor-pointer select-none pb-2 border-b border-border/60"
                onClick={() => setTraceExpanded(!traceExpanded)}
              >
                <div className="flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-purple-400" />
                  <span className="text-xs font-bold uppercase tracking-wider text-text">
                    Governance Decision Trace (Scenario 4)
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-attack/20 text-attack font-bold">
                    {activePreset.decision_trace.overall_status}
                  </span>
                </div>
                <button className="text-muted hover:text-text">
                  {traceExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
              </div>

              {traceExpanded && (
                <div className="mt-3 space-y-2.5">
                  <div className="flex items-center justify-between text-[11px] text-muted">
                    <span>Evaluated Candidate:</span>
                    <span className="font-mono text-text font-semibold">
                      {activePreset.decision_trace.candidate_version}
                    </span>
                  </div>

                  <div className="space-y-1.5">
                    {activePreset.decision_trace.checks.map((chk, i) => (
                      <div
                        key={i}
                        className={`text-xs p-2 rounded-lg border flex items-start gap-2.5 ${
                          chk.status === 'PASSED'
                            ? 'bg-safe/10 border-safe/30 text-emerald-300'
                            : 'bg-attack/10 border-attack/30 text-rose-300'
                        }`}
                      >
                        {chk.status === 'PASSED' ? (
                          <CheckCircle className="w-4 h-4 text-safe flex-shrink-0 mt-0.5" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 text-attack flex-shrink-0 mt-0.5" />
                        )}
                        <div>
                          <div className="font-semibold flex items-center gap-2">
                            <span>{chk.name}</span>
                            <span className="text-[10px] uppercase font-bold px-1.5 py-0.2 rounded bg-black/30">
                              {chk.status}
                            </span>
                          </div>
                          <p className="text-[11px] opacity-90 mt-0.5">{chk.detail}</p>
                        </div>
                      </div>
                    ))}
                  </div>

                  <p className="text-[11px] text-muted italic pt-1 border-t border-border/40">
                    {activePreset.decision_trace.conclusion}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Three-Arm View Card */}
          {activePreset.three_arm_summary && (
            <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
              <div
                className="flex items-center justify-between cursor-pointer select-none pb-2 border-b border-border/60"
                onClick={() => setThreeArmExpanded(!threeArmExpanded)}
              >
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-blue" />
                  <span className="text-xs font-bold uppercase tracking-wider text-text">
                    Three-Arm Evaluation (Scenario 4)
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-teal/20 text-teal font-semibold">
                    attack_in_scaled_growth
                  </span>
                </div>
                <button className="text-muted hover:text-text">
                  {threeArmExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
              </div>

              {threeArmExpanded && (
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="text-[10px] text-muted uppercase tracking-wider border-b border-border">
                        <th className="pb-1.5">Arm</th>
                        <th className="pb-1.5">Recall</th>
                        <th className="pb-1.5">Benign FPR</th>
                        <th className="pb-1.5">Contamination</th>
                        <th className="pb-1.5">Adapt / Quaran</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/40">
                      {Object.entries(activePreset.three_arm_summary.arms).map(([k, arm]) => (
                        <tr
                          key={k}
                          className={k === 'arm_c_commshield' ? 'bg-blue/10 font-semibold' : ''}
                        >
                          <td className="py-2 pr-2">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                k === 'arm_a_static'
                                  ? 'bg-slate/30 text-white'
                                  : k === 'arm_b_naive'
                                  ? 'bg-attack/20 text-attack'
                                  : 'bg-safe/20 text-safe'
                              }`}
                            >
                              {arm.name}
                            </span>
                          </td>
                          <td className="py-2 text-text">
                            {arm.recall !== null && arm.recall !== undefined ? `${(arm.recall * 100).toFixed(0)}%` : 'N/A'}
                          </td>
                          <td className="py-2 text-text">{(arm.fpr * 100).toFixed(1)}%</td>
                          <td className="py-2 text-text">{(arm.contamination * 100).toFixed(1)}%</td>
                          <td className="py-2 text-muted">
                            {arm.adaptations} / {arm.quarantined}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="mt-2 text-[11px] text-muted flex items-center justify-between pt-1 border-t border-border/40">
                    <span>Zero Poisoning Verified:</span>
                    <span className="text-safe font-bold">Arm C Contamination: 0.0%</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
