import React, { useEffect, useState } from 'react';
import { Radio, Users, Cpu, HardDrive } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ChartCard, DataTable, StatCard, Column } from '../components';
import { api, CanonicalTrafficWindow } from '../services/api';
import { formatBytes } from '../utils/formatters';

const throughputData = [
  { time: '12:00', uplink_mbps: 18.9, downlink_mbps: 119.2 },
  { time: '12:05', uplink_mbps: 22.4, downlink_mbps: 135.0 },
  { time: '12:10', uplink_mbps: 26.1, downlink_mbps: 148.5 },
  { time: '12:15', uplink_mbps: 21.0, downlink_mbps: 128.4 },
  { time: '12:20', uplink_mbps: 34.8, downlink_mbps: 195.1 },
  { time: '12:25', uplink_mbps: 45.2, downlink_mbps: 260.4 },
  { time: '12:30', uplink_mbps: 58.7, downlink_mbps: 340.8 },
  { time: '12:35', uplink_mbps: 62.1, downlink_mbps: 375.2 },
  { time: '12:40', uplink_mbps: 39.5, downlink_mbps: 215.0 },
  { time: '12:45', uplink_mbps: 25.0, downlink_mbps: 142.0 },
];

export const MonitoringView: React.FC = () => {
  const [windows, setWindows] = useState<CanonicalTrafficWindow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getWindows({ limit: 8 })
      .then((res) => setWindows(res.items))
      .catch((err) => console.warn('Failed to fetch windows in Monitoring:', err))
      .finally(() => setLoading(false));
  }, []);

  const columns: Column<CanonicalTrafficWindow>[] = [
    {
      key: 'window_id',
      header: 'Window ID',
      render: (w) => <span className="font-mono text-xs">{w.window_id.slice(0, 10)}...</span>,
    },
    {
      key: 'slice_id',
      header: 'Slice ID',
      render: (w) => <span className="font-semibold text-xs text-slate">{w.slice_id}</span>,
    },
    {
      key: 'active_ue',
      header: 'Active UEs',
      render: (w) => (
        <span className="font-medium text-xs">{w.raw_counters.active_ue_count ?? '—'}</span>
      ),
    },
    {
      key: 'pdu_sessions',
      header: 'PDU Sessions',
      render: (w) => (
        <span className="text-xs">{w.raw_counters.pdu_sessions_established ?? '—'}</span>
      ),
    },
    {
      key: 'nas_failures',
      header: 'NAS Failures',
      render: (w) => (
        <span className={`text-xs font-semibold ${Number(w.raw_counters.nas_failures || 0) > 0 ? 'text-attack' : 'text-safe'}`}>
          {w.raw_counters.nas_failures ?? 0}
        </span>
      ),
    },
    {
      key: 'bytes_uplink',
      header: 'Uplink Volume',
      render: (w) => (
        <span className="text-xs text-muted font-mono">
          {formatBytes(w.raw_counters.total_bytes_uplink)}
        </span>
      ),
    },
    {
      key: 'bytes_downlink',
      header: 'Downlink Volume',
      render: (w) => (
        <span className="text-xs text-muted font-mono">
          {formatBytes(w.raw_counters.total_bytes_downlink)}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text">Network Monitoring</h1>
        <p className="text-sm text-muted mt-0.5">
          Canonical slice telemetry counters, control-plane signalling, and user-plane throughput metrics.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Active UE Count"
          value="1,420"
          change="+8.4%"
          trend="up"
          subtitle="Unique subscriber SIMs in window"
          icon={<Users className="w-4 h-4 text-blue" />}
        />
        <StatCard
          title="PDU Sessions Established"
          value="1,410"
          change="+7.9%"
          trend="up"
          subtitle="GTP-U tunnels currently active"
          icon={<Radio className="w-4 h-4 text-teal" />}
        />
        <StatCard
          title="NAS Message Rate"
          value="450 msgs/min"
          change="0.44% failure ratio"
          trend="neutral"
          subtitle="AMF signalling registration attempts"
          icon={<Cpu className="w-4 h-4 text-slate" />}
        />
        <StatCard
          title="Aggregate Volume"
          value="1.03 GB/min"
          change="+12.5% surge"
          trend="up"
          subtitle="UPF combined UL + DL user data"
          icon={<HardDrive className="w-4 h-4 text-quarantined" />}
        />
      </div>

      <ChartCard
        title="Slice Data Plane Throughput"
        subtitle="Uplink and Downlink throughput per canonical 60-second window"
      >
        <div className="w-full h-[260px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={throughputData}>
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
              <Bar dataKey="uplink_mbps" name="Uplink (MB)" fill="#3478F6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="downlink_mbps" name="Downlink (MB)" fill="#14B8A6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      <div className="space-y-3">
        <h2 className="text-base font-bold text-text">Live Slice Counters</h2>
        <DataTable
          columns={columns}
          data={windows}
          keyExtractor={(w) => w.window_id}
          isLoading={loading}
          emptyMessage="No telemetry windows found"
        />
      </div>
    </div>
  );
};
// CommShield AI Core
