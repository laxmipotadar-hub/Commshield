import React from 'react';
import { StatusBadge, StatusVariant } from './StatusBadge';
import { Sparkles } from 'lucide-react';

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  badge?: string;
  badgeVariant?: StatusVariant;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  badge,
  badgeVariant = 'blue',
  className = '',
}) => {
  return (
    <div
      className={`bg-card rounded-xl border border-dashed border-border p-12 text-center flex flex-col items-center justify-center max-w-xl mx-auto my-8 shadow-sm ${className}`}
    >
      <div className="w-14 h-14 rounded-2xl bg-bg flex items-center justify-center text-slate mb-4 shadow-inner">
        {icon || <Sparkles className="w-7 h-7 text-blue" />}
      </div>

      {badge && (
        <div className="mb-2">
          <StatusBadge label={badge} variant={badgeVariant} size="sm" />
        </div>
      )}

      <h3 className="text-lg font-bold text-text">{title}</h3>
      {description && (
        <p className="mt-2 text-sm text-muted max-w-md leading-relaxed">
          {description}
        </p>
      )}

      {action && <div className="mt-6">{action}</div>}
    </div>
  );
};
// CommShield AI Core
