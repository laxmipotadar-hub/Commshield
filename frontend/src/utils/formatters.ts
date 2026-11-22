/**
 * CommShield UI Formatters.
 * Provides consistent, statistically and dimensionally correct formatting
 * for network volumes, percentages, and timestamps.
 */

export function formatBytes(bytes: number | undefined | null, decimals: number = 2): string {
  if (bytes === undefined || bytes === null || isNaN(bytes) || bytes <= 0) {
    return '0 B';
  }
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const safeIdx = Math.max(0, Math.min(i, sizes.length - 1));
  const val = bytes / Math.pow(k, safeIdx);
  return `${val.toFixed(safeIdx === 0 ? 0 : decimals)} ${sizes[safeIdx]}`;
}

export function formatPercent(val: number | undefined | null, decimals: number = 1): string {
  if (val === undefined || val === null || isNaN(val)) return '0.0%';
  const pct = val > 1.0 ? val : val * 100;
  return `${pct.toFixed(decimals)}%`;
}

export function formatDateTime(dtStr: string | undefined | null): string {
  if (!dtStr) return '—';
  try {
    const d = new Date(dtStr);
    if (isNaN(d.getTime())) return String(dtStr);
    return d.toISOString().replace('T', ' ').slice(0, 19);
  } catch {
    return String(dtStr);
  }
}
// CommShield AI Core
