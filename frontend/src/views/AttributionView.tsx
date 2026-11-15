import React from 'react';
import { GitBranch } from 'lucide-react';
import { EmptyState } from '../components';

export const AttributionView: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text">Drift Attribution</h1>
        <p className="text-sm text-muted mt-0.5">
          ADWIN concept drift tracking, proportional-growth JSD divergence testing, and machine-readable abstention reasons.
        </p>
      </div>

      <EmptyState
        icon={<GitBranch className="w-8 h-8 text-blue" />}
        title="Drift Attribution Engine"
        badge="Coming Soon"
        badgeVariant="blue"
        description="ADWIN trigger logic, proportional growth test with Jensen-Shannon Divergence, and 5 named abstention reasons are scheduled for Milestone M4."
      />
    </div>
  );
};
