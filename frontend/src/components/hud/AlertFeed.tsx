// File: src/components/hud/AlertFeed.tsx

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ShieldAlert, ShieldCheck, ChevronDown, ChevronUp } from 'lucide-react'
import { useCommShieldStore } from '../../store/commshieldStore'

export function AlertFeed() {
  const { currentAlerts } = useCommShieldStore()
  const [collapsed, setCollapsed] = useState(false)

  const severityColor: Record<string, string> = {
    critical: 'bg-rose-950/80 border-rose-700 text-rose-300',
    high: 'bg-amber-950/80 border-amber-700 text-amber-300',
    medium: 'bg-yellow-950/80 border-yellow-700 text-yellow-300',
    low: 'bg-cyan-950/80 border-cyan-700 text-cyan-300',
  }

  return (
    <motion.aside
      initial={{ x: 100, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      className="fixed top-16 right-6 z-40 w-80 font-mono text-xs"
    >
      <div className="bg-slate-900/95 backdrop-blur-xl border border-slate-700/80 rounded-2xl p-4 shadow-2xl flex flex-col gap-3">
        {/* Header */}
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            <span className="font-bold text-white uppercase tracking-wider text-sm">Security Alerts</span>
            {currentAlerts.length > 0 && (
              <span className="px-1.5 py-0.5 rounded-full bg-rose-500 text-slate-950 text-[10px] font-bold">
                {currentAlerts.length}
              </span>
            )}
          </div>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 text-slate-400 hover:text-white rounded transition-colors"
            title={collapsed ? 'Expand' : 'Collapse'}
          >
            {collapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
          </button>
        </div>

        {/* Collapsible Alerts Feed */}
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="flex flex-col gap-2 max-h-72 overflow-y-auto pr-1"
            >
              {currentAlerts.length === 0 ? (
                <div className="py-4 text-center text-slate-400 flex flex-col items-center justify-center gap-1.5">
                  <ShieldCheck className="w-6 h-6 text-emerald-400" />
                  <span className="text-[11px] text-slate-300">Zero Active Security Threats</span>
                  <span className="text-[10px] text-slate-400">All slices operating within nominal parameters.</span>
                </div>
              ) : (
                currentAlerts.map((alert) => (
                  <div
                    key={alert.id}
                    className={`p-2.5 rounded-xl border flex flex-col gap-1 transition-all shadow-sm ${
                      severityColor[alert.severity] || severityColor.low
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.2 rounded bg-black/40">
                        {alert.severity}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-[11px] font-medium text-slate-200">{alert.message}</p>
                    {alert.source && (
                      <span className="text-[9px] text-slate-400">Source: {alert.source}</span>
                    )}
                  </div>
                ))
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.aside>
  )
}

export default AlertFeed
// CommShield AI Core
