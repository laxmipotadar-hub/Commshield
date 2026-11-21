import React from 'react';
import {
  Routes,
  Route,
  NavLink,
  Navigate,
} from 'react-router-dom';
import {
  AlertOctagon,
  Check,
  Cpu,
  Database,
  GitBranch,
  Key,
  LayoutDashboard,
  Layers,
  Pause,
  Play,
  Radio,
  Search,
  Settings,
  Shield,
  ShieldCheck,
  Sliders,
  User,
  X,
} from 'lucide-react';
import { StatusBadge, DemoControlBar, DemoEventBanner, DataProvenanceStrip, DataPanelModal, BuiltVsPlannedModal } from './components';
import { getAnalystToken, setAnalystToken } from './services/api';
import { OverviewPage } from './pages/OverviewPage';
import { MonitoringPage } from './pages/MonitoringPage';
import { DetectionPage } from './pages/DetectionPage';
import { AttributionView } from './views/AttributionView';
import { GovernanceView } from './views/GovernanceView';
import { InvestigationView } from './views/InvestigationView';
import { ExperimentsView } from './views/ExperimentsView';
import { DigitalTwinView } from './views/DigitalTwinView';
import { ReplayProvider, SCENARIOS, ScenarioId, useReplay } from './context/ReplayContext';
import { DemoProvider } from './context/DemoContext';

interface NavItem {
  name: string;
  to: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { name: 'Overview', to: '/', icon: <LayoutDashboard className="w-4 h-4" /> },
  { name: 'Network Monitoring', to: '/monitoring', icon: <Radio className="w-4 h-4" /> },
  { name: 'Anomaly Detection', to: '/detection', icon: <AlertOctagon className="w-4 h-4" /> },
  { name: 'Drift Attribution', to: '/attribution', icon: <GitBranch className="w-4 h-4" /> },
  { name: 'Baseline Governance', to: '/governance', icon: <ShieldCheck className="w-4 h-4" /> },
  { name: 'Investigation', to: '/investigation', icon: <Search className="w-4 h-4" /> },
  { name: 'Experiment Comparison', to: '/experiments', icon: <Sliders className="w-4 h-4" /> },
  { name: 'Digital Twin', to: '/digital-twin', icon: <Cpu className="w-4 h-4" /> },
];

const AppLayout: React.FC = () => {
  const {
    selectedScenario,
    setSelectedScenario,
    selectedDataSource,
    setSelectedDataSource,
    open5gsAvailable,
    speed,
    setSpeed,
    status,
    currentIndex,
    totalWindows,
    activeBaselineVersion,
    selectedSlice,
    setSelectedSlice,
    handleStart,
    handlePause,
    handleResume,
  } = useReplay();

  const isRunning = status === 'RUNNING';
  const [showSettings, setShowSettings] = React.useState(false);
  const [showDataPanel, setShowDataPanel] = React.useState(false);
  const [showMatrixModal, setShowMatrixModal] = React.useState(false);
  const [tokenInput, setTokenInput] = React.useState('');
  const [tokenSaved, setTokenSaved] = React.useState(false);

  return (
    <div className="h-screen flex overflow-hidden bg-bg">
      {/* 1. Deep Navy Fixed Sidebar */}
      <aside className="w-64 h-full bg-navy text-white flex flex-col justify-between flex-shrink-0 z-30 shadow-xl">
        {/* Brand Header */}
        <div>
          <div className="h-16 flex items-center px-6 border-b border-slate/40 gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue/20 border border-blue/40 flex items-center justify-center text-blue shadow-sm">
              <Shield className="w-5 h-5 text-blue" />
            </div>
            <div>
              <span className="font-bold text-base tracking-wide text-white block">
                CommShield
              </span>
              <span className="text-[10px] tracking-wider uppercase text-teal font-semibold block">
                5G Zero-Trust Core
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1">
            <div className="px-3 py-2 text-[11px] font-semibold tracking-wider text-slate uppercase">
              Operations & Defense
            </div>
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all duration-150 ${
                    isActive
                      ? 'bg-blue text-white shadow-sm font-semibold'
                      : 'text-white/70 hover:bg-slate/50 hover:text-white'
                  }`
                }
              >
                {item.icon}
                <span>{item.name}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        {/* User / Settings pinned at bottom */}
        <div className="border-t border-slate/40 p-4 bg-navy/95">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-slate flex items-center justify-center text-white border border-slate/60">
                <User className="w-4 h-4" />
              </div>
              <div className="truncate">
                <span className="text-xs font-semibold text-white block truncate">
                  analyst_sec_09
                </span>
                <span className="text-[10px] text-teal block truncate font-medium">
                  5G SOC Operator
                </span>
              </div>
            </div>
            <button
              title="Operator Settings & Access Control"
              onClick={() => {
                setTokenInput(getAnalystToken());
                setTokenSaved(false);
                setShowSettings(true);
              }}
              className="p-1.5 rounded-lg text-white/60 hover:text-white hover:bg-slate/50 transition-colors"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* 2. Main Area with Top Bar */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Bar */}
        <header className="h-16 bg-card border-b border-border px-6 flex items-center justify-between flex-shrink-0 z-20 shadow-sm gap-4">
          {/* Left: Slice & Scenario Selectors */}
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-muted uppercase tracking-wider">
                Slice:
              </span>
              <select
                value={selectedSlice}
                onChange={(e) => setSelectedSlice(e.target.value)}
                className="bg-bg border border-border text-xs font-medium text-text rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue transition-colors cursor-pointer"
              >
                <option value="sst-1-sd-010203">sst-1-sd-010203 (eMBB)</option>
                <option value="sst-2-sd-010203">sst-2-sd-010203 (URLLC)</option>
                <option value="sst-3-sd-010203">sst-3-sd-010203 (mMTC)</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-muted uppercase tracking-wider">
                Scenario:
              </span>
              <select
                value={selectedScenario}
                onChange={(e) => setSelectedScenario(e.target.value as ScenarioId)}
                className="bg-bg border border-border text-xs font-medium text-text rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue transition-colors cursor-pointer"
              >
                {SCENARIOS.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Right: Replay Controls & Active Baseline Badge */}
          <div className="flex items-center gap-3 flex-wrap justify-end">
            {/* Demo Mode Presentation Controls */}
            <DemoControlBar />

            {/* Data Source Selector */}
            <div className="flex items-center gap-1.5 bg-bg px-2.5 py-1 rounded-lg border border-border">
              <Database className="w-3.5 h-3.5 text-teal" />
              <span className="text-xs font-semibold text-muted uppercase tracking-wider">
                Source:
              </span>
              <select
                value={selectedDataSource}
                onChange={(e) => setSelectedDataSource(e.target.value as any)}
                className="bg-transparent text-xs font-bold text-text focus:outline-none cursor-pointer"
                title="Active Telemetry Data Source"
              >
                <option value="5g_nidd">Real 5G-NIDD</option>
                <option value="synthetic">Synthetic</option>
                {open5gsAvailable && <option value="open5gs_lab">Open5GS lab</option>}
              </select>
            </div>

            {/* Replay Controls */}
            <div className="flex items-center gap-2 bg-bg px-2.5 py-1 rounded-lg border border-border">
              <button
                onClick={() => {
                  if (status === 'RUNNING') {
                    handlePause();
                  } else if (status === 'PAUSED') {
                    handleResume();
                  } else {
                    handleStart();
                  }
                }}
                className={`p-1 rounded-md transition-colors ${
                  isRunning
                    ? 'text-suspicious hover:bg-suspicious/10'
                    : 'text-safe hover:bg-safe/10'
                }`}
                title={isRunning ? 'Pause Replay' : 'Start / Resume Replay'}
              >
                {isRunning ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </button>
              <span className="text-[11px] font-semibold text-text uppercase min-w-[50px]">
                {isRunning
                  ? totalWindows > 0
                    ? `Playing (${currentIndex}/${totalWindows})`
                    : 'Playing'
                  : status === 'PAUSED'
                  ? 'Paused'
                  : status === 'COMPLETED'
                  ? 'Completed'
                  : 'Stopped'}
              </span>

              <div className="h-3.5 w-px bg-border mx-1" />

              <select
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
                className="bg-transparent text-xs font-semibold text-slate focus:outline-none cursor-pointer"
                title="Replay Speed Multiplier"
              >
                <option value={0.5}>0.5x</option>
                <option value={1.0}>1.0x</option>
                <option value={2.0}>2.0x</option>
                <option value={5.0}>5.0x</option>
                <option value={10.0}>10.0x</option>
              </select>
            </div>

            {/* Active Baseline Badge */}
            <div className="flex items-center gap-1.5 pl-2 border-l border-border">
              <span className="text-xs text-muted font-medium">Active:</span>
              <StatusBadge
                label={activeBaselineVersion}
                variant="approved"
                size="md"
                dot
              />
            </div>

            {/* Telemetry Data Catalog & Export Modal Button */}
            <button
              onClick={() => setShowDataPanel(true)}
              className="flex items-center gap-1.5 bg-bg hover:bg-slate/30 text-xs font-semibold text-text px-2.5 py-1.5 rounded-lg border border-border transition-colors cursor-pointer shadow-xs ml-1"
              title="Telemetry Data Catalog, Anonymized Preview & Live JSON Downloads"
            >
              <Database className="w-3.5 h-3.5 text-blue" />
              <span>Data</span>
            </button>

            {/* Built vs Planned Matrix Button */}
            <button
              onClick={() => setShowMatrixModal(true)}
              className="flex items-center gap-1.5 bg-bg hover:bg-slate/30 text-xs font-semibold text-text px-2.5 py-1.5 rounded-lg border border-border transition-colors cursor-pointer shadow-xs"
              title="View Built vs Planned Implementation Matrix"
            >
              <Layers className="w-3.5 h-3.5 text-teal" />
              <span>Matrix</span>
            </button>
          </div>
        </header>

        {/* Independently Scrolling Content Area */}
        <main className="flex-1 overflow-y-auto p-6 bg-bg">
          <div className="max-w-7xl mx-auto">
            {/* Presentation Demo Mode Key Event & Scenario 4 Banner */}
            <DemoEventBanner />

            {/* Data Provenance & Real Data Honest Labeling Strip */}
            <DataProvenanceStrip />

            <Routes>
              <Route path="/" element={<OverviewPage />} />
              <Route path="/monitoring" element={<MonitoringPage />} />
              <Route path="/detection" element={<DetectionPage />} />
              <Route path="/attribution" element={<AttributionView />} />
              <Route path="/governance" element={<GovernanceView />} />
              <Route path="/investigation" element={<InvestigationView />} />
              <Route path="/investigation/:id" element={<InvestigationView />} />
              <Route path="/experiments" element={<ExperimentsView />} />
              <Route path="/digital-twin" element={<DigitalTwinView />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </main>
      </div>

      {/* Telemetry Data Catalog & Export Panel */}
      <DataPanelModal
        isOpen={showDataPanel}
        onClose={() => setShowDataPanel(false)}
      />

      {/* Built vs Planned Implementation Matrix Modal */}
      <BuiltVsPlannedModal
        isOpen={showMatrixModal}
        onClose={() => setShowMatrixModal(false)}
      />

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-card border border-border rounded-xl shadow-2xl max-w-md w-full p-6 text-text">
            <div className="flex items-center justify-between pb-4 border-b border-border">
              <div className="flex items-center gap-2">
                <Key className="w-5 h-5 text-blue" />
                <h3 className="font-semibold text-base">Operator Access Control</h3>
              </div>
              <button
                onClick={() => setShowSettings(false)}
                className="text-muted hover:text-text p-1 rounded-lg hover:bg-bg transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="py-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-muted uppercase tracking-wider mb-1">
                  Analyst Token (Authorization Header)
                </label>
                <p className="text-xs text-muted mb-2">
                  Used for governance approvals, candidate rejections, and baseline rollbacks. Matches COMMSHIELD_ANALYST_TOKEN.
                </p>
                <input
                  type="password"
                  value={tokenInput}
                  onChange={(e) => {
                    setTokenInput(e.target.value);
                    setTokenSaved(false);
                  }}
                  placeholder="Enter analyst token..."
                  className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-xs font-mono text-text focus:outline-none focus:ring-1 focus:ring-blue"
                />
              </div>

              {tokenSaved && (
                <div className="flex items-center gap-2 text-xs text-green-600 bg-green-500/10 border border-green-500/20 px-3 py-2 rounded-lg">
                  <Check className="w-4 h-4" />
                  <span>Token saved to local session.</span>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
              <button
                onClick={() => setShowSettings(false)}
                className="px-3 py-1.5 text-xs font-medium text-muted hover:text-text rounded-lg hover:bg-bg transition-colors"
              >
                Close
              </button>
              <button
                onClick={() => {
                  setAnalystToken(tokenInput);
                  setTokenSaved(true);
                  setTimeout(() => setShowSettings(false), 600);
                }}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-blue rounded-lg hover:bg-blue/90 transition-colors shadow-sm"
              >
                Save Token
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ReplayProvider>
      <DemoProvider>
        <AppLayout />
      </DemoProvider>
    </ReplayProvider>
  );
};

export default App;
