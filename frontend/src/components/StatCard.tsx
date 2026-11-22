import React from 'react';
import { StatusBadge, StatusVariant } from './StatusBadge';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: string;
  trend?: 'up' | 'down' | 'neutral';
  subtitle?: string;
  icon?: React.ReactNode;
  badge?: string;
  badgeVariant?: StatusVariant;
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  change,
  trend,
  subtitle,
  icon,
  badge,
  badgeVariant = 'neutral',
  className = '',
}) => {
  return (
    <div
      className={`bg-card rounded-xl border border-border p-5 shadow-sm hover:shadow-md transition-shadow duration-200 ${className}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold tracking-wider uppercase text-muted truncate">
          {title}
        </span>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {badge && <StatusBadge label={badge} variant={badgeVariant} size="sm" />}
          {icon && (
            <div className="w-8 h-8 rounded-lg bg-bg flex items-center justify-center text-slate">
              {icon}
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl font-bold tracking-tight text-text">
          {value !== undefined && value !== null && value !== '' ? value : 'no data'}
        </span>
        {change && (
          <span
            className={`inline-flex items-center text-xs font-medium ${
              trend === 'up'
                ? 'text-safe'
                : trend === 'down'
                ? 'text-attack'
                : 'text-muted'
            }`}
          >
            {trend === 'up' && <TrendingUp className="w-3.5 h-3.5 mr-0.5" />}
            {trend === 'down' && <TrendingDown className="w-3.5 h-3.5 mr-0.5" />}
            {trend === 'neutral' && <Minus className="w-3.5 h-3.5 mr-0.5" />}
            {change}
          </span>
        )}
      </div>

      {subtitle && (
        <p className="mt-1 text-xs text-muted leading-relaxed line-clamp-1">
          {subtitle}
        </p>
      )}
    </div>
  );
};
