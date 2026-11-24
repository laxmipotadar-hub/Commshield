// File: src/components/CommShield3DTwin.tsx

import { Suspense, useEffect } from 'react'
import { Canvas } from '@react-three/fiber'
import { 
  OrbitControls, 
  PerspectiveCamera, 
  Environment,
  Grid,
  Stats,
  useHelper
} from '@react-three/drei'
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing'
import { useCommShieldStore } from '../store/commshieldStore'
import { SceneEnvironment } from './three/SceneEnvironment'
import { NetworkInfrastructure } from './three/NetworkInfrastructure'
import { DeviceZones } from './three/DeviceZones'
import { ControlPanel } from './hud/ControlPanel'
import { TelemetryDashboard } from './hud/TelemetryDashboard'
import { AlertFeed } from './hud/AlertFeed'

// Satisfy strict noUnusedLocals while preserving requested imports
void PerspectiveCamera
void Environment
void useHelper

function LoadingFallback() {
  return (
    <div className="w-full h-full flex items-center justify-center bg-slate-950">
      <div className="text-center">
        <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <div className="text-slate-400 font-mono">Initializing 3D Twin...</div>
      </div>
    </div>
  )
}

export function CommShield3DTwin() {
  const { connect, disconnect, isConnected } = useCommShieldStore()
  
  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])
  
  return (
    <div className="w-full h-screen bg-slate-950 relative overflow-hidden">
      {/* 3D Canvas */}
      <Canvas
        shadows
        dpr={[1, 2]}
        gl={{ 
          antialias: true, 
          toneMapping: 3, // ACES Filmic
        }}
        camera={{ position: [50, 40, 50], fov: 50 }}
      >
        <Suspense fallback={null}>
          {/* Lighting */}
          <ambientLight intensity={0.3} />
          <directionalLight 
            position={[50, 50, 25]} 
            intensity={1} 
            castShadow 
            shadow-mapSize={[2048, 2048]}
          />
          
          {/* Environment */}
          <SceneEnvironment theme="dark" fogDensity={0.02} />
          
          {/* Network Core */}
          <NetworkInfrastructure />
          
          {/* Device Zones */}
          <DeviceZones />
          
          {/* Grid helper */}
          <Grid 
            infiniteGrid 
            cellSize={5} 
            sectionSize={25} 
            fadeDistance={100}
            fadeStrength={2}
            cellColor="#1e293b"
            sectionColor="#334155"
          />
          
          {/* Camera controls */}
          <OrbitControls 
            makeDefault
            target={[0, 5, 0]}
            maxPolarAngle={Math.PI / 2 - 0.1}
            minDistance={10}
            maxDistance={200}
            enableDamping
            dampingFactor={0.05}
          />
          
          {/* Post-processing effects */}
          <EffectComposer>
            <Bloom 
              intensity={0.5} 
              luminanceThreshold={0.8}
              luminanceSmoothing={0.9}
            />
            <Vignette 
              offset={0.2} 
              darkness={0.8}
            />
          </EffectComposer>
          
          {/* Performance stats (dev only) */}
          {import.meta.env.DEV && <Stats />}
        </Suspense>
      </Canvas>
      
      {/* HUD Overlays */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="pointer-events-auto">
          <ControlPanel />
          <TelemetryDashboard />
          <AlertFeed />
        </div>
      </div>
      
      {/* Connection status */}
      <div className="absolute top-4 right-4 flex items-center gap-2 bg-slate-900/90 backdrop-blur px-3 py-2 rounded-lg border border-slate-700 z-50">
        <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
        <span className="text-slate-400 text-sm font-mono">
          {isConnected ? 'Live' : 'Disconnected'}
        </span>
      </div>
      
      {/* Loading overlay */}
      {!isConnected && <LoadingFallback />}
    </div>
  )
}

export default CommShield3DTwin
// CommShield AI Core
