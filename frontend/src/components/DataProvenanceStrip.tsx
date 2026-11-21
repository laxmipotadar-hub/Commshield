import React, { useEffect, useState } from 'react';
import { Info, Layers, ShieldCheck, Activity } from 'lucide-react';
import { useReplay } from '../context/ReplayContext';
import { DataSourceBadge } from './DataSourceBadge';
import { api, DatasetInfo, DatasetListResponse } from '../services/api';

export const DataProvenanceStrip: React.FC = () => {
  const { selectedDataSource, selectedScenario, totalWindows, currentIndex } = useReplay();
  const [datasetList, setDatasetList] = useState<DatasetInfo[]>([]);

  useEffect(() => {
    api.getDatasets()
      .then((res: DatasetListResponse) => {
        if (res && res.datasets) {
          setDatasetList(res.datasets);
        }
      })
      .catch(() => {
        // Fallback gracefully if API unavailable
      });
  }, []);

  const activeInfo = datasetList.find((d) => d.dataset_id === selectedScenario) || {
    name: selectedDataSource === '5g_nidd' ? '5G-NIDD Real Telemetry' : 'Synthetic 5G Core Stream',
    total_windows: totalWindows,
    data_source: selectedDataSource,
  };

  const isReal = selectedDataSource === '5g_nidd';

  return (
    <div className="mb-4 rounded-lg bg-surface border border-border p-3 shadow-xs">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Left: What the data is */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-muted">
            <Info className="w-3.5 h-3.5 text-teal" />
            <span>What the data is:</span>
          </div>

          <span className="text-xs font-medium text-text bg-navy/60 px-2 py-0.5 rounded border border-slate/30">
            {activeInfo.name}
          </span>

          <DataSourceBadge />
        </div>

        {/* Right: Window counts & Split stats */}
        <div className="flex items-center gap-3 text-xs text-muted flex-wrap">
          <div className="flex items-center gap-1">
            <Layers className="w-3.5 h-3.5 text-slate" />
            <span>Windows:</span>
            <span className="font-semibold text-text">
              {currentIndex} / {activeInfo.total_windows || totalWindows}
            </span>
          </div>

          <div className="h-3 w-px bg-border" />

          <div className="flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-safe" />
            <span>Split:</span>
            <span className="font-semibold text-text">
              {isReal ? 'Test Period (Assigned Slices)' : 'Controlled Benchmark'}
            </span>
          </div>

          <div className="h-3 w-px bg-border" />

          <div className="flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-accent" />
            <span>Inference:</span>
            <span className="font-semibold text-text">Dynamic at request-time</span>
          </div>
        </div>
      </div>
    </div>
  );
};
