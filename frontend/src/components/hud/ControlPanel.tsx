// File: src/components/hud/ControlPanel.tsx

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Play, 
  Pause, 
  SkipBack, 
  SkipForward, 
  ZoomIn, 
  ZoomOut,
  Layers,
  Filter,
  Settings
} from 'lucide-react'
import { useCommShieldStore } from '../../store/commshieldStore'

export function ControlPanel() {
  const { 
    isPlaying, 
    setIsPlaying, 
    playbackSpeed, 
    setPlaybackSpeed,
    selectedSlice,
    setSelectedSlice
  } = useCommShieldStore()
  
  const [showSettings, setShowSettings] = useState(false)
  void Filter; // Preserve requested Filter import under strict noUnusedLocals
  
  const speeds = [0.5, 1, 2, 4, 8]

  const sliceMap: Record<string, string> = {
    'sst-1': 'sst-1-sd-010203',
    'sst-2': 'sst-2-sd-010203',
    'sst-3': 'sst-3-sd-010203',
  }

  const handleSliceClick = (slice: string) => {
    const fullId = sliceMap[slice] || slice
    if (selectedSlice === slice || selectedSlice === fullId) {
      setSelectedSlice(null)
    } else {
      setSelectedSlice(fullId)
    }
  }

  const isSliceActive = (slice: string) => {
    return selectedSlice === slice || selectedSlice === sliceMap[slice]
  }
  
  return (
    <motion.div 
      initial={{ y: 100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50"
    >
      <div className="bg-slate-900/95 backdrop-blur-xl border border-slate-700 rounded-2xl px-6 py-4 shadow-2xl">
        <div className="flex items-center gap-6">
          {/* Playback controls */}
          <div className="flex items-center gap-2">
            <button className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors" title="Skip Back">
              <SkipBack className="w-5 h-5" />
            </button>
            
            <button 
              onClick={() => setIsPlaying(!isPlaying)}
              className="p-3 bg-blue-600 hover:bg-blue-500 rounded-xl text-white transition-colors"
              title={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6" />}
            </button>
            
            <button className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors" title="Skip Forward">
              <SkipForward className="w-5 h-5" />
            </button>
          </div>
          
          {/* Speed control */}
          <div className="flex items-center gap-2 bg-slate-800 rounded-lg p-1">
            {speeds.map((speed) => (
              <button
                key={speed}
                onClick={() => setPlaybackSpeed(speed)}
                className={`
                  px-3 py-1 rounded-md text-sm font-mono transition-colors
                  ${playbackSpeed === speed 
                    ? 'bg-slate-700 text-white' 
                    : 'text-slate-400 hover:text-white'}
                `}
              >
                {speed}x
              </button>
            ))}
          </div>
          
          {/* Divider */}
          <div className="w-px h-8 bg-slate-700" />
          
          {/* View controls */}
          <div className="flex items-center gap-2">
            <button className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors" title="Zoom In">
              <ZoomIn className="w-5 h-5" />
            </button>
            <button className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors" title="Zoom Out">
              <ZoomOut className="w-5 h-5" />
            </button>
            <button className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors" title="Layers">
              <Layers className="w-5 h-5" />
            </button>
            <button className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors" title="Filter">
              <Filter className="w-5 h-5" />
            </button>
          </div>
          
          {/* Divider */}
          <div className="w-px h-8 bg-slate-700" />
          
          {/* Slice selector */}
          <div className="flex items-center gap-2">
            {['sst-1', 'sst-2', 'sst-3'].map((slice) => (
              <button
                key={slice}
                onClick={() => handleSliceClick(slice)}
                className={`
                  px-3 py-1.5 rounded-lg text-xs font-mono uppercase transition-all
                  ${isSliceActive(slice)
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-800 text-slate-400 hover:text-white'}
                `}
              >
                {slice}
              </button>
            ))}
          </div>
          
          {/* Settings */}
          <button 
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors"
            title="Settings"
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
        
        {/* Settings panel */}
        <AnimatePresence>
          {showSettings && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="mt-4 pt-4 border-t border-slate-700"
            >
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <label className="text-slate-400 text-xs uppercase tracking-wider">Theme</label>
                  <select className="mt-1 w-full bg-slate-800 rounded-lg px-3 py-2 text-white border border-slate-700">
                    <option>Dark (Grafana)</option>
                    <option>Dark (Vercel)</option>
                    <option>Light</option>
                  </select>
                </div>
                <div>
                  <label className="text-slate-400 text-xs uppercase tracking-wider">Data Source</label>
                  <select className="mt-1 w-full bg-slate-800 rounded-lg px-3 py-2 text-white border border-slate-700">
                    <option>Real 5G-NIDD</option>
                    <option>Simulated Twin</option>
                    <option>Live Lab</option>
                  </select>
                </div>
                <div>
                  <label className="text-slate-400 text-xs uppercase tracking-wider">Quality</label>
                  <select className="mt-1 w-full bg-slate-800 rounded-lg px-3 py-2 text-white border border-slate-700">
                    <option>Ultra</option>
                    <option>High</option>
                    <option>Medium</option>
                    <option>Low</option>
                  </select>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

export default ControlPanel
// CommShield AI Core
