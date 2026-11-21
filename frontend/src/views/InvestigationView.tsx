import React, { useEffect, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import {
  AlertOctagon,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  Clock,
  Cpu,
  FileText,
  HelpCircle,
  Layers,
  MessageSquare,
  Radio,
  RefreshCw,
  Search,
  Send,
  ShieldAlert,
  ShieldCheck,
  ThumbsDown,
  ThumbsUp,
  Zap,
} from 'lucide-react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  ChartCard,
  EmptyState,
  ErrorState,
  LoadingState,
  StatusBadge,
} from '../components';
import {
  api,
  InvestigationDetailsResponse,
} from '../services/api';

const formatPctValue = (val: number | undefined | null): string => {
  if (val === undefined || val === null || isNaN(val)) return '0.0%';
  const pct = val > 1.0 ? val : val * 100;
  return `${pct.toFixed(1)}%`;
};

export const InvestigationView: React.FC = () => {
  const { id: routeTargetId } = useParams<{ id?: string }>();
  const navigate = useNavigate();

  const [activeTargetId, setActiveTargetId] = useState<string | null>(routeTargetId || null);
  const [data, setData] = useState<InvestigationDetailsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Analyst Action Form State
  const [analystId, setAnalystId] = useState('analyst_sec_01');
  const [classification, setClassification] = useState<'TRUE_POSITIVE' | 'FALSE_POSITIVE' | 'NOTE'>('TRUE_POSITIVE');
  const [analystNotes, setAnalystNotes] = useState('');
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  const [feedbackSuccessMsg, setFeedbackSuccessMsg] = useState<string | null>(null);

  // Synchronize route param with active state
  useEffect(() => {
    if (routeTargetId) {
      setActiveTargetId(routeTargetId);
    }
  }, [routeTargetId]);

  // Load investigation dossier
  const fetchInvestigation = async (targetId: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getInvestigationDetails(targetId);
      setData(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : `Failed to load investigation for ${targetId}`;
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  // If no ID is specified, load recent alerts/drift events to pick from
  useEffect(() => {
    if (!activeTargetId) {
      setLoading(true);
      Promise.all([
        api.getAlerts().catch(() => []),
        api.getDriftEvents(undefined, 20).catch(() => []),
      ])
        .then(([alertsRes, driftRes]) => {
          if (alertsRes && alertsRes.length > 0) {
            const firstId = alertsRes[0].window_id || alertsRes[0].id;
            setActiveTargetId(firstId);
            navigate(`/investigation/${firstId}`, { replace: true });
          } else if (driftRes && driftRes.length > 0) {
            const firstId = driftRes[0].window_id || driftRes[0].id;
            setActiveTargetId(firstId);
            navigate(`/investigation/${firstId}`, { replace: true });
          } else {
            setLoading(false);
          }
        })
        .catch((err) => {
          setError(err instanceof Error ? err.message : 'Failed to discover alerts');
          setLoading(false);
        });
    } else {
      fetchInvestigation(activeTargetId);
    }
  }, [activeTargetId]);

  // Submit Analyst Classification / Note
  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeTargetId || !analystNotes.trim()) return;

    setSubmittingFeedback(true);
    setFeedbackSuccessMsg(null);
    try {
      await api.submitInvestigationFeedback(activeTargetId, {
        analyst_id: analystId,
        classification,
        notes: analystNotes.trim(),
      });
      setFeedbackSuccessMsg('Analyst verification action recorded to audit_events and approval_logs.');
      setAnalystNotes('');
      // Refresh investigation details to update audit log
      const updated = await api.getInvestigationDetails(activeTargetId);
      setData(updated);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit analyst feedback';
      setError(msg);
    } finally {
      setSubmittingFeedback(false);
    }
  };

  // 1. Loading State
  if (loading) {
    return (
      <div className="py-12">
        <LoadingState message="Compiling investigation evidence, expected baselines, and audit traces..." size="lg" />
      </div>
    );
  }

  // 2. Error State
  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/detection')}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate hover:text-blue transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Anomaly Detection
          </button>
        </div>
        <ErrorState
          title="Investigation Error"
          message={error}
          onRetry={() => {
            if (activeTargetId) fetchInvestigation(activeTargetId);
          }}
        />
      </div>
    );
  }

  // 3. Empty State (no alert or window exists)
  if (!data || !data.alert_header) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-text">Security Investigation</h1>
          <p className="text-sm text-muted mt-0.5">
            Deep forensic drill-down into anomaly evidence, expected vs observed traffic, and autonomous decision traces.
          </p>
        </div>
        <EmptyState
          icon={<Search className="w-8 h-8 text-muted" />}
          title="No Investigation Dossier Available"
          description="No anomaly alerts or drift events are currently available to investigate. Trigger a scenario replay from the top bar to evaluate live telemetry windows."
          action={
            <button
              onClick={() => navigate('/detection')}
              className="px-4 py-2 text-xs font-semibold text-white bg-blue rounded-lg shadow-sm hover:bg-blue-hover transition-colors"
            >
              Go to Anomaly Detection
            </button>
          }
        />
      </div>
    );
  }

  const { alert_header, traffic_series, evidence, timeline_steps, why_explanation, governance_link, feedback_history } = data;

  // Severity styling
  const severityVariant =
    alert_header.severity === 'CRITICAL' ? 'attack' :
    alert_header.severity === 'HIGH' ? 'suspicious' :
    alert_header.severity === 'MEDIUM' ? 'blue' : 'neutral';

  const decisionVariant =
    alert_header.final_decision === 'Quarantine' ? 'quarantined' :
    alert_header.final_decision === 'Alert' ? 'attack' :
    alert_header.final_decision === 'Abstain' ? 'suspicious' : 'safe';

  return (
    <div className="space-y-6 pb-12">
      {/* Navigation & Context Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-border/60">
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate(-1)}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate hover:text-blue transition-colors px-2 py-1 rounded-md hover:bg-slate/10"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back
          </button>
          <span className="text-muted/60 text-xs">/</span>
          <span className="text-xs text-muted font-medium">Investigation Dossier</span>
          <span className="text-muted/60 text-xs">/</span>
          <span className="font-mono text-xs font-bold text-text">{alert_header.window_id.slice(0, 14)}...</span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchInvestigation(activeTargetId || alert_header.id)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate bg-card border border-border rounded-lg hover:bg-slate/5 transition-colors shadow-sm"
          >
            <RefreshCw className="w-3 h-3" />
            Refresh
          </button>
          {governance_link && (
            <Link
              to="/governance"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-teal bg-teal/10 border border-teal/20 rounded-lg hover:bg-teal/20 transition-colors"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Baseline Governance
              <ChevronRight className="w-3 h-3" />
            </Link>
          )}
        </div>
      </div>

      {/* 1. Alert Header Card */}
      <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="font-mono text-base font-bold text-text">
                Target: {alert_header.window_id}
              </span>
              <StatusBadge
                label={`${alert_header.severity} SEVERITY`}
                variant={severityVariant}
                size="sm"
                dot
              />
              <StatusBadge
                label={`VERDICT: ${alert_header.final_decision.toUpperCase()}`}
                variant={decisionVariant}
                size="sm"
              />
            </div>
            <p className="text-xs text-muted mt-1.5 flex flex-wrap items-center gap-4">
              <span className="inline-flex items-center gap-1">
                <Radio className="w-3.5 h-3.5 text-blue" />
                Slice: <strong className="font-semibold text-text">{alert_header.slice_id}</strong>
              </span>
              <span className="inline-flex items-center gap-1">
                <Layers className="w-3.5 h-3.5 text-teal" />
                NF: <strong className="font-semibold text-text">{alert_header.nf_id}</strong>
              </span>
              <span className="inline-flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-slate" />
                Evaluated: <strong className="font-mono text-text">{alert_header.timestamp}</strong>
              </span>
              <span className="inline-flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-approved" />
                Active Baseline: <strong className="font-mono text-text">{alert_header.baseline_version}</strong>
              </span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-xs font-semibold uppercase tracking-wider text-muted">Fused Percentile</div>
              <div className="text-2xl font-black text-attack font-mono">
                {formatPctValue(evidence.detector_scores.fusion.fused_percentile)}
              </div>
            </div>
            <div className="h-10 w-px bg-border/80" />
            <div className="text-right">
              <div className="text-xs font-semibold uppercase tracking-wider text-muted">JSD Divergence</div>
              <div className="text-2xl font-black text-slate font-mono">
                {evidence.js_divergence.value.toFixed(4)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 6. Special Callout if Abstained or Quarantined */}
      {alert_header.final_decision === 'Quarantine' && (
        <div className="p-4 rounded-xl border border-quarantined/30 bg-quarantined/5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-sm">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-quarantined/10 text-quarantined mt-0.5">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-text">Telemetry Window Quarantined (Zero-Trust Enforced)</h4>
              <p className="text-xs text-muted mt-0.5">
                {why_explanation.quarantine_reason ||
                  'Signaling composition failed proportional growth validation (JSD > 0.035). This window is strictly quarantined and excluded from future model training.'}
              </p>
            </div>
          </div>
          {governance_link && (
            <Link
              to="/governance"
              className="shrink-0 px-3 py-1.5 text-xs font-semibold text-white bg-quarantined hover:bg-purple-700 rounded-lg shadow-sm transition-colors inline-flex items-center gap-1.5"
            >
              <span>Inspect Candidate Gates</span>
              <ChevronRight className="w-3 h-3" />
            </Link>
          )}
        </div>
      )}

      {alert_header.final_decision === 'Abstain' && (
        <div className="p-4 rounded-xl border border-suspicious/30 bg-suspicious/5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-sm">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-suspicious/10 text-suspicious mt-0.5">
              <HelpCircle className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-text">Autonomous Decision Abstained</h4>
              <p className="text-xs text-muted mt-0.5">
                {why_explanation.abstain_reason ||
                  'The attribution pipeline encountered inconclusive evidence or insufficient sample volume. Automated baseline mutation was blocked.'}
              </p>
            </div>
          </div>
          <span className="shrink-0 text-xs font-mono font-semibold text-suspicious bg-suspicious/10 px-2.5 py-1 rounded-md border border-suspicious/20">
            Awaiting Operator Review
          </span>
        </div>
      )}

      {/* 5. Plain-Language "Why did the system decide this?" Card */}
      <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <FileText className="w-4 h-4 text-blue" />
          <h3 className="text-base font-bold text-text">Why did the system decide this?</h3>
          <span className="text-xs text-muted font-normal">(Derived directly from runtime audit metrics)</span>
        </div>

        <div className="p-4 rounded-lg bg-bg border border-border/80">
          <p className="text-sm font-medium text-text leading-relaxed">
            {why_explanation.summary}
          </p>
        </div>

        <div className="mt-4 space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-muted">Supporting Evidence & Triggers:</span>
          <ul className="space-y-1.5">
            {why_explanation.key_reasons.map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-slate">
                <span className="text-blue font-bold mt-0.5">•</span>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* 2. Expected vs Observed Traffic (Shaded Band + Observed Line + Deviation Markers) */}
      <ChartCard
        title="Expected vs Observed Traffic Trend"
        subtitle="Active baseline nominal range (Median ± 1.5 IQR) vs continuous 60s window packet counters"
      >
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={traffic_series} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="expectedBand" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3478F6" stopOpacity={0.18} />
                  <stop offset="95%" stopColor="#3478F6" stopOpacity={0.03} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
              <XAxis dataKey="time" tick={{ fontSize: 11, fill: '#64748B' }} stroke="#CBD5E1" />
              <YAxis tick={{ fontSize: 11, fill: '#64748B' }} stroke="#CBD5E1" />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload;
                    return (
                      <div className="bg-card border border-border p-3 rounded-lg shadow-lg text-xs space-y-1">
                        <div className="font-mono font-bold text-text border-b border-border/60 pb-1">
                          Time: {d.time} {d.is_current ? '(Investigated Window)' : ''}
                        </div>
                        <div className="text-slate">
                          Observed Packets: <strong className="text-blue font-mono">{d.observed_packets.toLocaleString()}</strong>
                        </div>
                        <div className="text-muted">
                          Expected Median: <strong className="font-mono">{d.expected_median.toLocaleString()}</strong>
                        </div>
                        <div className="text-muted">
                          Expected Bounds: <span className="font-mono">[{d.expected_min.toLocaleString()} – {d.expected_max.toLocaleString()}]</span>
                        </div>
                        {d.is_deviated && (
                          <div className="text-attack font-semibold pt-1">
                            ⚠ Deviation: Outside baseline nominal range
                          </div>
                        )}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Legend
                verticalAlign="top"
                align="right"
                wrapperStyle={{ paddingBottom: '12px', fontSize: '12px' }}
              />

              {/* Shaded Expected Baseline Range */}
              <Area
                type="monotone"
                dataKey="expected_max"
                stroke="transparent"
                fill="url(#expectedBand)"
                name="Expected Nominal Range"
              />
              <Area
                type="monotone"
                dataKey="expected_min"
                stroke="transparent"
                fill="#FFFFFF"
                name="Expected Lower Bound"
              />

              {/* Baseline Median Reference Line */}
              <Line
                type="monotone"
                dataKey="expected_median"
                stroke="#64748B"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                dot={false}
                name="Baseline Median"
              />

              {/* Observed Telemetry Line */}
              <Line
                type="monotone"
                dataKey="observed_packets"
                stroke="#3478F6"
                strokeWidth={2.5}
                name="Observed Packets"
                dot={(props) => {
                  const { cx, cy, payload } = props;
                  if (payload.is_current) {
                    return (
                      <circle
                        key={`curr-${payload.window_id}`}
                        cx={cx}
                        cy={cy}
                        r={6}
                        fill="#EF4444"
                        stroke="#FFFFFF"
                        strokeWidth={2}
                      />
                    );
                  }
                  if (payload.is_deviated) {
                    return (
                      <circle
                        key={`dev-${payload.window_id}`}
                        cx={cx}
                        cy={cy}
                        r={4}
                        fill="#F59E0B"
                        stroke="#FFFFFF"
                        strokeWidth={1.5}
                      />
                    );
                  }
                  return (
                    <circle
                      key={`pt-${payload.window_id}`}
                      cx={cx}
                      cy={cy}
                      r={3}
                      fill="#3478F6"
                    />
                  );
                }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>

      {/* 3. Evidence Panel & 4. Prominent Decision Trace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* 4. Decision Trace: Most Prominent Element (7 cols) */}
        <div className="lg:col-span-7 bg-card rounded-xl border border-border p-6 shadow-sm">
          <div className="flex items-center justify-between pb-4 border-b border-border/60">
            <div>
              <h3 className="text-base font-bold text-text flex items-center gap-2">
                <FileText className="w-4 h-4 text-blue" />
                Audit Decision Trace
              </h3>
              <p className="text-xs text-muted mt-0.5">
                Deterministic execution steps and verification checks enforced for this window
              </p>
            </div>
            <StatusBadge label={`${timeline_steps.length} Steps Logged`} variant="blue" size="sm" />
          </div>

          {/* Vertical Timeline */}
          <div className="mt-6 relative pl-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-border">
            <div className="space-y-6">
              {timeline_steps.map((step) => {
                const isFail = step.outcome === 'fail';
                const isWarn = step.outcome === 'warn';
                const iconColor = isFail ? 'text-attack bg-attack/10 border-attack/30' : isWarn ? 'text-suspicious bg-suspicious/10 border-suspicious/30' : 'text-approved bg-approved/10 border-approved/30';

                return (
                  <div key={step.step_number} className="relative flex items-start gap-4">
                    {/* Step Icon / Circle on timeline */}
                    <div
                      className={`absolute -left-6 mt-0.5 w-5 h-5 rounded-full border flex items-center justify-center font-mono text-[10px] font-bold ${iconColor}`}
                    >
                      {step.step_number}
                    </div>

                    <div className="flex-1 bg-bg/80 border border-border/80 rounded-lg p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-bold text-text">{step.title}</h4>
                          <span
                            className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                              isFail ? 'bg-attack/15 text-attack' : isWarn ? 'bg-suspicious/15 text-suspicious' : 'bg-approved/15 text-approved'
                            }`}
                          >
                            {step.outcome}
                          </span>
                        </div>
                        <span className="font-mono text-xs text-muted">{step.timestamp}</span>
                      </div>
                      <p className="text-xs text-slate mt-2 leading-relaxed">
                        {step.explanation}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* 3. Evidence Panel (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-card rounded-xl border border-border p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-border/60">
              <h3 className="text-sm font-bold text-text flex items-center gap-2">
                <Cpu className="w-4 h-4 text-teal" />
                Detection Evidence
              </h3>
              <StatusBadge
                label={evidence.detector_scores.fusion.flagged ? 'Anomaly Flagged' : 'Nominal'}
                variant={evidence.detector_scores.fusion.flagged ? 'attack' : 'safe'}
                size="sm"
              />
            </div>

            {/* Detector Scores */}
            <div className="space-y-3">
              <div className="p-3 rounded-lg bg-bg border border-border/70 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-text">Isolation Forest Score</div>
                  <div className="text-xs text-muted">
                    Percentile: <strong className="font-mono text-text">{formatPctValue(evidence.detector_scores.isolation_forest.percentile)}</strong> (Thresh: {formatPctValue(evidence.detector_scores.isolation_forest.threshold)})
                  </div>
                </div>
                {evidence.detector_scores.isolation_forest.flagged ? (
                  <AlertOctagon className="w-4 h-4 text-attack shrink-0" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 text-safe shrink-0" />
                )}
              </div>

              <div className="p-3 rounded-lg bg-bg border border-border/70 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-text">Autoencoder Reconstruction</div>
                  <div className="text-xs text-muted">
                    Loss: <strong className="font-mono text-text">{evidence.detector_scores.autoencoder.reconstruction_mse}</strong> | Percentile: <strong className="font-mono text-text">{formatPctValue(evidence.detector_scores.autoencoder.percentile)}</strong>
                  </div>
                </div>
                {evidence.detector_scores.autoencoder.flagged ? (
                  <AlertOctagon className="w-4 h-4 text-attack shrink-0" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 text-safe shrink-0" />
                )}
              </div>

              <div className="p-3 rounded-lg bg-bg border border-border/70 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-text">CUSUM Shift Tracking</div>
                  <div className="text-xs text-muted">
                    Score: <strong className="font-mono text-text">{evidence.cusum.score}</strong> | Alarm Limit: <strong className="font-mono text-text">{evidence.cusum.threshold_h}</strong>
                  </div>
                </div>
                {evidence.cusum.is_alarm ? (
                  <AlertTriangle className="w-4 h-4 text-attack shrink-0" />
                ) : (
                  <CheckCircle2 className="w-4 h-4 text-safe shrink-0" />
                )}
              </div>

              <div className="p-3 rounded-lg bg-bg border border-border/70 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-text">Jensen-Shannon Divergence</div>
                  <div className="text-xs text-muted">
                    JSD: <strong className="font-mono text-text">{evidence.js_divergence.value.toFixed(4)}</strong> (Limit: {evidence.js_divergence.threshold})
                  </div>
                </div>
                {evidence.js_divergence.is_pass ? (
                  <CheckCircle2 className="w-4 h-4 text-safe shrink-0" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-quarantined shrink-0" />
                )}
              </div>

              <div className="p-3 rounded-lg bg-bg border border-border/70 flex items-center justify-between">
                <div>
                  <div className="text-xs font-semibold text-text">Volume Multiplier (k)</div>
                  <div className="text-xs text-muted">
                    Growth Ratio: <strong className="font-mono text-text">{evidence.volume_multiplier.multiplier}x</strong> baseline traffic
                  </div>
                </div>
                <StatusBadge
                  label={evidence.volume_multiplier.is_proportional ? 'Proportional' : 'Disproportionate'}
                  variant={evidence.volume_multiplier.is_proportional ? 'safe' : 'quarantined'}
                  size="sm"
                />
              </div>
            </div>
          </div>

          {/* Threat Indicators / Key Feature Deviations */}
          <div className="bg-card rounded-xl border border-border p-5 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-text flex items-center gap-2">
              <Zap className="w-4 h-4 text-attack" />
              Signaling Threat Indicators
            </h3>
            <div className="space-y-2">
              {evidence.threat_indicators.map((t) => (
                <div key={t.feature} className="p-2.5 rounded-lg bg-bg border border-border/60 flex items-center justify-between text-xs">
                  <div className="truncate pr-2">
                    <div className="font-mono font-semibold text-text truncate">{t.feature}</div>
                    <div className="text-[11px] text-muted">
                      Observed: {t.observed_value} | Baseline: {t.baseline_median}
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span
                      className={`font-mono font-bold text-xs ${
                        t.status === 'danger' ? 'text-attack' : t.status === 'warn' ? 'text-suspicious' : 'text-safe'
                      }`}
                    >
                      {t.iqr_deviation > 0 ? `+${t.iqr_deviation}` : t.iqr_deviation} IQR
                    </span>
                    {t.status === 'danger' ? (
                      <AlertOctagon className="w-3.5 h-3.5 text-attack" />
                    ) : t.status === 'warn' ? (
                      <AlertTriangle className="w-3.5 h-3.5 text-suspicious" />
                    ) : (
                      <CheckCircle2 className="w-3.5 h-3.5 text-safe" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 7. Analyst Actions & Verification Notes */}
      <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
        <div className="flex items-center justify-between pb-4 border-b border-border/60">
          <div>
            <h3 className="text-base font-bold text-text flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-blue" />
              Analyst Verification & Review
            </h3>
            <p className="text-xs text-muted mt-0.5">
              Record ground-truth disposition (True Positive / False Positive) and rationale to persistent audit log
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted">Operator:</span>
            <input
              type="text"
              value={analystId}
              onChange={(e) => setAnalystId(e.target.value)}
              className="bg-bg border border-border px-2.5 py-1 rounded text-xs font-mono text-text focus:outline-none focus:ring-1 focus:ring-blue"
              placeholder="Analyst ID"
            />
          </div>
        </div>

        {feedbackSuccessMsg && (
          <div className="mt-4 p-3 rounded-lg bg-safe/10 border border-safe/20 text-xs font-medium text-safe flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{feedbackSuccessMsg}</span>
          </div>
        )}

        <form onSubmit={handleFeedbackSubmit} className="mt-5 space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-xs font-bold uppercase tracking-wider text-muted">Disposition:</label>
            <button
              type="button"
              onClick={() => setClassification('TRUE_POSITIVE')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 border transition-all ${
                classification === 'TRUE_POSITIVE'
                  ? 'bg-attack text-white border-attack shadow-sm'
                  : 'bg-bg text-slate border-border hover:bg-slate/5'
              }`}
            >
              <ThumbsUp className="w-3.5 h-3.5" />
              Mark True Positive (Malicious / Anomaly)
            </button>

            <button
              type="button"
              onClick={() => setClassification('FALSE_POSITIVE')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 border transition-all ${
                classification === 'FALSE_POSITIVE'
                  ? 'bg-teal text-white border-teal shadow-sm'
                  : 'bg-bg text-slate border-border hover:bg-slate/5'
              }`}
            >
              <ThumbsDown className="w-3.5 h-3.5" />
              Mark False Positive (Benign Traffic)
            </button>

            <button
              type="button"
              onClick={() => setClassification('NOTE')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 border transition-all ${
                classification === 'NOTE'
                  ? 'bg-blue text-white border-blue shadow-sm'
                  : 'bg-bg text-slate border-border hover:bg-slate/5'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              General Analyst Note
            </button>
          </div>

          <div>
            <textarea
              value={analystNotes}
              onChange={(e) => setAnalystNotes(e.target.value)}
              placeholder="Enter forensic notes, correlation with external 5G RAN alarms, or benign campaign rationale..."
              rows={3}
              className="w-full bg-bg border border-border text-xs text-text rounded-lg p-3 focus:outline-none focus:ring-1 focus:ring-blue resize-none"
              required
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="text-[11px] text-muted">
              Verification action will be stored in <code className="font-mono bg-bg px-1 py-0.5 rounded border border-border">approval_logs</code> and <code className="font-mono bg-bg px-1 py-0.5 rounded border border-border">audit_events</code>.
            </div>

            <button
              type="submit"
              disabled={submittingFeedback || !analystNotes.trim()}
              className="px-4 py-2 text-xs font-semibold text-white bg-blue hover:bg-blue-hover disabled:opacity-50 rounded-lg shadow-sm transition-colors inline-flex items-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{submittingFeedback ? 'Recording...' : 'Submit Verification Action'}</span>
            </button>
          </div>
        </form>

        {/* Existing feedback history */}
        {feedback_history && feedback_history.length > 0 && (
          <div className="mt-6 pt-5 border-t border-border/60">
            <h4 className="text-xs font-bold uppercase tracking-wider text-muted mb-3">Audit Verification Log</h4>
            <div className="space-y-2.5">
              {feedback_history.map((fb) => (
                <div key={fb.id} className="p-3 rounded-lg bg-bg border border-border/70 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-xs">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-text">{fb.analyst_id}</span>
                      <span
                        className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded ${
                          fb.classification === 'TRUE_POSITIVE'
                            ? 'bg-attack/15 text-attack'
                            : fb.classification === 'FALSE_POSITIVE'
                            ? 'bg-teal/15 text-teal'
                            : 'bg-slate/15 text-slate'
                        }`}
                      >
                        {fb.classification}
                      </span>
                      <span className="font-mono text-muted text-[11px]">{fb.timestamp}</span>
                    </div>
                    <p className="text-slate mt-1">{fb.notes}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default InvestigationView;
