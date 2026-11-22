import React from 'react';

export type StatusVariant =
  | 'safe'
  | 'suspicious'
  | 'attack'
  | 'quarantined'
  | 'approved'
  | 'blue'
  | 'slate'
  | 'neutral';

interface StatusBadgeProps {
  label: string;
  variant?: StatusVariant;
  size?: 'sm' | 'md' | 'lg';
  icon?: React.ReactNode;
  className?: string;
  dot?: boolean;
}

const variantStyles: Record<StatusVariant, { bg: string; text: string; border: string; dot: string }> = {
  safe: {
    bg: 'bg-safe/10',
    text: 'text-safe',
    border: 'border-safe/30',
    dot: 'bg-safe',
  },
  suspicious: {
    bg: 'bg-suspicious/10',
    text: 'text-suspicious',
    border: 'border-suspicious/30',
    dot: 'bg-suspicious',
  },
  attack: {
    bg: 'bg-attack/10',
    text: 'text-attack',
    border: 'border-attack/30',
    dot: 'bg-attack',
  },
  quarantined: {
    bg: 'bg-quarantined/10',
    text: 'text-quarantined',
    border: 'border-quarantined/30',
    dot: 'bg-quarantined',
  },
  approved: {
    bg: 'bg-approved/10',
    text: 'text-approved',
    border: 'border-approved/30',
    dot: 'bg-approved',
  },
  blue: {
    bg: 'bg-blue/10',
    text: 'text-blue',
    border: 'border-blue/30',
    dot: 'bg-blue',
  },
  slate: {
    bg: 'bg-slate/10',
    text: 'text-slate',
    border: 'border-slate/30',
    dot: 'bg-slate',
  },
  neutral: {
    bg: 'bg-muted/10',
    text: 'text-muted',
    border: 'border-muted/30',
    dot: 'bg-muted',
  },
};

const sizeStyles = {
  sm: 'text-xs px-2 py-0.5 gap-1',
  md: 'text-xs px-2.5 py-1 gap-1.5',
  lg: 'text-sm px-3 py-1.5 gap-2',
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  label,
  variant = 'neutral',
  size = 'md',
  icon,
  className = '',
  dot = false,
}) => {
  const styles = variantStyles[variant] || variantStyles.neutral;
  const sizeCls = sizeStyles[size];

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border ${styles.bg} ${styles.text} ${styles.border} ${sizeCls} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${styles.dot}`} />}
      {icon && <span className="flex-shrink-0">{icon}</span>}
      <span>{label}</span>
    </span>
  );
};
// CommShield AI Core
