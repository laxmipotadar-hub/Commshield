import React, { useState } from 'react';
import { ShieldAlert, Zap, Layers, Bell } from 'lucide-react';
import {
  LineChart,
  Line,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ChartCard, StatCard, StatusBadge } from '../components';

const detectionStream = [
  { time: '12:00', if_percentile: 0.82, ae_percentile: 0.85, fused: 0.85, cusum: 1.2 },
  { time: '12:05', if_percentile: 0.84, ae_percentile: 0.86, fused: 0.86, cusum: 1.4 },
  { time: '12:10', if_percentile: 0.89, ae_percentile: 0.87, fused: 0.89, cusum: 1.9 },
  { time: '12:15', if_percentile: 0.85, ae_percentile: 0.84, fused: 0.85, cusum: 1.5 },
  { time: '12:20', if_percentile: 0.92, ae_percentile: 0.91, fused: 0.92, cusum: 2.8 },
  { time: '12:25', if_percentile: 0.96, ae_percentile: 0.94, fused: 0.96, cusum: 3.9 },
  { time: '12:30', if_percentile: 0.985, ae_percentile: 0.991, fused: 0.991, cusum: 4.82 },
  { time: '12:35', if_percentile: 0.988, ae_percentile: 0.993, fused: 0.993, cusum: 5.40 },
  { time: '12:40', if_percentile: 0.93, ae_percentile: 0.92, fused: 0.93, cusum: 3.1 },
  { time: '12:45', if_percentile: 0.88, ae_percentile: 0.86, fused: 0.88, cusum: 1.8 },
];

export const DetectionView: React.FC = () => {
  const [agreementState] = useState<'BOTH_FIRE' | 'IF_ONLY' | 'AE_ONLY' | 'NONE'>('BOTH_FIRE');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text">Anomaly Detection</h1>
        <p className="text-sm text-muted mt-0.5">
          Dual-model unsupervised detection (Isolation Forest + Autoencoder), max-percentile fusion, and CUSUM accumulation.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Isolation Forest"
          value="0.985 %ile"
          change="Flagged > 0.980"
          trend="down"
          subtitle="Negated score: 0.684"
          badge="Triggered"
          badgeVariant="attack"
          icon={<ShieldAlert className="w-4 h-4 text-attack" />}
        />
        <StatCard
          title="Dense Autoencoder"
          value="0.991 %ile"
          change="Flagged > 0.980"
          trend="down"
          subtitle="Recon MSE: 0.0412"
          badge="Triggered"
          badgeVariant="attack"
          icon={<Zap className="w-4 h-4 text-attack" />}
        />
        <StatCard
          title="Fused Percentile"
          value="0.991"
          change="Agreement: BOTH_FIRE"
          trend="neutral"
          subtitle="Fusion Rule: MAX_PERCENTILE"
          badge="Anomalous"
          badgeVariant="attack"
          icon={<Layers className="w-4 h-4 text-attack" />}
        />
        <StatCard
          title="CUSUM Statistic"
          value="4.82"
          change="Alarm limit: 4.50"
          trend="up"
          subtitle="Temporal persistent alert"
          badge="Alarm High"
          badgeVariant="attack"
          icon={<Bell className="w-4 h-4 text-attack" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <ChartCard
          title="Fused Percentiles vs Benign Reference"
          subtitle="Score distribution calibrated against trusted anchor holdout windows"
          className="lg:col-span-2"
        >
          <div className="w-full h-[260px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={detectionStream}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
                <XAxis dataKey="time" stroke="#64748B" fontSize={12} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={12} tickLine={false} domain={[0.8, 1.0]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#FFFFFF',
                    borderColor: '#E2E8F0',
                    borderRadius: '0.75rem',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="if_percentile"
                  name="IF Percentile"
                  stroke="#3478F6"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
                <Line
                  type="monotone"
                  dataKey="ae_percentile"
                  name="AE Percentile"
                  stroke="#14B8A6"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
                <Line
                  type="monotone"
                  dataKey="fused"
                  name="Fused Score"
                  stroke="#DC2626"
                  strokeWidth={2.5}
                  dot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <div className="bg-card rounded-xl border border-border p-5 shadow-sm flex flex-col justify-between">
          <div>
            <h3 className="text-base font-semibold text-text">Model Agreement Matrix</h3>
            <p className="text-xs text-muted mt-0.5">Complementary detector verification</p>

            <div className="mt-4 space-y-3">
              <div
                className={`p-3 rounded-lg border flex items-center justify-between ${
                  agreementState === 'BOTH_FIRE'
                    ? 'bg-attack/10 border-attack/30'
                    : 'bg-bg/60 border-border/60'
                }`}
              >
                <div>
                  <span className="text-xs font-semibold block text-text">BOTH_FIRE</span>
                  <span className="text-xs text-muted">High-confidence anomaly</span>
                </div>
                {agreementState === 'BOTH_FIRE' && (
                  <StatusBadge label="Current State" variant="attack" size="sm" />
                )}
              </div>

              <div
                className={`p-3 rounded-lg border flex items-center justify-between ${
                  agreementState === 'IF_ONLY'
                    ? 'bg-suspicious/10 border-suspicious/30'
                    : 'bg-bg/60 border-border/60'
                }`}
              >
                <div>
                  <span className="text-xs font-semibold block text-text">IF_ONLY</span>
                  <span className="text-xs text-muted">Sparse outlier / boundary event</span>
                </div>
              </div>

              <div
                className={`p-3 rounded-lg border flex items-center justify-between ${
                  agreementState === 'AE_ONLY'
                    ? 'bg-suspicious/10 border-suspicious/30'
                    : 'bg-bg/60 border-border/60'
                }`}
              >
                <div>
                  <span className="text-xs font-semibold block text-text">AE_ONLY</span>
                  <span className="text-xs text-muted">Complex non-linear correlation shift</span>
                </div>
              </div>

              <div
                className={`p-3 rounded-lg border flex items-center justify-between ${
                  agreementState === 'NONE'
                    ? 'bg-safe/10 border-safe/30'
                    : 'bg-bg/60 border-border/60'
                }`}
              >
                <div>
                  <span className="text-xs font-semibold block text-text">NONE</span>
                  <span className="text-xs text-muted">Nominal benign operations</span>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-border/60 text-xs text-muted">
            Autoencoder Architecture: 9-6-4-6-9 dense reconstruction
          </div>
        </div>
      </div>
    </div>
  );
};
// CommShield AI Core
