import React from 'react';
import { ShieldCheck } from 'lucide-react';
import { EmptyState } from '../components';

export const GovernanceView: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text">Baseline Governance</h1>
        <p className="text-sm text-muted mt-0.5">
          Shadow candidate evaluation, canary retention testing, cumulative drift budgets, and atomic rollback registry.
        </p>
      </div>

      <EmptyState
        icon={<ShieldCheck className="w-8 h-8 text-approved" />}
        title="Baseline Governance & Adaptation Gate"
        badge="Coming Soon"
        badgeVariant="approved"
        description="Candidate shadow baseline generation, canary retention tests, drift budgets (D_rms, D_max, Delta_can), and one-click atomic rollback are scheduled for Milestone M5."
      />
    </div>
  );
};
