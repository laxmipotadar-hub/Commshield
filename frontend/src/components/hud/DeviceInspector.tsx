// File: src/components/hud/DeviceInspector.tsx

import { motion, AnimatePresence } from 'framer-motion'
import { X, ShieldAlert, ShieldCheck, Activity, Cpu, Crosshair } from 'lucide-react'
import { useCommShieldStore } from '../../store/commshieldStore'

export function DeviceInspector() {
  const { selectedDevice, setSelectedDevice, devices, quarantineDevice, unquarantineDevice, setCameraPreset } = useCommShieldStore()

  const device = devices.find((d) => d.id === selectedDevice)

  if (!device) return null

  const isQuarantined = device.status === 'quarantined'
  const isCritical = device.status === 'critical'
  const isWarning = device.status === 'warning'

  const statusColor = isQuarantined
    ? 'text-purple-400 bg-purple-950/80 border-purple-800'
    : isCritical
    ? 'text-rose-400 bg-rose-950/80 border-rose-800'
    : isWarning
    ? 'text-amber-400 bg-amber-950/80 border-amber-800'
    : 'text-emerald-400 bg-emerald-950/80 border-emerald-800'

  return (
    <AnimatePresence>
      <motion.aside
        initial={{ x: 300, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: 300, opacity: 0 }}
        className="fixed top-20 right-6 z-50 w-80 font-mono text-xs pointer-events-auto"
      >
        <div className="bg-slate-900/95 backdrop-blur-xl border border-slate-700/80 rounded-2xl p-4 shadow-2xl flex flex-col gap-3">
          {/* Header */}
          <div className="flex items-start justify-between pb-2 border-b border-slate-800">
            <div>
              <span className="text-[10px] text-cyan-400 uppercase tracking-wider block">Device Telemetry Inspector</span>
              <h3 className="text-base font-bold text-white">{device.id}</h3>
              <span className="text-[11px] text-slate-400 uppercase">{device.type} &bull; {device.sliceId}</span>
            </div>
            <button
              onClick={() => setSelectedDevice(null)}
              className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Status Badge */}
          <div className="flex items-center justify-between p-2 rounded-xl bg-slate-800/60 border border-slate-800">
            <span className="text-slate-400">OPERATIONAL STATUS:</span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${statusColor}`}>
              {device.status}
            </span>
          </div>

          {/* Real-time Telemetry Metrics */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-slate-800/60 border border-slate-800 rounded-xl p-2.5">
              <span className="text-[10px] text-slate-400 block mb-0.5 flex items-center gap-1">
                <Activity className="w-3 h-3 text-cyan-400" /> PACKET RATE
              </span>
              <span className="text-sm font-bold text-white">{device.telemetry.packetRate} pps</span>
            </div>

            <div className="bg-slate-800/60 border border-slate-800 rounded-xl p-2.5">
              <span className="text-[10px] text-slate-400 block mb-0.5 flex items-center gap-1">
                <Activity className="w-3 h-3 text-emerald-400" /> LATENCY
              </span>
              <span className="text-sm font-bold text-emerald-300">{device.telemetry.latency} ms</span>
            </div>

            <div className="bg-slate-800/60 border border-slate-800 rounded-xl p-2.5">
              <span className="text-[10px] text-slate-400 block mb-0.5 flex items-center gap-1">
                <Activity className="w-3 h-3 text-amber-400" /> JITTER
              </span>
              <span className="text-sm font-bold text-amber-300">{device.telemetry.jitter} ms</span>
            </div>

            <div className="bg-slate-800/60 border border-slate-800 rounded-xl p-2.5">
              <span className="text-[10px] text-slate-400 block mb-0.5 flex items-center gap-1">
                <Cpu className="w-3 h-3 text-purple-400" /> 3D LOCATION
              </span>
              <span className="text-[10px] font-bold text-slate-300 truncate block">
                [{device.position[0]}, {device.position[1]}, {device.position[2]}]
              </span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col gap-2 pt-1">
            <button
              onClick={() => setCameraPreset('device')}
              className="w-full py-2 rounded-xl bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800 font-bold flex items-center justify-center gap-1.5 transition-colors"
            >
              <Crosshair className="w-3.5 h-3.5" /> Center Camera on Device
            </button>

            {isQuarantined ? (
              <button
                onClick={() => unquarantineDevice(device.id)}
                className="w-full py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold flex items-center justify-center gap-1.5 shadow-md transition-colors"
              >
                <ShieldCheck className="w-3.5 h-3.5" /> Release Quarantine
              </button>
            ) : (
              <button
                onClick={() => quarantineDevice(device.id)}
                className="w-full py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold flex items-center justify-center gap-1.5 shadow-md transition-colors"
              >
                <ShieldAlert className="w-3.5 h-3.5" /> Quarantine Rogue Device
              </button>
            )}
          </div>
        </div>
      </motion.aside>
    </AnimatePresence>
  )
}

export default DeviceInspector
// CommShield AI Core
