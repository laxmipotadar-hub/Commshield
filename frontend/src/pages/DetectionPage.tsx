import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Eye,
  Info,
  Layers,
  Search,
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
  DataSourceBadge,
  EmptyState,
  ErrorState,
  LoadingState,
  StatusBadge,
} from '../components';
import {
  api,
  CanonicalTrafficWindow,
  DetectorOutput,
  RealDetectionResponse,
} from '../services/api';
import { useReplay } from '../context/ReplayContext';

interface WindowDetectionRecord {
  window: CanonicalTrafficWindow;
  output?: DetectorOutput;
}

export const DetectionPage: React.FC = () => {
  const { pollTick } = useReplay();
  const navigate = useNavigate();

  const [windows, setWindows] = useState<CanonicalTrafficWindow[]>([]);
  const [selectedWindowId, setSelectedWindowId] = useState<string | null>(null);
  const [detectorData, setDetectorData] = useState<DetectorOutput | null>(null);
  const [detectionMap, setDetectionMap] = useState<Record<string, DetectorOutput>>({});
  const [realDetection, setRealDetection] = useState<RealDetectionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch telemetry windows
  const fetchWindows = async (isInitial = false) => {
    if (isInitial) setLoading(true);
    setError(null);
    try {
      const [res, realDetRes] = await Promise.all([
        api.getWindows({ limit: 30 }),
        api.getRealDetection().catch(() => null),
      ]);
      const items = res.items || [];
      setWindows(items);
      if (realDetRes) {
        setRealDetection(realDetRes);
      }
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

  // Evaluate selected window and pre-fetch recent windows detection results
  useEffect(() => {
    if (!selectedWindowId) return;

    api.analyzeWindow({ window_id: selectedWindowId })
      .then((detRes) => {
        if (detRes) {
          setDetectorData(detRes);
          setDetectionMap((prev) => ({ ...prev, [selectedWindowId]: detRes }));
        }
      })
      .catch((err) => {
        console.error('Failed to analyze window:', err);
      });
  }, [selectedWindowId]);

  // Batch analyze recent windows for history trend if not cached
  useEffect(() => {
    if (windows.length === 0) return;

    const uncached = windows.slice(0, 15).filter((w) => !detectionMap[w.window_id]);
    if (uncached.length === 0) return;

    Promise.all(
      uncached.map((w) =>
        api
          .analyzeWindow({ window_id: w.window_id })
          .then((res) => ({ id: w.window_id, res }))
          .catch(() => null)
      )
    ).then((results) => {
      const updates: Record<string, DetectorOutput> = {};
      results.forEach((r) => {
        if (r && r.res) updates[r.id] = r.res;
      });
      if (Object.keys(updates).length > 0) {
        setDetectionMap((prev) => ({ ...prev, ...updates }));
      }
    });
  }, [windows, detectionMap]);

  // Combined records sorted chronologically
  const sortedRecords: WindowDetectionRecord[] = useMemo(() => {
    return [...windows]
      .sort((a, b) => new Date(a.window_start).getTime() - new Date(b.window_start).getTime())
      .map((w) => ({
        window: w,
        output: detectionMap[w.window_id],
      }));
  }, [windows, detectionMap]);

  // Trend data for sparklines and charts
  const historyData = useMemo(() => {
    if (realDetection && realDetection.scored_windows && realDetection.scored_windows.length > 0) {
      return realDetection.scored_windows.slice(0, 30).map((sw) => {
        const d = new Date(sw.timestamp);
        const timeStr = isNaN(d.getTime())
          ? (sw.timestamp ? sw.timestamp.slice(11, 16) : '--:--')
          : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const ifPct = Number((Math.min(1.0, Math.max(0.0, 1.0 - sw.if_score)) * 100).toFixed(1));
        const aePct = Number((Math.min(1.0, sw.ae_error) * 100).toFixed(1));
        const fusedPct = Number((sw.anomaly_score * 100).toFixed(1));
        const isAlarm = sw.verdict === 'attack';

        return {
          time: timeStr,
          window_id: sw.window_id,
          if_percentile: ifPct,
          ae_percentile: aePct,
          fused_percentile: fusedPct,
          cusum_score: Number((sw.anomaly_score * 5.0).toFixed(2)),
          alarm_threshold: 70.0,
          is_alarm: isAlarm,
          agreement: sw.anomaly_score > 0.7 ? 'both_fired' : 'neither',
        };
      });
    }
    return sortedRecords.map(({ window: w, output: out }) => {
      const d = new Date(w.window_start);
      const timeStr = isNaN(d.getTime())
        ? (w.window_start ? w.window_start.slice(11, 16) : '--:--')
        : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      const ifPct = out?.isolation_forest?.benign_percentile ?? 50.0;
      const aePct = out?.autoencoder?.benign_percentile ?? 50.0;
      const fusedPct = out?.fusion?.fused_percentile ?? Math.max(ifPct, aePct);
      const cusumStat = out?.cusum?.accumulated_statistic ?? 0.0;
      const isAlarm = out?.cusum?.is_alarm ?? false;
      const agreement = out?.fusion?.agreement_state ?? 'neither';

      return {
        time: timeStr,
        window_id: w.window_id,
        if_percentile: Number(ifPct.toFixed(1)),
        ae_percentile: Number(aePct.toFixed(1)),
        fused_percentile: Number(fusedPct.toFixed(1)),
        cusum_score: Number(cusumStat.toFixed(2)),
        alarm_threshold: 4.5,
        is_alarm: isAlarm,
        agreement: agreement,
      };
    });
  }, [sortedRecords, realDetection]);

  // Selected window metrics
  const activeOutput = detectorData;
  const ifPct = activeOutput?.isolation_forest?.benign_percentile ?? 50.0;
  const ifRaw = activeOutput?.isolation_forest?.raw_score_negated ?? 0.5;
  const ifFlagged = activeOutput?.isolation_forest?.is_flagged ?? false;

  const aePct = activeOutput?.autoencoder?.benign_percentile ?? 50.0;
  const aeMse = activeOutput?.autoencoder?.reconstruction_mse ?? 0.01;
  const aeFlagged = activeOutput?.autoencoder?.is_flagged ?? false;

  const fusedPct = activeOutput?.fusion?.fused_percentile ?? Math.max(ifPct, aePct);
  const secondaryMean = activeOutput?.fusion?.secondary_mean_percentile ?? (ifPct + aePct) / 2.0;
  const isAnomalous = activeOutput?.fusion?.is_anomalous ?? false;

  const agreementState = activeOutput?.fusion?.agreement_state || 'neither';
  const cusumStat = activeOutput?.cusum?.accumulated_statistic ?? 0.0;
  const cusumStatus = activeOutput?.cusum?.status || (cusumStat >= 4.5 ? 'triggered' : cusumStat > 0 ? 'accumulating' : 'idle');
  const cusumIsAlarm = activeOutput?.cusum?.is_alarm ?? false;

  // Normalize agreement state display
  const isBothFired = agreementState === 'both_fired' || agreementState === 'BOTH_FIRE';
  const isIfOnly = agreementState === 'only_isolation_forest' || agreementState === 'IF_ONLY';
  const isAeOnly = agreementState === 'only_autoencoder' || agreementState === 'AE_ONLY';
  const isNeither = agreementState === 'neither' || agreementState === 'NONE';

  // Agreement State badge variant
  const getAgreementBadge = (state: string) => {
    if (state === 'both_fired' || state === 'BOTH_FIRE') {
      return { label: 'both_fired', variant: 'attack' as const };
    }
    if (state === 'only_isolation_forest' || state === 'IF_ONLY') {
      return { label: 'only_isolation_forest', variant: 'suspicious' as const };
    }
    if (state === 'only_autoencoder' || state === 'AE_ONLY') {
      return { label: 'only_autoencoder', variant: 'suspicious' as const };
    }
    return { label: 'neither', variant: 'safe' as const };
  };

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
      key: 'if_score',
      header: 'IF Score',
      render: (w) => {
        const out = detectionMap[w.window_id];
        const val = out?.isolation_forest?.benign_percentile;
        return (
          <span className={`text-xs font-mono ${val !== undefined && val >= 95 ? 'text-attack font-bold' : 'text-text'}`}>
            {val !== undefined ? `${val.toFixed(1)}%` : '—'}
          </span>
        );
      },
    },
    {
      key: 'ae_score',
      header: 'AE Reconstruction',
      render: (w) => {
        const out = detectionMap[w.window_id];
        const mse = out?.autoencoder?.reconstruction_mse;
        const pct = out?.autoencoder?.benign_percentile;
        return (
          <div className="flex flex-col">
            <span className={`text-xs font-mono ${pct != null && pct >= 95 ? 'text-attack font-bold' : 'text-text'}`}>
              {pct != null ? `${pct.toFixed(1)}%` : '—'}
            </span>
            {mse != null && (
              <span className="text-[10px] font-mono text-muted">
                MSE: {mse.toFixed(4)}
              </span>
            )}
          </div>
        );
      },
    },
    {
      key: 'fused_score',
      header: 'Fused Percentile',
      render: (w) => {
        const out = detectionMap[w.window_id];
        const val = out?.fusion?.fused_percentile;
        return (
          <span className={`text-xs font-mono font-bold ${val !== undefined && val >= 95 ? 'text-attack' : 'text-slate'}`}>
            {val !== undefined ? `${val.toFixed(1)}%` : '—'}
          </span>
        );
      },
    },
    {
      key: 'agreement',
      header: 'Agreement',
      render: (w) => {
        const out = detectionMap[w.window_id];
        const state = out?.fusion?.agreement_state || 'neither';
        const badge = getAgreementBadge(state);
        return <StatusBadge label={badge.label} variant={badge.variant} size="sm" />;
      },
    },
    {
      key: 'status',
      header: 'Status',
      render: (w) => {
        const out = detectionMap[w.window_id];
        const isAnom = out?.fusion?.is_anomalous || out?.cusum?.is_alarm;
        return (
          <StatusBadge
            label={isAnom ? 'Anomaly Alarm' : 'Nominal Safe'}
            variant={isAnom ? 'attack' : 'safe'}
            size="sm"
            dot
          />
        );
      },
    },
    {
      key: 'action',
      header: 'Inspect / Investigate',
      render: (w) => (
        <div className="flex items-center gap-1.5">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setSelectedWindowId(w.window_id);
            }}
            className={`px-2 py-1 text-xs rounded-lg inline-flex items-center gap-1 font-medium transition-colors ${
              w.window_id === selectedWindowId
                ? 'bg-blue text-white shadow-sm'
                : 'bg-bg text-slate hover:bg-slate/10 border border-border'
            }`}
          >
            <Eye className="w-3 h-3" />
            <span>{w.window_id === selectedWindowId ? 'Inspecting' : 'Inspect'}</span>
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              navigate(`/investigation/${w.window_id}`);
            }}
            className="px-2 py-1 text-xs rounded-lg inline-flex items-center gap-1 font-medium bg-bg text-blue hover:bg-blue/10 border border-blue/20 transition-colors shadow-sm"
          >
            <Search className="w-3 h-3" />
            <span>Investigate</span>
          </button>
        </div>
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
        <div className="flex items-center gap-2.5 flex-wrap">
          <DataSourceBadge />
          {selectedWindowId && (
            <span className="text-xs font-mono px-2.5 py-1 rounded-md bg-card border border-border text-muted">
              Active: {selectedWindowId.slice(0, 8)}...
            </span>
          )}
        </div>
      </div>

      {/* Detector Score Panels (3 Columns: IF, AE, Fusion) with Real Values and Trend Lines */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* 1. Isolation Forest Panel */}
        <div className="bg-card rounded-xl border border-border p-5 shadow-sm space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
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
                label={ifFlagged ? 'Flagged' : 'Normal'}
                variant={ifFlagged ? 'attack' : 'safe'}
                size="sm"
                dot
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between items-baseline">
                <span className="text-xs text-muted">Benign Percentile</span>
                <span className="text-xl font-bold font-mono text-text">
                  {ifPct.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-bg rounded-full h-2 overflow-hidden border border-border">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${ifFlagged ? 'bg-attack' : 'bg-blue'}`}
                  style={{ width: `${Math.min(100, ifPct)}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-muted">
                <span>0% Nominal</span>
                <span>Threshold: 95.0%</span>
                <span>100% Anomalous</span>
              </div>
            </div>

            {/* Sparkline / Trend Line */}
            <div className="h-16 w-full pt-1">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historyData}>
                  <Line
                    type="monotone"
                    dataKey="if_percentile"
                    stroke="#3478F6"
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <ReferenceLine y={95} stroke="#DC2626" strokeDasharray="2 2" strokeOpacity={0.6} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="pt-2 border-t border-border/60 text-xs space-y-1 text-muted">
            <div className="flex justify-between">
              <span>Raw Score (Negated):</span>
              <span className="font-mono text-slate font-medium">{ifRaw.toFixed(4)}</span>
            </div>
            <div className="flex justify-between">
              <span>Calibration Reference:</span>
              <span className="font-medium text-slate">60 Benign Windows</span>
            </div>
          </div>
        </div>

        {/* 2. Autoencoder Panel */}
        <div className="bg-card rounded-xl border border-border p-5 shadow-sm space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
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
                label={aeFlagged ? 'Flagged' : 'Normal'}
                variant={aeFlagged ? 'attack' : 'safe'}
                size="sm"
                dot
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex justify-between items-baseline">
                <span className="text-xs text-muted">Benign Percentile</span>
                <span className="text-xl font-bold font-mono text-text">
                  {aePct.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-bg rounded-full h-2 overflow-hidden border border-border">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${aeFlagged ? 'bg-attack' : 'bg-teal'}`}
                  style={{ width: `${Math.min(100, aePct)}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-muted">
                <span>0% Nominal</span>
                <span>Threshold: 95.0%</span>
                <span>100% Anomalous</span>
              </div>
            </div>

            {/* Sparkline / Trend Line */}
            <div className="h-16 w-full pt-1">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historyData}>
                  <Line
                    type="monotone"
                    dataKey="ae_percentile"
                    stroke="#14B8A6"
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <ReferenceLine y={95} stroke="#DC2626" strokeDasharray="2 2" strokeOpacity={0.6} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="pt-2 border-t border-border/60 text-xs space-y-1 text-muted">
            <div className="flex justify-between">
              <span>Reconstruction MSE:</span>
              <span className="font-mono text-slate font-medium">{aeMse.toFixed(4)}</span>
            </div>
            <div className="flex justify-between">
              <span>Architecture:</span>
              <span className="font-medium text-slate">Dense PyTorch (9-6-3-6-9)</span>
            </div>
          </div>
        </div>

        {/* 3. Fused Score Panel */}
        <div className="bg-card rounded-xl border border-border p-5 shadow-sm space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
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

            <div className="space-y-1.5">
              <div className="flex justify-between items-baseline">
                <span className="text-xs text-muted">Fused Percentile</span>
                <span className="text-2xl font-bold font-mono text-text">
                  {fusedPct.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-bg rounded-full h-2 overflow-hidden border border-border">
                <div
                  className={`h-full rounded-full transition-all duration-300 ${isAnomalous ? 'bg-attack' : 'bg-safe'}`}
                  style={{ width: `${Math.min(100, fusedPct)}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-muted">
                <span>Rule: MAX_PERCENTILE</span>
                <span className="font-semibold text-slate">Mean: {secondaryMean.toFixed(1)}%</span>
              </div>
            </div>

            {/* Sparkline / Trend Line */}
            <div className="h-16 w-full pt-1">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historyData}>
                  <Line
                    type="monotone"
                    dataKey="fused_percentile"
                    stroke="#DC2626"
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                  <ReferenceLine y={95} stroke="#DC2626" strokeDasharray="2 2" strokeOpacity={0.6} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="pt-2 border-t border-border/60 text-xs space-y-1 text-muted">
            <div className="flex justify-between">
              <span>Agreement:</span>
              <span className="font-semibold text-slate font-mono">{agreementState}</span>
            </div>
            <div className="flex justify-between">
              <span>Active Baseline:</span>
              <span className="font-mono text-slate">{activeOutput?.baseline_version || 'v1.0.0-anchor'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Middle Grid: CUSUM Trend & Detector Agreement */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: CUSUM Trend with Status & Trigger Marker */}
        <div className="lg:col-span-2">
          <ChartCard
            title="CUSUM Persistent Shift Tracking"
            subtitle="Cumulative sum anomaly statistic across successive windows with trigger detection"
            action={
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted">Status:</span>
                <StatusBadge
                  label={cusumStatus}
                  variant={cusumStatus === 'triggered' ? 'attack' : cusumStatus === 'accumulating' ? 'suspicious' : 'safe'}
                  size="sm"
                  dot
                />
                {cusumIsAlarm && (
                  <span className="text-xs font-bold text-attack flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Alarm
                  </span>
                )}
              </div>
            }
          >
            {historyData.length === 0 ? (
              <EmptyState title="No CUSUM Telemetry" description="Start replay to generate cumulative anomaly tracking." />
            ) : (
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={historyData} margin={{ top: 10, right: 15, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                    <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#64748B' }} stroke="#E2E8F0" />
                    <YAxis tick={{ fontSize: 11, fill: '#64748B' }} stroke="#E2E8F0" domain={[0, 'auto']} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        borderRadius: '8px',
                        border: '1px solid #E2E8F0',
                        fontSize: '12px',
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                    <ReferenceLine
                      y={4.5}
                      stroke="#DC2626"
                      strokeDasharray="4 4"
                      label={{ value: 'Alarm Threshold: 4.5', fill: '#DC2626', fontSize: 10, position: 'insideTopRight' }}
                    />
                    <Line
                      type="monotone"
                      dataKey="cusum_score"
                      name="Accumulated CUSUM"
                      stroke="#8B5CF6"
                      strokeWidth={2}
                      dot={(props: any) => {
                        const { cx, cy, payload } = props;
                        if (payload.is_alarm || payload.cusum_score >= 4.5) {
                          return (
                            <circle
                              key={`trigger-${cx}-${cy}`}
                              cx={cx}
                              cy={cy}
                              r={5}
                              fill="#DC2626"
                              stroke="#FFFFFF"
                              strokeWidth={2}
                            />
                          );
                        }
                        return <circle key={`dot-${cx}-${cy}`} cx={cx} cy={cy} r={2} fill="#8B5CF6" />;
                      }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </ChartCard>
        </div>

        {/* Right 1 Col: Detector Agreement Panel with Current State & History Strip */}
        <div className="lg:col-span-1">
          <div className="bg-card rounded-xl border border-border p-5 shadow-sm space-y-4 h-full flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-border">
                <h3 className="text-sm font-semibold text-text">Detector Agreement State</h3>
                <StatusBadge
                  label={agreementState}
                  variant={isBothFired ? 'attack' : (isIfOnly || isAeOnly) ? 'suspicious' : 'safe'}
                  size="sm"
                />
              </div>

              {/* Current Agreement State Cards */}
              <div className="space-y-2 mt-4">
                <div
                  className={`p-2.5 rounded-lg border text-xs flex items-center justify-between transition-colors ${
                    isBothFired ? 'border-attack bg-attack/10 font-bold' : 'border-border bg-bg/50 text-muted'
                  }`}
                >
                  <span className="text-text">both_fired (Consensus Attack)</span>
                  {isBothFired && <CheckCircle2 className="w-4 h-4 text-attack" />}
                </div>

                <div
                  className={`p-2.5 rounded-lg border text-xs flex items-center justify-between transition-colors ${
                    isIfOnly ? 'border-suspicious bg-suspicious/10 font-bold' : 'border-border bg-bg/50 text-muted'
                  }`}
                >
                  <span className="text-text">only_isolation_forest (Tree Alone)</span>
                  {isIfOnly && <CheckCircle2 className="w-4 h-4 text-suspicious" />}
                </div>

                <div
                  className={`p-2.5 rounded-lg border text-xs flex items-center justify-between transition-colors ${
                    isAeOnly ? 'border-suspicious bg-suspicious/10 font-bold' : 'border-border bg-bg/50 text-muted'
                  }`}
                >
                  <span className="text-text">only_autoencoder (Recon Alone)</span>
                  {isAeOnly && <CheckCircle2 className="w-4 h-4 text-suspicious" />}
                </div>

                <div
                  className={`p-2.5 rounded-lg border text-xs flex items-center justify-between transition-colors ${
                    isNeither ? 'border-safe bg-safe/10 font-bold' : 'border-border bg-bg/50 text-muted'
                  }`}
                >
                  <span className="text-text">neither (All Detectors Nominal)</span>
                  {isNeither && <CheckCircle2 className="w-4 h-4 text-safe" />}
                </div>
              </div>

              {/* Agreement History Strip */}
              <div className="mt-4 pt-3 border-t border-border">
                <span className="text-xs font-semibold text-text block mb-1.5">Agreement History Strip</span>
                {historyData.length === 0 ? (
                  <span className="text-[11px] text-muted">Awaiting replay telemetry...</span>
                ) : (
                  <div className="flex items-center gap-1 overflow-x-auto pb-1">
                    {historyData.map((h, idx) => {
                      const state = h.agreement;
                      const color =
                        state === 'both_fired' || state === 'BOTH_FIRE'
                          ? 'bg-attack'
                          : state === 'only_isolation_forest' || state === 'IF_ONLY' || state === 'only_autoencoder' || state === 'AE_ONLY'
                          ? 'bg-suspicious'
                          : 'bg-safe';
                      const isSel = h.window_id === selectedWindowId;
                      return (
                        <div
                          key={`strip-${idx}`}
                          onClick={() => setSelectedWindowId(h.window_id)}
                          title={`${h.time}: ${state}`}
                          className={`h-6 w-3.5 rounded-sm cursor-pointer transition-all ${color} ${
                            isSel ? 'ring-2 ring-blue scale-110 shadow-sm' : 'opacity-80 hover:opacity-100'
                          }`}
                        />
                      );
                    })}
                  </div>
                )}
                <div className="flex justify-between text-[10px] text-muted mt-1">
                  <span>Earliest</span>
                  <span>Latest window</span>
                </div>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-bg border border-border text-xs text-muted flex items-start gap-2 mt-2">
              <Info className="w-4 h-4 text-blue flex-shrink-0 mt-0.5" />
              <p>
                Consensus scoring fuses Isolation Forest and Autoencoder percentiles. When either crosses 95%, the fused score triggers.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Anomaly Windows Table with All Columns and Status Badge per Row */}
      <div className="bg-card rounded-xl border border-border shadow-sm p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-text">Recent Telemetry Windows</h2>
            <p className="text-xs text-muted">
              Click &quot;Inspect&quot; on any window row to view its multi-model anomaly scoring and calibrated percentiles.
            </p>
          </div>
        </div>

        <DataTable
          columns={columns}
          data={windows}
          keyExtractor={(w) => w.window_id}
          onRowClick={(w) => navigate(`/investigation/${w.window_id}`)}
          emptyMessage="No detection telemetry windows found."
        />
      </div>
    </div>
  );
};

export default DetectionPage;
