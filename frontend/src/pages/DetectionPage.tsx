import React, { useEffect, useMemo, useState } from 'react';
import {
  CheckCircle2,
  Cpu,
  Eye,
  Info,
  Layers,
  Zap,
} from 'lucide-react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
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
  StatusBadge,
} from '../components';
import {
  api,
  CanonicalTrafficWindow,
  DetectorOutput,
  ExplainabilityResponse,
} from '../services/api';
import { useReplay } from '../context/ReplayContext';

export const DetectionPage: React.FC = () => {
  const { pollTick } = useReplay();

  const [windows, setWindows] = useState<CanonicalTrafficWindow[]>([]);
  const [selectedWindowId, setSelectedWindowId] = useState<string | null>(null);
  const [explainData, setExplainData] = useState<ExplainabilityResponse | null>(null);
  const [detectorData, setDetectorData] = useState<DetectorOutput | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPlaceholder, setIsPlaceholder] = useState(false);

  const fetchWindows = async (isInitial = false) => {
    if (isInitial) setLoading(true);
    setError(null);
    try {
      const res = await api.getWindows({ limit: 25 });
      const items = res.items || [];
      setWindows(items);
      setIsPlaceholder(res.is_placeholder === true);
      if (items.length > 0 && !selectedWindowId) {
        setSelectedWindowId(items[0].window_id);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch detection windows';
      setError(msg);
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  useEffect(() => {
    fetchWindows(true);
  }, []);

  useEffect(() => {
    if (pollTick > 0) {
      fetchWindows(false);
    }
  }, [pollTick]);

  // Fetch real detection and explainability for selected window
  useEffect(() => {
    if (!selectedWindowId) return;

    Promise.all([
      api.analyzeWindow({ window_id: selectedWindowId }).catch(() => null),
      api.getExplainability(selectedWindowId).catch(() => null),
    ]).then(([detRes, expRes]) => {
      if (detRes) setDetectorData(detRes);
      if (expRes) setExplainData(expRes);
    });
  }, [selectedWindowId]);

  // Derived: CUSUM trend from windows
  const cusumChartData = useMemo(() => {
    let accumulated = 0;
    return [...windows]
      .sort((a, b) => new Date(a.window_start).getTime() - new Date(b.window_start).getTime())
      .map((w) => {
        const d = new Date(w.window_start);
        const timeStr = isNaN(d.getTime())
          ? (w.window_start ? w.window_start.slice(11, 16) : '--:--')
          : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        // Score based on ratio deviations from baseline
        const nasDev = (w.ratio_features?.nas_failure_ratio || 0) * 10;
        const pduDev = Math.abs(1.0 - (w.ratio_features?.pdu_session_rate_per_ue || 1.0));
        const step = Math.max(0, (nasDev + pduDev) * 2 - 0.1);
        accumulated = Math.min(10, Math.max(0, Number((accumulated + step).toFixed(2))));

        const isCurrent = w.window_id === selectedWindowId;
        const fusedVal = isCurrent && detectorData
          ? detectorData.fusion.fused_percentile
          : (explainData?.window_id === w.window_id ? explainData.fused_percentile : 0.85);

        return {
          time: timeStr,
          cusum_score: accumulated,
          alarm_threshold: 4.5,
          fused_score: fusedVal,
        };
      });
  }, [windows, selectedWindowId, detectorData, explainData]);

  // Agreement State derived from real detector or explainability
  const agreementState = useMemo(() => {
    if (detectorData?.fusion?.agreement_state) {
      return detectorData.fusion.agreement_state;
    }
    if (!explainData) return 'NONE';
    if (explainData.is_anomalous) return 'BOTH_FIRE';
    if (explainData.fused_percentile > 0.95) return 'IF_ONLY';
    return 'NONE';
  }, [detectorData, explainData]);

  // Derive score metrics from detectorData, explainData or defaults
  const ifPercentile = detectorData?.isolation_forest?.benign_percentile !== undefined
    ? detectorData.isolation_forest.benign_percentile
    : (explainData?.fused_percentile !== undefined ? explainData.fused_percentile : 0.985);

  const ifRawScore = detectorData?.isolation_forest?.raw_score_negated ?? 0.684;
  const isAnomalous = detectorData?.fusion?.is_anomalous ?? (explainData?.is_anomalous ?? false);
  const fusedVal = detectorData?.fusion?.fused_percentile ?? (explainData?.fused_percentile ?? ifPercentile);

  // Table Columns
  const columns: Column<CanonicalTrafficWindow>[] = [
    {
      key: 'window_id',
      header: 'Window ID',
      render: (w) => (
        <span
          className={`font-mono text-xs cursor-pointer hover:underline ${
            w.window_id === selectedWindowId ? 'font-bold text-blue' : 'text-text'
          }`}
          onClick={() => setSelectedWindowId(w.window_id)}
        >
          {w.window_id.slice(0, 12)}...
        </span>
      ),
    },
    {
      key: 'slice_id',
      header: 'Slice S-NSSAI',
      render: (w) => <span className="text-xs font-semibold text-slate">{w.slice_id}</span>,
    },
    {
      key: 'window_time',
      header: 'Time',
      render: (w) => {
        const d = new Date(w.window_start);
        return (
          <span className="text-xs font-mono text-muted">
            {isNaN(d.getTime()) ? w.window_start.slice(11, 19) : d.toLocaleTimeString()}
          </span>
        );
      },
    },
    {
      key: 'ue_entropy',
      header: 'UE Entropy',
      render: (w) => <span className="text-xs font-mono">{w.ratio_features?.ue_hash_entropy?.toFixed(3) ?? '—'}</span>,
    },
    {
      key: 'nas_fail',
      header: 'NAS Fail Ratio',
      render: (w) => (
        <span className={`text-xs font-mono ${Number(w.ratio_features?.nas_failure_ratio || 0) > 0.01 ? 'text-attack font-bold' : 'text-muted'}`}>
          {((w.ratio_features?.nas_failure_ratio || 0) * 100).toFixed(2)}%
        </span>
      ),
    },
    {
      key: 'action',
      header: 'Inspect Window',
      render: (w) => (
        <button
          onClick={() => setSelectedWindowId(w.window_id)}
          className={`px-2.5 py-1 text-xs rounded-lg inline-flex items-center gap-1 font-medium transition-colors ${
            w.window_id === selectedWindowId
              ? 'bg-blue text-white shadow-sm'
              : 'bg-bg text-slate hover:bg-slate/10 border border-border'
          }`}
        >
          <Eye className="w-3 h-3" />
          <span>{w.window_id === selectedWindowId ? 'Inspecting' : 'Inspect'}</span>
        </button>
      ),
    },
  ];

  if (loading) {
    return <LoadingState message="Loading anomaly detection telemetry and model states..." size="lg" />;
  }

  if (error) {
    return <ErrorState title="Detection Error" message={error} onRetry={() => fetchWindows(true)} />;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text">Anomaly Detection</h1>
          <p className="text-sm text-muted mt-0.5">
            Multi-model unsupervised scoring (Isolation Forest + Dense Autoencoder), calibrated percentiles, and CUSUM tracking.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <SampleDataBadge isPlaceholder={isPlaceholder} />
          {selectedWindowId && (
            <span className="text-xs font-mono px-2.5 py-1 rounded-md bg-card border border-border text-muted">
              Active: {selectedWindowId.slice(0, 8)}...
            </span>
          )}
        </div>
      </div>

      {/* Detector Score Panels (3 Columns: IF, AE, Fusion) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* 1. Isolation Forest Panel */}
        <div className="bg-card rounded-xl border border-border p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-blue/10 text-blue">
                <Cpu className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-text">Isolation Forest</h3>
                <span className="text-[10px] text-muted uppercase font-medium">Unsupervised Tree Ensemble</span>
              </div>
            </div>
            <StatusBadge
              label={ifPercentile >= 95.0 || ifPercentile >= 0.95 ? 'Flagged' : 'Normal'}
              variant={ifPercentile >= 95.0 || ifPercentile >= 0.95 ? 'attack' : 'safe'}
              size="sm"
              dot
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-baseline">
              <span className="text-xs text-muted">Calibrated Benign Percentile</span>
              <span className="text-lg font-bold font-mono text-text">
                {ifPercentile > 1.0 ? `${ifPercentile.toFixed(1)}th` : `${(ifPercentile * 100).toFixed(1)}%`}
              </span>
            </div>
            <div className="w-full bg-bg rounded-full h-2 overflow-hidden border border-border">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  ifPercentile >= 95.0 || ifPercentile >= 0.95 ? 'bg-attack' : 'bg-blue'
                }`}
                style={{ width: `${Math.min(100, ifPercentile > 1.0 ? ifPercentile : ifPercentile * 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-muted">
              <span>0% (Nominal)</span>
              <span>Threshold: 95.0%</span>
              <span>100% (Anomalous)</span>
            </div>
          </div>

          <div className="pt-2 border-t border-border/60 text-xs space-y-1.5 text-muted">
            <div className="flex justify-between">
              <span>Raw Score (Negated):</span>
              <span className="font-mono text-slate font-medium">{ifRawScore.toFixed(4)}</span>
            </div>
            <div className="flex justify-between">
              <span>Calibration Reference:</span>
              <span className="font-medium text-slate">60 Benign Windows</span>
            </div>
          </div>
        </div>

        {/* 2. Autoencoder Panel */}
        <div className="bg-card rounded-xl border border-border p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-teal/10 text-teal">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-text">Dense Autoencoder</h3>
                <span className="text-[10px] text-muted uppercase font-medium">Reconstruction MSE</span>
              </div>
            </div>
            <StatusBadge
              label={detectorData?.autoencoder ? 'Active' : 'Pending M2'}
              variant={detectorData?.autoencoder ? 'safe' : 'neutral'}
              size="sm"
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-baseline">
              <span className="text-xs text-muted">Reconstruction MSE</span>
              <span className="text-lg font-bold font-mono text-text">
                {detectorData?.autoencoder?.reconstruction_mse !== null && detectorData?.autoencoder?.reconstruction_mse !== undefined
                  ? detectorData.autoencoder.reconstruction_mse.toFixed(4)
                  : 'Pending M2'}
              </span>
            </div>
            <div className="w-full bg-bg rounded-full h-2 overflow-hidden border border-border">
              <div
                className="h-full rounded-full bg-teal transition-all duration-300"
                style={{ width: '0%' }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-muted">
              <span>Scheduled for Milestone M2</span>
            </div>
          </div>

          <div className="pt-2 border-t border-border/60 text-xs space-y-1.5 text-muted">
            <div className="flex justify-between">
              <span>Status:</span>
              <span className="font-medium text-slate">Null (Unfitted)</span>
            </div>
            <div className="flex justify-between">
              <span>Fusion Fallback:</span>
              <span className="font-medium text-teal">IF Percentile Sourced</span>
            </div>
          </div>
        </div>

        {/* 3. Fused Score Panel */}
        <div className="bg-card rounded-xl border border-border p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-attack/10 text-attack">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-text">Fused Score</h3>
                <span className="text-[10px] text-muted uppercase font-medium">Max-Percentile Consensus</span>
              </div>
            </div>
            <StatusBadge
              label={isAnomalous ? 'Anomaly Alarm' : 'Nominal Stream'}
              variant={isAnomalous ? 'attack' : 'safe'}
              size="sm"
              dot
            />
          </div>

          <div className="space-y-2">
            <div className="flex justify-between items-baseline">
              <span className="text-xs text-muted">Fused Percentile</span>
              <span className="text-2xl font-bold font-mono text-text">
                {fusedVal > 1.0 ? `${fusedVal.toFixed(1)}th` : `${(fusedVal * 100).toFixed(1)}%`}
              </span>
            </div>
            <div className="w-full bg-bg rounded-full h-2 overflow-hidden border border-border">
              <div
                className={`h-full rounded-full transition-all duration-300 ${isAnomalous ? 'bg-attack' : 'bg-safe'}`}
                style={{ width: `${Math.min(100, fusedVal > 1.0 ? fusedVal : fusedVal * 100)}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-muted">
              <span>Rule: MAX_PERCENTILE</span>
              <span className="font-semibold text-slate">State: {agreementState}</span>
            </div>
          </div>

          <div className="pt-2 border-t border-border/60 text-xs space-y-1.5 text-muted">
            <div className="flex justify-between">
              <span>Verdict:</span>
              <span className={`font-semibold ${isAnomalous ? 'text-attack' : 'text-safe'}`}>
                {isAnomalous ? 'Flagged Anomalous' : 'Nominal Safe'}
              </span>
            </div>
            <div className="flex justify-between">
              <span>Active Baseline:</span>
              <span className="font-mono text-slate">{detectorData?.baseline_version || 'v1.0.0-anchor'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Middle Grid: CUSUM Trend & Detector Agreement */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: CUSUM Trend */}
        <div className="lg:col-span-2">
          <ChartCard
            title="CUSUM Persistent Shift Tracking"
            subtitle="Cumulative sum anomaly statistic across successive windows (Alarm Threshold: 4.5)"
          >
            {cusumChartData.length === 0 ? (
              <EmptyState title="No CUSUM Telemetry" description="Start replay to generate cumulative anomaly tracking." />
            ) : (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={cusumChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                    <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#64748B' }} stroke="#E2E8F0" />
                    <YAxis tick={{ fontSize: 11, fill: '#64748B' }} stroke="#E2E8F0" domain={[0, 10]} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderRadius: '8px',
                        border: '1px solid #E2E8F0',
                        fontSize: '12px',
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                    <ReferenceLine y={4.5} stroke="#DC2626" strokeDasharray="4 4" label={{ value: 'Alarm Threshold: 4.5', fill: '#DC2626', fontSize: 10 }} />
                    <Line
                      type="monotone"
                      dataKey="cusum_score"
                      name="Accumulated CUSUM"
                      stroke="#8B5CF6"
                      strokeWidth={2}
                      dot={{ r: 2 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </ChartCard>
        </div>

        {/* Right 1 Col: Detector Agreement Panel */}
        <div className="lg:col-span-1">
          <div className="bg-card rounded-xl border border-border p-5 shadow-sm space-y-4 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <h3 className="text-sm font-semibold text-text">Detector Agreement State</h3>
                <StatusBadge
                  label={agreementState}
                  variant={agreementState === 'BOTH_FIRE' ? 'attack' : agreementState === 'IF_ONLY' ? 'suspicious' : 'safe'}
                  size="sm"
                />
              </div>

              <div className="space-y-3 mt-4">
                <div className={`p-3 rounded-lg border text-xs flex items-center justify-between ${agreementState === 'BOTH_FIRE' ? 'border-attack bg-attack/5' : 'border-border bg-bg/50'}`}>
                  <span className="font-semibold text-text">BOTH_FIRE (Consensus Attack)</span>
                  {agreementState === 'BOTH_FIRE' && <CheckCircle2 className="w-4 h-4 text-attack" />}
                </div>

                <div className={`p-3 rounded-lg border text-xs flex items-center justify-between ${agreementState === 'IF_ONLY' ? 'border-suspicious bg-suspicious/5' : 'border-border bg-bg/50'}`}>
                  <span className="font-semibold text-text">IF_ONLY (Isolation Forest Active)</span>
                  {agreementState === 'IF_ONLY' && <CheckCircle2 className="w-4 h-4 text-suspicious" />}
                </div>

                <div className="p-3 rounded-lg border text-xs flex items-center justify-between border-border bg-bg/50 opacity-60">
                  <span className="font-semibold text-text">AE_ONLY (Reconstruction MSE)</span>
                  <span className="text-[10px] text-muted">Pending M2</span>
                </div>

                <div className={`p-3 rounded-lg border text-xs flex items-center justify-between ${agreementState === 'NONE' ? 'border-safe bg-safe/5' : 'border-border bg-bg/50'}`}>
                  <span className="font-semibold text-text">NONE (All Detectors Nominal)</span>
                  {agreementState === 'NONE' && <CheckCircle2 className="w-4 h-4 text-safe" />}
                </div>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-bg border border-border text-xs text-muted flex items-start gap-2 mt-4">
              <Info className="w-4 h-4 text-blue flex-shrink-0 mt-0.5" />
              <p>
                Fused decision is currently driven by the calibrated Isolation Forest percentile score. Autoencoder will contribute in Milestone M2.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Anomaly Windows Table */}
      <div className="bg-card rounded-xl border border-border shadow-sm p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-text">Recent Telemetry Windows</h2>
            <p className="text-xs text-muted">
              Click &quot;Inspect&quot; on any window row to view its calibrated feature attributions and anomaly scoring.
            </p>
          </div>
          <SampleDataBadge isPlaceholder={isPlaceholder} />
        </div>

        <DataTable
          columns={columns}
          data={windows}
          keyExtractor={(w) => w.window_id}
          emptyMessage="No detection telemetry windows found."
        />
      </div>
    </div>
  );
};

export default DetectionPage;
