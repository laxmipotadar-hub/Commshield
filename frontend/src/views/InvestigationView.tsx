import React from 'react';
import { Search } from 'lucide-react';
import { EmptyState } from '../components';

export const InvestigationView: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-text">Investigation</h1>
        <p className="text-sm text-muted mt-0.5">
          Explainability drill-downs, KernelSHAP feature contributions, hypothesis synthesis, and operator decision traces.
        </p>
      </div>

      <EmptyState
        icon={<Search className="w-8 h-8 text-quarantined" />}
        title="Deep Investigation & SHAP Explainability"
        badge="Coming Soon"
        badgeVariant="quarantined"
        description="Single-window SHAP attribution waterfalls, root cause hypotheses, and audit trail investigation tools are scheduled for Milestone M6."
      />
    </div>
  );
};
