import React from 'react';
import { DataSourceBadge } from './DataSourceBadge';

export interface ChartCaptionProps {
  whatThisShows: string;
  howToReadIt: string;
}

export interface ChartCardProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  n?: number;
  sourceBadge?: string;
  caption?: ChartCaptionProps;
  missingReason?: string | null;
}

export const ChartCard: React.FC<ChartCardProps> = ({
  title,
  subtitle,
  action,
  children,
  className = '',
  n,
  sourceBadge,
  caption,
  missingReason,
}) => {
  return (
    <div
      className={`bg-card rounded-xl border border-border p-5 shadow-sm flex flex-col justify-between ${className}`}
    >
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-border/60">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-text">{title}</h3>
              {n !== undefined && (
                <span className="text-[11px] font-mono text-muted bg-border/40 px-2 py-0.5 rounded">
                  {n < 10 ? `n=${n}, interval too wide` : `n=${n}`}
                </span>
              )}
              {sourceBadge && <DataSourceBadge sourceOverride={sourceBadge} />}
            </div>
            {subtitle && <p className="text-xs text-muted mt-0.5">{subtitle}</p>}
          </div>
          {action && <div className="flex-shrink-0">{action}</div>}
        </div>

        {missingReason ? (
          <div className="py-12 flex flex-col items-center justify-center text-center px-4">
            <span className="text-sm font-medium text-muted">Chart hidden</span>
            <p className="text-xs text-muted/80 mt-1 max-w-md">{missingReason}</p>
          </div>
        ) : (
          <div className="pt-4 flex-1 min-h-[220px]">{children}</div>
        )}
      </div>

      {caption && !missingReason && (
        <div className="mt-4 pt-3 border-t border-border/40 bg-surface/30 rounded-lg p-2.5 text-xs text-muted space-y-1">
          <p>
            <strong className="text-text/90 font-medium">What this shows:</strong>{' '}
            {caption.whatThisShows}
          </p>
          <p>
            <strong className="text-text/90 font-medium">How to read it:</strong>{' '}
            {caption.howToReadIt}
          </p>
        </div>
      )}
    </div>
  );
};
