import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Eye,
  Layers,
  Search,
  Zap,
} from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  Column,
  DataTable,
  DataSourceBadge,
  ErrorState,
  LoadingState,
  StatusBadge,
  DetectorAgreementMatrix,
} from '../components';
import { formatPercentileWithLogRatio } from '../utils/dataPresentation';
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

// Helper SVG Radial Gauge matching Stitch design
const RadialGauge: React.FC<{
  percentile: number;
  label: string;
  colorClass: string;
  strokeColor: string;
}> = ({ percentile, label, colorClass, strokeColor }) => {
  const clamped = Math.max(0, Math.min(100, percentile));
  // Arc length is 141.37 (r=45 on semicircle)
  const totalArc = 141.37;
  const dashoffset = totalArc - (clamped / 100) * totalArc;

  return (
    <div className="flex flex-col items-center my-2 relative">
      <svg className="w-28 h-20" viewBox="0 0 120 70">
        <path
          className="text-surface-variant dark:text-slate-800"
          d="M 15 65 A 45 45 0 0 1 105 65"
          fill="none"
          stroke="currentColor"
          strokeLinecap="round"
          strokeWidth="9"
        />
        <path
          d="M 15 65 A 45 45 0 0 1 105 65"
          fill="none"
          stroke={strokeColor}
          strokeDasharray={totalArc}
          strokeDashoffset={dashoffset}
          strokeLinecap="round"
          strokeWidth="9"
          className="transition-all duration-500"
        />
      </svg>
      <div className="absolute bottom-0 text-center">
        <span className={`font-metric-stat text-metric-stat font-bold ${colorClass}`}>
          {clamped.toFixed(0)}
          <span className="text-body-xs font-normal text-on-surface-variant">th</span>
        </span>
        <span className="block font-label-mono text-[10px] text-on-surface-variant -mt-1">
          {label}
        </span>
      </div>
    </div>
  );
};

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
  const [viewMode, setViewMode] = useState<'ensemble' | 'individual'>('ensemble');

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
          alarm_threshold: 4.5,
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
  const rawIfPct = activeOutput?.isolation_forest?.benign_percentile ?? 50.0;
  const ifPct = Math.min(100.0, Math.max(0.0, rawIfPct > 1.0 ? rawIfPct : rawIfPct * 100));
  const ifRaw = activeOutput?.isolation_forest?.raw_score_negated ?? 0.5;
  const ifFlagged = activeOutput?.isolation_forest?.is_flagged ?? false;

  const rawAePct = activeOutput?.autoencoder?.benign_percentile ?? 50.0;
  const aePct = Math.min(100.0, Math.max(0.0, rawAePct > 1.0 ? rawAePct : rawAePct * 100));
  const aeMse = activeOutput?.autoencoder?.reconstruction_mse ?? 0.01;
  const aeFlagged = activeOutput?.autoencoder?.is_flagged ?? false;

  const rawFusedPct = activeOutput?.fusion?.fused_percentile ?? Math.max(ifPct, aePct);
  const fusedPct = Math.min(100.0, Math.max(0.0, rawFusedPct > 1.0 ? rawFusedPct : rawFusedPct * 100));
  const rawSecondaryMean = activeOutput?.fusion?.secondary_mean_percentile ?? (ifPct + aePct) / 2.0;
  const secondaryMean = Math.min(100.0, Math.max(0.0, rawSecondaryMean > 1.0 ? rawSecondaryMean : rawSecondaryMean * 100));
  const isAnomalous = activeOutput?.fusion?.is_anomalous ?? false;

  const agreementState = activeOutput?.fusion?.agreement_state || 'neither';
  const cusumStat = activeOutput?.cusum?.accumulated_statistic ?? 0.0;
  const cusumIsAlarm = activeOutput?.cusum?.is_alarm ?? false;

  // Selected window object
  const selectedWindow = useMemo(() => {
    return windows.find((w) => w.window_id === selectedWindowId) || windows[0];
  }, [windows, selectedWindowId]);

  // Normalized agreement state display
  const isBothFired = agreementState === 'both_fired' || agreementState === 'BOTH_FIRE';
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
            w.window_id === selectedWindowId ? 'font-bold text-primary dark:text-blue-400' : 'text-on-surface'
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
      render: (w) => <span className="text-xs font-semibold text-secondary dark:text-slate-300">{w.slice_id}</span>,
    },
    {
      key: 'window_time',
      header: 'Time',
      render: (w) => {
        const d = new Date(w.window_start);
        return (
          <span className="text-xs font-mono text-on-surface-variant">
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
          <span className={`text-xs font-mono ${val !== undefined && val >= 95 ? 'text-error font-bold' : 'text-on-surface'}`}>
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
            <span className={`text-xs font-mono ${pct != null && pct >= 95 ? 'text-error font-bold' : 'text-on-surface'}`}>
              {pct != null ? `${pct.toFixed(1)}%` : '—'}
            </span>
            {mse != null && (
              <span className="text-[10px] font-mono text-on-surface-variant">
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
          <span className={`text-xs font-mono font-bold ${val !== undefined && val >= 95 ? 'text-error' : 'text-secondary dark:text-slate-300'}`}>
            {val !== undefined ? formatPercentileWithLogRatio(val) : 'no data'}
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
            className={`px-2.5 py-1 text-xs rounded-lg inline-flex items-center gap-1 font-medium transition-colors ${
              w.window_id === selectedWindowId
                ? 'bg-primary text-white shadow-sm'
                : 'bg-surface-container-low text-on-surface hover:bg-surface-container border border-outline-variant/60'
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
            className="px-2.5 py-1 text-xs rounded-lg inline-flex items-center gap-1 font-medium bg-surface-container-lowest text-primary hover:bg-primary/10 border border-primary/30 transition-colors shadow-sm"
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

  const agreementCounts = useMemo(() => {
    let both = 0;
    let ifo = 0;
    let aeo = 0;
    let non = 0;
    historyData.forEach((h) => {
      const isIf = (h.if_percentile ?? 0) >= 95;
      const isAe = (h.ae_percentile ?? 0) >= 95;
      if (isIf && isAe) both++;
      else if (isIf) ifo++;
      else if (isAe) aeo++;
      else non++;
    });
    return { both, ifo, aeo, non };
  }, [historyData]);

  const isSevere = fusedPct >= 95.0 || isAnomalous || cusumIsAlarm;

  return (
    <div className="flex flex-col w-full gap-space-lg pb-space-2xl">
      {/* 1. Investigation Context Header Banner matching Stitch */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md bg-surface-container-lowest dark:bg-card p-space-lg rounded-xl shadow-sm border border-outline-variant/40 dark:border-border">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-space-xs font-label-mono text-body-xs text-on-surface-variant flex-wrap">
            <span>DETECTION</span>
            <span className="text-outline">/</span>
            <span>MULTI-MODEL INFERENCE</span>
            <span className="text-outline">/</span>
            <span className="text-primary font-medium">WINDOW #{selectedWindowId ? selectedWindowId.slice(0, 14) : 'LIVE'}</span>
            {isSevere ? (
              <span className="px-2 py-0.5 ml-2 rounded-full bg-error-container text-on-error-container font-badge-status text-badge-status tracking-wider">
                ANOMALY FLAGGED
              </span>
            ) : (
              <span className="px-2 py-0.5 ml-2 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 font-badge-status text-badge-status tracking-wider">
                NOMINAL FLOW
              </span>
            )}
          </div>
          <h1 className="font-headline-xl text-headline-xl text-on-surface tracking-tight">
            Anomaly Detection & Multi-Model Inference
          </h1>
          <p className="font-body-sm text-body-sm text-on-surface-variant">
            Active 5G core telemetry analysis with concurrent non-parametric drift scoring across slices.
          </p>
        </div>

        {/* Controls Row */}
        <div className="flex flex-wrap items-center gap-space-sm">
          {/* Mode Toggle Segmented Control */}
          <div className="flex items-center p-1 bg-surface-container-low dark:bg-bg rounded-lg border border-outline-variant/50 dark:border-border">
            <button
              onClick={() => setViewMode('ensemble')}
              className={`px-3 py-1.5 rounded-lg font-body-sm text-body-sm font-semibold transition-all flex items-center gap-1.5 ${
                viewMode === 'ensemble'
                  ? 'bg-surface-container-lowest dark:bg-card text-primary shadow-sm'
                  : 'text-secondary hover:text-on-surface'
              }`}
            >
              <Cpu className="w-4 h-4 text-primary" />
              Ensemble Mode
            </button>
            <button
              onClick={() => setViewMode('individual')}
              className={`px-3 py-1.5 rounded-lg font-body-sm text-body-sm transition-all flex items-center gap-1.5 ${
                viewMode === 'individual'
                  ? 'bg-surface-container-lowest dark:bg-card text-primary shadow-sm font-semibold'
                  : 'text-secondary hover:text-on-surface'
              }`}
            >
              <Layers className="w-4 h-4" />
              Individual Models
            </button>
          </div>

          <DataSourceBadge />

          {selectedWindowId && (
            <button
              onClick={() => navigate(`/investigation/${selectedWindowId}`)}
              className="bg-primary text-on-primary px-3.5 py-1.5 rounded-lg font-body-sm text-body-sm font-medium hover:bg-surface-tint shadow-sm flex items-center gap-1.5 transition-colors"
            >
              <Search className="w-4 h-4" />
              Drill-down Dossier
            </button>
          )}
        </div>
      </div>

      {/* 2. Split View Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-lg">
        {/* LEFT 60%: Multi-Detector Diagnostic Panel */}
        <div className="lg:col-span-7 flex flex-col gap-space-md">
          {/* High Severity Fused Score Banner */}
          <div
            className={`relative overflow-hidden text-white p-space-md rounded-xl shadow-md ${
              isSevere
                ? 'bg-gradient-to-r from-error/90 via-error to-[#7a0606]'
                : 'bg-gradient-to-r from-[#004ac6] via-[#1e3a8a] to-[#0a1628]'
            }`}
          >
            <div className="absolute -right-6 -bottom-6 w-36 h-36 rounded-full bg-white/5 blur-xl pointer-events-none" />
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-space-sm relative z-10">
              <div className="flex items-center gap-space-md">
                <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center flex-shrink-0">
                  {isSevere ? (
                    <AlertTriangle className="w-7 h-7 text-white animate-pulse" />
                  ) : (
                    <CheckCircle2 className="w-7 h-7 text-emerald-300" />
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-label-mono text-body-xs tracking-wider uppercase opacity-90">
                      Ensemble Fused Anomaly Score
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-white/20 text-white font-badge-status text-badge-status tracking-widest uppercase">
                      {fusedPct >= 95 ? 'P95+ CRITICAL' : 'P50 NOMINAL'}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-2 mt-0.5">
                    <span className="font-display-lg text-display-lg font-bold tracking-tight">
                      {fusedPct.toFixed(1)}
                    </span>
                    <span className="font-headline-md text-headline-md opacity-80">/ 100</span>
                    <span className="font-label-mono text-body-xs bg-black/25 px-2 py-0.5 rounded ml-2">
                      Secondary Mean: {secondaryMean.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex flex-col items-end">
                <span className="px-3 py-1 rounded bg-black/30 font-label-mono text-body-xs font-semibold tracking-wider flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full ${isSevere ? 'bg-error animate-ping' : 'bg-emerald-400'}`} />
                  {isSevere ? 'ACTION TRIGGERED' : 'MONITORING NOMINAL FLOW'}
                </span>
                <span className="font-body-xs text-body-xs opacity-75 mt-1">
                  Baseline: {activeOutput?.baseline_version || 'v1.0.0-anchor'}
                </span>
              </div>
            </div>
          </div>

          {/* 3 Detector Cards Grid matching Stitch radial gauges */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
            {/* Detector 1: Isolation Forest */}
            <div className="bg-surface-container-lowest dark:bg-card p-space-md rounded-xl shadow-sm border border-outline-variant/40 dark:border-border flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-space-xs">
                  <span className="font-title-sm text-title-sm font-semibold text-on-surface">Isolation Forest</span>
                  <span className={`px-1.5 py-0.5 rounded font-label-mono text-[10px] font-bold ${
                    ifFlagged ? 'bg-error-container text-on-error-container' : 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300'
                  }`}>
                    {ifFlagged ? 'ALERT' : 'NOMINAL'}
                  </span>
                </div>
                <p className="font-body-xs text-body-xs text-on-surface-variant">Tree-path depth metric</p>
              </div>

              <RadialGauge
                percentile={ifPct}
                label="Percentile"
                colorClass={ifFlagged ? 'text-error' : 'text-primary dark:text-blue-400'}
                strokeColor={ifFlagged ? '#ba1a1a' : '#2563eb'}
              />

              <div className="flex flex-col gap-1.5 pt-2 bg-surface-container-low dark:bg-bg p-2 rounded-lg font-label-mono text-body-xs border border-outline-variant/30 dark:border-border/60">
                <div className="flex justify-between text-on-surface-variant">
                  <span>Raw Score:</span>
                  <span className="font-semibold text-on-surface">{ifRaw.toFixed(4)}</span>
                </div>
                <div className="flex justify-between text-on-surface-variant">
                  <span>Reference:</span>
                  <span className="font-semibold text-on-surface">60 Windows</span>
                </div>
                <div className="flex justify-between text-on-surface-variant">
                  <span>Threshold:</span>
                  <span className="font-semibold text-primary dark:text-blue-400">95.0%</span>
                </div>
              </div>
            </div>

            {/* Detector 2: Autoencoder */}
            <div className="bg-surface-container-lowest dark:bg-card p-space-md rounded-xl shadow-sm border border-outline-variant/40 dark:border-border flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-space-xs">
                  <span className="font-title-sm text-title-sm font-semibold text-on-surface">Autoencoder</span>
                  <span className={`px-1.5 py-0.5 rounded font-label-mono text-[10px] font-bold ${
                    aeFlagged ? 'bg-error-container text-on-error-container' : 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300'
                  }`}>
                    {aeFlagged ? 'LOSS SPIKE' : 'NORMAL'}
                  </span>
                </div>
                <p className="font-body-xs text-body-xs text-on-surface-variant">Reconstruction MSE</p>
              </div>

              <RadialGauge
                percentile={aePct}
                label="Percentile"
                colorClass={aeFlagged ? 'text-error' : 'text-teal-600 dark:text-teal-400'}
                strokeColor={aeFlagged ? '#ba1a1a' : '#007d57'}
              />

              <div className="flex flex-col gap-1.5 pt-2 bg-surface-container-low dark:bg-bg p-2 rounded-lg font-label-mono text-body-xs border border-outline-variant/30 dark:border-border/60">
                <div className="flex justify-between text-on-surface-variant">
                  <span>MSE Loss:</span>
                  <span className={`font-semibold ${aeFlagged ? 'text-error' : 'text-on-surface'}`}>{aeMse.toFixed(4)}</span>
                </div>
                <div className="flex justify-between text-on-surface-variant">
                  <span>Network:</span>
                  <span className="font-semibold text-on-surface">9-6-3-6-9</span>
                </div>
                <div className="flex justify-between text-on-surface-variant">
                  <span>Threshold:</span>
                  <span className="font-semibold text-primary dark:text-blue-400">95.0%</span>
                </div>
              </div>
            </div>

            {/* Detector 3: Bayesian Fusion / Fused Consensus */}
            <div className="bg-surface-container-lowest dark:bg-card p-space-md rounded-xl shadow-sm border border-outline-variant/40 dark:border-border flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-space-xs">
                  <span className="font-title-sm text-title-sm font-semibold text-on-surface">Fused Consensus</span>
                  <span className="px-1.5 py-0.5 rounded bg-tertiary-fixed text-on-tertiary-fixed font-label-mono text-[10px] font-bold">
                    {agreementState.toUpperCase()}
                  </span>
                </div>
                <p className="font-body-xs text-body-xs text-on-surface-variant">Max-percentile rule</p>
              </div>

              <RadialGauge
                percentile={fusedPct}
                label="Percentile"
                colorClass={isAnomalous ? 'text-error' : 'text-primary dark:text-blue-400'}
                strokeColor={isAnomalous ? '#ba1a1a' : '#004ac6'}
              />

              <div className="flex flex-col gap-1.5 pt-2 bg-surface-container-low dark:bg-bg p-2 rounded-lg font-label-mono text-body-xs border border-outline-variant/30 dark:border-border/60">
                <div className="flex justify-between text-on-surface-variant">
                  <span>Rule:</span>
                  <span className="font-semibold text-on-surface">MAX_PERCENTILE</span>
                </div>
                <div className="flex justify-between text-on-surface-variant">
                  <span>Secondary:</span>
                  <span className="font-semibold text-on-surface">{secondaryMean.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between text-on-surface-variant">
                  <span>Verdict:</span>
                  <span className={`font-semibold ${isAnomalous ? 'text-error' : 'text-emerald-600 dark:text-emerald-400'}`}>
                    {isAnomalous ? 'ANOMALOUS' : 'NOMINAL'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Feature Attribution Card matching Stitch */}
          <div className="bg-surface-container-lowest dark:bg-card p-space-md rounded-xl shadow-sm border border-outline-variant/40 dark:border-border">
            <div className="flex items-center justify-between mb-space-sm">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-primary" />
                <span className="font-title-sm text-title-sm font-semibold text-on-surface">
                  Multi-Model Feature Attribution (Calibrated Ratios)
                </span>
              </div>
              <span className="font-label-mono text-body-xs text-on-surface-variant">
                Target: {selectedWindow?.slice_id || 'eMBB-HighCap'}
              </span>
            </div>

            <div className="flex flex-col gap-3">
              <div>
                <div className="flex justify-between font-body-sm text-body-sm mb-1">
                  <span className="font-medium text-on-surface">GTP / Packet Rate Volatility</span>
                  <span className="font-label-mono text-primary dark:text-blue-400 font-semibold">
                    {selectedWindow?.raw_counters
                      ? `${(selectedWindow.raw_counters['packet_count'] ?? selectedWindow.raw_counters['packets'] ?? 0).toLocaleString()} pkts`
                      : 'Nominal'}
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-surface-container dark:bg-slate-800">
                  <div className="h-2 rounded-full bg-primary" style={{ width: `${Math.min(100, Math.max(15, fusedPct))}%` }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between font-body-sm text-body-sm mb-1">
                  <span className="font-medium text-on-surface">Byte Volume Rate</span>
                  <span className="font-label-mono text-primary-container dark:text-blue-300 font-semibold">
                    {selectedWindow?.raw_counters
                      ? `${((selectedWindow.raw_counters['byte_count'] ?? selectedWindow.raw_counters['bytes'] ?? 0) / (1024 * 1024)).toFixed(2)} MB`
                      : 'Nominal'}
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-surface-container dark:bg-slate-800">
                  <div className="h-2 rounded-full bg-primary-container" style={{ width: `${Math.min(100, Math.max(10, ifPct))}%` }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between font-body-sm text-body-sm mb-1">
                  <span className="font-medium text-on-surface">Reconstruction Residual Variance</span>
                  <span className="font-label-mono text-secondary dark:text-slate-300 font-semibold">
                    MSE: {aeMse.toFixed(4)} ({aePct.toFixed(1)}%)
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-surface-container dark:bg-slate-800">
                  <div className="h-2 rounded-full bg-secondary" style={{ width: `${Math.min(100, Math.max(8, aePct))}%` }} />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT 40%: CUSUM Drift & Agreement Timeline matching Stitch */}
        <div className="lg:col-span-5 flex flex-col gap-space-md">
          {/* CUSUM Sequential Drift Card */}
          <div className="bg-surface-container-lowest dark:bg-card p-space-md rounded-xl shadow-sm border border-outline-variant/40 dark:border-border flex flex-col">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-error" />
                <span className="font-title-sm text-title-sm font-semibold text-on-surface">
                  CUSUM Sequential Drift (H = 4.5σ)
                </span>
              </div>
              <span className={`px-2 py-0.5 rounded font-label-mono text-[10px] font-bold ${
                cusumIsAlarm
                  ? 'bg-error-container text-on-error-container'
                  : 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300'
              }`}>
                {cusumIsAlarm ? 'ALARM TRIGGERED' : `STAT: ${cusumStat.toFixed(2)}`}
              </span>
            </div>
            <p className="font-body-xs text-body-xs text-on-surface-variant mb-3">
              Continuous cumulative deviation monitoring indicating persistent state shift across successive windows.
            </p>

            <div className="h-44 w-full bg-surface-container-low dark:bg-bg rounded-lg p-2 border border-outline-variant/30 dark:border-border/60">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={historyData} margin={{ top: 8, right: 10, left: -25, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#CBD5E1" opacity={0.5} />
                  <XAxis dataKey="time" tick={{ fontSize: 9, fill: '#64748B' }} stroke="#CBD5E1" />
                  <YAxis tick={{ fontSize: 9, fill: '#64748B' }} stroke="#CBD5E1" domain={[0, 'auto']} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderRadius: '8px',
                      border: '1px solid #CBD5E1',
                      fontSize: '11px',
                    }}
                  />
                  <ReferenceLine
                    y={4.5}
                    stroke="#ba1a1a"
                    strokeDasharray="4 4"
                    label={{ value: 'H=4.5', fill: '#ba1a1a', fontSize: 9, position: 'insideTopRight' }}
                  />
                  <Line
                    type="monotone"
                    dataKey="cusum_score"
                    stroke="#ba1a1a"
                    strokeWidth={2}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="flex justify-between items-center text-[10px] font-label-mono text-outline pt-2">
              <span>Earliest Window</span>
              <span className={cusumIsAlarm ? 'text-error font-bold' : 'text-on-surface'}>
                Current Stat: {cusumStat.toFixed(2)}σ
              </span>
              <span>Latest Window</span>
            </div>
          </div>

          {/* Detector Agreement Heat Track Card */}
          <div className="bg-surface-container-lowest dark:bg-card p-space-md rounded-xl shadow-sm border border-outline-variant/40 dark:border-border flex flex-col justify-between flex-1">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-primary" />
                <span className="font-title-sm text-title-sm font-semibold text-on-surface">
                  Detector Agreement Heat Track
                </span>
              </div>
              <span className="font-label-mono text-body-xs text-on-surface-variant">
                State: {agreementState}
              </span>
            </div>

            <div className="flex flex-col gap-3 py-2">
              {/* Row 1: Isolation Forest */}
              <div className="flex flex-col gap-1">
                <div className="flex justify-between items-center text-[11px] font-label-mono text-on-surface">
                  <span className="font-semibold">Isolation Forest</span>
                  <span className={ifPct >= 95 ? 'text-error font-medium' : 'text-secondary'}>
                    {ifPct.toFixed(1)}% Pctl
                  </span>
                </div>
                <div className="flex items-center gap-1 overflow-x-auto pb-1">
                  {historyData.map((h, i) => (
                    <div
                      key={`if-${i}`}
                      onClick={() => setSelectedWindowId(h.window_id)}
                      title={`${h.time}: IF ${h.if_percentile}%`}
                      className={`h-4 flex-1 min-w-[10px] rounded-xs cursor-pointer transition-all ${
                        h.if_percentile >= 95 ? 'bg-error' : h.if_percentile >= 80 ? 'bg-primary-container' : 'bg-surface-container-high dark:bg-slate-700'
                      } ${h.window_id === selectedWindowId ? 'ring-2 ring-primary scale-110' : ''}`}
                    />
                  ))}
                </div>
              </div>

              {/* Row 2: Autoencoder */}
              <div className="flex flex-col gap-1">
                <div className="flex justify-between items-center text-[11px] font-label-mono text-on-surface">
                  <span className="font-semibold">Autoencoder Loss</span>
                  <span className={aePct >= 95 ? 'text-error font-medium' : 'text-secondary'}>
                    {aePct.toFixed(1)}% Pctl
                  </span>
                </div>
                <div className="flex items-center gap-1 overflow-x-auto pb-1">
                  {historyData.map((h, i) => (
                    <div
                      key={`ae-${i}`}
                      onClick={() => setSelectedWindowId(h.window_id)}
                      title={`${h.time}: AE ${h.ae_percentile}%`}
                      className={`h-4 flex-1 min-w-[10px] rounded-xs cursor-pointer transition-all ${
                        h.ae_percentile >= 95 ? 'bg-error' : h.ae_percentile >= 80 ? 'bg-tertiary-container' : 'bg-surface-container-high dark:bg-slate-700'
                      } ${h.window_id === selectedWindowId ? 'ring-2 ring-primary scale-110' : ''}`}
                    />
                  ))}
                </div>
              </div>

              {/* Row 3: Consensus Agreement */}
              <div className="flex flex-col gap-1">
                <div className="flex justify-between items-center text-[11px] font-label-mono text-on-surface">
                  <span className="font-semibold">Consensus Agreement</span>
                  <span className={isBothFired ? 'text-error font-bold' : 'text-secondary'}>
                    {isBothFired ? 'Consensus Attack' : isNeither ? 'Nominal' : 'Single Detector'}
                  </span>
                </div>
                <div className="flex items-center gap-1 overflow-x-auto pb-1">
                  {historyData.map((h, i) => {
                    const c =
                      h.agreement === 'both_fired' || h.agreement === 'BOTH_FIRE'
                        ? 'bg-error'
                        : h.agreement === 'neither' || h.agreement === 'NONE'
                        ? 'bg-surface-container-high dark:bg-slate-700'
                        : 'bg-primary-container';
                    return (
                      <div
                        key={`cn-${i}`}
                        onClick={() => setSelectedWindowId(h.window_id)}
                        title={`${h.time}: ${h.agreement}`}
                        className={`h-4 flex-1 min-w-[10px] rounded-xs cursor-pointer transition-all ${c} ${
                          h.window_id === selectedWindowId ? 'ring-2 ring-primary scale-110' : ''
                        }`}
                      />
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between text-body-xs font-label-mono text-on-surface-variant pt-2 border-t border-outline-variant/30 dark:border-border/60">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-surface-container-high dark:bg-slate-700" />
                <span>Nominal</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-primary-container" />
                <span>Single Warning</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded bg-error" />
                <span>Consensus Breach</span>
              </div>
            </div>
          </div>

          <DetectorAgreementMatrix
            bothFire={agreementCounts.both}
            ifOnly={agreementCounts.ifo}
            aeOnly={agreementCounts.aeo}
            none={agreementCounts.non}
            n={historyData.length}
            source="5g_nidd"
          />
        </div>
      </div>

      {/* 3. High-Fidelity 5G Ingress Packet Flow Diagnostics Table matching Stitch */}
      <div className="bg-surface-container-lowest dark:bg-card rounded-xl shadow-sm border border-outline-variant/40 dark:border-border overflow-hidden flex flex-col">
        <div className="p-space-md flex flex-col md:flex-row md:items-center justify-between gap-space-sm bg-surface-container-lowest dark:bg-card border-b border-outline-variant/30 dark:border-border">
          <div className="flex items-center gap-space-sm">
            <div className="p-2 rounded-lg bg-surface-container-low dark:bg-bg text-primary">
              <Search className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-title-sm text-title-sm font-semibold text-on-surface">
                5G Telemetry Window Diagnostics
              </h2>
              <span className="font-body-xs text-body-xs text-on-surface-variant">
                Live telemetry slice feed — UPF Edge ingress queue with non-parametric calibrated percentiles
              </span>
            </div>
          </div>
        </div>

        <div className="p-space-md">
          <DataTable
            columns={columns}
            data={windows}
            keyExtractor={(w) => w.window_id}
            onRowClick={(w) => setSelectedWindowId(w.window_id)}
            emptyMessage="No detection telemetry windows found."
          />
        </div>
      </div>
    </div>
  );
};

export default DetectionPage;
