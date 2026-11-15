import React from 'react';

interface SampleDataBadgeProps {
  isPlaceholder?: boolean;
  className?: string;
}

export const SampleDataBadge: React.FC<SampleDataBadgeProps> = ({
  isPlaceholder = false,
  className = '',
}) => {
  if (!isPlaceholder) return null;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-slate/10 text-slate border border-slate/20 tracking-wide uppercase ${className}`}
      title="Data provided by backend placeholder / sample dataset"
    >
      <span className="w-1.5 h-1.5 rounded-full bg-slate/60" />
      Sample data
    </span>
  );
};
