import React from 'react';
import { Sliders } from 'lucide-react';
import { EmptyState } from '../components';

export const ExperimentsView: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text">Experiment Comparison</h1>
        <p className="text-sm text-muted mt-0.5">
          Live head-to-head benchmarking across Arm A (Static Anchor), Arm B (Naive Retraining), and Arm C (CommShield).
        </p>
      </div>

      <EmptyState
        icon={<Sliders className="w-8 h-8 text-blue" />}
        title="Three-Arm Experiment Comparison"
        badge="Coming Soon"
        badgeVariant="blue"
        description="Parallel stream replay evaluation across all three architectural arms, tracking evasion rates, false alarms, and poisoning resistance in Milestone M6."
      />
    </div>
  );
};
