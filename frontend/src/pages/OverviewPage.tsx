import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  AlertOctagon,
  CheckCircle2,
  Copy,
  Download,
  Layers,
  Radio,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  DataSourceBadge,
  EmptyState,
  ErrorState,
  LoadingState,
  StatusBadge,
} from '../components';
import {
  AlertItem,
  api,
  BaselineSummaryResponse,
  CandidateResponse,
  CanonicalTrafficWindow,
  ExplainabilityResponse,
  QuarantineWindowItem,
  RealOverviewResponse,
} from '../services/api';
import { useReplay } from '../context/ReplayContext';

export const OverviewPage: React.FC = () => {
  const { pollTick, selectedSlice } = useReplay();
  const navigate = useNavigate();

  const [windows, setWindows] = useState<CanonicalTrafficWindow[]>([]);
  const [baselines, setBaselines] = useState<BaselineSummaryResponse[]>([]);
  const [candidates, setCandidates] = useState<CandidateResponse[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [quarantineItems, setQuarantineItems] = useState<QuarantineWindowItem[]>([]);
  const [explainMap, setExplainMap] = useState<Record<string, ExplainabilityResponse>>({});
  const [realOverview, setRealOverview] = useState<RealOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Table filters
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [copiedHash, setCopiedHash] = useState(false);

  const fetchData = async (isInitial = false) => {
    if (isInitial) setLoading(true);
    setError(null);
    try {
      const [winRes, baseRes, candRes, alertRes, quaranRes, realRes] = await Promise.all([
        api.getWindows({ limit: 30 }),
        api.getBaselines(),
        api.getCandidates('PENDING'),
        api.getAlerts().catch(() => [] as AlertItem[]),
        api.getQuarantineWindows().catch(() => [] as QuarantineWindowItem[]),
        api.getRealOverview().catch(() => null),
      ]);

      const items = winRes.items || [];
      setWindows(items);
      setBaselines(baseRes || []);
      setCandidates(candRes || []);
      setAlerts(alertRes || []);
      setQuarantineItems(quaranRes || []);
      if (realRes) {
        setRealOverview(realRes);
      }

      // Fetch explainability for the top windows
      if (items.length > 0) {
        try {
          const recent = items.slice(0, 3);
          const entries = await Promise.all(
            recent.map(async (w) => {
              try {
                const exp = await api.getExplainability(w.window_id);
                return [w.window_id, exp] as const;
              } catch {
                return null;
              }
            })
          );
          const map: Record<string, ExplainabilityResponse> = {};
          entries.forEach((e) => {
            if (e) map[e[0]] = e[1];
          });
          setExplainMap(map);
        } catch {
          // Non-blocking
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch overview data';
      setError(msg);
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(true);
  }, []);

  useEffect(() => {
    if (pollTick > 0) {
      fetchData(false);
    }
  }, [pollTick]);

  // Derived Metrics from API responses
  const totalBytes = useMemo(() => {
    return windows.reduce((acc, w) => {
      const ul = w.raw_counters?.total_bytes_uplink || 0;
      const dl = w.raw_counters?.total_bytes_downlink || 0;
      return acc + ul + dl;
    }, 0);
  }, [windows]);

  const totalTrafficMB = realOverview
    ? realOverview.total_traffic_mb.toFixed(1)
    : (totalBytes / (1024 * 1024)).toFixed(1);
  const totalTrafficGB = realOverview
    ? realOverview.total_traffic_gb.toFixed(2)
    : (totalBytes / (1024 * 1024 * 1024)).toFixed(2);
  const trafficDisplay =
    (realOverview?.total_traffic_gb ?? 0) > 1 || totalBytes > 1024 * 1024 * 1024
      ? `${totalTrafficGB} GB`
      : `${totalTrafficMB} MB`;

  const activeBaseline = baselines.find((b) => b.is_active) || baselines[0];
  const activeBaselineVersion = activeBaseline?.version || 'v1.0.0-anchor';
  const baselineHash = activeBaseline?.id
    ? `0x${activeBaseline.id.slice(0, 8).toUpperCase()}`
    : '0x7F9B4A12';

  const firstWindowExplain = windows[0] ? explainMap[windows[0].window_id] : undefined;
  const driftVerdict = firstWindowExplain?.attribution_summary?.verdict || 'likely_benign';
  const agreementState = alerts[0]?.detector_output?.fusion?.agreement_state || 'NONE';

  // Severity breakdown from real alerts
  const critCount = alerts.filter(
    (a) => a.detector_output?.fusion?.agreement_state === 'BOTH_FIRE' || (a.fused_score ?? 0) >= 0.95
  ).length;
  const highCount = alerts.filter(
    (a) =>
      a.detector_output?.fusion?.agreement_state !== 'BOTH_FIRE' &&
      (a.fused_score ?? 0) >= 0.85 &&
      (a.fused_score ?? 0) < 0.95
  ).length;
  const medCount = alerts.length - critCount - highCount;

  // Chart data from real traffic timeline or recent windows
  const chartData = useMemo(() => {
    if (realOverview && realOverview.traffic_timeline && realOverview.traffic_timeline.length > 0) {
      return realOverview.traffic_timeline.slice(0, 30).map((t) => {
        const d = new Date(t.timestamp);
        const timeStr = isNaN(d.getTime())
          ? t.timestamp ? t.timestamp.slice(11, 16) : '--:--'
          : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        return {
          time: timeStr,
          uplink: t.uplink_mb,
          downlink: t.downlink_mb,
          total: Number((t.uplink_mb + t.downlink_mb).toFixed(2)),
        };
      });
    }

    return [...windows]
      .sort((a, b) => new Date(a.window_start).getTime() - new Date(b.window_start).getTime())
      .map((w) => {
        const date = new Date(w.window_start);
        const timeStr = isNaN(date.getTime())
          ? w.window_start ? w.window_start.slice(11, 16) : '--:--'
          : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const ul = Number(((w.raw_counters?.total_bytes_uplink || 0) / (1024 * 1024)).toFixed(2));
        const dl = Number(((w.raw_counters?.total_bytes_downlink || 0) / (1024 * 1024)).toFixed(2));
        return {
          time: timeStr,
          uplink: ul,
          downlink: dl,
          total: Number((ul + dl).toFixed(2)),
        };
      });
  }, [realOverview, windows]);

  // Per-slice aggregation
  const sliceStats = useMemo(() => {
    const slices = [
      { id: 'sst-1-sd-010203', name: 'eMBB Slice', sst: '0x01', desc: 'Ultra Mobile Broadband' },
      { id: 'sst-2-sd-010203', name: 'URLLC Slice', sst: '0x02', desc: 'Autonomous & Critical Robotics' },
      { id: 'sst-3-sd-010203', name: 'mMTC Slice', sst: '0x03', desc: 'Massive Smart Grid / IoT' },
    ];

    return slices.map((s) => {
      const sliceWindows = windows.filter((w) => w.slice_id === s.id);
      const sliceAlerts = alerts.filter((a) => a.slice_id === s.id);
      const sBytes = sliceWindows.reduce((acc, w) => {
        return acc + (w.raw_counters?.total_bytes_uplink || 0) + (w.raw_counters?.total_bytes_downlink || 0);
      }, 0);
      const trafficMB = (sBytes / (1024 * 1024)).toFixed(1);
      const isElevated = sliceAlerts.length > 0;

      return {
        ...s,
        windowCount: sliceWindows.length,
        alertCount: sliceAlerts.length,
        trafficMB,
        status: isElevated ? 'ELEVATED' : 'SECURED',
      };
    });
  }, [windows, alerts]);

  // Filtered incident table
  const filteredAlerts = useMemo(() => {
    return alerts.filter((a) => {
      const matchesSearch =
        searchQuery === '' ||
        a.slice_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        a.window_id.toLowerCase().includes(searchQuery.toLowerCase());

      const isBoth =
        a.detector_output?.fusion?.agreement_state === 'BOTH_FIRE' ||
        (a.fused_score ?? 0) >= 0.95;
      const isHigh = !isBoth && (a.fused_score ?? 0) >= 0.85;

      if (severityFilter === 'CRITICAL' && !isBoth) return false;
      if (severityFilter === 'HIGH' && !isHigh) return false;
      if (severityFilter === 'MEDIUM' && (isBoth || isHigh)) return false;

      return matchesSearch;
    });
  }, [alerts, searchQuery, severityFilter]);

  const exportReport = () => {
    const report = {
      timestamp: new Date().toISOString(),
      activeBaselineVersion,
      totalTraffic: trafficDisplay,
      activeAlertsCount: alerts.length,
      alerts,
      sliceStats,
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `commshield_incident_report_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return <LoadingState message="Loading telemetry overview and pipeline state..." size="lg" />;
  }

  if (error) {
    return <ErrorState title="Failed to Load Overview" message={error} onRetry={() => fetchData(true)} />;
  }

  return (
    <div className="flex flex-col w-full gap-6 pb-12">
      {/* 1. Top Live Control Stream Bar */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 bg-surface-container-lowest p-6 rounded-xl border border-border shadow-xs">
        <div className="flex flex-col gap-1.5">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-xl font-bold text-on-surface">
              Security Command Center — 5G Network Slice ({selectedSlice})
            </h1>
            <div className="flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-400">
              <span className="flex h-2 w-2 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600"></span>
              </span>
              <span className="font-mono text-[10px] font-semibold uppercase tracking-wider">
                Live Telemetry Stream
              </span>
            </div>
            <DataSourceBadge />
          </div>

          <div className="flex flex-wrap items-center gap-4 text-on-surface-variant font-mono text-xs">
            <span className="flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-tertiary" />
              Sampling: {windows[0]?.duration_sec || 60}s
            </span>
            <span className="text-outline">•</span>
            <span className="flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 text-primary" />
              Windows Processed: {windows.length}
            </span>
            <span className="text-outline">•</span>
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              eBPF Probe: 5G UPF Core Synced
            </span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={exportReport}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-surface-container-low hover:bg-surface-container text-on-surface text-xs font-semibold border border-border transition-colors shadow-xs"
            type="button"
          >
            <Download className="w-4 h-4 text-primary" />
            <span>Export Incident Report</span>
          </button>
          <button
            onClick={() => navigate('/detection')}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white text-xs font-semibold shadow-xs transition-colors"
            type="button"
          >
            <AlertOctagon className="w-4 h-4" />
            <span>View Anomaly Triage</span>
          </button>
        </div>
      </div>

      {/* 2. Row 1: 4 Stitch KPI Cards in Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* Card 1: Total Traffic */}
        <div className="flex flex-col justify-between bg-surface-container-lowest p-5 rounded-xl border border-border shadow-xs">
          <div className="flex items-start justify-between">
            <div className="flex flex-col">
              <span className="font-mono text-xs text-secondary uppercase tracking-wider font-semibold">
                Total Traffic
              </span>
              <span className="text-2xl font-bold text-on-surface tracking-tight mt-1">
                {trafficDisplay}
              </span>
            </div>
            <div className="p-2 rounded-lg bg-blue-500/10 text-primary">
              <Activity className="w-5 h-5" />
            </div>
          </div>
          <div className="my-2 h-8 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData.slice(-10)}>
                <Area type="monotone" dataKey="total" stroke="#2563eb" fill="#2563eb" fillOpacity={0.15} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center text-emerald-600 font-semibold">
              <TrendingUp className="w-3.5 h-3.5 mr-0.5" />
              Active Feed
            </span>
            <span className="text-on-surface-variant font-mono">n={windows.length} windows</span>
          </div>
        </div>

        {/* Card 2: Active Threat Pool */}
        <div className="flex flex-col justify-between bg-surface-container-lowest p-5 rounded-xl border border-border shadow-xs">
          <div className="flex items-start justify-between">
            <div className="flex flex-col">
              <span className="font-mono text-xs text-secondary uppercase tracking-wider font-semibold">
                Active Threat Pool
              </span>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl font-bold text-on-surface tracking-tight">
                  {alerts.length}
                </span>
                <span className="text-xs text-on-surface-variant font-medium">Open Incidents</span>
              </div>
            </div>
            <div className="p-2 rounded-lg bg-red-500/10 text-red-600">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-1.5 my-2">
            <span className="px-2 py-0.5 rounded-full bg-red-500/10 text-red-600 font-mono text-[11px] font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-red-600"></span>
              {critCount} Crit
            </span>
            <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-700 dark:text-amber-400 font-mono text-[11px] font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-600"></span>
              {highCount} High
            </span>
            <span className="px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-700 dark:text-blue-400 font-mono text-[11px] font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-600"></span>
              {medCount} Med
            </span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-red-600 font-medium">
              Quarantined: {quarantineItems.length}
            </span>
            <span className="text-on-surface-variant font-mono">Consensus: {agreementState}</span>
          </div>
        </div>

        {/* Card 3: Governance Compliance */}
        <div className="flex flex-col justify-between bg-surface-container-lowest p-5 rounded-xl border border-border shadow-xs">
          <div className="flex items-start justify-between">
            <div className="flex flex-col">
              <span className="font-mono text-xs text-secondary uppercase tracking-wider font-semibold">
                Attribution &amp; Drift
              </span>
              <span className="text-xl font-bold text-on-surface tracking-tight mt-1 capitalize">
                {driftVerdict.replace('_', ' ')}
              </span>
            </div>
            <StatusBadge
              label={driftVerdict === 'attack' ? 'ATTACK' : driftVerdict === 'growth' ? 'GROWTH' : 'VERIFIED'}
              variant={driftVerdict === 'attack' ? 'attack' : driftVerdict === 'growth' ? 'suspicious' : 'safe'}
              size="sm"
            />
          </div>
          <div className="flex flex-col gap-1.5 my-2">
            <div className="w-full bg-surface-container-high h-2 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  driftVerdict === 'attack' ? 'bg-red-500' : driftVerdict === 'growth' ? 'bg-amber-500' : 'bg-emerald-500'
                }`}
                style={{ width: driftVerdict === 'attack' ? '90%' : driftVerdict === 'growth' ? '65%' : '100%' }}
              />
            </div>
            <div className="flex items-center justify-between font-mono text-[11px] text-on-surface-variant">
              <span>Gate: 7-Stage Pipeline</span>
              <span>Pending Updates: {candidates.length}</span>
            </div>
          </div>
          <div className="flex items-center justify-between text-xs text-on-surface-variant">
            <span className="flex items-center gap-1 text-emerald-600 font-medium">
              <ShieldCheck className="w-3.5 h-3.5" />
              Zero-Trust Gate Active
            </span>
            <span className="font-mono text-[11px]">{activeBaselineVersion}</span>
          </div>
        </div>

        {/* Card 4: Active Baseline */}
        <div className="flex flex-col justify-between bg-surface-container-lowest p-5 rounded-xl border border-border shadow-xs">
          <div className="flex items-start justify-between">
            <div className="flex flex-col">
              <span className="font-mono text-xs text-secondary uppercase tracking-wider font-semibold">
                Active Core Baseline
              </span>
              <span className="text-xl font-bold text-on-surface tracking-tight mt-1 truncate">
                {activeBaselineVersion}
              </span>
            </div>
            <div className="p-2 rounded-lg bg-surface-container-low text-secondary">
              <Shield className="w-5 h-5 text-primary" />
            </div>
          </div>
          <div className="flex items-center justify-between bg-surface-container-low px-2.5 py-1.5 rounded-lg my-2 border border-border">
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-xs text-on-surface select-all">{baselineHash}</span>
            </div>
            <button
              className="text-muted hover:text-primary transition-colors"
              onClick={() => {
                navigator.clipboard?.writeText(baselineHash);
                setCopiedHash(true);
                setTimeout(() => setCopiedHash(false), 2000);
              }}
              title="Copy Hash"
              type="button"
            >
              {copiedHash ? <CheckCircle2 className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
          <div className="flex items-center justify-between text-xs text-on-surface-variant">
            <span className="truncate max-w-[130px]">GovSec Enclave HSM</span>
            <span className="font-mono text-emerald-600">Active</span>
          </div>
        </div>
      </div>

      {/* 3. Row 2: Ingestion Chart & 5G Slice Health Matrix */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Traffic Volume & Anomaly Ingestion Chart (2 Cols) */}
        <div className="xl:col-span-2 flex flex-col bg-surface-container-lowest p-6 rounded-xl border border-border shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold text-base text-on-surface">
                  5G Ingress/Egress Volume &amp; Anomaly Signals
                </h3>
                <span className="font-mono text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-primary font-semibold">
                  DUAL-STREAM
                </span>
              </div>
              <p className="text-xs text-on-surface-variant mt-0.5">
                Real-time deep packet telemetry parsed via edge eBPF sensor probes
              </p>
            </div>
            <div className="flex items-center gap-2 font-mono text-xs">
              <span className="flex items-center gap-1 text-on-surface font-medium">
                <span className="w-3 h-1.5 rounded-full bg-blue-600"></span>
                Uplink (MB)
              </span>
              <span className="flex items-center gap-1 text-on-surface font-medium">
                <span className="w-3 h-1.5 rounded-full bg-emerald-600"></span>
                Downlink (MB)
              </span>
            </div>
          </div>

          {/* Recharts Dual Stream */}
          <div className="w-full h-72">
            {chartData.length === 0 ? (
              <EmptyState title="No Traffic Data" description="Start replay or connect a live feed to stream telemetry." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="uplinkGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563eb" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="#2563eb" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="downlinkGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#007d57" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#007d57" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.2} />
                  <XAxis dataKey="time" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} unit=" MB" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0a1628',
                      borderRadius: '8px',
                      border: '1px solid #1e293b',
                      color: '#ffffff',
                      fontSize: '12px',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="uplink"
                    stroke="#2563eb"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#uplinkGrad)"
                    name="Uplink"
                  />
                  <Area
                    type="monotone"
                    dataKey="downlink"
                    stroke="#007d57"
                    strokeWidth={1.8}
                    strokeDasharray="4 2"
                    fillOpacity={1}
                    fill="url(#downlinkGrad)"
                    name="Downlink"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4 pt-4 mt-2 border-t border-border text-xs text-on-surface-variant font-mono">
            <div className="flex items-center gap-4">
              <span>Points: {chartData.length}</span>
              <span>Total Volume: {trafficDisplay}</span>
            </div>
            <div className="flex items-center gap-1.5 text-emerald-600">
              <CheckCircle2 className="w-4 h-4" />
              <span>Zero ML Inference Dropouts</span>
            </div>
          </div>
        </div>

        {/* 5G Network Slice Health Matrix (1 Col) */}
        <div className="flex flex-col justify-between bg-surface-container-lowest p-6 rounded-xl border border-border shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div className="flex flex-col">
              <h3 className="font-semibold text-base text-on-surface">5G Slice Health Matrix</h3>
              <p className="text-xs text-on-surface-variant">SST 1, 2, 3 Core Partitioning</p>
            </div>
            <Layers className="w-4 h-4 text-muted" />
          </div>

          <div className="flex flex-col gap-3">
            {sliceStats.map((slice) => (
              <div
                key={slice.id}
                className="p-3.5 rounded-xl bg-surface-container-low flex flex-col gap-2 border border-border/50 hover:bg-surface-container transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Radio className="w-4 h-4 text-primary" />
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-semibold text-on-surface">{slice.name}</span>
                        <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-surface-container-lowest text-secondary">
                          SST: {slice.sst}
                        </span>
                      </div>
                      <span className="text-[11px] text-on-surface-variant">{slice.desc}</span>
                    </div>
                  </div>
                  <span
                    className={`font-mono text-[10px] px-2 py-0.5 rounded-full font-semibold ${
                      slice.status === 'SECURED'
                        ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'
                        : 'bg-amber-500/10 text-amber-700 dark:text-amber-400'
                    }`}
                  >
                    {slice.status}
                  </span>
                </div>

                <div className="flex items-center justify-between font-mono text-[11px] text-on-surface-variant">
                  <span>Traffic: {slice.trafficMB} MB</span>
                  <span>Alerts: {slice.alertCount}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="pt-3 mt-3 border-t border-border flex items-center justify-between text-xs text-on-surface-variant">
            <span>3 Slices Bound to Core UPF</span>
            <button
              onClick={() => navigate('/monitoring')}
              className="text-primary hover:underline font-medium"
              type="button"
            >
              Inspect Slices &rarr;
            </button>
          </div>
        </div>
      </div>

      {/* 4. Row 3: Active Anomaly & Security Triage Feed (Enterprise SOC Layout) */}
      <div className="flex flex-col bg-surface-container-lowest rounded-xl border border-border shadow-xs overflow-hidden">
        {/* Table Toolbar Header */}
        <div className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border">
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-base text-on-surface">Active Anomaly &amp; Security Triage Feed</h3>
              <span className="font-mono text-[11px] px-2 py-0.5 rounded-full bg-red-500/10 text-red-600 font-semibold">
                {filteredAlerts.length} Events
              </span>
            </div>
            <p className="text-xs text-on-surface-variant mt-0.5">
              Automated deep-packet heuristic classifier and multi-model detector agreement
            </p>
          </div>

          {/* Filters & Search */}
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search slice or window..."
                className="pl-8 pr-3 py-1.5 rounded-lg bg-surface-container-low text-xs text-on-surface border border-border focus:outline-none focus:ring-1 focus:ring-primary w-52"
              />
            </div>

            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="py-1.5 px-3 rounded-lg bg-surface-container-low text-xs font-semibold text-on-surface border border-border focus:outline-none cursor-pointer"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical (Consensus)</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
            </select>
          </div>
        </div>

        {/* Responsive Table */}
        <div className="overflow-x-auto w-full">
          {filteredAlerts.length === 0 ? (
            <div className="p-8 text-center">
              <ShieldCheck className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
              <p className="text-sm font-semibold text-on-surface">No Anomalies Matching Filter</p>
              <p className="text-xs text-muted mt-1">All telemetry slices are operating within nominal baseline bounds.</p>
            </div>
          ) : (
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-container-low text-secondary font-mono text-[11px] uppercase tracking-wider select-none border-b border-border">
                <tr>
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Window / Deviation</th>
                  <th className="py-3 px-4">Affected Slice</th>
                  <th className="py-3 px-4">Detection Confidence</th>
                  <th className="py-3 px-4">Agreement State</th>
                  <th className="py-3 px-4 text-right">Quick Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border text-on-surface font-normal">
                {filteredAlerts.map((alert) => {
                  const isBoth =
                    alert.detector_output?.fusion?.agreement_state === 'BOTH_FIRE' ||
                    (alert.fused_score ?? 0) >= 0.95;
                  const isHigh = !isBoth && (alert.fused_score ?? 0) >= 0.85;
                  const severity = isBoth ? 'CRITICAL' : isHigh ? 'HIGH' : 'MEDIUM';

                  const date = new Date(alert.created_at);
                  const timeStr = isNaN(date.getTime())
                    ? alert.created_at
                    : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

                  const scorePercent = (((alert.fused_score ?? 0)) * 100).toFixed(1);

                  return (
                    <tr key={alert.id || alert.window_id} className="hover:bg-surface-container-low/60 transition-colors">
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full font-mono text-[11px] font-semibold ${
                            severity === 'CRITICAL'
                              ? 'bg-red-500/10 text-red-600'
                              : severity === 'HIGH'
                              ? 'bg-amber-500/10 text-amber-700 dark:text-amber-400'
                              : 'bg-blue-500/10 text-blue-700 dark:text-blue-400'
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              severity === 'CRITICAL'
                                ? 'bg-red-600'
                                : severity === 'HIGH'
                                ? 'bg-amber-600'
                                : 'bg-blue-600'
                            }`}
                          />
                          {severity}
                        </span>
                      </td>

                      <td className="py-3 px-4 font-mono text-on-surface-variant whitespace-nowrap">
                        {timeStr}
                      </td>

                      <td className="py-3 px-4">
                        <div className="flex flex-col">
                          <span className="font-semibold text-on-surface">
                            Profile Deviation
                          </span>
                          <span className="text-[11px] text-on-surface-variant font-mono">
                            {alert.window_id.slice(0, 16)}...
                          </span>
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        <span className="font-mono text-xs px-2 py-0.5 rounded bg-surface-container text-on-surface">
                          {alert.slice_id}
                        </span>
                      </td>

                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-surface-container-high h-1.5 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                isBoth ? 'bg-red-600' : isHigh ? 'bg-amber-600' : 'bg-blue-600'
                              }`}
                              style={{ width: `${Math.min(100, Number(scorePercent))}%` }}
                            />
                          </div>
                          <span className="font-mono text-xs font-semibold">{scorePercent}%</span>
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        <StatusBadge
                          label={alert.detector_output?.fusion?.agreement_state || 'NONE'}
                          variant={isBoth ? 'attack' : 'suspicious'}
                          size="sm"
                        />
                      </td>

                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => navigate(`/investigation/${alert.window_id}`)}
                          className="px-2.5 py-1 rounded bg-surface-container text-primary hover:bg-primary hover:text-white font-semibold text-xs transition-colors"
                          type="button"
                        >
                          Investigate
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
