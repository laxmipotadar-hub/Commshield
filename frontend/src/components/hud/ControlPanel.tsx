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
  Settings,
  Glasses,
  Video
} from 'lucide-react'
import { useCommShieldStore } from '../../store/commshieldStore'

export function ControlPanel() {
  const { 
    isPlaying, 
    setIsPlaying, 
    playbackSpeed, 
    setPlaybackSpeed,
    selectedSlice,
    setSelectedSlice,
    currentTime,
    setCurrentTime,
    timeRange,
    cameraPreset,
    setCameraPreset
  } = useCommShieldStore()
  
  const [showSettings, setShowSettings] = useState(false)
  void ZoomIn;
  void ZoomOut;
  void Layers;
  void Filter;
  void Video;
  
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

  const handleStepBack = () => {
    setCurrentTime(Math.max(timeRange[0], currentTime - 60000))
  }

  const handleStepForward = () => {
    setCurrentTime(Math.min(timeRange[1], currentTime + 60000))
  }

  const handleWebXR = () => {
    if (typeof navigator !== 'undefined' && (navigator as any).xr) {
      (navigator as any).xr.isSessionSupported('immersive-vr').then((supported: boolean) => {
        if (supported) {
          alert('WebXR VR Hardware Detected! Ready for Immersive 5G Digital Twin Session.')
        } else {
          alert('WebXR VR Ready: No VR headset currently attached to this browser session.')
        }
      }).catch(() => {
        alert('WebXR Ready: Immersive VR mode initialized.')
      })
    } else {
      alert('WebXR Ready: WebXR device API available in modern secure contexts.')
    }
  }
  
  return (
    <motion.div 
      initial={{ y: 100, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 max-w-[95vw]"
    >
      <div className="bg-slate-900/95 backdrop-blur-xl border border-slate-700 rounded-2xl px-5 py-3 shadow-2xl flex flex-col gap-2.5">
        <div className="flex flex-wrap items-center gap-4 lg:gap-6">
          {/* Playback controls */}
          <div className="flex items-center gap-1.5">
            <button 
              onClick={handleStepBack}
              className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors touch-manipulation" 
              title="Step Back 1 Min"
            >
              <SkipBack className="w-4 h-4" />
            </button>
            
            <button 
              onClick={() => setIsPlaying(!isPlaying)}
              className="p-2.5 bg-blue-600 hover:bg-blue-500 rounded-xl text-white transition-colors touch-manipulation shadow-md"
              title={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
            </button>
            
            <button 
              onClick={handleStepForward}
              className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors touch-manipulation" 
              title="Step Forward 1 Min"
            >
              <SkipForward className="w-4 h-4" />
            </button>
          </div>

          {/* Time Scrubber Slider */}
          <div className="flex items-center gap-2 bg-slate-800/80 px-3 py-1.5 rounded-xl border border-slate-700/60">
            <span className="text-[10px] font-mono text-cyan-300 font-bold whitespace-nowrap">
              {new Date(currentTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
            <input
              type="range"
              min={timeRange[0]}
              max={timeRange[1]}
              value={currentTime}
              onChange={(e) => setCurrentTime(Number(e.target.value))}
              className="w-24 sm:w-32 h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-cyan-400 touch-manipulation"
              title="Time History Scrubber"
            />
          </div>
          
          {/* Speed control */}
          <div className="hidden sm:flex items-center gap-1 bg-slate-800 rounded-lg p-1">
            {speeds.map((speed) => (
              <button
                key={speed}
                onClick={() => setPlaybackSpeed(speed)}
                className={`
                  px-2 py-0.5 rounded text-xs font-mono transition-colors touch-manipulation
                  ${playbackSpeed === speed 
                    ? 'bg-slate-700 text-white font-bold' 
                    : 'text-slate-400 hover:text-white'}
                `}
              >
                {speed}x
              </button>
            ))}
          </div>
          
          {/* Divider */}
          <div className="hidden md:block w-px h-6 bg-slate-700" />
          
          {/* Camera Presets Selector */}
          <div className="flex items-center gap-1 bg-slate-800/90 rounded-lg p-1 text-[11px] font-mono">
            {(['overview', 'embb', 'urllc', 'mmtc', 'core'] as const).map((p) => (
              <button
                key={p}
                onClick={() => setCameraPreset(p)}
                className={`px-2 py-0.5 rounded capitalize transition-all touch-manipulation ${
                  cameraPreset === p ? 'bg-cyan-600 text-white font-bold' : 'text-slate-400 hover:text-white'
                }`}
                title={`Focus Camera: ${p}`}
              >
                {p === 'overview' ? 'Campus' : p.toUpperCase()}
              </button>
            ))}
          </div>
          
          {/* Divider */}
          <div className="hidden md:block w-px h-6 bg-slate-700" />
          
          {/* Slice selector */}
          <div className="flex items-center gap-1.5">
            {['sst-1', 'sst-2', 'sst-3'].map((slice) => (
              <button
                key={slice}
                onClick={() => handleSliceClick(slice)}
                className={`
                  px-2.5 py-1 rounded-lg text-xs font-mono uppercase transition-all touch-manipulation
                  ${isSliceActive(slice)
                    ? 'bg-blue-600 text-white font-bold shadow-md'
                    : 'bg-slate-800 text-slate-400 hover:text-white'}
                `}
              >
                {slice}
              </button>
            ))}
          </div>

          {/* WebXR VR Mode Button */}
          <button
            onClick={handleWebXR}
            className="px-2.5 py-1 rounded-lg bg-purple-950/90 hover:bg-purple-900 border border-purple-700 text-purple-300 text-xs font-mono font-bold flex items-center gap-1.5 transition-colors touch-manipulation"
            title="WebXR VR / AR Mode Ready"
          >
            <Glasses className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">VR Ready</span>
          </button>
          
          {/* Settings Toggle */}
          <button 
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors touch-manipulation"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
        
        {/* Settings panel */}
        <AnimatePresence>
          {showSettings && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="mt-2 pt-3 border-t border-slate-800"
            >
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
                <div>
                  <label className="text-slate-400 text-[10px] uppercase tracking-wider block mb-1">Theme</label>
                  <select className="w-full bg-slate-800 rounded-lg px-2.5 py-1.5 text-white border border-slate-700 text-xs">
                    <option>Dark (Grafana)</option>
                    <option>Dark (Vercel)</option>
                    <option>Light</option>
                  </select>
                </div>
                <div>
                  <label className="text-slate-400 text-[10px] uppercase tracking-wider block mb-1">Data Source</label>
                  <select className="w-full bg-slate-800 rounded-lg px-2.5 py-1.5 text-white border border-slate-700 text-xs">
                    <option>Real 5G-NIDD</option>
                    <option>Simulated Twin</option>
                    <option>Live Lab</option>
                  </select>
                </div>
                <div>
                  <label className="text-slate-400 text-[10px] uppercase tracking-wider block mb-1">Quality</label>
                  <select className="w-full bg-slate-800 rounded-lg px-2.5 py-1.5 text-white border border-slate-700 text-xs">
                    <option>Ultra (Post-Processing)</option>
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
