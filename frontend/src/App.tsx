import React, { useEffect, useRef, useState } from 'react';
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
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Sun,
  User,
  X,
  Zap,
  ZapOff,
  Home,
  Flame,
  Activity,
  Box,
  FileText,
  Sparkles,
} from 'lucide-react';
import {
  StatusBadge,
  DemoControlBar,
  DemoEventBanner,
  DataProvenanceStrip,
  DataPanelModal,
  ErrorBoundary,
  FullDemoProgressBar,
  FullDemoExplanationPopup,
  FullDemoFinalReportModal,
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
import { FullDemoProvider, useFullDemo } from './context/FullDemoContext';

// Suppress unused imports for strict TypeScript compliance
void AlertOctagon;
void LayoutDashboard;
void GitBranch;
void Sliders;
void Radio;
void Zap;
void ZapOff;
void Pause;
void Play;
void Shield;
void ShieldCheck;

interface NavItem {
  name: string;
  to: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { name: 'Plant Overview', to: '/', icon: <Home className="w-4 h-4" /> },
  { name: '3D Plant View', to: '/digital-twin', icon: <Cpu className="w-4 h-4" /> },
  { name: 'Attack Simulation', to: '/digital-twin?tab=attacks', icon: <Flame className="w-4 h-4" /> },
  { name: 'Threat Intelligence', to: '/detection', icon: <ShieldAlert className="w-4 h-4" /> },
  { name: 'Network Analytics', to: '/monitoring', icon: <Activity className="w-4 h-4" /> },
  { name: 'Industrial Assets', to: '/experiments', icon: <Box className="w-4 h-4" /> },
  { name: 'Incident Investigation', to: '/investigation', icon: <Search className="w-4 h-4" /> },
  { name: 'Reports', to: '/governance', icon: <FileText className="w-4 h-4" /> },
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
  const { isFullDemoActive, startFullDemo, stopFullDemo } = useFullDemo();
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

  // Reset scroll position on route transitions to prevent inherited scroll offset
  const mainScrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (mainScrollRef.current) {
      mainScrollRef.current.scrollTop = 0;
    }
    window.scrollTo(0, 0);
  }, [location.pathname]);

  // Current page breadcrumb label
  const currentNav = navItems.find((item) => {
    const baseTo = item.to.split('?')[0];
    return baseTo === '/' ? location.pathname === '/' : location.pathname.startsWith(baseTo);
  });

  return (
    <div className="h-[100dvh] flex overflow-hidden bg-surface text-on-surface">
      {/* 1. Deep Navy Fixed Command Sidebar */}
      <aside className="w-60 h-full bg-[#0a1628] text-white flex flex-col justify-between flex-shrink-0 z-50 border-r border-[#1e293b] select-none shadow-xl">
        <div className="flex flex-col">
          {/* Brand Header */}
          <div className="h-16 px-4 flex items-center justify-between border-b border-[#1e293b]">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-blue-600/20 border border-blue-500/40 flex items-center justify-center text-cyan-400 shadow-md">
                {/* Industrial Factory Chimney Logo Icon */}
                <svg className="w-5 h-5 text-cyan-400" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M4 21V11l4 2V9l4 2V5l8 4v12H4zm2-2h12v-8.8l-4-2v4l-4-2v4l-4-2V19z" />
                </svg>
              </div>
              <div className="flex flex-col leading-tight">
                <span className="text-sm font-black text-white tracking-tight">CommShield</span>
                <span className="font-mono text-[9px] text-[#94a3b8] uppercase tracking-wider">Industrial Cyber Twin</span>
              </div>
            </div>
            <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-cyan-950/80 text-cyan-400 border border-cyan-700/60 uppercase tracking-wider">
              LIVE SOC
            </span>
          </div>

          {/* Full System Demo Quick Action Pill */}
          <div className="px-3 pt-2.5 pb-1">
            <button
              onClick={() => (isFullDemoActive ? stopFullDemo() : startFullDemo(0))}
              className={`w-full flex items-center justify-center gap-2 py-2 px-3 rounded-xl font-mono text-xs font-bold transition-all shadow-md ${
                isFullDemoActive
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white ring-2 ring-cyan-400 animate-pulse-subtle'
                  : 'bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-[0_4px_12px_rgba(6,182,212,0.35)]'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-cyan-200 animate-pulse" />
              <span>{isFullDemoActive ? 'Exit Full Demo' : 'Full Demo (26 Steps)'}</span>
            </button>
          </div>

          {/* Section Heading */}
          <div className="px-4 pt-3 pb-1.5">
            <span className="font-mono text-[10px] font-semibold text-[#64748b] tracking-wider uppercase">
              Operations &amp; Security
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="flex flex-col gap-1 px-2.5">
            {navItems.map((item) => {
              const baseTo = item.to.split('?')[0];
              const isItemActive = baseTo === '/' ? location.pathname === '/' : location.pathname.startsWith(baseTo);
              return (
                <NavLink
                  key={item.name}
                  to={item.to}
                  end={item.to === '/'}
                  className={
                    `flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                      isItemActive
                        ? 'bg-blue-600 text-white font-semibold shadow-[0_2px_8px_rgba(37,99,235,0.35)]'
                        : 'text-[#94a3b8] hover:bg-[#15233c] hover:text-white'
                    }`
                  }
                >
                  {item.icon}
                  <span>{item.name}</span>
                </NavLink>
              );
            })}
            {/* Direct Settings Link in Nav */}
            <button
              onClick={() => {
                setTokenInput(getAnalystToken());
                setTokenSaved(false);
                setShowSettings(true);
              }}
              className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium text-[#94a3b8] hover:bg-[#15233c] hover:text-white transition-all text-left"
            >
              <Settings className="w-4 h-4" />
              <span>Settings</span>
            </button>
          </nav>
        </div>

        {/* Bottom Section: Visual Industrial Graphic + User Pill */}
        <div className="flex flex-col">
          {/* Visual Industrial Banner: "Smart Factory. Stronger Security." */}
          <div className="mx-3 mb-3 p-3 rounded-xl bg-gradient-to-b from-[#0e213d] to-[#0a1628] border border-cyan-500/30 text-center relative overflow-hidden group shadow-lg">
            <div className="absolute inset-0 bg-cyan-500/5 group-hover:bg-cyan-500/10 transition-colors pointer-events-none" />
            <div className="flex justify-center mb-1 text-cyan-400">
              <svg className="w-9 h-9 text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.5)]" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M6 42h36M10 42V26l8 4V20l10 5V12l10 5v25" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M14 36h4M22 36h4M30 36h4M14 30h4M22 30h4M30 30h4M22 24h4M30 24h4M30 18h4" strokeLinecap="round" />
                <circle cx="28" cy="8" r="1.5" fill="currentColor" />
                <path d="M28 8v4" strokeLinecap="round" />
              </svg>
            </div>
            <div className="font-mono text-[11px] font-bold text-white tracking-tight">
              Smart Factory.
            </div>
            <div className="font-mono text-[10px] font-medium text-cyan-400 tracking-wide">
              Stronger Security.
            </div>
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
        </div>
      </aside>

      {/* 2. Main Area with Analytical Canvas Header */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden h-full relative">
        {/* Full System Demo Persistent Multi-Section Progress Bar */}
        <FullDemoProgressBar />

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

            {/* Full System Demo (26 Steps) Trigger */}
            <button
              onClick={() => (isFullDemoActive ? stopFullDemo() : startFullDemo(0))}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all shadow-sm ${
                isFullDemoActive
                  ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white ring-2 ring-cyan-400'
                  : 'bg-surface-container-low border border-cyan-500/50 text-cyan-400 hover:bg-cyan-950/40'
              }`}
              title="Launch 26-Step End-to-End System Demonstration"
            >
              <Sparkles className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
              <span>Full Demo</span>
              <span className="text-[9px] px-1.5 py-0.2 rounded bg-black/30 text-cyan-200">26 Steps</span>
            </button>

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
        {location.pathname === '/digital-twin' ? (
          <main
            ref={mainScrollRef}
            className="flex-1 flex flex-col min-h-0 min-w-0 h-full overflow-hidden bg-[#070e1b]"
          >
            <ErrorBoundary fallbackTitle="Digital Twin Security Interface Error">
              <Routes>
                <Route path="/digital-twin" element={<DigitalTwinView />} />
              </Routes>
            </ErrorBoundary>
          </main>
        ) : (
          <main ref={mainScrollRef} className="flex-1 overflow-y-auto p-6 bg-surface min-h-0">
            <div className="max-w-7xl mx-auto space-y-4">
              {/* Presentation Demo Mode Key Event & Scenario 4 Banner */}
              <DemoEventBanner />

              {/* Data Provenance & Real Data Honest Labeling Strip */}
              <DataProvenanceStrip />

              <ErrorBoundary fallbackTitle="Security Navigation Error">
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
              </ErrorBoundary>
            </div>
          </main>
        )}
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

      {/* Full Demo Floating Explanation Popup & Final Report Modal */}
      <FullDemoExplanationPopup />
      <FullDemoFinalReportModal />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ReplayProvider>
      <DemoProvider>
        <FullDemoProvider>
          <AppLayout />
        </FullDemoProvider>
      </DemoProvider>
    </ReplayProvider>
  );
};

export default App;
// CommShield AI Core
