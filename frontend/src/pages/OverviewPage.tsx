import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  GitBranch,
  Layers,
  Radio,
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
  ChartCard,
  Column,
  DataTable,
  EmptyState,
  ErrorState,
  LoadingState,
  SampleDataBadge,
  StatCard,
  StatusBadge,
} from '../components';
import {
  AlertItem,
  api,
  BaselineSummaryResponse,
  CandidateResponse,
  CanonicalTrafficWindow,
  ExplainabilityResponse,
} from '../services/api';
import { useReplay } from '../context/ReplayContext';

export const OverviewPage: React.FC = () => {
  const { pollTick } = useReplay();

  const [windows, setWindows] = useState<CanonicalTrafficWindow[]>([]);
  const [baselines, setBaselines] = useState<BaselineSummaryResponse[]>([]);
  const [candidates, setCandidates] = useState<CandidateResponse[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [explainMap, setExplainMap] = useState<Record<string, ExplainabilityResponse>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [windowsPlaceholder, setWindowsPlaceholder] = useState(false);

  const fetchData = async (isInitial = false) => {
    if (isInitial) setLoading(true);
    setError(null);
    try {
      const [winRes, baseRes, candRes, alertRes] = await Promise.all([
        api.getWindows({ limit: 20 }),
        api.getBaselines(),
        api.getCandidates('PENDING'),
        api.getAlerts().catch(() => [] as AlertItem[]),
      ]);

      const items = winRes.items || [];
      setWindows(items);
      setWindowsPlaceholder(winRes.is_placeholder === true);

      setBaselines(baseRes || []);
      setCandidates(candRes || []);
      setAlerts(alertRes || []);

      // Fetch explainability for recent windows
      if (items.length > 0) {
        try {
          const exp = await api.getExplainability(items[0].window_id);
          setExplainMap({ [items[0].window_id]: exp });
        } catch {
          // Non-blocking explainability fetch
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch overview data';
      setError(msg);
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchData(true);
  }, []);

  // Poll when replay ticks
  useEffect(() => {
    if (pollTick > 0) {
      fetchData(false);
    }
  }, [pollTick]);

  if (loading) {
    return <LoadingState message="Loading telemetry overview and pipeline state..." size="lg" />;
  }

  if (error) {
    return <ErrorState title="Failed to Load Overview" message={error} onRetry={() => fetchData(true)} />;
  }

  // Derived Metrics from live API responses
  const totalBytes = windows.reduce((acc, w) => {
    const ul = w.raw_counters?.total_bytes_uplink || 0;
    const dl = w.raw_counters?.total_bytes_downlink || 0;
    return acc + ul + dl;
  }, 0);

  const totalTrafficMB = (totalBytes / (1024 * 1024)).toFixed(1);
  const totalTrafficGB = (totalBytes / (1024 * 1024 * 1024)).toFixed(2);
  const trafficDisplay = totalBytes > 1024 * 1024 * 1024 ? `${totalTrafficGB} GB` : `${totalTrafficMB} MB`;

  const uniqueSlices = Array.from(new Set(windows.map((w) => w.slice_id).filter(Boolean)));
  const activeSlicesCount = uniqueSlices.length || (baselines.length > 0 ? baselines.length : 3);

  const activeBaseline = baselines.find((b) => b.is_active) || baselines[0];
  const activeBaselineVersion = activeBaseline?.version || 'v1.0.0-anchor';

  const pendingUpdatesCount = candidates.filter((c) => c.status === 'PENDING').length;

  const firstWindowExplain = windows[0] ? explainMap[windows[0].window_id] : undefined;
  const isAnomalous = alerts.length > 0 || (firstWindowExplain?.is_anomalous ?? false);
  const driftVerdict = firstWindowExplain?.attribution_summary?.verdict || 'likely_benign';
  const driftReason = firstWindowExplain?.attribution_summary?.abstain_reason;

  const quarantinedCount = windows.filter(
    (w) => explainMap[w.window_id]?.attribution_summary?.verdict === 'uncertain'
  ).length;

  // Chart Data: traffic volume over time from windows
  const chartData = [...windows]
    .sort((a, b) => new Date(a.window_start).getTime() - new Date(b.window_start).getTime())
    .map((w) => {
      const date = new Date(w.window_start);
      const timeStr = isNaN(date.getTime())
        ? (w.window_start ? w.window_start.slice(11, 16) : '--:--')
        : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      return {
        time: timeStr,
        uplink: Number(((w.raw_counters?.total_bytes_uplink || 0) / (1024 * 1024)).toFixed(2)),
        downlink: Number(((w.raw_counters?.total_bytes_downlink || 0) / (1024 * 1024)).toFixed(2)),
      };
    });

  // Alerts Table Columns
  const alertColumns: Column<CanonicalTrafficWindow>[] = [
    {
      key: 'timestamp',
      header: 'Window Time',
      render: (w) => {
        const d = new Date(w.window_start);
        return (
          <span className="font-mono text-xs text-text">
            {isNaN(d.getTime()) ? w.window_start : d.toLocaleString([], { dateStyle: 'short', timeStyle: 'medium' })}
          </span>
        );
      },
    },
    {
      key: 'window_id',
      header: 'Window ID',
      render: (w) => <span className="font-mono text-xs text-muted">{w.window_id.slice(0, 12)}...</span>,
    },
    {
      key: 'slice_id',
      header: 'S-NSSAI Slice',
      render: (w) => <span className="font-semibold text-xs text-slate">{w.slice_id}</span>,
    },
    {
      key: 'nf_id',
      header: 'Network Function',
      render: (w) => (
        <span className="inline-flex items-center gap-1 text-xs">
          <Layers className="w-3.5 h-3.5 text-muted" />
          {w.nf_id}
        </span>
      ),
    },
    {
      key: 'duration',
      header: 'Duration',
      render: (w) => <span className="text-xs text-muted">{w.duration_sec}s</span>,
    },
    {
      key: 'alert_state',
      header: 'Detection / Status',
      render: (w) => {
        const isAlerted = alerts.some((a) => a.window_id === w.window_id) || explainMap[w.window_id]?.is_anomalous;
        if (isAlerted) {
          return <StatusBadge label="Anomaly Flagged" variant="attack" size="sm" dot />;
        }
        return <StatusBadge label="Nominal Benign" variant="safe" size="sm" dot />;
      },
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text">Overview</h1>
          <p className="text-sm text-muted mt-0.5">
            5G Core zero-trust telemetry stream, anomaly alerts, and active baseline status.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <SampleDataBadge isPlaceholder={windowsPlaceholder} />
        </div>
      </div>

      {/* 1. Stat Cards Grid (7 key indicators per design) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. Total Traffic */}
        <StatCard
          title="Total Traffic Volume"
          value={trafficDisplay}
          subtitle={`${windows.length} windows captured`}
          icon={<TrendingUp className="w-4 h-4 text-blue" />}
          badge={windowsPlaceholder ? 'Sample data' : undefined}
          badgeVariant="neutral"
        />

        {/* 2. Active Slices */}
        <StatCard
          title="Active Slices"
          value={activeSlicesCount}
          subtitle={uniqueSlices.join(', ') || 'eMBB, URLLC, mMTC'}
          icon={<Radio className="w-4 h-4 text-teal" />}
          badge={windowsPlaceholder ? 'Sample data' : undefined}
          badgeVariant="neutral"
        />

        {/* 3. Anomaly Alerts */}
        <StatCard
          title="Anomaly Alerts"
          value={alerts.length > 0 ? `${alerts.length} Flagged` : (isAnomalous ? '1 Flagged' : '0 Flagged')}
          subtitle={alerts.length > 0 ? 'Exceeding calibrated baseline threshold' : 'All windows operating within bounds'}
          badge={isAnomalous || alerts.length > 0 ? 'Warning' : 'Normal'}
          badgeVariant={isAnomalous || alerts.length > 0 ? 'attack' : 'safe'}
          icon={<AlertTriangle className={`w-4 h-4 ${isAnomalous || alerts.length > 0 ? 'text-attack' : 'text-safe'}`} />}
        />

        {/* 4. Drift Status */}
        <StatCard
          title="Drift Status"
          value={driftVerdict === 'likely_attack' ? 'Shift Detected' : 'Stable'}
          subtitle={driftReason ? `Abstain reason: ${driftReason}` : 'Proportional growth test evaluated'}
          badge={driftVerdict === 'likely_attack' ? 'Shift' : 'Normal'}
          badgeVariant={driftVerdict === 'likely_attack' ? 'suspicious' : 'safe'}
          icon={<Activity className="w-4 h-4 text-slate" />}
        />

        {/* 5. Quarantined Windows */}
        <StatCard
          title="Quarantined Windows"
          value={quarantinedCount}
          subtitle="Windows isolated for candidate retraining"
          badge="Quarantine"
          badgeVariant="quarantined"
          icon={<GitBranch className="w-4 h-4 text-quarantined" />}
        />

        {/* 6. Active Baseline Version */}
        <StatCard
          title="Active Baseline"
          value={activeBaselineVersion}
          subtitle={activeBaseline?.is_anchor ? 'Trusted immutable anchor' : 'Candidate adaptation baseline'}
          badge="Active"
          badgeVariant="approved"
          icon={<ShieldCheck className="w-4 h-4 text-teal" />}
        />

        {/* 7. Pending Updates */}
        <StatCard
          title="Pending Updates"
          value={pendingUpdatesCount}
          subtitle="Shadow candidates awaiting operator review"
          badge={pendingUpdatesCount > 0 ? 'Action Needed' : 'Up to Date'}
          badgeVariant={pendingUpdatesCount > 0 ? 'suspicious' : 'neutral'}
          icon={<Layers className="w-4 h-4 text-slate" />}
        />
      </div>

      {/* 2. Traffic Volume Over Time Chart */}
      <ChartCard
        title="Live Traffic Volume Over Time"
        subtitle="Uplink and Downlink megabytes aggregated across 60s windows"
        action={windowsPlaceholder ? <SampleDataBadge isPlaceholder={windowsPlaceholder} /> : undefined}
      >
        {chartData.length === 0 ? (
          <EmptyState
            title="No Traffic Windows"
            description="No traffic data has been recorded yet. Start replay to produce windows."
          />
        ) : (
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="uplinkGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3478F6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#3478F6" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="downlinkGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#14B8A6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#14B8A6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#64748B' }} stroke="#E2E8F0" />
                <YAxis tick={{ fontSize: 11, fill: '#64748B' }} stroke="#E2E8F0" unit=" MB" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderRadius: '8px',
                    border: '1px solid #E2E8F0',
                    fontSize: '12px',
                    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="uplink"
                  name="Uplink MB"
                  stroke="#3478F6"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#uplinkGrad)"
                />
                <Area
                  type="monotone"
                  dataKey="downlink"
                  name="Downlink MB"
                  stroke="#14B8A6"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#downlinkGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </ChartCard>

      {/* 3. Recent Alerts / Telemetry Windows Table */}
      <div className="bg-card rounded-xl border border-border shadow-sm p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-text">Recent Telemetry Windows</h2>
            <p className="text-xs text-muted">
              Latest canonical windows streamed through the zero-trust evaluation pipeline.
            </p>
          </div>
          <SampleDataBadge isPlaceholder={windowsPlaceholder} />
        </div>

        <DataTable
          columns={alertColumns}
          data={windows}
          keyExtractor={(w) => w.window_id}
          emptyMessage="No telemetry windows found. Start a replay to ingest data."
        />
      </div>
    </div>
  );
};

export default OverviewPage;
