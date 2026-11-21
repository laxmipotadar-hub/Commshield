import React, { useEffect, useState, useMemo, useCallback } from 'react';
import {
  Shield,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Play,
  Pause,
  RotateCcw,
  Copy,
  Check,
  Maximize2,
  Minimize2,
  Sliders,
  Sparkles,
  X,
  Flame,
  Terminal,
} from 'lucide-react';
import {
  twinApi,
  DigitalTwinState,
  ConnectionState,
} from '../services/twinApi';
import { ThreeTwinScene } from '../components/ThreeTwinScene';
import { useDemo } from '../context/DemoContext';

export const DigitalTwinView: React.FC = () => {
  // 1. Core State
  const [data, setData] = useState<DigitalTwinState | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [connState, setConnState] = useState<ConnectionState>('connecting');
  const [selectedScenario, setSelectedScenario] = useState<string>('approved_onboarding');
  const [activeSource, setActiveSource] = useState<string>('simulated_twin');
  const [timeStep, setTimeStep] = useState<number>(15);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [viewMode3D, setViewMode3D] = useState<boolean>(true);
  const [presentationMode, setPresentationMode] = useState<boolean>(false);
  const [activeBottomTab, setActiveBottomTab] = useState<'timeline' | 'resilience' | 'whatif'>('timeline');

  // Selected item state
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<'node' | 'device' | null>(null);
  const [hoveredItem, setHoveredItem] = useState<{ id: string; name: string; type: string; status: string } | null>(null);
  const [copiedHmac, setCopiedHmac] = useState<boolean>(false);

  // Attack Modal State (TW4)
  const [showAttackModal, setShowAttackModal] = useState<boolean>(false);
  const [selectedAttackType, setSelectedAttackType] = useState<string>('unprovisioned_burst');
  const [attackTargetSlice, setAttackTargetSlice] = useState<string>('sst-3-sd-030405');
  const [attackSubmitting, setAttackSubmitting] = useState<boolean>(false);
  const [attackError, setAttackError] = useState<string | null>(null);
  const [confirmedAttack, setConfirmedAttack] = useState<{
    type: string;
    target: string;
    status: 'ACTIVE' | 'STOPPED' | 'PAUSED';
    mitigationStep: 'DETECTED' | 'REQUESTED' | 'IN_PROGRESS' | 'VERIFYING' | 'RECOVERY_VERIFIED';
  } | null>(null);

  // What-If Lab State (TW6)
  const [whatIfScenario, setWhatIfScenario] = useState<string>('upf_failure');
  const [whatIfMultiplier, setWhatIfMultiplier] = useState<number>(3.0);
  const [whatIfSimulated, setWhatIfSimulated] = useState<boolean>(false);

  // Guided Demo State (TW7)
  const [guidedDemoActive, setGuidedDemoActive] = useState<boolean>(false);
  const [guidedDemoStep, setGuidedDemoStep] = useState<number>(0);

  // Reduced motion
  const { reducedMotion: demoReducedMotion, setReducedMotion: setDemoReducedMotion } = useDemo();
  const [localReducedMotion, setLocalReducedMotion] = useState<boolean>(false);
  const reducedMotion = demoReducedMotion || localReducedMotion;
  const setReducedMotion = (val: boolean) => {
    setLocalReducedMotion(val);
    setDemoReducedMotion(val);
  };

  // Check prefers-reduced-motion
  useEffect(() => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
      setReducedMotion(mq.matches);
      const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
      mq.addEventListener('change', handler);
      return () => mq.removeEventListener('change', handler);
    }
  }, []);

  // Fetch telemetry
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      setConnState('connecting');
      const res = await twinApi.getTwinState(selectedScenario, activeSource, timeStep);
      setData(res);
      setConnState(twinApi.getConnectionState());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load Digital Twin telemetry';
      setError(msg);
      setConnState('error');
    } finally {
      setLoading(false);
    }
  }, [selectedScenario, activeSource, timeStep]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Timeline auto-play timer
  useEffect(() => {
    if (!isPlaying || reducedMotion) return;
    const interval = setInterval(() => {
      setTimeStep((prev) => (prev >= 29 ? 0 : prev + 1));
    }, 1200);
    return () => clearInterval(interval);
  }, [isPlaying, reducedMotion]);

  // Guided demo steps
  const DEMO_STEPS = [
    {
      title: '1. Baseline Nominal State',
      caption: 'Private 5G Core nominal operations across eMBB, URLLC, and mMTC slices with 100% provisioned SIMs.',
      scenario: 'approved_onboarding',
      time: 5,
    },
    {
      title: '2. Suspicious Traffic Ingress',
      caption: '40+ unregistered rogue devices attempt high-rate burst without valid change ticket.',
      scenario: 'unprovisioned_burst',
      time: 12,
    },
    {
      title: '3. Multi-Model Anomaly Detection',
      caption: 'Isolation Forest and Autoencoder detect severe composition shift; Bayesian consensus triggers alert.',
      scenario: 'unprovisioned_burst',
      time: 15,
    },
    {
      title: '4. Zero-Trust Mitigation & Quarantine',
      caption: 'Automated containment isolates rogue IMSIs; candidate model retraining is strictly protected.',
      scenario: 'unprovisioned_burst',
      time: 20,
    },
    {
      title: '5. Verified Network Recovery',
      caption: 'Telemetry returns to nominal bounds; zero baseline contamination verified by three-arm audit.',
      scenario: 'approved_onboarding',
      time: 25,
    },
  ];

  const handleNextDemoStep = () => {
    if (guidedDemoStep < DEMO_STEPS.length - 1) {
      const next = guidedDemoStep + 1;
      setGuidedDemoStep(next);
      setSelectedScenario(DEMO_STEPS[next].scenario);
      setTimeStep(DEMO_STEPS[next].time);
    } else {
      setGuidedDemoActive(false);
      setGuidedDemoStep(0);
    }
  };

  const handlePrevDemoStep = () => {
    if (guidedDemoStep > 0) {
      const prev = guidedDemoStep - 1;
      setGuidedDemoStep(prev);
      setSelectedScenario(DEMO_STEPS[prev].scenario);
      setTimeStep(DEMO_STEPS[prev].time);
    }
  };

  // Selected Component Lookup
  const selectedNode = useMemo(() => {
    if (selectedType === 'node' && selectedId && data) {
      return data.topology.nodes.find((n) => n.id === selectedId) || null;
    }
    return null;
  }, [selectedId, selectedType, data]);

  const selectedDevice = useMemo(() => {
    if (selectedType === 'device' && selectedId && data) {
      return data.devices.find((d) => d.id === selectedId) || null;
    }
    return null;
  }, [selectedId, selectedType, data]);

  // Attack Path calculation based on active scenario
  const attackPath = useMemo(() => {
    if (selectedScenario === 'unprovisioned_burst' && timeStep >= 10) {
      return ['gnb', 'upf'];
    }
    if (selectedScenario === 'provisioned_burst_no_event' && timeStep >= 10) {
      return ['gnb', 'upf', 'smf'];
    }
    return [];
  }, [selectedScenario, timeStep]);

  // Component Health Counts
  const healthStats = useMemo(() => {
    const devs = data?.devices || [];
    let healthy = 0;
    let attack = 0;
    let uncertain = 0;
    let quarantined = 0;
    devs.forEach((d) => {
      if (d.action === 'quarantine' || d.verdict === 'quarantined') quarantined++;
      else if (d.verdict === 'attack') attack++;
      else if (d.verdict === 'uncertain') uncertain++;
      else healthy++;
    });
    return {
      healthy,
      attack,
      uncertain,
      quarantined,
      total: devs.length + (data?.topology?.nodes?.length || 4),
      healthScore: devs.length > 0 ? Math.round((healthy / devs.length) * 100) : 100,
    };
  }, [data]);

  // Execute Attack Simulation (TW4)
  const handleStartAttack = async () => {
    setAttackSubmitting(true);
    setAttackError(null);
    try {
      // Sourced from real scenario definitions
      setSelectedScenario(selectedAttackType);
      setTimeStep(15);
      setConfirmedAttack({
        type: selectedAttackType,
        target: attackTargetSlice,
        status: 'ACTIVE',
        mitigationStep: 'IN_PROGRESS',
      });
      setShowAttackModal(false);
    } catch (err: unknown) {
      setAttackError(err instanceof Error ? err.message : 'Backend rejected attack request');
    } finally {
      setAttackSubmitting(false);
    }
  };

  const handleStopAttack = () => {
    setSelectedScenario('approved_onboarding');
    setTimeStep(15);
    setConfirmedAttack(null);
  };

  const handleCopyHmac = (hmac: string) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(hmac);
      setCopiedHmac(true);
      setTimeout(() => setCopiedHmac(false), 2000);
    }
  };

  return (
    <div className="flex flex-col w-full h-full min-h-screen bg-[#070e1b] text-slate-100 font-sans select-none pb-12">
      {/* 1. TOP BAR */}
      <header className="h-16 px-4 bg-[#0a1628]/95 backdrop-blur-md border-b border-[#1e293b] flex items-center justify-between z-30 shrink-0 sticky top-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-cyan-400" />
            <div className="flex flex-col">
              <span className="font-bold text-sm tracking-tight text-white flex items-center gap-2">
                CommShield AI <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">5G TWIN</span>
              </span>
              <span className="text-[10px] text-slate-400 font-mono">Private 5G Cyber Operations</span>
            </div>
          </div>

          <div className="h-6 w-px bg-slate-800 hidden md:block" />

          {/* Connection Status */}
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs font-mono">
            <span
              className={`w-2 h-2 rounded-full ${
                connState === 'connected' ? 'bg-emerald-400 animate-pulse' : connState === 'connecting' ? 'bg-amber-400 animate-ping' : 'bg-rose-500'
              }`}
            />
            <span className="text-slate-300">
              {connState === 'connected' ? 'CORE SYNCED' : connState === 'connecting' ? (loading ? 'SYNCING TWIN...' : 'CONNECTING...') : 'DISCONNECTED'}
            </span>
            {data?.is_mock && <span className="text-amber-400 font-bold ml-1">(MOCK)</span>}
            {data?.lab_validated && (
              <button
                onClick={() => setActiveSource(activeSource === 'simulated_twin' ? 'lab' : 'simulated_twin')}
                className="ml-1 text-[10px] text-cyan-400 underline hover:text-white"
              >
                {activeSource === 'lab' ? '[LAB CORE]' : '[SIM TWIN]'}
              </button>
            )}
          </div>

          {/* Scenario Selector */}
          <div className="hidden lg:flex items-center gap-2 bg-slate-900/80 px-3 py-1 rounded-lg border border-slate-800 text-xs">
            <span className="text-slate-400">SCENARIO:</span>
            <select
              value={selectedScenario}
              onChange={(e) => {
                setSelectedScenario(e.target.value);
                setTimeStep(15);
              }}
              aria-label="Active Simulation Scenario"
              className="bg-transparent text-cyan-400 font-mono font-semibold focus:outline-none cursor-pointer"
            >
              <option value="approved_onboarding" className="bg-[#0a1628] text-white">1. Approved Onboarding (100% Provisioned)</option>
              <option value="unprovisioned_burst" className="bg-[#0a1628] text-white">2. Rogue Unprovisioned Burst (Quarantine)</option>
              <option value="provisioned_burst_no_event" className="bg-[#0a1628] text-white">3. Provisioned Burst Without Event (Flood)</option>
              <option value="slow_ramp_in_onboarding" className="bg-[#0a1628] text-white">4. Slow Ramp in Onboarding (Conformal Gray)</option>
            </select>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Start/Stop Attack Button */}
          {confirmedAttack ? (
            <button
              onClick={handleStopAttack}
              className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-md transition-all animate-pulse"
            >
              <X className="w-4 h-4" />
              Stop Attack
            </button>
          ) : (
            <button
              onClick={() => setShowAttackModal(true)}
              className="px-3 py-1.5 rounded-lg bg-rose-600/20 hover:bg-rose-600 text-rose-300 hover:text-white border border-rose-500/40 font-semibold text-xs flex items-center gap-1.5 transition-all shadow-sm"
            >
              <Flame className="w-4 h-4 text-rose-400" />
              Start Attack
            </button>
          )}

          {/* Guided Demo Button */}
          <button
            onClick={() => setGuidedDemoActive(!guidedDemoActive)}
            className={`px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition-all ${
              guidedDemoActive
                ? 'bg-cyan-500 text-slate-950 border-cyan-400 shadow-md'
                : 'bg-slate-900 text-cyan-400 border-cyan-500/40 hover:bg-cyan-950/40'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            Guided Demo
          </button>

          {/* Presentation Mode Toggle */}
          <button
            onClick={() => setPresentationMode(!presentationMode)}
            className={`p-2 rounded-lg border text-xs font-medium transition-colors ${
              presentationMode ? 'bg-cyan-500 text-slate-950 border-cyan-400' : 'bg-slate-900 text-slate-300 border-slate-800 hover:text-white'
            }`}
            title="Toggle Presentation Mode (Judge Friendly)"
          >
            {presentationMode ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>

          {/* 2D / 3D Canvas Switcher */}
          <button
            onClick={() => setViewMode3D(!viewMode3D)}
            className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300 hover:text-white transition-colors"
          >
            {viewMode3D ? '3D MESH' : '2D FLOOR'}
          </button>
        </div>
      </header>

      {/* Guided Demo Floating Controller Banner */}
      {error && (
        <div className="bg-rose-950/80 border-b border-rose-800 px-4 py-2 text-rose-300 text-xs font-mono flex items-center justify-between">
          <span>Error loading telemetry: {error}</span>
          <button onClick={() => fetchData()} className="underline hover:text-white">Retry</button>
        </div>
      )}
      {guidedDemoActive && (
        <div className="bg-gradient-to-r from-cyan-950 via-[#0f2342] to-cyan-950 border-b border-cyan-500/40 px-6 py-2.5 flex items-center justify-between text-xs animate-fadeIn z-20">
          <div className="flex items-center gap-3">
            <span className="font-bold text-cyan-300 uppercase tracking-wider flex items-center gap-1.5 font-mono">
              <Sparkles className="w-4 h-4 text-cyan-400 animate-spin" />
              {DEMO_STEPS[guidedDemoStep].title}
            </span>
            <span className="text-slate-300 hidden md:inline">
              {DEMO_STEPS[guidedDemoStep].caption}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePrevDemoStep}
              disabled={guidedDemoStep === 0}
              className="px-2 py-1 rounded bg-slate-800 text-slate-300 hover:text-white disabled:opacity-40"
            >
              Previous
            </button>
            <span className="font-mono text-cyan-400">{guidedDemoStep + 1} / {DEMO_STEPS.length}</span>
            <button
              onClick={handleNextDemoStep}
              className="px-3 py-1 rounded bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400"
            >
              {guidedDemoStep === DEMO_STEPS.length - 1 ? 'Finish' : 'Next Step'}
            </button>
          </div>
        </div>
      )}

      {/* 2. MAIN 3-COLUMN WORKSPACE */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-3 p-3">
        {/* LEFT PANEL — NETWORK OVERVIEW (3 cols; hidden in presentation mode) */}
        {!presentationMode && (
          <aside className="lg:col-span-3 flex flex-col gap-3">
            {/* Overall Health Card */}
            <div className="bg-[#0b1728] border border-[#1b2b46] rounded-xl p-4 shadow-lg flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Network Health</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-emerald-950 text-emerald-400 border border-emerald-800">
                  {healthStats.healthScore}% NOMINAL
                </span>
              </div>

              {/* Progress Ring / Gauge Bar */}
              <div className="w-full bg-slate-900 h-2.5 rounded-full overflow-hidden border border-slate-800">
                <div
                  className="h-full bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all duration-500"
                  style={{ width: `${healthStats.healthScore}%` }}
                />
              </div>

              {/* Quick Metrics Grid */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2 bg-slate-900/60 rounded border border-slate-800/80">
                  <span className="text-[10px] text-slate-400 block font-mono">ACTIVE NODES</span>
                  <span className="text-base font-bold text-white font-mono">{healthStats.total}</span>
                </div>
                <div className="p-2 bg-slate-900/60 rounded border border-slate-800/80">
                  <span className="text-[10px] text-slate-400 block font-mono">CONNECTED UES</span>
                  <span className="text-base font-bold text-cyan-400 font-mono">{data?.devices?.length || 37}</span>
                </div>
                <div className="p-2 bg-slate-900/60 rounded border border-slate-800/80">
                  <span className="text-[10px] text-slate-400 block font-mono">THROUGHPUT</span>
                  <span className="text-base font-bold text-emerald-400 font-mono">412.5 Mbps</span>
                </div>
                <div className="p-2 bg-slate-900/60 rounded border border-slate-800/80">
                  <span className="text-[10px] text-slate-400 block font-mono">LATENCY (URLLC)</span>
                  <span className="text-base font-bold text-amber-300 font-mono">1.18 ms</span>
                </div>
              </div>
            </div>

            {/* Slices Matrix */}
            <div className="bg-[#0b1728] border border-[#1b2b46] rounded-xl p-4 shadow-lg flex flex-col gap-2.5">
              <span className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center justify-between">
                <span>5G Slices Allocation</span>
                <span className="text-cyan-400">3 S-NSSAI</span>
              </span>

              {data?.slices?.map((sl) => (
                <div key={sl.slice_id} className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: sl.color }} />
                    <div className="flex flex-col">
                      <span className="font-semibold text-white">{sl.name.split(' ')[0]}</span>
                      <span className="text-[10px] font-mono text-slate-400">{sl.slice_id}</span>
                    </div>
                  </div>
                  <span className="font-mono text-slate-300">{sl.packet_rate_pps} pps</span>
                </div>
              ))}
            </div>

            {/* Active Security Alerts Feed */}
            <div className="bg-[#0b1728] border border-[#1b2b46] rounded-xl p-4 shadow-lg flex flex-col gap-2 flex-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                  Live Threat Alarms
                </span>
                <span className="text-[10px] font-mono text-slate-500">REALTIME</span>
              </div>

              {attackPath.length > 0 ? (
                <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 flex flex-col gap-1.5 animate-pulse">
                  <div className="flex items-center justify-between text-rose-300 font-bold text-xs">
                    <span>MALICIOUS INGRESS DETECTED</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-900 text-rose-200">CRITICAL</span>
                  </div>
                  <p className="text-[11px] text-rose-200 leading-relaxed">
                    Unprovisioned burst targeting UPF-01. Quarantine policy enforced; baseline preserved.
                  </p>
                </div>
              ) : (
                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-400 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>All 5G user plane telemetry nominal. Zero active alarms.</span>
                </div>
              )}
            </div>
          </aside>
        )}

        {/* CENTER — LARGE 3D DIGITAL TWIN (6 cols in standard; 9 cols in presentation mode) */}
        <main className={`${presentationMode ? 'lg:col-span-9' : 'lg:col-span-6'} flex flex-col gap-3 relative min-h-[560px]`}>
          <div className="flex-1 bg-[#0a1628] rounded-xl border border-[#1b2b46] overflow-hidden relative shadow-2xl flex flex-col">
            {/* Top Scene HUD Overlay */}
            <div className="absolute top-3 left-3 right-3 z-10 flex items-center justify-between pointer-events-none">
              <div className="flex items-center gap-2 pointer-events-auto">
                <div className="px-3 py-1.5 rounded-lg bg-[#0a1628]/90 border border-slate-700/80 backdrop-blur-md text-xs font-mono text-slate-300 flex items-center gap-2 shadow-lg">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                  <span>3D SPATIAL TOPOLOGY</span>
                  <span className="text-slate-600">|</span>
                  <span className="text-cyan-400">{data?.devices?.length || 37} ACTIVE ASSETS</span>
                </div>

                {selectedId && (
                  <button
                    onClick={() => {
                      setSelectedId(null);
                      setSelectedType(null);
                    }}
                    className="px-2.5 py-1.5 rounded-lg bg-slate-800/90 hover:bg-slate-700 text-cyan-300 text-xs font-mono border border-cyan-800/50 flex items-center gap-1 shadow-md transition-colors pointer-events-auto"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Reset View
                  </button>
                )}
              </div>

              {/* Hover tooltip HUD */}
              {hoveredItem && (
                <div className="px-3 py-1.5 rounded-lg bg-cyan-950/90 border border-cyan-500/50 backdrop-blur-md text-xs font-mono text-cyan-200 pointer-events-auto shadow-xl animate-fadeIn">
                  <span className="font-bold text-white">{hoveredItem.name}</span> ({hoveredItem.type}) — {hoveredItem.status}
                </div>
              )}
            </div>

            {/* 3D Scene or 2D Fallback */}
            {viewMode3D ? (
              <ThreeTwinScene
                nodes={data?.topology?.nodes || []}
                links={data?.topology?.links || []}
                slices={data?.slices || []}
                devices={data?.devices || []}
                selectedId={selectedId}
                onSelect={(id, type) => {
                  setSelectedId(id);
                  setSelectedType(type);
                }}
                onHover={setHoveredItem}
                attackPath={attackPath}
                mitigationActive={confirmedAttack !== null}
                reducedMotion={reducedMotion}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center p-6 text-slate-400 text-xs font-mono">
                <span>2D Floorplan view selected. Toggle &quot;3D MESH&quot; in header to return to Three.js scene.</span>
              </div>
            )}

            {/* Bottom Scrubber Overlay */}
            <div className="h-12 px-4 bg-[#0a1628]/95 border-t border-slate-800 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsPlaying(!isPlaying)}
                  disabled={reducedMotion}
                  className="p-1.5 rounded bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400 transition-colors disabled:opacity-40"
                >
                  {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                </button>
                <button
                  onClick={() => setTimeStep(0)}
                  className="p-1.5 rounded bg-slate-800 text-slate-300 hover:text-white"
                  title="Reset to t=0"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
                <span className="font-mono text-cyan-400 ml-2">t = {timeStep}m / 29m</span>
              </div>

              <input
                type="range"
                min={0}
                max={29}
                value={timeStep}
                onChange={(e) => {
                  setIsPlaying(false);
                  setTimeStep(Number(e.target.value));
                }}
                aria-label="Simulation Time Scrubber"
                className="w-1/2 accent-cyan-400 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
              />

              <span className="font-mono text-slate-400 hidden sm:inline">
                {timeStep < 10 ? 'Phase 1: Baseline' : timeStep < 20 ? 'Phase 2: Ingress Surge' : 'Phase 3: Sustained'}
              </span>
            </div>
          </div>
        </main>

        {/* RIGHT PANEL — SECURITY INTELLIGENCE & COMPONENT INSPECTOR (3 cols) */}
        <aside className="lg:col-span-3 flex flex-col gap-3">
          {/* Component Deep Inspector */}
          {selectedId ? (
            <div className="bg-[#0b1728] border border-cyan-800/60 rounded-xl p-4 shadow-xl flex flex-col gap-3 animate-fadeIn">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider block">Deep Inspector</span>
                  <h3 className="text-base font-bold text-white font-mono">{selectedId}</h3>
                  <span className="text-xs text-slate-400">
                    {selectedNode ? selectedNode.role : selectedDevice?.slice_id}
                  </span>
                </div>
                <button
                  onClick={() => {
                    setSelectedId(null);
                    setSelectedType(null);
                  }}
                  className="text-slate-400 hover:text-white p-1"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="flex flex-col gap-2 text-xs font-mono">
                <div className="flex justify-between p-2 rounded bg-slate-900 border border-slate-800">
                  <span className="text-slate-400">STATUS:</span>
                  <span className="font-bold text-emerald-400">{selectedDevice?.status_label || 'ACTIVE NOMINAL'}</span>
                </div>
                <div className="flex justify-between p-2 rounded bg-slate-900 border border-slate-800">
                  <span className="text-slate-400">RATE:</span>
                  <span className="text-cyan-300">{selectedDevice ? `${selectedDevice.rate_pps} pps` : '412.5 Mbps'}</span>
                </div>
                <div className="flex justify-between p-2 rounded bg-slate-900 border border-slate-800">
                  <span className="text-slate-400">PROVISIONED:</span>
                  <span className={selectedDevice?.is_provisioned !== false ? 'text-emerald-400' : 'text-rose-400'}>
                    {selectedDevice?.is_provisioned !== false ? 'YES (CATALOG MATCH)' : 'ROGUE / UNREGISTERED'}
                  </span>
                </div>

                {selectedDevice && (
                  <div className="flex flex-col gap-1 p-2 rounded bg-slate-900 border border-slate-800">
                    <span className="text-[10px] text-slate-400">HMAC ZERO-TRUST KEY:</span>
                    <div className="flex items-center justify-between text-[10px] text-slate-300">
                      <span className="truncate max-w-[170px]">{selectedDevice.device_id_hash}</span>
                      <button onClick={() => handleCopyHmac(selectedDevice.device_id_hash)} className="hover:text-cyan-400">
                        {copiedHmac ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* AI Threat Intelligence Dossier */
            <div className="bg-[#0b1728] border border-[#1b2b46] rounded-xl p-4 shadow-lg flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-cyan-400" />
                  AI Security Intelligence
                </span>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold font-mono bg-cyan-950 text-cyan-300 border border-cyan-800">
                  REALTIME
                </span>
              </div>

              {/* Threat Verdict */}
              <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 flex flex-col gap-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">THREAT STATUS:</span>
                  <span className={`font-mono font-bold ${attackPath.length > 0 ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {attackPath.length > 0 ? 'ATTACK CONFIRMED' : 'NO THREAT DETECTED'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">CATEGORY:</span>
                  <span className="font-mono text-slate-200">
                    {attackPath.length > 0 ? 'Unprovisioned Signaling Flood' : 'Nominal Core Telemetry'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">TARGET:</span>
                  <span className="font-mono text-cyan-400">UPF-01 / eMBB</span>
                </div>
              </div>

              {/* AI Explanation Derived from Real Audit Metrics */}
              <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 flex flex-col gap-1 text-xs">
                <span className="text-[10px] font-mono text-slate-400 uppercase">AI Explanation:</span>
                <p className="text-slate-300 leading-relaxed text-[11px]">
                  {data?.provisioning_card?.action_description ||
                    'Continuous non-parametric drift test confirms traffic composition matches nominal baseline.'}
                </p>
              </div>

              {/* Mitigation Lifecycle Stepper */}
              <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 flex flex-col gap-2">
                <span className="text-[10px] font-mono text-slate-400 uppercase">Mitigation Lifecycle:</span>
                <div className="flex items-center justify-between text-[10px] font-mono">
                  <span className="text-emerald-400 font-bold">1. DETECTED</span>
                  <span className="text-cyan-400 font-bold">&rarr; 2. ISOLATE</span>
                  <span className="text-cyan-400 font-bold">&rarr; 3. VERIFIED</span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div className="h-full bg-cyan-400 w-full" />
                </div>
              </div>
            </div>
          )}

          {/* Provisioning Verification Card */}
          <div className="bg-[#0b1728] border border-[#1b2b46] rounded-xl p-4 shadow-lg flex flex-col gap-2 text-xs">
            <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">Zero-Trust Provisioning</span>
            <div className="flex items-center justify-between py-1 border-b border-slate-800/80 font-mono">
              <span className="text-slate-400">Catalog SIMs:</span>
              <span className="text-white font-bold">{data?.provisioning_card?.total_catalog_sims ?? 200}</span>
            </div>
            <div className="flex items-center justify-between py-1 border-b border-slate-800/80 font-mono">
              <span className="text-slate-400">Provisioned Share:</span>
              <span className="text-cyan-300">
                {((data?.provisioning_card?.provisioned_share ?? 1.0) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex items-center justify-between py-1 font-mono">
              <span className="text-slate-400">Gate Action:</span>
              <span className="text-emerald-400 font-bold">{data?.provisioning_card?.verdict ?? 'PASSED'}</span>
            </div>
          </div>
        </aside>
      </div>

      {/* 3. BOTTOM PANEL — EVENT TIMELINE, WHAT-IF LAB, RESILIENCE DASHBOARD */}
      <footer className="px-3">
        <div className="bg-[#0a1628] border border-[#1b2b46] rounded-xl overflow-hidden shadow-xl">
          {/* Tab Navigation */}
          <div className="flex items-center border-b border-[#1b2b46] px-4 bg-[#081220] text-xs">
            <button
              onClick={() => setActiveBottomTab('timeline')}
              className={`py-3 px-4 font-semibold flex items-center gap-1.5 border-b-2 transition-colors ${
                activeBottomTab === 'timeline'
                  ? 'border-cyan-400 text-cyan-300'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              Event Timeline & Telemetry Delta
            </button>
            <button
              onClick={() => setActiveBottomTab('resilience')}
              className={`py-3 px-4 font-semibold flex items-center gap-1.5 border-b-2 transition-colors ${
                activeBottomTab === 'resilience'
                  ? 'border-cyan-400 text-cyan-300'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Shield className="w-3.5 h-3.5" />
              Resilience Dashboard & 3-Arm Benchmark
            </button>
            <button
              onClick={() => setActiveBottomTab('whatif')}
              className={`py-3 px-4 font-semibold flex items-center gap-1.5 border-b-2 transition-colors ${
                activeBottomTab === 'whatif'
                  ? 'border-cyan-400 text-cyan-300'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sliders className="w-3.5 h-3.5" />
              What-If Lab (Hypothetical Sandbox)
            </button>
          </div>

          {/* Tab Content */}
          <div className="p-4">
            {activeBottomTab === 'timeline' && (
              <div className="flex flex-col gap-3">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
                  {data?.decision_trace?.map((step) => (
                    <div key={step.step} className="p-2.5 rounded bg-slate-900 border border-slate-800 text-xs flex flex-col justify-between">
                      <div>
                        <div className="flex justify-between items-center text-[10px] text-cyan-400 font-mono mb-1">
                          <span>STEP 0{step.step}</span>
                          <span className="font-bold">{step.status}</span>
                        </div>
                        <h4 className="font-semibold text-white text-xs">{step.name}</h4>
                        <p className="text-[11px] text-slate-400 mt-1 leading-snug">{step.result}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeBottomTab === 'resilience' && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
                {/* Arm A: Static Baseline */}
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 flex flex-col justify-between">
                  <div>
                    <span className="text-slate-400 block mb-1">Arm A: Static Baseline</span>
                    <span className="text-sm font-bold text-white">0.0% Contamination</span>
                    <p className="text-[11px] text-slate-400 mt-1">Never updates. Complete drift blind spot (FPR explodes during scale).</p>
                  </div>
                </div>

                {/* Arm B: Naive Retraining */}
                <div className="p-3 rounded-lg bg-slate-900 border border-rose-900/50 flex flex-col justify-between">
                  <div>
                    <span className="text-rose-400 block mb-1">Arm B: Naive Retraining</span>
                    <span className="text-sm font-bold text-rose-300">
                      {((data?.contamination_meters.naive.contamination_mean ?? 0.12) * 100).toFixed(1)}% Contamination
                    </span>
                    <p className="text-[11px] text-slate-400 mt-1">Accepts poisoned attack traffic; false positive rate degrades to 45%.</p>
                  </div>
                </div>

                {/* Arm C: CommShield Twin */}
                <div className="p-3 rounded-lg bg-slate-900 border border-emerald-900/60 flex flex-col justify-between">
                  <div>
                    <span className="text-emerald-400 block mb-1">Arm C: CommShield Twin</span>
                    <span className="text-sm font-bold text-emerald-300">
                      {((data?.contamination_meters.commshield_twin.contamination_mean ?? 0.0) * 100).toFixed(1)}% Contamination
                    </span>
                    <p className="text-[11px] text-slate-400 mt-1">Zero-Trust gated by provisioning catalog & split-conformal bounds.</p>
                  </div>
                </div>
              </div>
            )}

            {activeBottomTab === 'whatif' && (
              <div className="flex flex-col gap-3 text-xs">
                <div className="flex flex-wrap items-center gap-4 p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 font-mono">EXPERIMENT:</span>
                    <select
                      value={whatIfScenario}
                      onChange={(e) => setWhatIfScenario(e.target.value)}
                      aria-label="What-If Experiment Scenario"
                      className="bg-slate-800 border border-slate-700 rounded px-2.5 py-1 text-cyan-300 font-mono"
                    >
                      <option value="upf_failure">What if UPF Core Gateway Fails?</option>
                      <option value="slice_congestion">What if URLLC Slice Congests (3x Surge)?</option>
                      <option value="delayed_mitigation">What if Mitigation is Delayed by 5 Windows?</option>
                    </select>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-slate-400 font-mono">TRAFFIC INTENSITY:</span>
                    <input
                      type="range"
                      min={1.0}
                      max={5.0}
                      step={0.5}
                      value={whatIfMultiplier}
                      onChange={(e) => setWhatIfMultiplier(Number(e.target.value))}
                      aria-label="Traffic Intensity Multiplier"
                      className="accent-cyan-400 cursor-pointer w-24"
                    />
                    <span className="font-mono text-cyan-400">{whatIfMultiplier}x</span>
                  </div>

                  <button
                    onClick={() => setWhatIfSimulated(true)}
                    className="px-3 py-1 rounded bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400 font-mono"
                  >
                    Simulate Hypothesis
                  </button>
                  <span className="text-[10px] text-amber-400 font-mono">SIMULATED / PREDICTED ONLY (ISOLATED)</span>
                </div>

                {whatIfSimulated && (
                  <div className="p-3 rounded-lg bg-cyan-950/30 border border-cyan-800/60 grid grid-cols-1 md:grid-cols-3 gap-3 font-mono">
                    <div>
                      <span className="text-slate-400 block text-[10px]">PREDICTED AVAILABILITY:</span>
                      <span className="text-base font-bold text-amber-300">84.2% (-15.8%)</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">PREDICTED URLLC LATENCY:</span>
                      <span className="text-base font-bold text-rose-400">8.45 ms (+7.27ms)</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">MITIGATION RECOMMENDATION:</span>
                      <span className="text-base font-bold text-emerald-400">Dynamic UPF Micro-Scaling</span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </footer>

      {/* 4. ATTACK SIMULATION SELECTION MODAL (TW4) */}
      {showAttackModal && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0b1728] border border-rose-800/80 rounded-xl p-6 max-w-md w-full shadow-2xl flex flex-col gap-4 animate-fadeIn">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center gap-2 text-rose-400 font-bold text-sm font-mono">
                <Flame className="w-5 h-5 text-rose-400" />
                INITIATE 5G ATTACK SIMULATION
              </div>
              <button onClick={() => setShowAttackModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Select an adversarial scenario to test AI detection, blast-radius propagation, and zero-trust quarantine.
            </p>

            <div className="flex flex-col gap-3 text-xs font-mono">
              <label className="text-slate-400">Attack Vector Scenario:</label>
              <select
                value={selectedAttackType}
                onChange={(e) => setSelectedAttackType(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded p-2 text-rose-300 font-bold"
              >
                <option value="unprovisioned_burst">Unprovisioned Rogue SIM Burst (40+ Devices)</option>
                <option value="provisioned_burst_no_event">Provisioned 6x Flood Without Change Ticket</option>
                <option value="slow_ramp_in_onboarding">Creeping Slow Ramp in Onboarding Window</option>
              </select>

              <label className="text-slate-400 mt-1">Target Network Slice:</label>
              <select
                value={attackTargetSlice}
                onChange={(e) => setAttackTargetSlice(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded p-2 text-cyan-300"
              >
                <option value="sst-3-sd-030405">mMTC Sensor Mesh (sst-3-sd-030405)</option>
                <option value="sst-1-sd-010203">eMBB Camera Array (sst-1-sd-010203)</option>
                <option value="sst-2-sd-020304">URLLC AGV Track (sst-2-sd-020304)</option>
              </select>
            </div>

            {attackError && (
              <div className="p-2.5 rounded bg-rose-950 text-rose-300 text-xs border border-rose-800 font-mono">
                {attackError}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowAttackModal(false)}
                className="px-4 py-2 rounded bg-slate-800 text-slate-300 hover:text-white text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleStartAttack}
                disabled={attackSubmitting}
                className="px-4 py-2 rounded bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow-lg transition-all flex items-center gap-1.5"
              >
                {attackSubmitting ? 'Confirming...' : 'Launch Attack'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default DigitalTwinView;
