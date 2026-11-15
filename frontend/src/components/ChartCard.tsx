import React from 'react';

interface ChartCardProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export const ChartCard: React.FC<ChartCardProps> = ({
  title,
  subtitle,
  action,
  children,
  className = '',
}) => {
  return (
    <div
      className={`bg-card rounded-xl border border-border p-5 shadow-sm flex flex-col ${className}`}
    >
      <div className="flex items-center justify-between pb-4 border-b border-border/60">
        <div>
          <h3 className="text-base font-semibold text-text">{title}</h3>
          {subtitle && <p className="text-xs text-muted mt-0.5">{subtitle}</p>}
        </div>
        {action && <div className="flex-shrink-0">{action}</div>}
      </div>
      <div className="pt-4 flex-1 min-h-[220px]">{children}</div>
    </div>
  );
};
