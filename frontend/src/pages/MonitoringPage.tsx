import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  Database,
  Layers,
  Radio,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  ChartCard,
  Column,
  DataTable,
  DataSourceBadge,
  EmptyState,
  ErrorState,
  LoadingState,
  StatCard,
} from '../components';
import { api, CanonicalTrafficWindow, RealMonitoringResponse } from '../services/api';
import { useReplay } from '../context/ReplayContext';

const PIE_COLORS = ['#3478F6', '#14B8A6', '#8B5CF6', '#F59E0B', '#294C70'];

export const MonitoringPage: React.FC = () => {
  const { pollTick } = useReplay();

  const [windows, setWindows] = useState<CanonicalTrafficWindow[]>([]);
  const [realMonitoring, setRealMonitoring] = useState<RealMonitoringResponse | null>(null);
  const [sliceFilter, setSliceFilter] = useState<string>('ALL');
  const [timeRangeLimit, setTimeRangeLimit] = useState<number>(50);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMonitoringData = async (isInitial = false) => {
    if (isInitial) setLoading(true);
    setError(null);
    try {
      const [res, realRes] = await Promise.all([
        api.getWindows({
          slice_id: sliceFilter !== 'ALL' ? sliceFilter : undefined,
          limit: timeRangeLimit,
        }),
        api.getRealMonitoring({
          slice_id: sliceFilter !== 'ALL' ? sliceFilter : undefined,
          limit: timeRangeLimit,
        }).catch(() => null),
      ]);
      setWindows(res.items || []);
      if (realRes) {
        setRealMonitoring(realRes);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch network monitoring data';
      setError(msg);
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  useEffect(() => {
    fetchMonitoringData(true);
  }, [sliceFilter, timeRangeLimit]);

  useEffect(() => {
    if (pollTick > 0) {
      fetchMonitoringData(false);
    }
  }, [pollTick]);

  // Derived: Traffic volume over time
  const trafficTimeData = useMemo(() => {
    let raw: { time: string; uplink_mb: number; downlink_mb: number }[] = [];
    if (realMonitoring && realMonitoring.time_series && realMonitoring.time_series.length > 0) {
      raw = realMonitoring.time_series.map((pt) => {
        const d = new Date(pt.timestamp);
        const timeStr = isNaN(d.getTime())
          ? (pt.timestamp ? pt.timestamp.slice(11, 16) : '--:--')
          : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        return {
          time: timeStr,
          uplink_mb: pt.uplink_mb,
          downlink_mb: pt.downlink_mb,
        };
      });
    } else {
      raw = [...windows]
        .sort((a, b) => new Date(a.window_start).getTime() - new Date(b.window_start).getTime())
        .map((w) => {
          const d = new Date(w.window_start);
          const timeStr = isNaN(d.getTime())
            ? (w.window_start ? w.window_start.slice(11, 16) : '--:--')
            : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
          return {
            time: timeStr,
            uplink_mb: Number(((w.raw_counters?.total_bytes_uplink || 0) / 1048576).toFixed(2)),
            downlink_mb: Number(((w.raw_counters?.total_bytes_downlink || 0) / 1048576).toFixed(2)),
          };
        });
    }
    // Prune trailing zero windows that cause sudden plummet to zero
    while (raw.length > 1 && raw[raw.length - 1].uplink_mb === 0 && raw[raw.length - 1].downlink_mb === 0) {
      raw.pop();
    }
    return raw;
  }, [windows, realMonitoring]);

  // Derived: Distribution across slices
  const sliceDistributionData = useMemo(() => {
    if (realMonitoring && realMonitoring.slice_breakdown && Object.keys(realMonitoring.slice_breakdown).length > 0) {
      return Object.entries(realMonitoring.slice_breakdown).map(([name, item]) => ({
        name,
        value: item.traffic_mb,
      }));
    }
    const map: Record<string, number> = {};
    windows.forEach((w) => {
      const sId = w.slice_id || 'unknown';
      const bytes = (w.raw_counters?.total_bytes_uplink || 0) + (w.raw_counters?.total_bytes_downlink || 0);
      map[sId] = (map[sId] || 0) + bytes;
    });
    return Object.entries(map).map(([name, bytes]) => ({
      name,
      value: Number((bytes / 1048576).toFixed(2)),
    }));
  }, [windows, realMonitoring]);

  // Derived: Network Function activity
  const nfActivityData = useMemo(() => {
    const map: Record<string, { packets: number; bytes: number; ues: number }> = {};
    windows.forEach((w) => {
      const nf = w.nf_id || 'UPF-01';
      const current = map[nf] || { packets: 0, bytes: 0, ues: 0 };
      current.packets += w.raw_counters?.total_packets || 0;
      current.bytes += (w.raw_counters?.total_bytes_uplink || 0) + (w.raw_counters?.total_bytes_downlink || 0);
      current.ues = Math.max(current.ues, w.raw_counters?.active_ue_count || 0);
      map[nf] = current;
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
    const raw = [...windows]
      .sort((a, b) => new Date(a.window_start).getTime() - new Date(b.window_start).getTime())
      .map((w) => {
        const d = new Date(w.window_start);
        const timeStr = isNaN(d.getTime())
          ? (w.window_start ? w.window_start.slice(11, 16) : '--:--')
          : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        return {
          time: timeStr,
          nas_failure_pct: Number(((w.ratio_features?.nas_failure_ratio || 0) * 100).toFixed(3)),
          pfcp_failure_pct: Number(((w.ratio_features?.pfcp_failure_ratio || 0) * 100).toFixed(3)),
          reg_rate: Number((w.ratio_features?.registrations_per_active_ue || 0).toFixed(4)),
        };
      });
    if (raw.length > 1 && windows.length > 1) {
      const lastW = windows[windows.length - 1];
      if ((lastW.raw_counters?.total_bytes_uplink || 0) + (lastW.raw_counters?.total_bytes_downlink || 0) === 0) {
        raw.pop();
      }
    }
    return raw;
  }, [windows]);

  // Derived: Normalised traffic composition
  const compositionData = useMemo(() => {
    let raw: { time: string; session_setup: number; registration: number; failure: number; other: number }[] = [];
    if (realMonitoring && realMonitoring.time_series && realMonitoring.time_series.length > 0) {
      raw = realMonitoring.time_series.map((pt) => {
        const d = new Date(pt.timestamp);
        const timeStr = isNaN(d.getTime())
          ? (pt.timestamp ? pt.timestamp.slice(11, 16) : '--:--')
          : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        return {
          time: timeStr,
          session_setup: Number((pt.tcp_ratio * 100).toFixed(1)),
          registration: Number((pt.udp_ratio * 100).toFixed(1)),
          failure: Number((pt.rst_flag_ratio * 100).toFixed(2)),
          other: Number((pt.icmp_ratio * 100).toFixed(1)),
        };
      });
    } else {
      raw = [...windows]
        .sort((a, b) => new Date(a.window_start).getTime() - new Date(b.window_start).getTime())
        .map((w) => {
          const d = new Date(w.window_start);
          const timeStr = isNaN(d.getTime())
            ? (w.window_start ? w.window_start.slice(11, 16) : '--:--')
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
    }
    while (raw.length > 1 && raw[raw.length - 1].session_setup === 0 && raw[raw.length - 1].registration === 0 && raw[raw.length - 1].other === 0) {
      raw.pop();
    }
    return raw;
  }, [windows, realMonitoring]);

  // Aggregate stats
  const totalUEs = windows.reduce((max, w) => Math.max(max, w.raw_counters?.active_ue_count || 0), 0);
  const avgNasFailure = windows.length > 0
    ? (windows.reduce((sum, w) => sum + (w.ratio_features?.nas_failure_ratio || 0), 0) / windows.length * 100).toFixed(3)
    : '0.000';
  const totalVolumeMB = realMonitoring
    ? realMonitoring.total_traffic_mb.toFixed(1)
    : (
        windows.reduce((sum, w) => sum + (w.raw_counters?.total_bytes_uplink || 0) + (w.raw_counters?.total_bytes_downlink || 0), 0) / 1048576
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
    return <ErrorState title="Telemetry Error" message={error} onRetry={() => fetchMonitoringData(true)} />;
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

        {/* Slice Filter, Time-Range Selector and Data Source Badge */}
        <div className="flex flex-wrap items-center gap-3">
          <DataSourceBadge />
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-muted uppercase">Slice Filter:</span>
            <select
              value={sliceFilter}
              onChange={(e) => setSliceFilter(e.target.value)}
              className="bg-bg border border-border text-xs font-medium text-text rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue cursor-pointer"
            >
              <option value="ALL">All Network Slices</option>
              <option value="sst-1-sd-010203">sst-1-sd-010203 (eMBB)</option>
              <option value="sst-2-sd-010203">sst-2-sd-010203 (URLLC)</option>
              <option value="sst-3-sd-010203">sst-3-sd-010203 (mMTC)</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-muted uppercase">Time Range:</span>
            <select
              value={timeRangeLimit}
              onChange={(e) => setTimeRangeLimit(Number(e.target.value))}
              className="bg-bg border border-border text-xs font-medium text-text rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue cursor-pointer"
            >
              <option value={10}>Last 10 Windows (~10m)</option>
              <option value={25}>Last 25 Windows (~25m)</option>
              <option value={50}>Last 50 Windows (~50m)</option>
              <option value={100}>Last 100 Windows (~100m)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Aggregate Overview Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          title="Monitored Volume"
          value={`${totalVolumeMB} MB`}
          subtitle={`Across ${windows.length} aggregated windows`}
          icon={<Database className="w-4 h-4 text-blue" />}
        />
        <StatCard
          title="Peak Concurrent UEs"
          value={totalUEs.toLocaleString()}
          subtitle="Observed during telemetry window"
          icon={<Radio className="w-4 h-4 text-teal" />}
        />
        <StatCard
          title="Avg NAS Rejection Ratio"
          value={`${avgNasFailure}%`}
          subtitle="Signalling establishment failure rate"
          icon={<AlertCircle className={`w-4 h-4 ${Number(avgNasFailure) > 0.05 ? 'text-attack' : 'text-safe'}`} />}
          badge={Number(avgNasFailure) > 0.05 ? 'Elevated' : 'Nominal'}
          badgeVariant={Number(avgNasFailure) > 0.05 ? 'attack' : 'safe'}
        />
      </div>

      {/* Charts Grid: Volume Over Time & Slice Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Traffic Volume Time Series */}
        <div className="lg:col-span-2">
          <ChartCard
            title="Traffic Volume Over Time"
            subtitle="Separated Uplink and Downlink throughput (Megabytes)"
          >
            {trafficTimeData.length === 0 ? (
              <EmptyState title="No Traffic Data" description="Start replay to generate throughput telemetry." />
            ) : (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trafficTimeData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="monUplink" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3478F6" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#3478F6" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="monDownlink" x1="0" y1="0" x2="0" y2="1">
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
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                    <Area
                      type="monotone"
                      dataKey="uplink_mb"
                      name="Uplink MB"
                      stroke="#3478F6"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#monUplink)"
                    />
                    <Area
                      type="monotone"
                      dataKey="downlink_mb"
                      name="Downlink MB"
                      stroke="#14B8A6"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#monDownlink)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </ChartCard>
        </div>

        {/* Right 1 Col: Slice Volume Distribution Donut */}
        <div className="lg:col-span-1">
          <ChartCard
            title="Distribution Across Slices"
            subtitle="Relative bandwidth consumption by slice ID"
          >
            {sliceDistributionData.length === 0 ? (
              <EmptyState title="No Slice Data" description="No slice data currently available." />
            ) : (
              <div className="h-64 w-full flex flex-col items-center justify-center">
                <ResponsiveContainer width="100%" height={180}>
                  <PieChart>
                    <Pie
                      data={sliceDistributionData}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={75}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {sliceDistributionData.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(val: number) => [`${val} MB`, 'Traffic']}
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderRadius: '8px',
                        border: '1px solid #E2E8F0',
                        fontSize: '12px',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="w-full flex flex-wrap justify-center gap-2 mt-2">
                  {sliceDistributionData.map((entry, index) => (
                    <div key={entry.name} className="flex items-center gap-1.5 text-[11px] text-muted">
                      <span
                        className="w-2.5 h-2.5 rounded-full"
                        style={{ backgroundColor: PIE_COLORS[index % PIE_COLORS.length] }}
                      />
                      <span className="truncate max-w-[100px]">{entry.name}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </ChartCard>
        </div>
      </div>

      {/* Charts Grid: Failure Rates & Normalised Traffic Composition */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Failure Rates Trend */}
        <ChartCard
          title="Signalling & Session Failure Rates"
          subtitle="NAS and PFCP failure ratios indicating signalling stress or attack"
        >
          {failureRatesData.length === 0 ? (
            <EmptyState title="No Failure Data" description="No failure rate metrics available." />
          ) : (
            <div className="h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={failureRatesData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                  <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#64748B' }} stroke="#E2E8F0" />
                  <YAxis tick={{ fontSize: 11, fill: '#64748B' }} stroke="#E2E8F0" unit="%" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderRadius: '8px',
                      border: '1px solid #E2E8F0',
                      fontSize: '12px',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                  <Line
                    type="monotone"
                    dataKey="nas_failure_pct"
                    name="NAS Failure %"
                    stroke="#DC2626"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="pfcp_failure_pct"
                    name="PFCP Failure %"
                    stroke="#F59E0B"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </ChartCard>

        {/* Normalised Traffic Composition (Stacked Bar Chart for JSD Analysis) */}
        <ChartCard
          title="Normalised Traffic Composition"
          subtitle="Relative distribution of signalling events (Key input to JSD Attribution)"
        >
          {compositionData.length === 0 ? (
            <EmptyState title="No Composition Data" description="No composition vectors available." />
          ) : (
            <div className="h-60 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={compositionData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                  <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#64748B' }} stroke="#E2E8F0" />
                  <YAxis tick={{ fontSize: 11, fill: '#64748B' }} stroke="#E2E8F0" unit="%" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderRadius: '8px',
                      border: '1px solid #E2E8F0',
                      fontSize: '12px',
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                  <Bar dataKey="session_setup" name="Session Setup %" stackId="a" fill="#3478F6" />
                  <Bar dataKey="registration" name="Registration %" stackId="a" fill="#14B8A6" />
                  <Bar dataKey="other" name="Other Signalling %" stackId="a" fill="#294C70" />
                  <Bar dataKey="failure" name="Failure %" stackId="a" fill="#DC2626" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </ChartCard>
      </div>

      {/* Network Function Activity Table */}
      <div className="bg-card rounded-xl border border-border shadow-sm p-5 space-y-4">
        <div>
          <h2 className="text-base font-semibold text-text">Network Function Core Breakdown</h2>
          <p className="text-xs text-muted">
            Telemetry load aggregated per Core Network Function (AMF, SMF, UPF).
          </p>
        </div>

        <DataTable
          columns={nfColumns}
          data={nfActivityData}
          keyExtractor={(item) => item.nf_id}
          emptyMessage="No Network Function telemetry available."
        />
      </div>
    </div>
  );
};

export default MonitoringPage;
// CommShield AI Core
