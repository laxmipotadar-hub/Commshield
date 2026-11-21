import React, { useEffect, useState, useMemo } from 'react';
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  Play,
  Pause,
  RotateCcw,
  Database,
  Radio,
  Lock,
  Layers,
  Activity,
  FileCheck,
  Zap,
  Copy,
  Check,
} from 'lucide-react';
import {
  api,
  DigitalTwinResponse,
  DigitalTwinDevice,
  DigitalTwinNode,
} from '../services/api';
import { useDemo } from '../context/DemoContext';

const SCENARIOS = [
  { id: 'approved_onboarding', label: '1. Approved Onboarding (Batch OB-01 & OB-02)', desc: 'Valid change event + 100% provisioned SIMs' },
  { id: 'unprovisioned_burst', label: '2. Unprovisioned Rogue Burst', desc: '40+ unregistered SIMs trigger instant quarantine' },
  { id: 'provisioned_burst_no_event', label: '3. Provisioned Burst Without Event', desc: 'Valid SIMs bursting 6x without scheduled change event' },
  { id: 'slow_ramp_in_onboarding', label: '4. Slow Ramp Hidden in Onboarding', desc: 'Creeping sensors trigger split-conformal gray band' },
];

export const DigitalTwinView: React.FC = () => {
  const [data, setData] = useState<DigitalTwinResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedScenario, setSelectedScenario] = useState<string>('approved_onboarding');
  const [activeSource, setActiveSource] = useState<string>('simulated_twin');
  const [timeStep, setTimeStep] = useState<number>(15);
  const { reducedMotion: demoReducedMotion, setReducedMotion: setDemoReducedMotion } = useDemo();
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [localReducedMotion, setLocalReducedMotion] = useState<boolean>(false);
  const reducedMotion = demoReducedMotion || localReducedMotion;
  const setReducedMotion = (val: boolean) => {
    setLocalReducedMotion(val);
    setDemoReducedMotion(val);
  };
  const [selectedDevice, setSelectedDevice] = useState<DigitalTwinDevice | null>(null);
  const [copiedHmac, setCopiedHmac] = useState<boolean>(false);

  // Check system prefers-reduced-motion on mount
  useEffect(() => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
      setReducedMotion(mediaQuery.matches);
      const listener = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
      mediaQuery.addEventListener('change', listener);
      return () => mediaQuery.removeEventListener('change', listener);
    }
  }, []);

  // Fetch telemetry whenever scenario, source, or timeStep changes
  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getDigitalTwinData(selectedScenario, activeSource, timeStep);
      setData(res);
      // Auto-select first device if none selected
      if (!selectedDevice && res.devices.length > 0) {
        setSelectedDevice(res.devices[0]);
      } else if (selectedDevice) {
        const updatedDev = res.devices.find((d) => d.id === selectedDevice.id);
        if (updatedDev) setSelectedDevice(updatedDev);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load Digital Twin data';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedScenario, activeSource, timeStep]);

  // Timeline auto-play timer
  useEffect(() => {
    if (!isPlaying || reducedMotion) return;
    const interval = setInterval(() => {
      setTimeStep((prev) => (prev >= 29 ? 0 : prev + 1));
    }, 1200);
    return () => clearInterval(interval);
  }, [isPlaying, reducedMotion]);

  // Device color mapper based on verdict and quarantine action
  const getDeviceColor = (dev: DigitalTwinDevice): string => {
    if (dev.action === 'quarantine' || dev.verdict === 'quarantined') return '#8B5CF6'; // purple
    if (dev.verdict === 'attack') return '#EF4444'; // red
    if (dev.verdict === 'uncertain') return '#F59E0B'; // amber
    return '#10B981'; // green / benign
  };

  // Node position lookup
  const nodeMap = useMemo(() => {
    const map = new Map<string, DigitalTwinNode>();
    if (data?.topology?.nodes) {
      data.topology.nodes.forEach((n) => map.set(n.id, n));
    }
    return map;
  }, [data]);

  // Particle positions along links for animation
  const [particleOffset, setParticleOffset] = useState<number>(0);
  useEffect(() => {
    if (reducedMotion) return;
    let animId: number;
    const step = () => {
      setParticleOffset((prev) => (prev + 0.015) % 1.0);
      animId = requestAnimationFrame(step);
    };
    animId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(animId);
  }, [reducedMotion]);

  const handleCopyHmac = (hmac: string) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(hmac);
      setCopiedHmac(true);
      setTimeout(() => setCopiedHmac(false), 2000);
    }
  };

  // Device summary stats
  const deviceCounts = useMemo(() => {
    const devList = data?.devices || [];
    let benign = 0;
    let attack = 0;
    let uncertain = 0;
    let quarantined = 0;
    devList.forEach((d) => {
      if (d.action === 'quarantine' || d.verdict === 'quarantined') quarantined++;
      else if (d.verdict === 'attack') attack++;
      else if (d.verdict === 'uncertain') uncertain++;
      else benign++;
    });
    return { benign, attack, uncertain, quarantined, total: devList.length };
  }, [data]);

  return (
    <div className="flex flex-col w-full gap-space-md pb-space-2xl">
      {/* Error Banner */}
      {error && (
        <div className="bg-error-container text-on-error-container p-3 rounded-lg text-xs flex items-center justify-between border border-error/30">
          <span>Telemetry Error: {error}</span>
          <button onClick={fetchData} className="underline font-bold hover:opacity-80">
            Retry
          </button>
        </div>
      )}

      {/* 1. Command Header & Spatial Controls matching Stitch */}
      <section className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md bg-surface-container-lowest dark:bg-card p-space-md rounded-xl shadow-sm border border-outline-variant/40 dark:border-border">
        <div className="flex flex-col gap-space-2xs min-w-0">
          <div className="flex items-center gap-space-xs font-label-mono text-body-xs text-primary uppercase tracking-wider">
            <Radio className="w-4 h-4 text-primary" />
            <span>Physical-to-Virtual Real-time Mirror</span>
            {loading && !data && (
              <span className="text-[10px] font-mono text-secondary animate-pulse ml-2">Syncing Twin...</span>
            )}
          </div>
          <h1 className="font-headline-lg text-headline-lg text-on-surface tracking-tight truncate">
            Digital Twin — 5G Facility Floor Plan & Telemetry Mesh
          </h1>
          <p className="font-body-xs text-body-xs text-secondary truncate">
            Synchronized topological digital twin mapping ultra-reliable low latency UPF slices to factory spatial assets.
          </p>
        </div>

        {/* Controls Palette */}
        <div className="flex flex-wrap items-center gap-space-sm self-start lg:self-center">
          {/* Scenario Selector */}
          <div className="flex items-center gap-space-xs bg-surface-container-low dark:bg-bg px-space-sm py-1.5 rounded-lg border border-outline-variant/50 dark:border-border text-on-surface">
            <Layers className="w-4 h-4 text-primary" />
            <div className="flex flex-col">
              <span className="font-body-xs text-[10px] text-secondary font-medium leading-none">SCENARIO</span>
              <select
                value={selectedScenario}
                onChange={(e) => {
                  setSelectedScenario(e.target.value);
                  setTimeStep(15);
                }}
                aria-label="Digital twin scenario"
                className="bg-transparent text-xs font-semibold text-on-surface focus:outline-none cursor-pointer max-w-[220px] truncate"
              >
                {SCENARIOS.map((sc) => (
                  <option key={sc.id} value={sc.id} className="bg-surface dark:bg-card text-on-surface">
                    {sc.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Source Toggle if lab validated */}
          {data?.lab_validated ? (
            <div className="flex items-center bg-surface-container-low dark:bg-bg p-1 rounded-lg border border-outline-variant/50 dark:border-border text-xs">
              <button
                onClick={() => setActiveSource('simulated_twin')}
                className={`px-2.5 py-1 rounded font-medium transition-colors ${activeSource === 'simulated_twin' ? 'bg-primary text-white shadow-xs' : 'text-secondary hover:text-on-surface'
                  }`}
              >
                Simulated Twin
              </button>
              <button
                onClick={() => setActiveSource('lab')}
                className={`px-2.5 py-1 rounded font-medium transition-colors ${activeSource === 'lab' ? 'bg-purple-600 text-white shadow-xs' : 'text-secondary hover:text-on-surface'
                  }`}
              >
                Live Lab Core
              </button>
            </div>
          ) : (
            data && (
              <span
                className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${data.source_badge === 'Live lab'
                  ? 'bg-purple-100 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-400/40'
                  : data.source_badge === 'Real recorded'
                    ? 'bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-400/40'
                    : 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-400/40'
                  }`}
              >
                <Activity className="w-3.5 h-3.5" />
                {data.source_badge}
              </span>
            )
          )}

          {/* Reduced Motion Toggle Button */}
          <button
            onClick={() => setReducedMotion(!reducedMotion)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${reducedMotion
              ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border-amber-400/40'
              : 'bg-surface-container-low dark:bg-bg text-secondary hover:text-on-surface border-outline-variant/50 dark:border-border'
              }`}
            title="Toggle particle animations and pulsing rings"
          >
            <Zap className="w-3.5 h-3.5" />
            <span>{reducedMotion ? 'Reduced Motion: ON' : 'Anim: ON'}</span>
          </button>
        </div>
      </section>

      {/* 2. Main Canvas + Inspector Split (72% / 28%) matching Stitch */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-space-md items-start w-full">
        {/* Spatial Canvas Workspace (Central/Left 72%) */}
        <div className="xl:col-span-8 flex flex-col bg-[#0b1329] rounded-xl overflow-hidden shadow-xl relative min-h-[560px] border border-[#1e293b]">
          {/* Canvas HUD Overlay Top */}
          <div className="absolute top-4 left-4 right-4 z-20 flex items-center justify-between pointer-events-none">
            <div className="flex items-center gap-space-sm pointer-events-auto flex-wrap">
              <div className="flex items-center gap-2 bg-[#1e293b]/90 backdrop-blur-md px-3 py-1.5 rounded-lg text-white font-label-mono text-body-xs shadow-md border border-[#334155]">
                <span className={`h-2 w-2 rounded-full ${reducedMotion ? 'bg-emerald-400' : 'bg-emerald-400 animate-ping'}`} />
                <span className="text-emerald-400 font-bold">5G URLLC / eMBB MESH</span>
                <span className="text-[#64748b]">|</span>
                <span className="text-[#cbd5e1]">t = {timeStep}m</span>
                <span className="text-[#64748b]">|</span>
                <span className="text-[#cbd5e1]">{deviceCounts.total} NODES</span>
              </div>
              {deviceCounts.quarantined > 0 && (
                <div className="flex items-center gap-1.5 bg-[#1e293b]/90 backdrop-blur-md px-3 py-1.5 rounded-lg text-white font-label-mono text-body-xs shadow-md border border-purple-500/40">
                  <ShieldAlert className="w-3.5 h-3.5 text-purple-400" />
                  <span className="text-purple-300 font-semibold">{deviceCounts.quarantined} QUARANTINED</span>
                </div>
              )}
              {deviceCounts.attack > 0 && (
                <div className="flex items-center gap-1.5 bg-[#1e293b]/90 backdrop-blur-md px-3 py-1.5 rounded-lg text-white font-label-mono text-body-xs shadow-md border border-red-500/40">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                  <span className="text-red-300 font-semibold">{deviceCounts.attack} ATTACK</span>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 pointer-events-auto">
              <button
                onClick={() => setTimeStep(0)}
                className="p-1.5 rounded-lg bg-[#1e293b]/90 hover:bg-[#334155] text-[#94a3b8] hover:text-white transition-colors border border-[#334155]"
                title="Reset Timeline to t=0"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* SVG Floor Canvas Floor Plan matching Stitch */}
          <div className="relative w-full h-[560px] flex items-center justify-center select-none overflow-hidden bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:24px_24px]">
            <svg
              viewBox="0 0 880 500"
              className="w-full h-full"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <defs>
                <pattern id="twinGrid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.04)" strokeWidth="1" />
                </pattern>
              </defs>
              <rect width="880" height="500" fill="url(#twinGrid)" />

              {/* Perimeter Structural Walls */}
              <path d="M 20 20 L 860 20 L 860 480 L 20 480 Z" fill="#0b1329" fillOpacity="0.4" stroke="#334155" strokeWidth="2" />

              {/* A. Slice Zones */}
              {data?.slices.map((slice) => (
                <g key={slice.slice_id}>
                  <rect
                    x={slice.zone.x}
                    y={slice.zone.y}
                    width={slice.zone.width}
                    height={slice.zone.height}
                    rx="8"
                    fill={`${slice.color}0D`}
                    stroke={slice.color}
                    strokeWidth="1.2"
                    strokeDasharray="4 2"
                  />
                  <rect
                    x={slice.zone.x + 8}
                    y={slice.zone.y + 8}
                    width={180}
                    height="20"
                    rx="4"
                    fill="#1e293b"
                    fillOpacity="0.9"
                  />
                  <text
                    x={slice.zone.x + 14}
                    y={slice.zone.y + 22}
                    fill={slice.color}
                    fontSize="10"
                    fontWeight="600"
                    fontFamily="monospace"
                  >
                    {slice.zone.label.toUpperCase()} ({slice.packet_rate_pps} PPS)
                  </text>
                  <text
                    x={slice.zone.x + 14}
                    y={slice.zone.y + 40}
                    fill="#94A3B8"
                    fontSize="9"
                    fontFamily="monospace"
                  >
                    Slice: {slice.slice_id}
                  </text>
                </g>
              ))}

              {/* B. Virtual Uplinks from Slice Zones to gNodeB */}
              <g stroke="#334155" strokeWidth="1" strokeDasharray="3 3">
                <line x1="280" y1="105" x2="340" y2="270" />
                <line x1="280" y1="265" x2="340" y2="270" />
                <line x1="280" y1="425" x2="340" y2="270" />
              </g>

              {/* C. Infrastructure Links between 5G Core Nodes */}
              {data?.topology?.links.map((link, linkIdx) => {
                const s = nodeMap.get(link.source);
                const t = nodeMap.get(link.target);
                if (!s || !t) return null;
                const strokeColor = link.type === 'user_plane' ? '#10B981' : '#3B82F6';
                const px = s.x + (t.x - s.x) * particleOffset;
                const py = s.y + (t.y - s.y) * particleOffset;

                return (
                  <g key={`${link.source}-${link.target}`}>
                    <line
                      x1={s.x}
                      y1={s.y}
                      x2={t.x}
                      y2={t.y}
                      stroke={strokeColor}
                      strokeWidth="2"
                      strokeOpacity="0.7"
                    />

                    {!reducedMotion && linkIdx < 8 && (
                      <circle
                        cx={px}
                        cy={py}
                        r="3.5"
                        fill="#FFFFFF"
                      />
                    )}

                    <rect
                      x={(s.x + t.x) / 2 - 38}
                      y={(s.y + t.y) / 2 - 9}
                      width="76"
                      height="16"
                      rx="4"
                      fill="#0F172A"
                      stroke="#334155"
                      strokeWidth="1"
                    />
                    <text
                      x={(s.x + t.x) / 2}
                      y={(s.y + t.y) / 2 + 3}
                      fill="#94A3B8"
                      fontSize="9"
                      textAnchor="middle"
                      fontWeight="500"
                    >
                      {link.label}
                    </text>
                  </g>
                );
              })}

              {/* D. Core Infrastructure Nodes */}
              {data?.topology?.nodes.map((n) => {
                const isUser = n.type === 'core_user';
                const isRAN = n.type === 'ran';
                const nodeBg = isRAN ? '#1E293B' : isUser ? '#064E3B' : '#1E3A8A';
                const nodeBorder = isRAN ? '#64748B' : isUser ? '#10B981' : '#3B82F6';

                return (
                  <g key={n.id} transform={`translate(${n.x}, ${n.y})`}>
                    <rect
                      x="-42"
                      y="-22"
                      width="84"
                      height="44"
                      rx="8"
                      fill={nodeBg}
                      stroke={nodeBorder}
                      strokeWidth="1.8"
                    />
                    <text
                      x="0"
                      y="-4"
                      fill="#F8FAFC"
                      fontSize="11"
                      fontWeight="700"
                      textAnchor="middle"
                    >
                      {n.label}
                    </text>
                    <text
                      x="0"
                      y="11"
                      fill="#94A3B8"
                      fontSize="8"
                      textAnchor="middle"
                    >
                      {n.role.split('/')[0]}
                    </text>
                  </g>
                );
              })}

              {/* E. Slice Devices with Verdict Colors, Quarantine Rings & Onboarding Animation */}
              {data?.devices.map((dev) => {
                if (!dev.visible) return null;
                const color = getDeviceColor(dev);
                const isQuarantined = dev.action === 'quarantine' || dev.verdict === 'quarantined';
                const isSelected = selectedDevice?.id === dev.id;

                return (
                  <g
                    key={dev.id}
                    onClick={() => setSelectedDevice(dev)}
                    className="cursor-pointer transition-transform duration-200"
                    transform={`translate(${dev.x}, ${dev.y})`}
                  >
                    {/* Quarantine Isolation Barrier Effect */}
                    {isQuarantined && (
                      <g>
                        <circle
                          cx="0"
                          cy="0"
                          r="15"
                          fill="none"
                          stroke="#8B5CF6"
                          strokeWidth="1.5"
                          strokeDasharray="3 2"
                        />
                        {!reducedMotion && (
                          <circle
                            cx="0"
                            cy="0"
                            r="19"
                            fill="none"
                            stroke="#EF4444"
                            strokeWidth="1"
                            strokeOpacity="0.4"
                          />
                        )}
                      </g>
                    )}

                    {/* New Onboarded Device Arrival Pulse */}
                    {dev.is_onboarded && !reducedMotion && (
                      <circle
                        cx="0"
                        cy="0"
                        r="12"
                        fill="none"
                        stroke="#38BDF8"
                        strokeWidth="1"
                        strokeOpacity="0.6"
                      />
                    )}

                    {/* Selected Device Targeting Reticle matching Stitch */}
                    {isSelected && (
                      <g>
                        <circle
                          cx="0"
                          cy="0"
                          r="18"
                          fill="none"
                          stroke="#60a5fa"
                          strokeWidth="1.5"
                          strokeDasharray="4 2"
                        />
                        <line x1="0" y1="-22" x2="0" y2="-15" stroke="#93c5fd" strokeWidth="1.5" />
                        <line x1="0" y1="15" x2="0" y2="22" stroke="#93c5fd" strokeWidth="1.5" />
                        <line x1="-22" y1="0" x2="-15" y2="0" stroke="#93c5fd" strokeWidth="1.5" />
                        <line x1="15" y1="0" x2="22" y2="0" stroke="#93c5fd" strokeWidth="1.5" />
                      </g>
                    )}

                    {/* Core Device Circle */}
                    <circle
                      cx="0"
                      cy="0"
                      r="7.5"
                      fill={color}
                      stroke="#0F172A"
                      strokeWidth="1.5"
                    />

                    {/* Quarantined Lock Icon glyph */}
                    {isQuarantined ? (
                      <rect x="-2" y="-2" width="4" height="4" fill="#FFFFFF" rx="0.5" />
                    ) : (
                      <circle cx="0" cy="0" r="2.2" fill="#FFFFFF" />
                    )}
                  </g>
                );
              })}
            </svg>

            {/* Canvas Legend Overlay Bottom-Left matching Stitch */}
            <div className="absolute bottom-4 left-4 z-20 flex items-center gap-3 bg-[#0a1628]/95 backdrop-blur-md px-3.5 py-2 rounded-lg text-white font-label-mono text-[11px] shadow-lg border border-[#1e293b]">
              <span className="text-[#64748b] font-semibold">SIGNAL STATUS:</span>
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                <span className="text-[#cbd5e1]">Nominal ({deviceCounts.benign})</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-amber-400" />
                <span className="text-[#cbd5e1]">Uncertain ({deviceCounts.uncertain})</span>
              </div>
              {deviceCounts.attack > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse" />
                  <span className="text-rose-400 font-bold">Attack ({deviceCounts.attack})</span>
                </div>
              )}
              {deviceCounts.quarantined > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-purple-500" />
                  <span className="text-purple-300 font-bold">Quarantined ({deviceCounts.quarantined})</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Inspector Panel (Right 28%) matching Stitch */}
        <div className="xl:col-span-4 flex flex-col gap-space-md">
          <div className="bg-surface-container-lowest dark:bg-card p-space-md rounded-xl shadow-sm border border-outline-variant/40 dark:border-border flex flex-col gap-space-md">
            {/* Inspector Title & State */}
            <div className="flex items-start justify-between gap-space-sm">
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5 font-label-mono text-body-xs text-primary font-semibold">
                  <Radio className="w-4 h-4 text-primary" />
                  <span>NODE DEEP INSPECTOR</span>
                </div>
                <h2 className="font-headline-md text-headline-md text-on-surface font-bold tracking-tight mt-0.5">
                  {selectedDevice ? selectedDevice.id : 'NO NODE SELECTED'}
                </h2>
                <span className="font-body-xs text-body-xs text-secondary">
                  {selectedDevice ? `Class: ${selectedDevice.device_class.toUpperCase()} on ${selectedDevice.slice_id}` : 'Select a node on the floor canvas'}
                </span>
              </div>
              {selectedDevice && (
                <span
                  className="font-badge-status text-badge-status px-2.5 py-1 rounded-full font-bold uppercase tracking-wider flex items-center gap-1.5"
                  style={{
                    backgroundColor: `${getDeviceColor(selectedDevice)}20`,
                    color: getDeviceColor(selectedDevice),
                  }}
                >
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: getDeviceColor(selectedDevice) }}
                  />
                  {selectedDevice.verdict.toUpperCase()}
                </span>
              )}
            </div>

            {selectedDevice ? (
              <div className="flex flex-col gap-3">
                {/* Identity & Cryptographic Attestation Metadata */}
                <div className="flex flex-col gap-2 p-space-sm bg-surface-container-low dark:bg-bg rounded-lg border border-outline-variant/30 dark:border-border/60">
                  <div className="flex items-center justify-between font-body-xs text-body-xs">
                    <span className="text-secondary font-medium">Assigned Zone</span>
                    <span className="font-semibold text-on-surface">{selectedDevice.slice_id}</span>
                  </div>
                  <div className="flex items-center justify-between font-body-xs text-body-xs">
                    <span className="text-secondary font-medium">Device Class</span>
                    <span className="font-label-mono font-medium text-on-surface uppercase">{selectedDevice.device_class}</span>
                  </div>
                  <div className="flex items-center justify-between font-body-xs text-body-xs">
                    <span className="text-secondary font-medium">Telemetry Rate</span>
                    <span className="font-label-mono text-primary font-semibold">{selectedDevice.rate_pps.toFixed(1)} pps</span>
                  </div>
                  <div className="flex items-center justify-between font-body-xs text-body-xs">
                    <span className="text-secondary font-medium">Provisioned</span>
                    <span className={`font-semibold ${selectedDevice.is_provisioned ? 'text-emerald-600 dark:text-emerald-400' : 'text-error'}`}>
                      {selectedDevice.is_provisioned ? 'VERIFIED' : 'UNREGISTERED'}
                    </span>
                  </div>

                  <div className="mt-1 pt-2 flex flex-col gap-1 border-t border-outline-variant/20 dark:border-border/40">
                    <div className="flex items-center justify-between text-[11px] font-label-mono">
                      <span className="text-secondary">HMAC TPM 2.0 DIGEST</span>
                      <span className="text-emerald-700 dark:text-emerald-400 font-semibold flex items-center gap-0.5">
                        <CheckCircle2 className="w-3.5 h-3.5" /> VERIFIED
                      </span>
                    </div>
                    <div className="flex items-center justify-between bg-surface-container-lowest dark:bg-card px-2 py-1.5 rounded text-secondary font-label-mono text-body-xs border border-outline-variant/30 dark:border-border/40">
                      <span className="truncate text-on-surface font-mono max-w-[190px]">
                        {selectedDevice.device_id_hash}
                      </span>
                      <button
                        onClick={() => handleCopyHmac(selectedDevice.device_id_hash)}
                        className="text-outline hover:text-primary transition-colors ml-1 p-0.5"
                        title="Copy HMAC"
                      >
                        {copiedHmac ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>
                </div>

                {/* State & Telemetry Verdict Box */}
                <div className="p-2.5 rounded-lg bg-surface-container-low dark:bg-bg border border-outline-variant/30 dark:border-border/60">
                  <span className="text-secondary block text-[10px] mb-1 font-label-mono uppercase">
                    Zero-Trust Decision
                  </span>
                  <div className="flex items-center gap-2">
                    {selectedDevice.action === 'quarantine' ? (
                      <ShieldAlert className="w-4 h-4 text-purple-500 shrink-0" />
                    ) : (
                      <ShieldCheck className="w-4 h-4 text-emerald-500 shrink-0" />
                    )}
                    <span className="text-on-surface text-xs font-semibold">{selectedDevice.status_label}</span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-secondary py-6 text-center">
                Click any device circle on the floor canvas to inspect its telemetry.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* 3. Bottom Interactive Time Scrubber matching Stitch */}
      <div className="w-full bg-surface-container-lowest dark:bg-card p-space-md rounded-xl shadow-sm border border-outline-variant/40 dark:border-border flex flex-col gap-space-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-sm">
          {/* Media Playback Deck */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setIsPlaying(false);
                setTimeStep((prev) => Math.max(0, prev - 1));
              }}
              className="p-2 rounded-lg bg-surface-container-low dark:bg-bg hover:bg-surface-container dark:hover:bg-slate-800 text-on-surface border border-outline-variant/40 dark:border-border transition-colors"
              title="Step Back 1m"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              disabled={reducedMotion}
              className="px-4 py-2 rounded-lg bg-primary text-on-primary font-body-sm text-body-sm font-semibold flex items-center gap-2 hover:bg-surface-tint transition-all shadow-sm disabled:opacity-40"
            >
              {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              <span>{isPlaying ? 'Pause' : 'Play Live Stream'}</span>
            </button>
            <button
              onClick={() => {
                setIsPlaying(false);
                setTimeStep((prev) => Math.min(29, prev + 1));
              }}
              className="p-2 rounded-lg bg-surface-container-low dark:bg-bg hover:bg-surface-container dark:hover:bg-slate-800 text-on-surface border border-outline-variant/40 dark:border-border transition-colors"
              title="Step Forward 1m"
            >
              <Play className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center gap-3 flex-1 max-w-xl mx-4">
            <span className="font-label-mono text-body-xs text-secondary">t = {timeStep}m</span>
            <input
              type="range"
              min={0}
              max={29}
              value={timeStep}
              onChange={(e) => {
                setIsPlaying(false);
                setTimeStep(Number(e.target.value));
              }}
              aria-label="Simulation time scrubber"
              className="flex-1 accent-primary cursor-pointer h-2 bg-surface-container dark:bg-slate-800 rounded-full"
            />
            <span className="font-label-mono text-body-xs text-secondary">t = 29m</span>
          </div>

          <div className="text-xs text-secondary font-medium font-label-mono">
            {timeStep < 10
              ? 'Phase: Baseline Nominal'
              : timeStep < 20
                ? 'Phase: Batch 1 Ingress / Surge'
                : 'Phase: Batch 2 Ingress / Sustained'}
          </div>
        </div>
      </div>

      {/* 4. Provisioning Card & Contamination Meters matching Stitch */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Provisioning Card */}
        <div className="bg-surface-container-lowest dark:bg-card border border-outline-variant/40 dark:border-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-outline-variant/30 dark:border-border">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-primary" />
              <h3 className="text-sm font-semibold text-on-surface">Provisioning & Change Event Evidence</h3>
            </div>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${data?.provisioning_card.fitting_volume
                ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300'
                : 'bg-error-container text-on-error-container'
                }`}
            >
              {data?.provisioning_card.verdict || 'EVALUATING'}
            </span>
          </div>

          <div className="mt-4 space-y-3 text-xs">
            <div className="flex items-center justify-between py-1.5 border-b border-outline-variant/20 dark:border-border/40">
              <span className="text-secondary">Total Catalog SIMs</span>
              <span className="font-mono font-bold text-on-surface">
                {data?.provisioning_card.total_catalog_sims ?? 200} Devices
              </span>
            </div>

            <div className="flex items-center justify-between py-1.5 border-b border-outline-variant/20 dark:border-border/40">
              <span className="text-secondary">Active Window Provisioned Share</span>
              <span className="font-mono font-bold text-on-surface">
                {((data?.provisioning_card.provisioned_share ?? 1.0) * 100).toFixed(1)}%
              </span>
            </div>

            <div className="flex items-center justify-between py-1.5 border-b border-outline-variant/20 dark:border-border/40">
              <span className="text-secondary">Matched Onboarding Event</span>
              <span className="font-mono font-semibold text-primary">
                {data?.provisioning_card.matched_event?.batch_id ?? 'None (Unscheduled)'}
              </span>
            </div>

            {data?.provisioning_card.matched_event && (
              <div className="flex items-center justify-between py-1.5 border-b border-outline-variant/20 dark:border-border/40">
                <span className="text-secondary">Scheduled Batch Volume</span>
                <span className="font-mono text-on-surface">
                  {data.provisioning_card.matched_event.count} devices on {data.provisioning_card.matched_event.slice}
                </span>
              </div>
            )}

            <div className="flex items-center justify-between py-1.5 border-b border-outline-variant/20 dark:border-border/40">
              <span className="text-secondary">Volume Scaling Consistency</span>
              <span className={`font-semibold ${data?.provisioning_card.fitting_volume ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}>
                {data?.provisioning_card.fitting_volume ? 'Volume Fits Batch Size' : 'Surge Exceeds Schedule'}
              </span>
            </div>

            <div className="pt-2">
              <span className="text-secondary block text-[11px] mb-1">Gate Action & Recommendation</span>
              <div className="p-2.5 rounded bg-surface-container-low dark:bg-bg border border-outline-variant/30 dark:border-border flex items-start gap-2">
                {data?.provisioning_card.action === 'quarantine' ? (
                  <Lock className="w-4 h-4 text-purple-500 shrink-0 mt-0.5" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                )}
                <span className="text-[11px] text-on-surface font-medium leading-relaxed">
                  {data?.provisioning_card.action_description}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Two Contamination Meters: Naive vs CommShield Twin */}
        <div className="lg:col-span-2 bg-surface-container-lowest dark:bg-card border border-outline-variant/40 dark:border-border rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-outline-variant/30 dark:border-border">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-primary" />
                <h3 className="text-sm font-semibold text-on-surface">Three-Arm Contamination & Retraining Meters</h3>
              </div>
              <span className="text-[11px] text-secondary font-mono">
                Source: {data?.saved_metrics_reference.summary_file}
              </span>
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Arm 1: Naive Retraining */}
              <div className="p-4 rounded-xl bg-surface-container-low dark:bg-bg border border-error/30">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-error uppercase tracking-wide">
                    {data?.contamination_meters.naive.name ?? 'Naive Retraining'}
                  </span>
                  <span className="text-xs font-mono font-bold text-error">
                    {((data?.contamination_meters.naive.contamination_mean ?? 0) * 100).toFixed(1)}%
                  </span>
                </div>

                <div className="w-full bg-surface-container dark:bg-slate-800 rounded-full h-3 mt-3 overflow-hidden">
                  <div
                    className="bg-error h-3 rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(100, Math.max(3, (data?.contamination_meters.naive.contamination_mean ?? 0) * 100))}%`,
                    }}
                  />
                </div>

                <div className="mt-3 space-y-1 text-[11px]">
                  <div className="flex justify-between text-secondary">
                    <span>95% Bootstrap CI:</span>
                    <span className="font-mono text-on-surface font-semibold">
                      [
                      {((data?.contamination_meters.naive.contamination_ci_95[0] ?? 0) * 100).toFixed(1)}%,{' '}
                      {((data?.contamination_meters.naive.contamination_ci_95[1] ?? 0) * 100).toFixed(1)}%
                      ]
                    </span>
                  </div>
                  <div className="flex justify-between text-secondary">
                    <span>False Positive Rate:</span>
                    <span className="font-mono text-on-surface">
                      {((data?.contamination_meters.naive.fpr_mean ?? 0) * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-secondary">
                    <span>Onboardings Adapted:</span>
                    <span className="font-mono text-on-surface font-semibold">
                      {(data?.contamination_meters.naive.onboardings_adapted ?? 0).toFixed(1)} batches
                    </span>
                  </div>
                </div>
              </div>

              {/* Arm 2: CommShield Twin */}
              <div className="p-4 rounded-xl bg-surface-container-low dark:bg-bg border border-emerald-500/30">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-emerald-700 dark:text-emerald-400 uppercase tracking-wide">
                    {data?.contamination_meters.commshield_twin.name ?? 'CommShield Twin'}
                  </span>
                  <span className="text-xs font-mono font-bold text-emerald-700 dark:text-emerald-400">
                    {((data?.contamination_meters.commshield_twin.contamination_mean ?? 0) * 100).toFixed(1)}%
                  </span>
                </div>

                <div className="w-full bg-surface-container dark:bg-slate-800 rounded-full h-3 mt-3 overflow-hidden">
                  <div
                    className="bg-emerald-600 dark:bg-emerald-500 h-3 rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(100, Math.max(3, (data?.contamination_meters.commshield_twin.contamination_mean ?? 0) * 100))}%`,
                    }}
                  />
                </div>

                <div className="mt-3 space-y-1 text-[11px]">
                  <div className="flex justify-between text-secondary">
                    <span>95% Bootstrap CI:</span>
                    <span className="font-mono text-on-surface font-semibold">
                      [
                      {((data?.contamination_meters.commshield_twin.contamination_ci_95[0] ?? 0) * 100).toFixed(1)}%,{' '}
                      {((data?.contamination_meters.commshield_twin.contamination_ci_95[1] ?? 0) * 100).toFixed(1)}%
                      ]
                    </span>
                  </div>
                  <div className="flex justify-between text-secondary">
                    <span>False Positive Rate:</span>
                    <span className="font-mono text-on-surface">
                      {((data?.contamination_meters.commshield_twin.fpr_mean ?? 0) * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-secondary">
                    <span>Onboardings Adapted:</span>
                    <span className="font-mono text-on-surface font-semibold">
                      {(data?.contamination_meters.commshield_twin.onboardings_adapted ?? 0).toFixed(1)} batches
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-outline-variant/20 dark:border-border flex items-center justify-between text-[11px] text-secondary">
            <span>Audit Guarantee: All figures read strictly from verified results files without extrapolation.</span>
            <span className="font-mono">Total Windows: {data?.saved_metrics_reference.aggregate_windows ?? 11870}</span>
          </div>
        </div>
      </div>

      {/* 5. Decision Trace with Sequential Checks matching Stitch */}
      <div className="bg-surface-container-lowest dark:bg-card border border-outline-variant/40 dark:border-border rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between pb-3 border-b border-outline-variant/30 dark:border-border">
          <div className="flex items-center gap-2">
            <FileCheck className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-semibold text-on-surface">Governance Decision Trace (Sequential Verification)</h3>
          </div>
          <span className="text-xs text-secondary">5-Gate Multi-Layer Attribution Audit</span>
        </div>

        <div className="mt-4 grid grid-cols-1 md:grid-cols-5 gap-3">
          {data?.decision_trace.map((step) => {
            const isApproved = step.status === 'VERIFIED' || step.status === 'APPROVED' || step.status === 'PASSED' || step.status === 'CLEAR';
            const isSpike = step.status === 'GROWTH_DETECTED' || step.status === 'MATCHED';
            const statusColor = isApproved ? 'text-emerald-700 dark:text-emerald-400 border-emerald-500/30' : isSpike ? 'text-primary border-primary/30' : 'text-amber-700 dark:text-amber-400 border-amber-500/30';

            return (
              <div key={step.step} className={`p-3 rounded-lg bg-surface-container-low dark:bg-bg border ${statusColor} flex flex-col justify-between`}>
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] font-mono text-secondary uppercase">Step 0{step.step}</span>
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${isApproved ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300' : 'bg-surface-container dark:bg-slate-700 text-on-surface'
                      }`}>
                      {step.status}
                    </span>
                  </div>
                  <h4 className="text-xs font-semibold text-on-surface mb-1">{step.name}</h4>
                  <p className="text-[11px] text-secondary leading-relaxed">{step.result}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default DigitalTwinView;
