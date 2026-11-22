import React from 'react';

interface LoadingStateProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const spinnerSizes = {
  sm: 'h-5 w-5 border-2',
  md: 'h-8 w-8 border-2',
  lg: 'h-12 w-12 border-3',
};

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading data...',
  size = 'md',
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 bg-card/60 rounded-xl border border-border/60 ${className}`}
    >
      <div
        className={`animate-spin rounded-full border-border border-t-blue ${spinnerSizes[size]}`}
      />
      {message && <p className="mt-3 text-sm font-medium text-muted">{message}</p>}
    </div>
  );
};
// CommShield AI Core
