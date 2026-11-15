import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertOctagon,
  GitBranch,
  ShieldCheck,
  Radio,
  Layers,
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
  DataTable,
  StatCard,
  StatusBadge,
  Column,
} from '../components';
import { api, CanonicalTrafficWindow } from '../services/api';

const sampleChartData = [
  { time: '12:00', if_score: 0.12, ae_error: 0.08, threshold: 0.98 },
  { time: '12:05', if_score: 0.15, ae_error: 0.11, threshold: 0.98 },
  { time: '12:10', if_score: 0.22, ae_error: 0.14, threshold: 0.98 },
  { time: '12:15', if_score: 0.18, ae_error: 0.09, threshold: 0.98 },
  { time: '12:20', if_score: 0.35, ae_error: 0.21, threshold: 0.98 },
  { time: '12:25', if_score: 0.42, ae_error: 0.28, threshold: 0.98 },
  { time: '12:30', if_score: 0.88, ae_error: 0.65, threshold: 0.98 },
  { time: '12:35', if_score: 0.99, ae_error: 0.92, threshold: 0.98 },
  { time: '12:40', if_score: 0.54, ae_error: 0.39, threshold: 0.98 },
  { time: '12:45', if_score: 0.29, ae_error: 0.19, threshold: 0.98 },
];

export const OverviewView: React.FC = () => {
  const [windows, setWindows] = useState<CanonicalTrafficWindow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getWindows({ limit: 5 })
      .then((res) => {
        setWindows(res.items);
      })
      .catch((err) => {
        console.warn('Failed to fetch windows in Overview:', err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const columns: Column<CanonicalTrafficWindow>[] = [
    {
      key: 'window_id',
      header: 'Window ID',
      render: (w) => (
        <span className="font-mono text-xs text-text">{w.window_id.slice(0, 12)}...</span>
      ),
    },
    {
      key: 'slice_id',
      header: 'Slice S-NSSAI',
      render: (w) => (
        <span className="font-semibold text-xs text-slate">{w.slice_id}</span>
      ),
    },
    {
      key: 'nf_id',
      header: 'Network Function',
      render: (w) => (
        <span className="inline-flex items-center gap-1 text-xs text-text">
          <Layers className="w-3.5 h-3.5 text-muted" />
          {w.nf_id}
        </span>
      ),
    },
    {
      key: 'duration_sec',
      header: 'Scale',
      render: (w) => <span className="text-xs text-muted">{w.duration_sec}s</span>,
    },
    {
      key: 'status',
      header: 'Attribution State',
      render: (w) => (
        <StatusBadge
          label={w.is_placeholder ? 'Placeholder' : 'Live'}
          variant={w.is_placeholder ? 'neutral' : 'safe'}
          size="sm"
          dot
        />
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text">Overview</h1>
          <p className="text-sm text-muted mt-0.5">
            Real-time 5G core telemetry monitoring, multi-model anomaly detection, and baseline health.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge label="Zero-Trust Enforced" variant="safe" size="md" dot />
          <StatusBadge label="Replay Active" variant="blue" size="md" />
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Monitored Slices"
          value="3 Slices"
          change="+1 this week"
          trend="up"
          subtitle="eMBB-01, uRLLC-02, MIoT-03"
          icon={<Radio className="w-4 h-4 text-blue" />}
        />
        <StatCard
          title="Anomaly Flag Rate"
          value="1.24%"
          change="-0.38%"
          trend="down"
          subtitle="Fused IF + AE score > 98th %ile"
          icon={<AlertOctagon className="w-4 h-4 text-attack" />}
        />
        <StatCard
          title="JSD Drift Metric"
          value="0.0124"
          change="Within null bounds"
          trend="neutral"
          subtitle="Threshold: 0.0350 (99th %ile)"
          badge="Stable"
          badgeVariant="safe"
          icon={<Activity className="w-4 h-4 text-teal" />}
        />
        <StatCard
          title="Active Serving Baseline"
          value="v1.0.0-anchor"
          subtitle="Immutable trusted anchor verified"
          badge="Gated"
          badgeVariant="approved"
          icon={<ShieldCheck className="w-4 h-4 text-approved" />}
        />
      </div>

      {/* Primary Chart Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <ChartCard
          title="Detection Score Trend"
          subtitle="Percentile calibrated scores from Isolation Forest & Autoencoder vs 98th %ile threshold"
          className="lg:col-span-2"
          action={
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-text">
                <span className="w-3 h-0.5 bg-blue rounded-full" />
                IF Score
              </span>
              <span className="flex items-center gap-1.5 text-text">
                <span className="w-3 h-0.5 bg-teal rounded-full" />
                AE Error
              </span>
              <span className="flex items-center gap-1.5 text-attack font-medium">
                <span className="w-3 h-0.5 bg-attack border border-dashed border-attack" />
                Threshold
              </span>
            </div>
          }
        >
          <div className="w-full h-[260px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={sampleChartData}>
                <defs>
                  <linearGradient id="colorIF" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3478F6" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#3478F6" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorAE" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#14B8A6" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#14B8A6" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                <XAxis dataKey="time" stroke="#64748B" fontSize={12} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={12} tickLine={false} domain={[0, 1.2]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderColor: '#E2E8F0',
                    borderRadius: '0.75rem',
                    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="if_score"
                  stroke="#3478F6"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorIF)"
                />
                <Area
                  type="monotone"
                  dataKey="ae_error"
                  stroke="#14B8A6"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorAE)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        {/* Quick Health Summary Card */}
        <div className="bg-card rounded-xl border border-border p-5 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-base font-semibold text-text">Zero-Trust Pipeline Status</h3>
            <p className="text-xs text-muted mt-0.5">Continuous defense architecture state</p>

            <div className="mt-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-border/60">
                <div className="flex items-center gap-2 text-sm text-text">
                  <Activity className="w-4 h-4 text-blue" />
                  <span>Streaming Normalizer</span>
                </div>
                <StatusBadge label="Operational" variant="safe" size="sm" dot />
              </div>

              <div className="flex items-center justify-between pb-3 border-b border-border/60">
                <div className="flex items-center gap-2 text-sm text-text">
                  <AlertOctagon className="w-4 h-4 text-teal" />
                  <span>Dual Detectors (IF + AE)</span>
                </div>
                <StatusBadge label="Active" variant="safe" size="sm" dot />
              </div>

              <div className="flex items-center justify-between pb-3 border-b border-border/60">
                <div className="flex items-center gap-2 text-sm text-text">
                  <GitBranch className="w-4 h-4 text-quarantined" />
                  <span>ADWIN Drift Tracker</span>
                </div>
                <StatusBadge label="Listening" variant="blue" size="sm" dot />
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-text">
                  <ShieldCheck className="w-4 h-4 text-approved" />
                  <span>Canary Safety Gate</span>
                </div>
                <StatusBadge label="Gated" variant="approved" size="sm" dot />
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-border/60 text-xs text-muted flex items-center justify-between">
            <span>Last Heartbeat: 2s ago</span>
            <span className="font-mono text-slate">latency: 18ms</span>
          </div>
        </div>
      </div>

      {/* Recent Windows Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-text">Recent Canonical Windows</h2>
            <p className="text-xs text-muted">Latest 60s normalized telemetry traffic windows</p>
          </div>
        </div>
        <DataTable
          columns={columns}
          data={windows}
          keyExtractor={(w) => w.window_id}
          isLoading={loading}
          emptyMessage="No traffic windows available"
        />
      </div>
    </div>
  );
};
