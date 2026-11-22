import React from 'react';
import { CheckCircle2, Clock, Layers, X } from 'lucide-react';

interface BuiltVsPlannedModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const BuiltVsPlannedModal: React.FC<BuiltVsPlannedModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const builtFeatures = [
    {
      title: 'Real 5G-NIDD Dataset Integration',
      description: '4,351 Argus flow records across 156 60s windows and 3 network slices; mapped to 8 attack classes.',
      badge: 'Production Code',
    },
    {
      title: 'Three-Tier Graduated Governance Engine',
      description: 'Autonomous Tier 1 auto-approval (JSD < 0.020), Tier 2 review flagging, and Tier 3 quarantine with safety gate overrides.',
      badge: 'Ubuntu Verified',
    },
    {
      title: 'Four-Gate Verification Pipeline',
      description: 'Normal holdout backtest (FPR <= 5%), canary attack retention, bounded drift budget (step/anchor sigma), and JSD proportional test.',
      badge: 'Fully Enforced',
    },
    {
      title: 'Multi-Detector Anomaly Ensemble',
      description: 'Isolation Forest with calibrated tie-handling percentiles, Autoencoder reconstruction MSE, CUSUM shift detector, and consensus fusion.',
      badge: 'Calibrated',
    },
    {
      title: 'Concept Drift Attribution (ADWIN)',
      description: 'Distinguishes benign organic volume scaling from malicious attack ramps; prevents baseline poisoning.',
      badge: 'Automated',
    },
    {
      title: 'Cryptographic SHA-256 Provenance Ledger',
      description: 'Append-only hash-chained audit ledger tracking candidate creation, tier decisions, and atomic rollbacks.',
      badge: 'Tamper-Evident',
    },
    {
      title: 'Empirical Three-Arm Comparison',
      description: 'Direct measurement of Static Anchor vs Naive Retraining vs CommShield Gated on identical telemetry replay.',
      badge: 'Reproducible',
    },
    {
      title: 'Judge Demo Mode with Auto-Advance',
      description: '30-second progress bar auto-advancement, scene selector, key-event pauses, and scene skip controls.',
      badge: 'Presentation Ready',
    },
  ];

  const plannedFeatures = [
    {
      title: 'Live Open5GS + UERANSIM Testbed Execution',
      description: 'Physical SDR RF channel deployment with real UE radio emulation (current prototype utilizes 5G-NIDD and calibrated twin).',
      badge: 'Phase 2 Roadmap',
    },
    {
      title: 'Kernel-Space eBPF GTP-U Offload',
      description: 'Direct XDP/eBPF telemetry extraction inside Linux kernel UPF data plane for sub-microsecond latency.',
      badge: 'Hardware Roadmap',
    },
    {
      title: '3GPP NWDAF Standard Compliance',
      description: 'Standard Nnwdaf_AnalyticsInfo and Nnwdaf_EventsSubscription REST interfaces for commercial 5G core integration.',
      badge: 'Standards Roadmap',
    },
    {
      title: 'Multi-Operator Federated Governance',
      description: 'Cross-carrier slice consensus with threshold signatures for international roaming security.',
      badge: 'Research Roadmap',
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-card w-full max-w-4xl rounded-2xl border border-border shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-6 border-b border-border flex items-center justify-between bg-bg/50">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-teal/15 text-teal">
              <Layers className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-text">Built vs. Planned Implementation Matrix</h2>
              <p className="text-xs text-muted">
                Transparent verification matrix separating live-tested prototype capabilities from planned commercial roadmap items.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-muted hover:text-text hover:bg-slate/20 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Section 1: Fully Built */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-safe" />
              <h3 className="text-sm font-bold text-text uppercase tracking-wider">
                Fully Built & Live Verified ({builtFeatures.length} Modules)
              </h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {builtFeatures.map((f, i) => (
                <div key={i} className="p-3.5 rounded-xl border border-safe/20 bg-safe/5 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-text">{f.title}</span>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-safe/15 text-safe">
                      {f.badge}
                    </span>
                  </div>
                  <p className="text-[11px] text-muted leading-relaxed">{f.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Section 2: Planned Roadmap */}
          <div className="space-y-3 pt-4 border-t border-border">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-blue" />
              <h3 className="text-sm font-bold text-text uppercase tracking-wider">
                Planned Future Roadmap ({plannedFeatures.length} Capabilities)
              </h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {plannedFeatures.map((f, i) => (
                <div key={i} className="p-3.5 rounded-xl border border-blue/20 bg-blue/5 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-text">{f.title}</span>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-blue/15 text-blue">
                      {f.badge}
                    </span>
                  </div>
                  <p className="text-[11px] text-muted leading-relaxed">{f.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border bg-bg/50 flex justify-between items-center text-xs text-muted">
          <span>Platform: Ubuntu 24.04 LTS | Python 3.14 | FastAPI | React + Vite</span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-teal hover:bg-teal/90 text-white rounded-lg font-bold transition-colors"
          >
            Close Matrix
          </button>
        </div>
      </div>
    </div>
  );
};
// CommShield AI Core
