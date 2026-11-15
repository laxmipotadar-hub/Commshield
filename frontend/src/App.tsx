import React, { useState } from 'react';
import {
  Routes,
  Route,
  NavLink,
  Navigate,
} from 'react-router-dom';
import {
  AlertOctagon,
  GitBranch,
  LayoutDashboard,
  Pause,
  Play,
  Radio,
  Search,
  Settings,
  Shield,
  ShieldCheck,
  Sliders,
  User,
} from 'lucide-react';
import { StatusBadge } from './components';
import { OverviewView } from './views/OverviewView';
import { MonitoringView } from './views/MonitoringView';
import { DetectionView } from './views/DetectionView';
import { AttributionView } from './views/AttributionView';
import { GovernanceView } from './views/GovernanceView';
import { InvestigationView } from './views/InvestigationView';
import { ExperimentsView } from './views/ExperimentsView';

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
];

export const App: React.FC = () => {
  const [selectedSlice, setSelectedSlice] = useState('sst-1-sd-010203');
  const [isPlaying, setIsPlaying] = useState(true);
  const [replaySpeed, setReplaySpeed] = useState('2.0x');

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
              title="Settings"
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
        <header className="h-16 bg-card border-b border-border px-6 flex items-center justify-between flex-shrink-0 z-20 shadow-sm">
          {/* Left: Slice Selector */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-muted uppercase tracking-wider">
              Slice:
            </span>
            <select
              value={selectedSlice}
              onChange={(e) => setSelectedSlice(e.target.value)}
              className="bg-bg border border-border text-xs font-medium text-text rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue transition-colors cursor-pointer"
            >
              <option value="sst-1-sd-010203">sst-1-sd-010203 (eMBB-01 Broad Band)</option>
              <option value="sst-2-sd-020304">sst-2-sd-020304 (uRLLC-02 Ultra Low Latency)</option>
              <option value="sst-3-sd-030405">sst-3-sd-030405 (MIoT-03 Massive IoT)</option>
            </select>
          </div>

          {/* Right: Replay Controls & Active Baseline Badge */}
          <div className="flex items-center gap-4">
            {/* Replay Controls */}
            <div className="flex items-center gap-2 bg-bg px-2.5 py-1 rounded-lg border border-border">
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className={`p-1 rounded-md transition-colors ${
                  isPlaying
                    ? 'text-suspicious hover:bg-suspicious/10'
                    : 'text-safe hover:bg-safe/10'
                }`}
                title={isPlaying ? 'Pause Replay' : 'Resume Replay'}
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </button>
              <span className="text-[11px] font-semibold text-text uppercase">
                {isPlaying ? 'Playing' : 'Paused'}
              </span>

              <div className="h-3.5 w-px bg-border mx-1" />

              <select
                value={replaySpeed}
                onChange={(e) => setReplaySpeed(e.target.value)}
                className="bg-transparent text-xs font-semibold text-slate focus:outline-none cursor-pointer"
              >
                <option value="1.0x">1x</option>
                <option value="2.0x">2x</option>
                <option value="5.0x">5x</option>
                <option value="10.0x">10x</option>
              </select>
            </div>

            {/* Active Baseline Badge */}
            <div className="flex items-center gap-1.5 pl-2 border-l border-border">
              <span className="text-xs text-muted font-medium">Active:</span>
              <StatusBadge
                label="v1.0.0-anchor"
                variant="approved"
                size="md"
                dot
              />
            </div>
          </div>
        </header>

        {/* Independently Scrolling Content Area */}
        <main className="flex-1 overflow-y-auto p-6 bg-bg">
          <div className="max-w-7xl mx-auto">
            <Routes>
              <Route path="/" element={<OverviewView />} />
              <Route path="/monitoring" element={<MonitoringView />} />
              <Route path="/detection" element={<DetectionView />} />
              <Route path="/attribution" element={<AttributionView />} />
              <Route path="/governance" element={<GovernanceView />} />
              <Route path="/investigation" element={<InvestigationView />} />
              <Route path="/experiments" element={<ExperimentsView />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  );
};

export default App;
