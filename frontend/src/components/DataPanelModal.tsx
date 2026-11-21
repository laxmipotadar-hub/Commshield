import React, { useEffect, useState } from 'react';
import {
  Check,
  ChevronDown,
  ChevronRight,
  Copy,
  Database,
  Download,
  Play,
  RefreshCw,
  Tag,
  X,
} from 'lucide-react';
import {
  DataDatasetItem,
  fetchDataDatasets,
  fetchDataPreview,
  generateDataStream,
  getDownloadUrl,
} from '../services/api';

interface DataPanelModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DataPanelModal: React.FC<DataPanelModalProps> = ({ isOpen, onClose }) => {
  const [datasets, setDatasets] = useState<DataDatasetItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<DataDatasetItem | null>(null);
  const [previewData, setPreviewData] = useState<any>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [jsonExpanded, setJsonExpanded] = useState(true);
  const [copied, setCopied] = useState(false);
  const [seedInput, setSeedInput] = useState<number>(42);
  const [generating, setGenerating] = useState(false);
  const [genStatus, setGenStatus] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadDatasets();
    }
  }, [isOpen]);

  const loadDatasets = async () => {
    setLoading(true);
    try {
      const res = await fetchDataDatasets();
      setDatasets(res.datasets);
      if (res.datasets.length > 0 && !selectedDataset) {
        handleSelectDataset(res.datasets[0]);
      }
    } catch (err) {
      console.error('Failed to load datasets', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDataset = async (ds: DataDatasetItem) => {
    setSelectedDataset(ds);
    setSeedInput(ds.seed || 42);
    setGenStatus(null);
    setPreviewLoading(true);
    try {
      const prev = await fetchDataPreview(ds.name, 20);
      setPreviewData(prev);
    } catch (err) {
      console.error('Failed to load preview', err);
      // Fallback preview
      setPreviewData({
        name: ds.name,
        source: ds.source,
        seed: ds.seed,
        metadata: ds.metadata,
        windows: [{ note: 'Preview temporarily unavailable from backend; use download for complete stream.' }],
      });
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleCopyJson = () => {
    if (!previewData) return;
    navigator.clipboard.writeText(JSON.stringify(previewData, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleGenerate = async () => {
    if (!selectedDataset) return;
    setGenerating(true);
    setGenStatus(null);
    try {
      const res = await generateDataStream(selectedDataset.name, Number(seedInput));
      setGenStatus(`Generated ${res.record_count} windows deterministically in-memory.`);
      setPreviewData({
        name: res.stream,
        source: res.source,
        seed: res.seed,
        config_version: res.config_version,
        metadata: res.metadata,
        windows: res.preview,
      });
    } catch (err: any) {
      setGenStatus(`Generation error: ${err.message || 'Validation failed'}`);
    } finally {
      setGenerating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-hidden">
      <div className="bg-card border border-border rounded-xl shadow-2xl max-w-5xl w-full h-[85vh] flex flex-col text-text overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-slate/10 flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue/10 text-blue border border-blue/20">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-wide">
                Telemetry Data Exports & Live Dataset Catalog
              </h2>
              <p className="text-xs text-muted">
                Sanitized canonical windows with verified zero identifier leakage and Wilson confidence metadata.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-muted hover:text-text p-1.5 rounded-lg hover:bg-slate/20 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body: Two Columns */}
        <div className="flex-1 flex min-h-0 overflow-hidden">
          {/* Left: Datasets List */}
          <div className="w-1/2 border-r border-border p-4 overflow-y-auto space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <span className="text-xs font-bold uppercase text-muted tracking-wider">
                Available Datasets ({datasets.length})
              </span>
              <button
                onClick={loadDatasets}
                disabled={loading}
                className="text-xs text-blue hover:underline flex items-center gap-1"
              >
                <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} /> Refresh
              </button>
            </div>

            {loading ? (
              <div className="text-center py-10 text-sm text-muted">Loading datasets...</div>
            ) : (
              <div className="space-y-2">
                {datasets.map((ds) => {
                  const isSelected = selectedDataset?.name === ds.name;
                  return (
                    <div
                      key={ds.name}
                      onClick={() => handleSelectDataset(ds)}
                      className={`p-3 rounded-lg border text-left cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-blue/10 border-blue/50 text-white shadow-xs'
                          : 'bg-bg/40 border-border/80 hover:bg-bg/80 text-text'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="font-semibold text-xs">{ds.display_name}</span>
                        {/* Source Tag Badge */}
                        <span
                          className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${
                            ds.source === 'real_recorded'
                              ? 'bg-blue/20 text-blue border-blue/40'
                              : ds.source === 'semi_synthetic'
                              ? 'bg-purple-500/20 text-purple-400 border-purple-500/40'
                              : ds.source === 'lab'
                              ? 'bg-amber-500/20 text-amber-400 border-amber-500/40'
                              : 'bg-teal/20 text-teal border-teal/40'
                          }`}
                        >
                          {ds.source === 'real_recorded'
                            ? 'Real Recorded'
                            : ds.source === 'semi_synthetic'
                            ? 'Semi-Synthetic'
                            : ds.source === 'lab'
                            ? 'Live Lab'
                            : 'Simulated Twin'}
                        </span>
                      </div>

                      <p className="text-[11px] text-muted line-clamp-2 mb-2">{ds.description}</p>

                      <div className="flex items-center gap-3 text-[10px] text-muted">
                        <span>Records: {ds.record_count}</span>
                        <span>Seed: {ds.seed}</span>
                        {ds.slices_assigned && (
                          <span className="text-amber-400 flex items-center gap-0.5">
                            <Tag className="w-2.5 h-2.5" /> Slices Assigned
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Right: Selected Dataset Details, Controls & Preview */}
          <div className="w-1/2 p-4 flex flex-col min-h-0 bg-bg/20">
            {selectedDataset ? (
              <>
                {/* Action Strip: Download & Deterministic Generate */}
                <div className="p-3 bg-card border border-border rounded-lg mb-3 flex-shrink-0 space-y-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <h3 className="text-xs font-bold text-white">{selectedDataset.display_name}</h3>
                      <span className="text-[10px] text-muted">
                        Config: {selectedDataset.config_version} | Seed: {seedInput}
                      </span>
                    </div>

                    <a
                      href={getDownloadUrl(selectedDataset.name, seedInput)}
                      download
                      className="px-3 py-1.5 bg-blue hover:bg-blue/80 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-sm transition-colors cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5" /> Download JSON
                    </a>
                  </div>

                  {/* Generate with Seed Control */}
                  <div className="flex items-center gap-2 pt-2 border-t border-border">
                    <span className="text-[11px] text-muted font-medium whitespace-nowrap">Seed:</span>
                    <input
                      type="number"
                      min={0}
                      max={1000000}
                      value={seedInput}
                      onChange={(e) => setSeedInput(Number(e.target.value))}
                      className="w-24 bg-bg border border-border text-xs text-text rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue"
                    />
                    <button
                      onClick={handleGenerate}
                      disabled={generating}
                      className="px-2.5 py-1 bg-slate/40 hover:bg-slate/60 text-xs font-semibold rounded text-white flex items-center gap-1 transition-colors disabled:opacity-50"
                      title="Run deterministic generator with this seed"
                    >
                      <Play className="w-3 h-3 text-teal" /> Generate
                    </button>
                    {genStatus && (
                      <span className="text-[10px] text-teal truncate max-w-[200px]" title={genStatus}>
                        {genStatus}
                      </span>
                    )}
                  </div>
                </div>

                {/* Collapsible JSON Preview */}
                <div className="flex-1 flex flex-col min-h-0 border border-border rounded-lg bg-card overflow-hidden">
                  <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-slate/10 flex-shrink-0">
                    <button
                      onClick={() => setJsonExpanded(!jsonExpanded)}
                      className="flex items-center gap-1 text-xs font-bold text-white hover:text-blue transition-colors"
                    >
                      {jsonExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                      Canonical JSON Preview (Top 20 Windows)
                    </button>

                    <button
                      onClick={handleCopyJson}
                      className="text-xs text-muted hover:text-white flex items-center gap-1 transition-colors"
                      title="Copy JSON payload"
                    >
                      {copied ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-safe" />
                          <span className="text-safe">Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copy JSON</span>
                        </>
                      )}
                    </button>
                  </div>

                  {jsonExpanded && (
                    <div className="flex-1 p-3 overflow-auto font-mono text-[11px] leading-relaxed text-slate-300 bg-bg/80">
                      {previewLoading ? (
                        <div className="text-center py-10 text-muted">Loading preview...</div>
                      ) : previewData ? (
                        <pre className="whitespace-pre-wrap">{JSON.stringify(previewData, null, 2)}</pre>
                      ) : (
                        <div className="text-center py-10 text-muted">No preview available</div>
                      )}
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-muted text-xs">
                Select a dataset from the catalog to preview and export
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
