/**
 * dataPresentation.ts
 * Rigorous statistical and data presentation helpers for CommShield UI.
 * Conforms to DP2 & DP4 requirements:
 * 1. Missing or unavailable values render as "no data", never 0.
 * 2. Proportions show n and Wilson score confidence intervals.
 * 3. Counts < 10 show "n=<count>, interval too wide".
 * 4. Saturated percentiles show raw-to-threshold ratio on a log scale.
 * 5. Genuine 0 or 100% display n, CI, and explicit justification.
 */

export interface WilsonIntervalResult {
  p: number;
  lower: number;
  upper: number;
  n: number;
  label: string;
  isWide: boolean;
}

/**
 * Calculates Wilson Score 95% Confidence Interval for a binomial proportion k / n.
 */
export function calculateWilsonInterval(k: number, n: number, z = 1.95996): WilsonIntervalResult {
  if (n <= 0) {
    return { p: 0, lower: 0, upper: 0, n: 0, label: 'no data', isWide: true };
  }

  const p = k / n;
  if (n < 10) {
    return {
      p,
      lower: 0,
      upper: 1,
      n,
      label: `n=${n}, interval too wide`,
      isWide: true,
    };
  }

  const z2 = z * z;
  const denominator = 1 + z2 / n;
  const centerAdjusted = p + z2 / (2 * n);
  const radical = Math.sqrt((p * (1 - p) + z2 / (4 * n)) / n);

  const lower = Math.max(0, (centerAdjusted - z * radical) / denominator);
  const upper = Math.min(1, (centerAdjusted + z * radical) / denominator);

  const pctP = (p * 100).toFixed(1);
  const pctLow = (lower * 100).toFixed(1);
  const pctHigh = (upper * 100).toFixed(1);

  return {
    p,
    lower,
    upper,
    n,
    label: `${pctP}% [${pctLow}%, ${pctHigh}%] (n=${n})`,
    isWide: false,
  };
}

/**
 * Formats a value safely. If null/undefined, returns "no data", never 0.
 */
export function formatValue(
  val: number | null | undefined,
  fallback = 'no data',
  precision = 2
): string {
  if (val === null || val === undefined || Number.isNaN(val)) {
    return fallback;
  }
  return Number(val).toFixed(precision);
}

/**
 * Formats saturated percentiles (e.g. 100% or >=99%).
 * Displays raw score ratio to threshold on log-scale so differences above 99% remain visible.
 */
export function formatPercentileWithLogRatio(
  percentile: number | null | undefined,
  rawScore?: number | null,
  threshold?: number | null
): string {
  if (percentile === null || percentile === undefined) {
    return 'no data';
  }

  const pct = percentile > 1.0 ? percentile : percentile * 100;
  if (pct < 99.0) {
    return `${pct.toFixed(1)}%`;
  }

  if (rawScore !== undefined && rawScore !== null && threshold && threshold > 0) {
    const ratio = rawScore / threshold;
    const logRatio = Math.log10(Math.max(1e-4, ratio));
    const sign = logRatio >= 0 ? '+' : '';
    return `${pct >= 99.9 ? '99.9%+' : pct.toFixed(1) + '%'} (log-ratio ${sign}${logRatio.toFixed(2)} [${ratio.toFixed(2)}× thr])`;
  }

  return pct >= 100 ? '100% (saturated cap)' : `${pct.toFixed(1)}%`;
}

/**
 * Formats genuine boundary numbers (0.0 or 100.0) with required sample size and rationale.
 */
export function formatBoundaryMetric(
  val: number | null | undefined,
  n: number,
  options?: {
    isProportion?: boolean;
    reasonIfZero?: string;
    reasonIfHundred?: string;
  }
): { text: string; subtext?: string } {
  if (val === null || val === undefined) {
    return { text: 'no data' };
  }

  const isZero = Math.abs(val) < 1e-6;
  const isHundred = Math.abs(val - (options?.isProportion ? 1.0 : 100.0)) < 1e-6;

  if (options?.isProportion) {
    const k = Math.round(val * n);
    const wilson = calculateWilsonInterval(k, n);
    let subtext = wilson.label;
    if (isZero && options?.reasonIfZero) {
      subtext = `${options.reasonIfZero} • ${wilson.label}`;
    } else if (isHundred && options?.reasonIfHundred) {
      subtext = `${options.reasonIfHundred} • ${wilson.label}`;
    }
    return {
      text: `${(val * 100).toFixed(1)}%`,
      subtext,
    };
  }

  return {
    text: val.toString(),
    subtext: n < 10 ? `n=${n}, interval too wide` : `n=${n}`,
  };
}
