// File: src/components/hud/TelemetryDashboard.tsx

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Activity, Radio, Cpu, Network, ChevronDown, ChevronUp } from 'lucide-react'
import { useCommShieldStore } from '../../store/commshieldStore'

export function TelemetryDashboard() {
  const { devices, networkStatus } = useCommShieldStore()
  const [collapsed, setCollapsed] = useState(false)

  // Compute live averages across connected factory devices
  const activeCount = devices.length
  const avgLatency = activeCount > 0
    ? (devices.reduce((acc, d) => acc + d.telemetry.latency, 0) / activeCount).toFixed(1)
    : '2.8'

  return (
    <motion.aside
      initial={{ x: -100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="fixed top-6 left-6 z-40 w-72"
    >
      <div className="bg-slate-900/95 backdrop-blur-xl border border-slate-700/80 rounded-2xl p-4 shadow-2xl font-mono text-xs">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400 animate-pulse" />
            <span className="font-bold text-white uppercase tracking-wider text-sm">Telemetry HUD</span>
          </div>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 text-slate-400 hover:text-white rounded transition-colors"
            title={collapsed ? 'Expand' : 'Collapse'}
          >
            {collapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </button>
        </div>

        {/* Collapsible Content */}
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="mt-3 flex flex-col gap-3"
            >
              {/* Primary KPIs */}
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-2.5">
                  <span className="text-[10px] text-slate-400 block mb-0.5">THROUGHPUT</span>
                  <span className="text-sm font-bold text-cyan-300">75.0 Mbps</span>
                </div>
                <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-2.5">
                  <span className="text-[10px] text-slate-400 block mb-0.5">AVG LATENCY</span>
                  <span className="text-sm font-bold text-emerald-400">{avgLatency} ms</span>
                </div>
                <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-2.5">
                  <span className="text-[10px] text-slate-400 block mb-0.5">PACKET LOSS</span>
                  <span className="text-sm font-bold text-emerald-400">0.00%</span>
                </div>
                <div className="bg-slate-800/80 border border-slate-700/60 rounded-xl p-2.5">
                  <span className="text-[10px] text-slate-400 block mb-0.5">ACTIVE UES</span>
                  <span className="text-sm font-bold text-sky-400">{activeCount} Online</span>
                </div>
              </div>

              {/* 5G Core Network Functions Status */}
              <div className="bg-slate-800/50 border border-slate-800 rounded-xl p-2.5 flex flex-col gap-1.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">3GPP Network Functions</span>
                
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-slate-300 flex items-center gap-1.5">
                    <Radio className="w-3 h-3 text-cyan-400" /> gNodeB RAN
                  </span>
                  <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold uppercase ${
                    networkStatus.gnodeb === 'active' ? 'text-emerald-400 bg-emerald-950/80' : 'text-rose-400 bg-rose-950/80'
                  }`}>
                    {networkStatus.gnodeb}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-slate-300 flex items-center gap-1.5">
                    <Network className="w-3 h-3 text-emerald-400" /> UPF Gateway
                  </span>
                  <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold uppercase ${
                    networkStatus.upf === 'active' ? 'text-emerald-400 bg-emerald-950/80' : 'text-rose-400 bg-rose-950/80'
                  }`}>
                    {networkStatus.upf}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-slate-300 flex items-center gap-1.5">
                    <Cpu className="w-3 h-3 text-purple-400" /> AMF / SMF
                  </span>
                  <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold uppercase ${
                    networkStatus.amf === 'active' ? 'text-emerald-400 bg-emerald-950/80' : 'text-rose-400 bg-rose-950/80'
                  }`}>
                    {networkStatus.amf}
                  </span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.aside>
  )
}

export default TelemetryDashboard
// CommShield AI Core
