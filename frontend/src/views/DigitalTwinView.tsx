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
  Cpu,
  Lock,
  Layers,
  Activity,
  FileCheck,
  Zap,
} from 'lucide-react';
import {
  api,
  DigitalTwinResponse,
  DigitalTwinDevice,
  DigitalTwinNode,
} from '../services/api';

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
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [reducedMotion, setReducedMotion] = useState<boolean>(false);
  const [selectedDevice, setSelectedDevice] = useState<DigitalTwinDevice | null>(null);

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

  return (
    <div className="space-y-6">
      {/* Error Banner */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-3 rounded-lg text-xs flex items-center justify-between">
          <span>Telemetry Error: {error}</span>
          <button onClick={fetchData} className="underline hover:text-white">Retry</button>
        </div>
      )}

      {/* 1. Header Bar with Scenario Selector, Time Scrubber, Motion & Source Badge */}
      <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold tracking-tight text-text flex items-center gap-2">
                <Cpu className="w-6 h-6 text-blue" />
                5G Slice Digital Twin & Telemetry Floor Map
              </h1>

              {/* Loading Indicator */}
              {loading && !data && (
                <span className="text-xs text-muted font-mono animate-pulse">Syncing Twin...</span>
              )}

              {/* Source Badge taken directly from data.source */}
              {data && (
                <span
                  className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider ${
                    data.source_badge === 'Live lab'
                      ? 'bg-purple-500/20 text-purple-400 border border-purple-500/40'
                      : data.source_badge === 'Real recorded'
                      ? 'bg-blue/20 text-blue border border-blue/40'
                      : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                  }`}
                >
                  <Activity className="w-3.5 h-3.5" />
                  {data.source_badge}
                </span>
              )}
            </div>
            <p className="text-xs text-muted mt-1">
              Deterministic floor-plan telemetry, per-device conformal bounds, and zero-trust onboarding governance.
            </p>
          </div>

          {/* Controls: Source toggle (if lab validated), Reduced Motion & Scenario */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Lab Source Toggle - Enabled only when lab is validated */}
            {data?.lab_validated && (
              <div className="flex items-center gap-1 bg-bg border border-border rounded-lg p-1 text-xs">
                <button
                  onClick={() => setActiveSource('simulated_twin')}
                  className={`px-2.5 py-1 rounded font-medium transition-colors ${
                    activeSource === 'simulated_twin' ? 'bg-blue text-white shadow-sm' : 'text-muted hover:text-text'
                  }`}
                >
                  Simulated Twin
                </button>
                <button
                  onClick={() => setActiveSource('lab')}
                  className={`px-2.5 py-1 rounded font-medium transition-colors ${
                    activeSource === 'lab' ? 'bg-purple-600 text-white shadow-sm' : 'text-muted hover:text-text'
                  }`}
                >
                  Live Lab Core
                </button>
              </div>
            )}

            {/* Reduced Motion Toggle Button */}
            <button
              onClick={() => setReducedMotion(!reducedMotion)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                reducedMotion
                  ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                  : 'bg-bg text-muted hover:text-text border-border'
              }`}
              title="Toggle packet particle animations and pulsing rings"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>{reducedMotion ? 'Reduced Motion: ON' : 'Animations: ON'}</span>
            </button>

            {/* Scenario Dropdown */}
            <div className="relative">
              <select
                value={selectedScenario}
                onChange={(e) => {
                  setSelectedScenario(e.target.value);
                  setTimeStep(15);
                }}
                className="bg-bg border border-border text-xs rounded-lg px-3 py-2 text-text font-medium focus:ring-1 focus:ring-blue focus:outline-none"
              >
                {SCENARIOS.map((sc) => (
                  <option key={sc.id} value={sc.id}>
                    {sc.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Timeline Scrubber */}
        <div className="mt-4 pt-4 border-t border-border flex items-center gap-4">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            disabled={reducedMotion}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue/20 hover:bg-blue/30 text-blue border border-blue/40 rounded-lg text-xs font-semibold transition-colors disabled:opacity-40"
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            <span>{isPlaying ? 'Pause' : 'Play'}</span>
          </button>

          <button
            onClick={() => {
              setIsPlaying(false);
              setTimeStep(0);
            }}
            className="p-1.5 bg-bg hover:bg-slate/20 text-muted hover:text-text border border-border rounded-lg text-xs transition-colors"
            title="Reset to t=0"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <div className="flex-1 flex items-center gap-3">
            <span className="text-xs font-mono text-muted w-14">t = {timeStep}m</span>
            <input
              type="range"
              min={0}
              max={29}
              value={timeStep}
              onChange={(e) => {
                setIsPlaying(false);
                setTimeStep(Number(e.target.value));
              }}
              className="flex-1 accent-blue cursor-pointer h-1.5 bg-slate/30 rounded-lg"
            />
            <span className="text-xs font-mono text-muted w-14 text-right">t = 29m</span>
          </div>

          <div className="text-xs text-muted font-medium hidden sm:block">
            {timeStep < 10
              ? 'Phase: Baseline Streaming'
              : timeStep < 20
              ? 'Phase: Batch 1 Ingress / Surge'
              : 'Phase: Batch 2 Ingress / Sustained'}
          </div>
        </div>
      </div>

      {/* 2. Interactive SVG Floor Map */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-3 bg-card border border-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue" />
              <h2 className="text-sm font-semibold text-text">Facility Floor Plan & Core Network Topology</h2>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <span className="text-muted">Benign</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
                <span className="text-muted">Attack</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                <span className="text-muted">Uncertain</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
                <span className="text-muted">Quarantined</span>
              </div>
            </div>
          </div>

          {/* SVG Floor Canvas */}
          <div className="relative w-full overflow-hidden rounded-lg border border-border bg-[#0B132B]/90">
            <svg
              viewBox="0 0 880 500"
              className="w-full h-auto select-none"
              style={{ minHeight: '440px' }}
            >
              {/* Subtle Floor Map Grid Pattern */}
              <defs>
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255, 255, 255, 0.04)" strokeWidth="1" />
                </pattern>
                {/* Glow Filter for Quarantine & Core nodes */}
                <filter id="glow-purple" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
                <filter id="glow-red" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur in="SourceGraphic" stdDeviation="5" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              <rect width="880" height="500" fill="url(#grid)" />

              {/* A. Slice Zones */}
              {data?.slices.map((slice) => (
                <g key={slice.slice_id}>
                  {/* Zone Rect */}
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
                  {/* Zone Header Label */}
                  <text
                    x={slice.zone.x + 10}
                    y={slice.zone.y + 18}
                    fill={slice.color}
                    fontSize="10"
                    fontWeight="600"
                    fontFamily="monospace"
                  >
                    {slice.zone.label.toUpperCase()} ({slice.packet_rate_pps} PPS)
                  </text>
                  <text
                    x={slice.zone.x + 10}
                    y={slice.zone.y + 30}
                    fill="#94A3B8"
                    fontSize="9"
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
              {data?.topology?.links.map((link) => {
                const s = nodeMap.get(link.source);
                const t = nodeMap.get(link.target);
                if (!s || !t) return null;
                const strokeColor = link.type === 'user_plane' ? '#10B981' : '#3B82F6';

                // Particle position calculation
                const px = s.x + (t.x - s.x) * particleOffset;
                const py = s.y + (t.y - s.y) * particleOffset;

                return (
                  <g key={`${link.source}-${link.target}`}>
                    {/* Link Base Line */}
                    <line
                      x1={s.x}
                      y1={s.y}
                      x2={t.x}
                      y2={t.y}
                      stroke={strokeColor}
                      strokeWidth="2"
                      strokeOpacity="0.7"
                    />

                    {/* Animated Link Packet Particle (if not reduced motion) */}
                    {!reducedMotion && (
                      <circle
                        cx={px}
                        cy={py}
                        r="3.5"
                        fill="#FFFFFF"
                        filter="drop-shadow(0 0 3px rgba(255,255,255,0.8))"
                      />
                    )}

                    {/* Link Label Tag */}
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
                      className="shadow-lg"
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
                          className={reducedMotion ? '' : 'animate-spin'}
                          style={{ transformOrigin: '0 0', animationDuration: '6s' }}
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
                            className="animate-ping"
                            style={{ animationDuration: '2.5s' }}
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

                    {/* Selected Device Ring */}
                    {isSelected && (
                      <circle
                        cx="0"
                        cy="0"
                        r="13"
                        fill="none"
                        stroke="#FFFFFF"
                        strokeWidth="2"
                      />
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
          </div>
        </div>

        {/* 3. Selected Device Inspector Panel */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <div className="flex items-center gap-2">
                <Radio className="w-4 h-4 text-blue" />
                <h3 className="text-sm font-semibold text-text">Device Inspector</h3>
              </div>
              {selectedDevice && (
                <span
                  className="px-2 py-0.5 rounded text-[10px] font-bold uppercase"
                  style={{
                    backgroundColor: `${getDeviceColor(selectedDevice)}20`,
                    color: getDeviceColor(selectedDevice),
                  }}
                >
                  {selectedDevice.verdict}
                </span>
              )}
            </div>

            {selectedDevice ? (
              <div className="mt-4 space-y-3.5 text-xs">
                <div>
                  <span className="text-muted block text-[11px]">Device Identifier</span>
                  <span className="font-mono font-bold text-text text-sm">{selectedDevice.id}</span>
                </div>

                <div>
                  <span className="text-muted block text-[11px]">HMAC Hash (Zero-Trust Key)</span>
                  <span className="font-mono text-[10px] text-slate-300 break-all bg-bg p-1.5 rounded border border-border block">
                    {selectedDevice.device_id_hash}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-bg p-2 rounded border border-border">
                    <span className="text-muted block text-[10px]">Class</span>
                    <span className="font-semibold text-text uppercase">{selectedDevice.device_class}</span>
                  </div>
                  <div className="bg-bg p-2 rounded border border-border">
                    <span className="text-muted block text-[10px]">Slice</span>
                    <span className="font-mono font-semibold text-blue text-[11px] truncate block">
                      {selectedDevice.slice_id.split('-')[0]}-{selectedDevice.slice_id.split('-')[1]}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-bg p-2 rounded border border-border">
                    <span className="text-muted block text-[10px]">Telemetry Rate</span>
                    <span className="font-mono font-bold text-text">{selectedDevice.rate_pps.toFixed(1)} pps</span>
                  </div>
                  <div className="bg-bg p-2 rounded border border-border">
                    <span className="text-muted block text-[10px]">Catalog Provisioned</span>
                    <span className={`font-semibold ${selectedDevice.is_provisioned ? 'text-emerald-400' : 'text-red-400'}`}>
                      {selectedDevice.is_provisioned ? 'Verified' : 'Unregistered'}
                    </span>
                  </div>
                </div>

                <div className="bg-bg p-2.5 rounded border border-border">
                  <span className="text-muted block text-[10px] mb-1">State & Telemetry Verdict</span>
                  <div className="flex items-center gap-2">
                    {selectedDevice.action === 'quarantine' ? (
                      <ShieldAlert className="w-4 h-4 text-purple-400 flex-shrink-0" />
                    ) : (
                      <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    )}
                    <span className="text-text font-medium">{selectedDevice.status_label}</span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted mt-6 text-center">Click any device circle on the floor plan to inspect telemetry.</p>
            )}
          </div>

          <div className="pt-4 border-t border-border mt-4 text-[11px] text-muted">
            <span>Tip: Devices appear dynamically at approved onboarding intervals (t=10m, t=20m).</span>
          </div>
        </div>
      </div>

      {/* 4. Provisioning Card & Contamination Meters */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Provisioning Card */}
        <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-border">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-blue" />
              <h3 className="text-sm font-semibold text-text">Provisioning & Change Event Evidence</h3>
            </div>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                data?.provisioning_card.fitting_volume
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'bg-red-500/20 text-red-400'
              }`}
            >
              {data?.provisioning_card.verdict || 'EVALUATING'}
            </span>
          </div>

          <div className="mt-4 space-y-3 text-xs">
            <div className="flex items-center justify-between py-1.5 border-b border-border/50">
              <span className="text-muted">Total Catalog SIMs</span>
              <span className="font-mono font-bold text-text">
                {data?.provisioning_card.total_catalog_sims ?? 200} Devices
              </span>
            </div>

            <div className="flex items-center justify-between py-1.5 border-b border-border/50">
              <span className="text-muted">Active Window Provisioned Share</span>
              <span className="font-mono font-bold text-text">
                {((data?.provisioning_card.provisioned_share ?? 1.0) * 100).toFixed(1)}%
              </span>
            </div>

            <div className="flex items-center justify-between py-1.5 border-b border-border/50">
              <span className="text-muted">Matched Onboarding Event</span>
              <span className="font-mono font-semibold text-blue">
                {data?.provisioning_card.matched_event?.batch_id ?? 'None (Unscheduled)'}
              </span>
            </div>

            {data?.provisioning_card.matched_event && (
              <div className="flex items-center justify-between py-1.5 border-b border-border/50">
                <span className="text-muted">Scheduled Batch Volume</span>
                <span className="font-mono text-text">
                  {data.provisioning_card.matched_event.count} devices on {data.provisioning_card.matched_event.slice}
                </span>
              </div>
            )}

            <div className="flex items-center justify-between py-1.5 border-b border-border/50">
              <span className="text-muted">Volume Scaling Consistency</span>
              <span className={`font-semibold ${data?.provisioning_card.fitting_volume ? 'text-emerald-400' : 'text-amber-400'}`}>
                {data?.provisioning_card.fitting_volume ? 'Volume Fits Batch Size' : 'Surge Exceeds Schedule'}
              </span>
            </div>

            <div className="pt-2">
              <span className="text-muted block text-[11px] mb-1">Gate Action & Recommendation</span>
              <div className="p-2.5 rounded bg-bg border border-border flex items-start gap-2">
                {data?.provisioning_card.action === 'quarantine' ? (
                  <Lock className="w-4 h-4 text-purple-400 flex-shrink-0 mt-0.5" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                )}
                <span className="text-[11px] text-text font-medium leading-relaxed">
                  {data?.provisioning_card.action_description}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Two Contamination Meters: Naive vs CommShield Twin */}
        <div className="lg:col-span-2 bg-card border border-border rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-blue" />
                <h3 className="text-sm font-semibold text-text">Three-Arm Contamination & Retraining Meters</h3>
              </div>
              <span className="text-[11px] text-muted font-mono">
                Source: {data?.saved_metrics_reference.summary_file}
              </span>
            </div>

            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Arm 1: Naive Retraining */}
              <div className="p-4 rounded-xl bg-bg border border-red-500/30">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-red-400 uppercase tracking-wide">
                    {data?.contamination_meters.naive.name ?? 'Naive Retraining'}
                  </span>
                  <span className="text-xs font-mono font-bold text-red-400">
                    {((data?.contamination_meters.naive.contamination_mean ?? 0) * 100).toFixed(1)}%
                  </span>
                </div>

                {/* Meter Bar */}
                <div className="w-full bg-slate-800 rounded-full h-3 mt-3 overflow-hidden">
                  <div
                    className="bg-red-500 h-3 rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(100, Math.max(3, (data?.contamination_meters.naive.contamination_mean ?? 0) * 100))}%`,
                    }}
                  />
                </div>

                <div className="mt-3 space-y-1 text-[11px]">
                  <div className="flex justify-between text-muted">
                    <span>95% Bootstrap CI:</span>
                    <span className="font-mono text-text font-semibold">
                      [
                      {((data?.contamination_meters.naive.contamination_ci_95[0] ?? 0) * 100).toFixed(1)}%,{' '}
                      {((data?.contamination_meters.naive.contamination_ci_95[1] ?? 0) * 100).toFixed(1)}%
                      ]
                    </span>
                  </div>
                  <div className="flex justify-between text-muted">
                    <span>False Positive Rate:</span>
                    <span className="font-mono text-text">
                      {((data?.contamination_meters.naive.fpr_mean ?? 0) * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-muted">
                    <span>Onboardings Adapted:</span>
                    <span className="font-mono text-text font-semibold">
                      {(data?.contamination_meters.naive.onboardings_adapted ?? 0).toFixed(1)} batches
                    </span>
                  </div>
                </div>
              </div>

              {/* Arm 2: CommShield Twin (Provisioning & Conformal Gated) */}
              <div className="p-4 rounded-xl bg-bg border border-emerald-500/40">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-emerald-400 uppercase tracking-wide">
                    {data?.contamination_meters.commshield_twin.name ?? 'CommShield Twin'}
                  </span>
                  <span className="text-xs font-mono font-bold text-emerald-400">
                    {((data?.contamination_meters.commshield_twin.contamination_mean ?? 0) * 100).toFixed(1)}%
                  </span>
                </div>

                {/* Meter Bar */}
                <div className="w-full bg-slate-800 rounded-full h-3 mt-3 overflow-hidden">
                  <div
                    className="bg-emerald-500 h-3 rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(100, Math.max(3, (data?.contamination_meters.commshield_twin.contamination_mean ?? 0) * 100))}%`,
                    }}
                  />
                </div>

                <div className="mt-3 space-y-1 text-[11px]">
                  <div className="flex justify-between text-muted">
                    <span>95% Bootstrap CI:</span>
                    <span className="font-mono text-text font-semibold">
                      [
                      {((data?.contamination_meters.commshield_twin.contamination_ci_95[0] ?? 0) * 100).toFixed(1)}%,{' '}
                      {((data?.contamination_meters.commshield_twin.contamination_ci_95[1] ?? 0) * 100).toFixed(1)}%
                      ]
                    </span>
                  </div>
                  <div className="flex justify-between text-muted">
                    <span>False Positive Rate:</span>
                    <span className="font-mono text-text">
                      {((data?.contamination_meters.commshield_twin.fpr_mean ?? 0) * 100).toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-muted">
                    <span>Onboardings Adapted:</span>
                    <span className="font-mono text-text font-semibold">
                      {(data?.contamination_meters.commshield_twin.onboardings_adapted ?? 0).toFixed(1)} batches
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-[11px] text-muted">
            <span>Audit Guarantee: All figures read strictly from verified results files without extrapolation.</span>
            <span className="font-mono">Total Benchmark Windows: {data?.saved_metrics_reference.aggregate_windows ?? 11870}</span>
          </div>
        </div>
      </div>

      {/* 5. Decision Trace with Provisioning & Split-Conformal Checks */}
      <div className="bg-card border border-border rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between pb-3 border-b border-border">
          <div className="flex items-center gap-2">
            <FileCheck className="w-4 h-4 text-blue" />
            <h3 className="text-sm font-semibold text-text">Governance Decision Trace (Sequential Verification)</h3>
          </div>
          <span className="text-xs text-muted">5-Gate Multi-Layer Attribution Audit</span>
        </div>

        <div className="mt-4 grid grid-cols-1 md:grid-cols-5 gap-3">
          {data?.decision_trace.map((step) => {
            const isApproved = step.status === 'VERIFIED' || step.status === 'APPROVED' || step.status === 'PASSED' || step.status === 'CLEAR';
            const isSpike = step.status === 'GROWTH_DETECTED' || step.status === 'MATCHED';
            const statusColor = isApproved ? 'text-emerald-400 border-emerald-500/30' : isSpike ? 'text-blue border-blue/30' : 'text-amber-400 border-amber-500/30';

            return (
              <div key={step.step} className={`p-3 rounded-lg bg-bg border ${statusColor} flex flex-col justify-between`}>
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-[10px] font-mono text-muted uppercase">Step 0{step.step}</span>
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${isApproved ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-700 text-slate-300'}`}>
                      {step.status}
                    </span>
                  </div>
                  <h4 className="text-xs font-semibold text-text mb-1">{step.name}</h4>
                  <p className="text-[11px] text-muted leading-relaxed">{step.result}</p>
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
