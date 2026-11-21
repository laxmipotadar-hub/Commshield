import React, { useEffect, useState } from 'react';
import {
  Routes,
  Route,
  NavLink,
  Navigate,
  useLocation,
} from 'react-router-dom';
import {
  AlertOctagon,
  Check,
  ChevronRight,
  Cpu,
  Database,
  GitBranch,
  Key,
  LayoutDashboard,
  Moon,
  Pause,
  Play,
  Radio,
  Search,
  Settings,
  Shield,
  ShieldCheck,
  Sliders,
  Sun,
  User,
  X,
  Zap,
  ZapOff,
} from 'lucide-react';
import {
  StatusBadge,
  DemoControlBar,
  DemoEventBanner,
  DataProvenanceStrip,
  DataPanelModal,
} from './components';
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
  { name: 'Anomaly Detection', to: '/detection', icon: <AlertOctagon className="w-4 h-4" /> },
  { name: 'Baseline Governance', to: '/governance', icon: <ShieldCheck className="w-4 h-4" /> },
  { name: 'Digital Twin', to: '/digital-twin', icon: <Cpu className="w-4 h-4" /> },
  { name: 'Experiment Matrix', to: '/experiments', icon: <Sliders className="w-4 h-4" /> },
  { name: 'Investigation', to: '/investigation', icon: <Search className="w-4 h-4" /> },
  { name: 'Drift Attribution', to: '/attribution', icon: <GitBranch className="w-4 h-4" /> },
  { name: 'Network Monitoring', to: '/monitoring', icon: <Radio className="w-4 h-4" /> },
];

const AppLayout: React.FC = () => {
  const location = useLocation();
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
  const [showSettings, setShowSettings] = useState(false);
  const [showDataPanel, setShowDataPanel] = useState(false);
  const [tokenInput, setTokenInput] = useState('');
  const [tokenSaved, setTokenSaved] = useState(false);

  // Theme Management (Light / Dark mode follows prefers-color-scheme by default)
  const [isDarkMode, setIsDarkMode] = useState<boolean>(() => {
    const saved = localStorage.getItem('commshield-theme');
    if (saved) return saved === 'dark';
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  // Low-Motion Accessibility Toggle
  const [lowMotion, setLowMotion] = useState<boolean>(() => {
    const saved = localStorage.getItem('commshield-low-motion');
    if (saved) return saved === 'true';
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  });

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('commshield-theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('commshield-theme', 'light');
    }
  }, [isDarkMode]);

  useEffect(() => {
    if (lowMotion) {
      document.documentElement.classList.add('low-motion');
      localStorage.setItem('commshield-low-motion', 'true');
    } else {
      document.documentElement.classList.remove('low-motion');
      localStorage.setItem('commshield-low-motion', 'false');
    }
  }, [lowMotion]);

  // Current page breadcrumb label
  const currentNav = navItems.find((item) =>
    item.to === '/' ? location.pathname === '/' : location.pathname.startsWith(item.to)
  );

  return (
    <div className="h-screen flex overflow-hidden bg-surface text-on-surface">
      {/* 1. Deep Navy Fixed Command Sidebar */}
      <aside className="w-60 h-screen bg-[#0a1628] text-white flex flex-col justify-between flex-shrink-0 z-50 border-r border-[#1e293b] select-none shadow-xl">
        <div className="flex flex-col">
          {/* Brand Header */}
          <div className="h-16 px-4 flex items-center justify-between border-b border-[#1e293b]">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-blue-400 shadow-sm">
                <Shield className="w-5 h-5 text-blue-400" />
              </div>
              <div className="flex flex-col leading-tight">
                <span className="text-sm font-bold text-white tracking-tight">CommShield</span>
                <span className="font-mono text-[10px] text-[#94a3b8] uppercase tracking-wider">5G Core Ops</span>
              </div>
            </div>
            <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-cyan-950/80 text-cyan-400 border border-cyan-700/60 uppercase tracking-wider">
              5G SOC
            </span>
          </div>

          {/* Section Heading */}
          <div className="px-4 pt-4 pb-2">
            <span className="font-mono text-[11px] font-semibold text-[#64748b] tracking-wider uppercase">
              Telemetry &amp; Control
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="flex flex-col gap-1 px-2.5">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-blue-600 text-white font-semibold shadow-[0_2px_8px_rgba(37,99,235,0.35)]'
                      : 'text-[#94a3b8] hover:bg-[#15233c] hover:text-white'
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
        <div className="p-3 border-t border-[#1e293b] bg-[#0f1d33]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              <div className="relative flex-shrink-0">
                <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-white border border-[#1e293b]">
                  <User className="w-4 h-4 text-slate-300" />
                </div>
                <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-[#0f1d33]"></span>
              </div>
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-semibold text-white truncate">analyst_sec_09</span>
                  <span className="flex h-1.5 w-1.5 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
                  </span>
                </div>
                <span className="text-[10px] text-emerald-400 font-mono tracking-wide truncate">ONLINE • ACTIVE SESSION</span>
              </div>
            </div>
            <button
              title="Operator Settings &amp; Access Control"
              onClick={() => {
                setTokenInput(getAnalystToken());
                setTokenSaved(false);
                setShowSettings(true);
              }}
              className="p-1.5 rounded-lg text-white/60 hover:text-white hover:bg-[#15233c] transition-colors"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* 2. Main Area with Analytical Canvas Header */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top Bar Header (Dedicated analytical header for dashboard pages; hidden on digital twin for full-screen immersive 3D canvas) */}
        {location.pathname !== '/digital-twin' && (
          <header className="h-16 bg-surface-container-lowest border-b border-border px-6 flex items-center justify-between flex-shrink-0 z-40 shadow-xs gap-4">
            {/* Left: Breadcrumbs & Enclave Status */}
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex items-center gap-1.5 text-xs text-on-surface-variant font-medium">
                <span className="font-bold text-on-surface">CommShield</span>
                <ChevronRight className="w-3.5 h-3.5 text-outline" />
                <span className="text-slate-500">5G Slice</span>
                <ChevronRight className="w-3.5 h-3.5 text-outline" />
                <span className="text-primary font-semibold">{currentNav?.name || 'Security Command'}</span>
              </div>

              <div className="h-4 w-px bg-border" />

              <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-400">
                <span className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-600"></span>
                </span>
                <span className="font-mono text-[11px] font-semibold">5G-CORE-UPF</span>
              </div>
            </div>

          {/* Right: Selectors, Controls, Baseline Badge, Theme & Motion */}
          <div className="flex items-center gap-2.5 flex-wrap justify-end">
            {/* Slice Selector */}
            <div className="flex items-center gap-1 bg-surface-container-low px-2 py-1 rounded-lg border border-border">
              <span className="text-[11px] font-semibold text-muted uppercase tracking-wider">Slice:</span>
              <select
                value={selectedSlice}
                onChange={(e) => setSelectedSlice(e.target.value)}
                className="bg-transparent border-0 text-xs font-semibold text-on-surface focus:outline-none cursor-pointer"
              >
                <option value="sst-1-sd-010203">eMBB (sst-1)</option>
                <option value="sst-2-sd-010203">URLLC (sst-2)</option>
                <option value="sst-3-sd-010203">mMTC (sst-3)</option>
              </select>
            </div>

            {/* Scenario Selector */}
            <div className="flex items-center gap-1 bg-surface-container-low px-2 py-1 rounded-lg border border-border">
              <span className="text-[11px] font-semibold text-muted uppercase tracking-wider">Scenario:</span>
              <select
                value={selectedScenario}
                onChange={(e) => setSelectedScenario(e.target.value as ScenarioId)}
                className="bg-transparent border-0 text-xs font-semibold text-on-surface focus:outline-none cursor-pointer max-w-[130px] truncate"
              >
                {SCENARIOS.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Presentation Controls */}
            <DemoControlBar />

            {/* Data Source Selector */}
            <div className="flex items-center gap-1 bg-surface-container-low px-2 py-1 rounded-lg border border-border">
              <Database className="w-3.5 h-3.5 text-teal" />
              <select
                value={selectedDataSource}
                onChange={(e) => setSelectedDataSource(e.target.value as any)}
                className="bg-transparent text-xs font-bold text-on-surface focus:outline-none cursor-pointer"
                title="Active Telemetry Data Source"
              >
                <option value="5g_nidd">Real 5G-NIDD</option>
                <option value="synthetic">Synthetic</option>
                {open5gsAvailable && <option value="open5gs_lab">Open5GS lab</option>}
              </select>
            </div>

            {/* Replay Controls */}
            <div className="flex items-center gap-1.5 bg-surface-container-low px-2 py-1 rounded-lg border border-border">
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
                {isRunning ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              </button>
              <span className="text-[10px] font-mono font-semibold text-on-surface uppercase min-w-[48px]">
                {isRunning
                  ? totalWindows > 0
                    ? `Play ${currentIndex}/${totalWindows}`
                    : 'Playing'
                  : status === 'PAUSED'
                  ? 'Paused'
                  : status === 'COMPLETED'
                  ? 'Done'
                  : 'Idle'}
              </span>
              <div className="h-3 w-px bg-border mx-0.5" />
              <select
                value={speed}
                onChange={(e) => setSpeed(Number(e.target.value))}
                className="bg-transparent text-[11px] font-mono font-semibold text-slate-500 focus:outline-none cursor-pointer"
                title="Replay Speed"
              >
                <option value={0.5}>0.5x</option>
                <option value={1.0}>1.0x</option>
                <option value={2.0}>2.0x</option>
                <option value={5.0}>5.0x</option>
              </select>
            </div>

            {/* Active Baseline Badge */}
            <div className="flex items-center gap-1.5 pl-1.5 border-l border-border">
              <StatusBadge
                label={activeBaselineVersion}
                variant="approved"
                size="sm"
                dot
              />
            </div>

            {/* Telemetry Data Catalog & Export Modal Button */}
            <button
              onClick={() => setShowDataPanel(true)}
              className="flex items-center gap-1 bg-surface-container-low hover:bg-surface-container text-xs font-semibold text-on-surface px-2.5 py-1.5 rounded-lg border border-border transition-colors cursor-pointer shadow-xs"
              title="Telemetry Data Catalog, Anonymized Preview &amp; Live JSON Downloads"
            >
              <Database className="w-3.5 h-3.5 text-primary" />
              <span>Data</span>
            </button>

            {/* Low Motion Toggle */}
            <button
              onClick={() => setLowMotion(!lowMotion)}
              className="p-1.5 rounded-lg bg-surface-container-low hover:bg-surface-container text-on-surface-variant hover:text-on-surface border border-border transition-colors"
              title={lowMotion ? 'Enable Full Animations' : 'Reduce Motion (Accessibility)'}
            >
              {lowMotion ? <ZapOff className="w-4 h-4 text-amber-500" /> : <Zap className="w-4 h-4" />}
            </button>

            {/* Dark / Light Theme Toggle */}
            <button
              onClick={() => setIsDarkMode(!isDarkMode)}
              className="p-1.5 rounded-lg bg-surface-container-low hover:bg-surface-container text-on-surface-variant hover:text-on-surface border border-border transition-colors"
              title={isDarkMode ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
            >
              {isDarkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-blue-600" />}
            </button>
          </div>
        </header>
        )}

        {/* 3. Independently Scrolling Content Area */}
        <main
          className={
            location.pathname === '/digital-twin'
              ? 'flex-1 overflow-hidden flex flex-col bg-[#070e1b]'
              : 'flex-1 overflow-y-auto p-6 bg-surface'
          }
        >
          {location.pathname === '/digital-twin' ? (
            <Routes>
              <Route path="/digital-twin" element={<DigitalTwinView />} />
            </Routes>
          ) : (
            <div className="max-w-7xl mx-auto space-y-4">
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
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </div>
          )}
        </main>
      </div>

      {/* Telemetry Data Catalog &amp; Export Panel */}
      <DataPanelModal
        isOpen={showDataPanel}
        onClose={() => setShowDataPanel(false)}
      />

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-surface-container-lowest border border-border rounded-xl shadow-2xl max-w-md w-full p-6 text-on-surface">
            <div className="flex items-center justify-between pb-4 border-b border-border">
              <div className="flex items-center gap-2">
                <Key className="w-5 h-5 text-primary" />
                <h3 className="font-semibold text-base">Operator Access Control</h3>
              </div>
              <button
                onClick={() => setShowSettings(false)}
                className="text-muted hover:text-on-surface p-1 rounded-lg hover:bg-surface-container-low transition-colors"
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
                  className="w-full bg-surface-container-low border border-border rounded-lg px-3 py-2 text-xs font-mono text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              {tokenSaved && (
                <div className="flex items-center gap-2 text-xs text-emerald-600 bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 rounded-lg">
                  <Check className="w-4 h-4" />
                  <span>Token saved to local session.</span>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 pt-4 border-t border-border">
              <button
                onClick={() => setShowSettings(false)}
                className="px-3 py-1.5 text-xs font-medium text-muted hover:text-on-surface rounded-lg hover:bg-surface-container-low transition-colors"
              >
                Close
              </button>
              <button
                onClick={() => {
                  setAnalystToken(tokenInput);
                  setTokenSaved(true);
                  setTimeout(() => setShowSettings(false), 600);
                }}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-primary rounded-lg hover:bg-primary/90 transition-colors shadow-sm"
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
