import React from 'react';
import { Database, Tag } from 'lucide-react';
import { useReplay } from '../context/ReplayContext';

export interface DataSourceBadgeProps {
  className?: string;
  sourceOverride?: 'synthetic' | '5g_nidd' | 'open5gs_lab' | string;
  forceSemiSynthetic?: boolean;
}

export const DataSourceBadge: React.FC<DataSourceBadgeProps> = ({
  className = '',
  sourceOverride,
  forceSemiSynthetic = false,
}) => {
  const { selectedDataSource, selectedScenario } = useReplay();
  const activeSource = sourceOverride || selectedDataSource;

  const isReal5GNIDD =
    activeSource === '5g_nidd' ||
    activeSource === 'real' ||
    activeSource === 'real_recorded' ||
    activeSource === '5G-NIDD';
  const isAssignedSlices = isReal5GNIDD;
  const isSemiSynthetic =
    forceSemiSynthetic ||
    (activeSource === '5g_nidd' &&
      (selectedScenario === 'legitimate_growth' ||
        selectedScenario === 'attack_in_growth' ||
        selectedScenario.includes('growth') ||
        selectedScenario.includes('scaled')));

  let badgeLabel = 'Simulated Twin';
  if (isReal5GNIDD) {
    badgeLabel = '5G-NIDD (Real)';
  } else if (activeSource === 'open5gs_lab') {
    badgeLabel = 'Open5GS Lab';
  }

  return (
    <div className={`inline-flex items-center gap-2 flex-wrap ${className}`}>
      {/* Active Source Name Badge */}
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-navy text-white border border-slate/40 shadow-xs">
        <Database className="w-3.5 h-3.5 text-teal" />
        <span>{badgeLabel}</span>
      </span>

      {/* Assigned Slices Badge */}
      {isAssignedSlices && (
        <span
          title="Slices mapped from testbed base stations (BS1: eMBB, BS2: URLLC) rather than 3GPP S-NSSAI protocol headers"
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/30"
        >
          <Tag className="w-3 h-3" />
          <span>slices assigned</span>
        </span>
      )}

      {/* Semi-Synthetic Badge */}
      {isSemiSynthetic && (
        <span
          title="Real baseline flow distributions scaled with synthetic proportional multiplier"
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/30"
        >
          <Tag className="w-3 h-3" />
          <span>semi-synthetic</span>
        </span>
      )}
    </div>
  );
};
// CommShield AI Core
