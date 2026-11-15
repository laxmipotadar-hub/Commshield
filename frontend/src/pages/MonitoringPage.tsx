import React, { useEffect, useState, useMemo } from 'react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
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
import { api, CanonicalTrafficWindow } from '../services/api';
import { Radio, Layers, HardDrive } from 'lucide-react';

const SLICE_COLORS = ['#3478F6', '#14B8A6', '#8B5CF6', '#F59E0B', '#142B4A'];

export const MonitoringPage: React.FC = () => {
  const [sliceFilter, setSliceFilter] = useState<string>('ALL');
  const [timeRangeLimit, setTimeRangeLimit] = useState<number>(20);
  const [windows, setWindows] = useState<CanonicalTrafficWindow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPlaceholder, setIsPlaceholder] = useState(false);

  const fetchMonitoringData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getWindows({
        slice_id: sliceFilter !== 'ALL' ? sliceFilter : undefined,
        limit: timeRangeLimit,
      });
      setWindows(res.items || []);
      setIsPlaceholder(Boolean(res.is_placeholder));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch network monitoring data';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMonitoringData();
  }, [sliceFilter, timeRangeLimit]);

  // Derived: Traffic volume over time
  const trafficTimeData = useMemo(() => {
    return [...windows]
      .sort((a, b) => new Date(a.window_start).getTime() - new Date(b.window_start).getTime())
      .map((w) => {
        const d = new Date(w.window_start);
        const timeStr = isNaN(d.getTime())
          ? w.window_start.slice(11, 16)
          : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        return {
          time: timeStr,
          uplink_mb: Number(((w.raw_counters.total_bytes_uplink || 0) / 1048576).toFixed(2)),
          downlink_mb: Number(((w.raw_counters.total_bytes_downlink || 0) / 1048576).toFixed(2)),
        };
      });
  }, [windows]);

  // Derived: Distribution across slices
  const sliceDistributionData = useMemo(() => {
    const map: Record<string, number> = {};
    windows.forEach((w) => {
      const bytes = (w.raw_counters.total_bytes_uplink || 0) + (w.raw_counters.total_bytes_downlink || 0);
      map[w.slice_id] = (map[w.slice_id] || 0) + bytes;
    });
    return Object.entries(map).map(([name, bytes]) => ({
      name,
      value: Number((bytes / 1048576).toFixed(2)),
    }));
  }, [windows]);

  // Derived: Network Function activity
  const nfActivityData = useMemo(() => {
    const map: Record<string, { packets: number; bytes: number; ues: number }> = {};
    windows.forEach((w) => {
      const current = map[w.nf_id] || { packets: 0, bytes: 0, ues: 0 };
      current.packets += w.raw_counters.total_packets || 0;
      current.bytes += (w.raw_counters.total_bytes_uplink || 0) + (w.raw_counters.total_bytes_downlink || 0);
      current.ues = Math.max(current.ues, w.raw_counters.active_ue_count || 0);
      map[w.nf_id] = current;
    });
    return Object.entries(map).map(([nf, d]) => ({
      nf_id: nf,
      packets: d.packets,
      volume_mb: Number((d.bytes / 1048576).toFixed(1)),
      active_ues: d.ues,
    }));
  }, [windows]);

  // Derived: Registration and session failure rates
  const failureRatesData = useMemo(() => {
    return [...windows]
      .sort((a, b) => new Date(a.window_start).getTime() - new Date(b.window_start).getTime())
      .map((w) => {
        const d = new Date(w.window_start);
        const timeStr = isNaN(d.getTime())
          ? w.window_start.slice(11, 16)
          : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        return {
          time: timeStr,
          nas_failure_pct: Number(((w.ratio_features.nas_failure_ratio || 0) * 100).toFixed(3)),
          pfcp_failure_pct: Number(((w.ratio_features.pfcp_failure_ratio || 0) * 100).toFixed(3)),
          reg_rate: Number((w.ratio_features.registrations_per_active_ue || 0).toFixed(4)),
        };
      });
  }, [windows]);

  // Derived: Normalised traffic composition
  const compositionData = useMemo(() => {
    return [...windows]
      .sort((a, b) => new Date(a.window_start).getTime() - new Date(b.window_start).getTime())
      .map((w) => {
        const d = new Date(w.window_start);
        const timeStr = isNaN(d.getTime())
          ? w.window_start.slice(11, 16)
          : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const c = w.composition_vector || {};
        return {
          time: timeStr,
          session_setup: Number(((c.session_setup_ratio || 0) * 100).toFixed(1)),
          registration: Number(((c.registration_ratio || 0) * 100).toFixed(1)),
          failure: Number(((c.failure_ratio || 0) * 100).toFixed(2)),
          other: Number(((c.other_signalling_ratio || 0) * 100).toFixed(1)),
        };
      });
  }, [windows]);

  // Aggregate stats
  const totalUEs = windows.reduce((max, w) => Math.max(max, w.raw_counters.active_ue_count || 0), 0);
  const avgNasFailure = windows.length > 0
    ? (windows.reduce((sum, w) => sum + (w.ratio_features.nas_failure_ratio || 0), 0) / windows.length * 100).toFixed(3)
    : '0.000';
  const totalVolumeMB = (
    windows.reduce((sum, w) => sum + (w.raw_counters.total_bytes_uplink || 0) + (w.raw_counters.total_bytes_downlink || 0), 0) / 1048576
  ).toFixed(1);

  const nfColumns: Column<{ nf_id: string; packets: number; volume_mb: number; active_ues: number }>[] = [
    {
      key: 'nf_id',
      header: 'Network Function',
      render: (item) => (
        <span className="font-semibold text-xs text-text flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-blue" />
          {item.nf_id}
        </span>
      ),
    },
    {
      key: 'volume_mb',
      header: 'Processed Volume',
      render: (item) => <span className="font-mono text-xs">{item.volume_mb} MB</span>,
    },
    {
      key: 'packets',
      header: 'Packets Count',
      render: (item) => <span className="font-mono text-xs text-muted">{item.packets.toLocaleString()}</span>,
    },
    {
      key: 'active_ues',
      header: 'Max Concurrent UEs',
      render: (item) => <span className="text-xs font-semibold text-slate">{item.active_ues}</span>,
    },
  ];

  if (loading) {
    return <LoadingState message="Querying live 5G core telemetry streams..." size="lg" />;
  }

  if (error) {
    return <ErrorState title="Telemetry Error" message={error} onRetry={fetchMonitoringData} />;
  }

  return (
    <div className="space-y-6">
      {/* Header and Filter Controls */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-card p-4 rounded-xl border border-border shadow-sm">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text">Network Monitoring</h1>
          <p className="text-sm text-muted mt-0.5">
            Real-time telemetry aggregation, failure rates, and traffic composition across slices.
          </p>
        </div>

        {/* Slice Filter and Time-Range Selector */}
        <div className="flex flex-wrap items-center gap-3">
          <SampleDataBadge isPlaceholder={isPlaceholder} />

          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-muted uppercase">Slice Filter:</span>
            <select
              value={sliceFilter}
              onChange={(e) => setSliceFilter(e.target.value)}
              className="bg-bg border border-border text-xs font-medium text-text rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue cursor-pointer"
            >
              <option value="ALL">All Network Slices</option>
              <option value="sst-1-sd-010203">sst-1-sd-010203 (eMBB-01)</option>
              <option value="sst-2-sd-020304">sst-2-sd-020304 (uRLLC-02)</option>
              <option value="sst-3-sd-030405">sst-3-sd-030405 (MIoT-03)</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-muted uppercase">Time Range:</span>
            <select
              value={timeRangeLimit}
              onChange={(e) => setTimeRangeLimit(Number(e.target.value))}
              className="bg-bg border border-border text-xs font-medium text-text rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue cursor-pointer"
            >
              <option value={10}>Last 10 Windows (10m)</option>
              <option value={20}>Last 20 Windows (20m)</option>
              <option value={50}>Last 50 Windows (50m)</option>
            </select>
          </div>
        </div>
      </div>

      {/* KPI Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          title="Monitored Window Traffic"
          value={`${totalVolumeMB} MB`}
          subtitle={`Aggregated volume over ${windows.length} windows`}
          icon={<HardDrive className="w-4 h-4 text-blue" />}
        />
        <StatCard
          title="Max Concurrent UEs"
          value={totalUEs.toLocaleString()}
          subtitle="Peak active subscribers in slice"
          icon={<Radio className="w-4 h-4 text-teal" />}
        />
        <StatCard
          title="Mean NAS Failure Rate"
          value={`${avgNasFailure}%`}
          subtitle="Control plane rejection ratio"
          badge={Number(avgNasFailure) > 1.0 ? 'Elevated' : 'Nominal'}
          badgeVariant={Number(avgNasFailure) > 1.0 ? 'suspicious' : 'safe'}
          icon={<Radio className="w-4 h-4 text-slate" />}
        />
      </div>

      {/* Row 1: Traffic Volume Over Time & Slice Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 1. Traffic volume over time */}
        <ChartCard
          title="Traffic Volume Over Time"
          subtitle="Uplink and Downlink throughput (MB) per window"
          className="lg:col-span-2"
          action={
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-text">
                <span className="w-3 h-1 bg-blue rounded-full" /> Uplink
              </span>
              <span className="flex items-center gap-1.5 text-text">
                <span className="w-3 h-1 bg-teal rounded-full" /> Downlink
              </span>
            </div>
          }
        >
          <div className="w-full h-[260px]">
            {trafficTimeData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-sm text-muted">No data available</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trafficTimeData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis dataKey="time" stroke="#64748B" fontSize={12} tickLine={false} />
                  <YAxis stroke="#64748B" fontSize={12} tickLine={false} unit=" MB" />
                  <Tooltip contentStyle={{ backgroundColor: '#FFFFFF', borderColor: '#E2E8F0', borderRadius: '0.75rem' }} />
                  <Area type="monotone" dataKey="uplink_mb" stroke="#3478F6" fill="#3478F6" fillOpacity={0.2} name="Uplink (MB)" />
                  <Area type="monotone" dataKey="downlink_mb" stroke="#14B8A6" fill="#14B8A6" fillOpacity={0.2} name="Downlink (MB)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </ChartCard>

        {/* 2. Distribution across slices */}
        <ChartCard
          title="Distribution Across Slices"
          subtitle="Traffic share by S-NSSAI identifier"
        >
          <div className="w-full h-[260px] flex flex-col items-center justify-center">
            {sliceDistributionData.length === 0 ? (
              <div className="text-sm text-muted">No slice data</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={sliceDistributionData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={75}
                    innerRadius={45}
                    paddingAngle={3}
                  >
                    {sliceDistributionData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={SLICE_COLORS[index % SLICE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(val: number) => [`${val} MB`, 'Volume']}
                    contentStyle={{ backgroundColor: '#FFFFFF', borderColor: '#E2E8F0', borderRadius: '0.75rem' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
            <div className="flex flex-wrap justify-center gap-2 mt-2">
              {sliceDistributionData.map((item, idx) => (
                <div key={item.name} className="flex items-center gap-1.5 text-xs text-text">
                  <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: SLICE_COLORS[idx % SLICE_COLORS.length] }} />
                  <span className="truncate max-w-[100px]">{item.name}</span>
                </div>
              ))}
            </div>
          </div>
        </ChartCard>
      </div>

      {/* Row 2: Failure Rates & Normalised Traffic Composition */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 4. Registration and session failure rates */}
        <ChartCard
          title="Signalling Failure Rates"
          subtitle="NAS and PFCP failure percentages in control plane"
          action={
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-text">
                <span className="w-2.5 h-2.5 rounded bg-attack" /> NAS Failures (%)
              </span>
              <span className="flex items-center gap-1.5 text-text">
                <span className="w-2.5 h-2.5 rounded bg-suspicious" /> PFCP Failures (%)
              </span>
            </div>
          }
        >
          <div className="w-full h-[240px]">
            {failureRatesData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-sm text-muted">No failure data</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={failureRatesData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis dataKey="time" stroke="#64748B" fontSize={12} tickLine={false} />
                  <YAxis stroke="#64748B" fontSize={12} tickLine={false} unit="%" />
                  <Tooltip contentStyle={{ backgroundColor: '#FFFFFF', borderColor: '#E2E8F0', borderRadius: '0.75rem' }} />
                  <Bar dataKey="nas_failure_pct" fill="#DC2626" name="NAS Failure (%)" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="pfcp_failure_pct" fill="#F59E0B" name="PFCP Failure (%)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </ChartCard>

        {/* 5. Normalised Traffic Composition */}
        <ChartCard
          title="Normalised Traffic Composition"
          subtitle="Relative distribution of control signalling vs user sessions (used for JSD test)"
          action={
            <div className="flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1.5 text-text">
                <span className="w-2.5 h-2.5 rounded bg-blue" /> Session Setup
              </span>
              <span className="flex items-center gap-1.5 text-text">
                <span className="w-2.5 h-2.5 rounded bg-teal" /> Registration
              </span>
            </div>
          }
        >
          <div className="w-full h-[240px]">
            {compositionData.length === 0 ? (
              <div className="h-full flex items-center justify-center text-sm text-muted">No composition data</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={compositionData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                  <XAxis dataKey="time" stroke="#64748B" fontSize={12} tickLine={false} />
                  <YAxis stroke="#64748B" fontSize={12} tickLine={false} unit="%" domain={[0, 100]} />
                  <Tooltip contentStyle={{ backgroundColor: '#FFFFFF', borderColor: '#E2E8F0', borderRadius: '0.75rem' }} />
                  <Area type="monotone" dataKey="session_setup" stackId="1" stroke="#3478F6" fill="#3478F6" name="Session Setup (%)" />
                  <Area type="monotone" dataKey="registration" stackId="1" stroke="#14B8A6" fill="#14B8A6" name="Registration (%)" />
                  <Area type="monotone" dataKey="failure" stackId="1" stroke="#DC2626" fill="#DC2626" name="Failures (%)" />
                  <Area type="monotone" dataKey="other" stackId="1" stroke="#64748B" fill="#64748B" name="Other Signalling (%)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </ChartCard>
      </div>

      {/* 3. Network Function Activity Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-text">Network Function Activity</h2>
            <p className="text-xs text-muted">Aggregate load across 5G Core NFs (AMF, UPF, SMF)</p>
          </div>
          <StatusBadge label="All Functions Online" variant="safe" size="sm" dot />
        </div>
        <DataTable
          columns={nfColumns}
          data={nfActivityData}
          keyExtractor={(item) => item.nf_id}
          emptyMessage="No network function activity logged"
        />
      </div>
    </div>
  );
};
