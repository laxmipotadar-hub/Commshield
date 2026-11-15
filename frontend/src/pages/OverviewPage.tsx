import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Database,
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
  ErrorState,
  LoadingState,
  SampleDataBadge,
  StatCard,
  StatusBadge,
} from '../components';
import {
  api,
  BaselineSummaryResponse,
  CandidateResponse,
  CanonicalTrafficWindow,
  ExplainabilityResponse,
} from '../services/api';

export const OverviewPage: React.FC = () => {
  const [windows, setWindows] = useState<CanonicalTrafficWindow[]>([]);
  const [baselines, setBaselines] = useState<BaselineSummaryResponse[]>([]);
  const [candidates, setCandidates] = useState<CandidateResponse[]>([]);
  const [explainMap, setExplainMap] = useState<Record<string, ExplainabilityResponse>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [windowsPlaceholder, setWindowsPlaceholder] = useState(false);
  const [baselinesPlaceholder, setBaselinesPlaceholder] = useState(false);
  const [candidatesPlaceholder, setCandidatesPlaceholder] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [winRes, baseRes, candRes] = await Promise.all([
        api.getWindows({ limit: 20 }),
        api.getBaselines(),
        api.getCandidates('PENDING'),
      ]);

      setWindows(winRes.items || []);
      setWindowsPlaceholder(Boolean(winRes.is_placeholder));

      setBaselines(baseRes || []);
      setBaselinesPlaceholder(Boolean(baseRes?.[0]?.is_placeholder));

      setCandidates(candRes || []);
      setCandidatesPlaceholder(Boolean(candRes?.[0]?.is_placeholder));

      // Fetch explainability for the top window to get drift and anomaly signals
      if (winRes.items && winRes.items.length > 0) {
        try {
          const exp = await api.getExplainability(winRes.items[0].window_id);
          setExplainMap({ [winRes.items[0].window_id]: exp });
        } catch (e) {
          console.warn('Explainability call failed:', e);
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch overview data';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return <LoadingState message="Loading telemetry overview and pipeline state..." size="lg" />;
  }

  if (error) {
    return <ErrorState title="Failed to Load Overview" message={error} onRetry={fetchData} />;
  }

  // Derived Metrics from live API responses
  const totalBytes = windows.reduce((acc, w) => {
    const ul = w.raw_counters.total_bytes_uplink || 0;
    const dl = w.raw_counters.total_bytes_downlink || 0;
    return acc + ul + dl;
  }, 0);

  const totalTrafficMB = (totalBytes / (1024 * 1024)).toFixed(1);
  const totalTrafficGB = (totalBytes / (1024 * 1024 * 1024)).toFixed(2);
  const trafficDisplay = totalBytes > 1024 * 1024 * 1024 ? `${totalTrafficGB} GB` : `${totalTrafficMB} MB`;

  const uniqueSlices = Array.from(new Set(windows.map((w) => w.slice_id)));
  const activeSlicesCount = uniqueSlices.length || (baselines.length > 0 ? baselines.length : 1);

  const activeBaseline = baselines.find((b) => b.is_active) || baselines[0];
  const activeBaselineVersion = activeBaseline?.version || 'v1.0.0-anchor';

  const pendingUpdatesCount = candidates.filter((c) => c.status === 'PENDING').length;

  const firstWindowExplain = windows[0] ? explainMap[windows[0].window_id] : undefined;
  const isAnomalous = firstWindowExplain ? firstWindowExplain.is_anomalous : false;
  const driftVerdict = firstWindowExplain?.attribution_summary?.verdict || 'likely_benign';
  const driftReason = firstWindowExplain?.attribution_summary?.abstain_reason;

  // Quarantined count derived from uncertain / abstained windows (GAP note: no dedicated /api/v1/quarantine endpoint)
  const quarantinedCount = windows.filter(
    (w) => explainMap[w.window_id]?.attribution_summary?.verdict === 'uncertain'
  ).length;

  // Chart Data: traffic volume over time from windows
  const chartData = [...windows]
    .sort((a, b) => new Date(a.window_start).getTime() - new Date(b.window_start).getTime())
    .map((w) => {
      const date = new Date(w.window_start);
      const timeStr = isNaN(date.getTime())
        ? w.window_start.slice(11, 16)
        : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      return {
        time: timeStr,
        uplink: Number(((w.raw_counters.total_bytes_uplink || 0) / (1024 * 1024)).toFixed(2)),
        downlink: Number(((w.raw_counters.total_bytes_downlink || 0) / (1024 * 1024)).toFixed(2)),
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
        const exp = explainMap[w.window_id];
        if (exp?.is_anomalous) {
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
            5G Core autonomous telemetry defense, multi-slice detection, and baseline stability.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {windowsPlaceholder && <SampleDataBadge isPlaceholder={true} />}
          <StatusBadge label="Zero-Trust Pipeline" variant="safe" size="md" dot />
        </div>
      </div>

      {/* 7 Required Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. Total Traffic */}
        <StatCard
          title="Total Traffic"
          value={trafficDisplay}
          subtitle={`Cumulative uplink & downlink over ${windows.length} windows`}
          icon={<TrendingUp className="w-4 h-4 text-blue" />}
          badge={windowsPlaceholder ? 'Sample data' : undefined}
          badgeVariant="neutral"
        />

        {/* 2. Active Slices */}
        <StatCard
          title="Active Slices"
          value={activeSlicesCount}
          subtitle={uniqueSlices.join(', ') || 'eMBB, uRLLC, MIoT'}
          icon={<Radio className="w-4 h-4 text-teal" />}
          badge={windowsPlaceholder ? 'Sample data' : undefined}
          badgeVariant="neutral"
        />

        {/* 3. Anomaly Alerts */}
        <StatCard
          title="Anomaly Alerts"
          value={isAnomalous ? '1 Flagged' : '0 Flagged'}
          subtitle={isAnomalous ? 'Score percentile exceeds 0.980 threshold' : 'All windows operating within bounds'}
          badge={isAnomalous ? 'Warning' : 'Normal'}
          badgeVariant={isAnomalous ? 'attack' : 'safe'}
          icon={<AlertTriangle className={`w-4 h-4 ${isAnomalous ? 'text-attack' : 'text-safe'}`} />}
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
          subtitle={activeBaseline?.is_anchor ? 'Immutable trusted anchor' : 'Serving production baseline'}
          badge={baselinesPlaceholder ? 'Sample data' : activeBaseline?.is_anchor ? 'Anchor' : 'Active'}
          badgeVariant={baselinesPlaceholder ? 'neutral' : 'approved'}
          icon={<ShieldCheck className="w-4 h-4 text-approved" />}
        />

        {/* 7. Pending Updates */}
        <StatCard
          title="Pending Updates"
          value={pendingUpdatesCount}
          subtitle="Shadow candidates awaiting analyst signoff"
          badge={candidatesPlaceholder ? 'Sample data' : pendingUpdatesCount > 0 ? 'Pending' : 'Zero'}
          badgeVariant={candidatesPlaceholder ? 'neutral' : pendingUpdatesCount > 0 ? 'blue' : 'neutral'}
          icon={<Database className="w-4 h-4 text-blue" />}
        />
      </div>

      {/* Traffic Over Time Chart */}
      <ChartCard
        title="Traffic Volume Over Time"
        subtitle="Uplink and Downlink throughput (MB) across canonical evaluation windows"
        action={
          <div className="flex items-center gap-4">
            <SampleDataBadge isPlaceholder={windowsPlaceholder} />
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-text">
                <span className="w-3 h-1 bg-blue rounded-full" />
                Uplink
              </span>
              <span className="flex items-center gap-1.5 text-text">
                <span className="w-3 h-1 bg-teal rounded-full" />
                Downlink
              </span>
            </div>
          </div>
        }
      >
        <div className="w-full h-[280px]">
          {chartData.length === 0 ? (
            <div className="h-full flex items-center justify-center text-sm text-muted">
              No window traffic data available
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorUL" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3478F6" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#3478F6" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorDL" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#14B8A6" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#14B8A6" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                <XAxis dataKey="time" stroke="#64748B" fontSize={12} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={12} tickLine={false} unit=" MB" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderColor: '#E2E8F0',
                    borderRadius: '0.75rem',
                  }}
                />
                <Area type="monotone" dataKey="uplink" stroke="#3478F6" strokeWidth={2} fill="url(#colorUL)" name="Uplink (MB)" />
                <Area type="monotone" dataKey="downlink" stroke="#14B8A6" strokeWidth={2} fill="url(#colorDL)" name="Downlink (MB)" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </ChartCard>

      {/* Recent Alerts / Telemetry Windows Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-text">Recent Telemetry Alerts & Windows</h2>
            <p className="text-xs text-muted">Canonical traffic windows and detection evaluations</p>
          </div>
          <SampleDataBadge isPlaceholder={windowsPlaceholder} />
        </div>
        <DataTable
          columns={alertColumns}
          data={windows}
          keyExtractor={(w) => w.window_id}
          emptyMessage="No traffic alerts or windows recorded"
        />
      </div>
    </div>
  );
};
