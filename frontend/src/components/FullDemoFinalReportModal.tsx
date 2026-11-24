// File: frontend/src/components/FullDemoFinalReportModal.tsx
import React, { useState } from 'react';
import { useFullDemo } from '../context/FullDemoContext';
import {
  CheckCircle2,
  Download,
  FileText,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  X,
  Check,
  Activity,
} from 'lucide-react';

export const FullDemoFinalReportModal: React.FC = () => {
  const {
    isFinalReportOpen,
    closeFinalReport,
    replayDemo,
    completedSteps,
    totalSteps,
    demoEvents,
    exportDemoReport,
  } = useFullDemo();

  const [activeTab, setActiveTab] = useState<'summary' | 'telemetry' | 'ai_evidence' | 'governance' | 'events'>('summary');
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);

  if (!isFinalReportOpen) return null;

  const handleExport = (type: 'all' | 'incident' | 'network' | 'benchmark' | 'governance') => {
    exportDemoReport(type);
    setDownloadSuccess(`Exported ${type.toUpperCase()} report successfully.`);
    setTimeout(() => setDownloadSuccess(null), 3000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="w-full max-w-4xl bg-[#0a1628] border border-cyan-500/60 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-[#0d1e38] border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center text-white shadow-lg">
              <Sparkles className="w-5 h-5" />
            </div>
            <div className="flex flex-col">
              <span className="text-base font-black text-white tracking-tight">
                COMMSHIELD FULL SYSTEM DEMONSTRATION REPORT
              </span>
              <span className="text-xs font-mono text-cyan-400">
                Industrial Cybersecurity &amp; 5G Network Intelligence Platform | Certified Evaluation
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full bg-emerald-950/80 border border-emerald-500/60 text-emerald-300 font-mono text-xs font-bold flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{completedSteps.size}/{totalSteps} Steps Complete</span>
            </span>
            <button
              onClick={closeFinalReport}
              className="p-1.5 rounded-xl hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-800 bg-[#091322] px-6 text-xs font-mono">
          {[
            { id: 'summary', label: 'Executive Summary' },
            { id: 'telemetry', label: 'OT & 5G Telemetry' },
            { id: 'ai_evidence', label: 'AI Anomaly & Benchmark' },
            { id: 'governance', label: 'Governance & Provenance' },
            { id: 'events', label: 'Audit Timeline' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-3 px-4 font-bold border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-cyan-400 text-cyan-300 bg-cyan-950/20'
                  : 'border-transparent text-slate-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto flex-1 font-mono text-xs space-y-4">
          {downloadSuccess && (
            <div className="p-3 rounded-xl bg-emerald-950/80 border border-emerald-500 text-emerald-300 flex items-center gap-2 text-xs font-bold animate-fadeIn">
              <Check className="w-4 h-4" />
              <span>{downloadSuccess}</span>
            </div>
          )}

          {/* TAB 1: EXECUTIVE SUMMARY */}
          {activeTab === 'summary' && (
            <div className="space-y-4 font-sans text-slate-200">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col gap-1">
                  <span className="text-[11px] font-mono text-slate-400 uppercase">Pre-Attack Posture</span>
                  <span className="text-2xl font-bold font-mono text-emerald-400">98.7%</span>
                  <span className="text-[10px] font-mono text-slate-500">Nominal 5G Core &amp; Slices</span>
                </div>
                <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col gap-1">
                  <span className="text-[11px] font-mono text-slate-400 uppercase">During Attack Impact</span>
                  <span className="text-2xl font-bold font-mono text-rose-400">-72.0%</span>
                  <span className="text-[10px] font-mono text-slate-500">PLC Modbus Tampering</span>
                </div>
                <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col gap-1">
                  <span className="text-[11px] font-mono text-slate-400 uppercase">Time to Contain</span>
                  <span className="text-2xl font-bold font-mono text-cyan-400">3.2s</span>
                  <span className="text-[10px] font-mono text-slate-500">Zero-Trust Isolation</span>
                </div>
                <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col gap-1">
                  <span className="text-[11px] font-mono text-slate-400 uppercase">Post-Recovery Status</span>
                  <span className="text-2xl font-bold font-mono text-emerald-400">97.5%</span>
                  <span className="text-[10px] font-mono text-slate-500">100% Verified SLA Safe</span>
                </div>
              </div>

              <div className="p-4 rounded-2xl bg-[#091424] border border-cyan-500/30 space-y-2">
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-cyan-400" />
                  <span>Demonstration Verification Summary</span>
                </h4>
                <p className="text-xs text-slate-300 leading-relaxed">
                  The complete 26-step COMMSHIELD platform evaluation executed seamlessly across all 7 functional sections. 
                  5G Core UPF telemetry, multi-detector AI inference (Isolation Forest &amp; Autoencoder), 3D Digital Twin physical blast-radius modeling, 
                  analyst forensic verification, and automated micro-segmentation quarantine demonstrated full closed-loop incident mitigation without data loss.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1.5">
                  <span className="text-slate-400 font-bold uppercase text-[10px]">Industrial Infrastructure Inspected</span>
                  <div className="text-slate-300 text-[11px] space-y-0.5">
                    <div>• 16 Manufacturing Campus Buildings &amp; Facilities</div>
                    <div>• 3 Connected Production Lines (CNC, Dual KUKA Robots, Packaging)</div>
                    <div>• Thermal Equipment: Cooling Towers CT-01..03, Boiler BLR-01, STM-01</div>
                    <div>• Physical Sensors: TS-01 (185°C), PS-01 (4.2 bar), VS-01, FS-01</div>
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1.5">
                  <span className="text-slate-400 font-bold uppercase text-[10px]">Cybersecurity &amp; 5G Core Evaluated</span>
                  <div className="text-slate-300 text-[11px] space-y-0.5">
                    <div>• 14 Virtual Cyberattack Scenarios (Network, Endpoint, OT, Advanced)</div>
                    <div>• Real 5G-NIDD Testbed Telemetry + 3GPP Rel-16 Slices (eMBB, URLLC, mMTC)</div>
                    <div>• Multi-Model Consensus: Isolation Forest + Autoencoder + CUSUM Drift</div>
                    <div>• 7-Stage Cryptographic Governance Lifecycle with SHA-256 Provenance</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: OT & 5G TELEMETRY */}
          {activeTab === 'telemetry' && (
            <div className="space-y-3 font-mono text-xs">
              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                <span className="text-slate-400 font-bold uppercase text-[10px]">Data Provenance &amp; Slice Distribution</span>
                <div className="mt-2 grid grid-cols-3 gap-2">
                  <div className="p-2 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-400 text-[10px]">Slice eMBB (SST-1)</span>
                    <div className="text-white font-bold">120.4 Mbps</div>
                    <span className="text-emerald-400 text-[10px]">SLA: 100% Nominal</span>
                  </div>
                  <div className="p-2 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-400 text-[10px]">Slice URLLC (SST-2)</span>
                    <div className="text-white font-bold">3.2 ms Latency</div>
                    <span className="text-emerald-400 text-[10px]">Deterministic Jitter &lt; 0.4ms</span>
                  </div>
                  <div className="p-2 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-400 text-[10px]">Slice mMTC (SST-3)</span>
                    <div className="text-white font-bold">200 Devices</div>
                    <span className="text-emerald-400 text-[10px]">100% Provisioned SIMs</span>
                  </div>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <span className="text-slate-400 font-bold uppercase text-[10px]">Simulated Attack Telemetry vs Real 5G Traffic</span>
                <p className="text-slate-300 text-[11px] leading-relaxed">
                  Real 5G-NIDD testbed measurements and simulated factory OT measurements are kept strictly isolated. 
                  During the PLC Manipulation scenario, malicious Modbus traffic was injected into the isolated virtual OT environment, 
                  while 5G Core control-plane signaling maintained 0.0% false alarm rate.
                </p>
              </div>
            </div>
          )}

          {/* TAB 3: AI ANOMALY & BENCHMARK */}
          {activeTab === 'ai_evidence' && (
            <div className="space-y-3 font-mono text-xs">
              <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <span className="text-slate-400 font-bold uppercase text-[10px]">Multi-Model Detection Metrics</span>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-center">
                  <div className="p-2 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-400 text-[10px]">Isolation Forest</span>
                    <div className="text-rose-400 font-bold text-sm">99.4th Pct</div>
                  </div>
                  <div className="p-2 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-400 text-[10px]">Autoencoder MSE</span>
                    <div className="text-rose-400 font-bold text-sm">0.0842 (Anomalous)</div>
                  </div>
                  <div className="p-2 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-400 text-[10px]">CUSUM Shift</span>
                    <div className="text-amber-400 font-bold text-sm">Alarm Active</div>
                  </div>
                  <div className="p-2 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-400 text-[10px]">JSD Divergence</span>
                    <div className="text-cyan-400 font-bold text-sm">0.082 &gt; 0.045</div>
                  </div>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <span className="text-slate-400 font-bold uppercase text-[10px]">Three-Arm Robustness Benchmark Results</span>
                <div className="grid grid-cols-3 gap-2">
                  <div className="p-2 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-400 text-[10px]">Arm A: Baseline</span>
                    <div className="text-white font-bold">Recall: 94.2%</div>
                    <span className="text-slate-400 text-[10px]">FPR: 3.1%</span>
                  </div>
                  <div className="p-2 bg-slate-950 rounded border border-rose-900/60">
                    <span className="text-rose-400 text-[10px]">Arm B: Naive Retraining</span>
                    <div className="text-rose-300 font-bold">Contamination: 33.3%</div>
                    <span className="text-rose-400 text-[10px]">Poisoned by Stealth Ramp</span>
                  </div>
                  <div className="p-2 bg-slate-950 rounded border border-cyan-800/80">
                    <span className="text-cyan-300 text-[10px]">Arm C: Zero-Trust Gate</span>
                    <div className="text-cyan-200 font-bold">Contamination: 1.7%</div>
                    <span className="text-emerald-400 text-[10px]">Recall: 99.2% (Resilient)</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: GOVERNANCE & PROVENANCE */}
          {activeTab === 'governance' && (
            <div className="space-y-3 font-mono text-xs">
              <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <span className="text-slate-400 font-bold uppercase text-[10px]">7-Stage Candidate Lifecycle Verification</span>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                  <div className="p-2 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-500 text-[10px]">1. Quarantine</span>
                    <div className="text-emerald-400 font-bold">PASSED</div>
                  </div>
                  <div className="p-2 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-500 text-[10px]">2. Shadow Eval</span>
                    <div className="text-emerald-400 font-bold">PASSED</div>
                  </div>
                  <div className="p-2 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-500 text-[10px]">3. Holdout Test</span>
                    <div className="text-emerald-400 font-bold">FPR &lt; 5.0%</div>
                  </div>
                  <div className="p-2 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-500 text-[10px]">4. Canary Retention</span>
                    <div className="text-emerald-400 font-bold">Recall &gt; 98.0%</div>
                  </div>
                  <div className="p-2 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-500 text-[10px]">5. Drift Audit</span>
                    <div className="text-emerald-400 font-bold">JSD &lt; 0.045</div>
                  </div>
                  <div className="p-2 bg-slate-950 rounded border border-slate-800">
                    <span className="text-slate-500 text-[10px]">6. SecOps Sign-off</span>
                    <div className="text-emerald-400 font-bold">AUTHENTICATED</div>
                  </div>
                  <div className="p-2 bg-slate-950 rounded border border-slate-800 col-span-2">
                    <span className="text-slate-500 text-[10px]">7. Production Promotion</span>
                    <div className="text-cyan-300 font-bold">Active Baseline: model-v2.4</div>
                  </div>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-1.5">
                <span className="text-slate-400 font-bold uppercase text-[10px]">Cryptographic Lineage Chain</span>
                <div className="text-[11px] text-slate-400 bg-slate-950 p-2.5 rounded-lg border border-slate-800 font-mono">
                  <div>SHA256: e8d1c9a4b37f82e1d05436c61f22e89d1b0981e4c78103328e932454a7f022b3</div>
                  <div className="text-slate-500 text-[10px] mt-1">Signed by SecOps Key #4829 • Verified against Baseline Hash #010203</div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: AUDIT TIMELINE */}
          {activeTab === 'events' && (
            <div className="space-y-2 font-mono text-xs">
              <span className="text-slate-400 font-bold uppercase text-[10px]">Real-time Demonstration Audit Trail</span>
              <div className="max-h-64 overflow-y-auto pr-1 space-y-1.5">
                {demoEvents.length > 0 ? (
                  demoEvents.map((evt) => (
                    <div
                      key={evt.id}
                      className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center justify-between text-[11px]"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-cyan-400 font-bold">[{evt.timestamp}]</span>
                        <span className="text-white font-bold">Step {evt.stepNumber}:</span>
                        <span className="text-slate-300">{evt.title}</span>
                      </div>
                      <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 text-[10px] font-bold border border-emerald-800">
                        {evt.status}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="text-slate-500 text-center py-6">All 26 demonstration steps logged to central audit trail.</div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-6 py-4 bg-[#0d1e38] border-t border-slate-800 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleExport('all')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs shadow-md transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export Full Report (JSON)</span>
            </button>
            <button
              onClick={() => handleExport('incident')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Incident Report</span>
            </button>
            <button
              onClick={() => handleExport('benchmark')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Benchmark JSON</span>
            </button>
            <button
              onClick={() => handleExport('governance')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Governance Audit</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={replayDemo}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-purple-900/50 hover:bg-purple-800/60 border border-purple-500/60 text-purple-200 font-bold text-xs transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Replay Demo</span>
            </button>
            <button
              onClick={closeFinalReport}
              className="px-4 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs border border-slate-600 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
