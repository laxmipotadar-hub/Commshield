// File: src/components/three/DeviceZones.tsx

import { useRef, useMemo, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import { Html, Billboard } from '@react-three/drei'
import * as THREE from 'three'
import { useCommShieldStore } from '../../store/commshieldStore'

export interface DeviceZoneProps {
  position: [number, number, number]
  size: [number, number] // width, depth
  sliceId: string
  sliceType: 'embb' | 'urllc' | 'mmtc'
  label: string
  color: string
  devices: Device[]
}

export interface Device {
  id: string
  type: 'camera' | 'agv' | 'sensor'
  position: [number, number, number]
  status: 'normal' | 'warning' | 'critical' | 'quarantined'
  sliceId?: string
  telemetry: {
    packetRate: number
    latency: number
    jitter: number
  }
}

export function Device({ device, onClick }: { device: Device; onClick: () => void }) {
  const meshRef = useRef<THREE.Mesh>(null)
  const [hovered, setHovered] = useState(false)
  
  const statusColors = {
    normal: '#10b981',
    warning: '#f59e0b',
    critical: '#ef4444',
    quarantined: '#8b5cf6'
  }
  
  useFrame((state) => {
    if (meshRef.current) {
      // Pulse animation for warnings
      if (device.status !== 'normal') {
        const scale = 1 + Math.sin(state.clock.elapsedTime * 4) * 0.1
        meshRef.current.scale.setScalar(scale)
      }
      
      // Rotate cameras
      if (device.type === 'camera') {
        meshRef.current.rotation.y += 0.01
      }
    }
  })
  
  const geometry = useMemo(() => {
    switch(device.type) {
      case 'camera': return <sphereGeometry args={[0.5, 16, 16]} />
      case 'agv': return <boxGeometry args={[1.5, 0.8, 1]} />
      case 'sensor': return <cylinderGeometry args={[0.2, 0.2, 0.5, 8]} />
    }
  }, [device.type])

  return (
    <group position={device.position}>
      <mesh 
        ref={meshRef}
        onClick={onClick}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        {geometry}
        <meshStandardMaterial 
          color={hovered ? '#ffffff' : '#334155'}
          emissive={statusColors[device.status]}
          emissiveIntensity={device.status === 'normal' ? 0.2 : 0.8}
          metalness={0.5}
          roughness={0.5}
        />
      </mesh>
      
      {/* Status indicator ring */}
      <mesh rotation={[-Math.PI/2, 0, 0]} position={[0, -0.5, 0]}>
        <ringGeometry args={[0.6, 0.8, 32]} />
        <meshBasicMaterial 
          color={statusColors[device.status]}
          transparent
          opacity={0.6}
          side={THREE.DoubleSide}
        />
      </mesh>
      
      {/* Hover tooltip */}
      {hovered && (
        <Html position={[0, 2, 0]} center distanceFactor={10}>
          <div className="bg-slate-900/95 backdrop-blur border border-slate-700 rounded-lg p-3 text-xs min-w-[200px]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-slate-400 font-mono">{device.id}</span>
              <span 
                className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase"
                style={{ 
                  backgroundColor: `${statusColors[device.status]}20`,
                  color: statusColors[device.status]
                }}
              >
                {device.status}
              </span>
            </div>
            <div className="space-y-1 text-slate-300">
              <div className="flex justify-between">
                <span>Packet Rate</span>
                <span className="font-mono">{device.telemetry.packetRate} pps</span>
              </div>
              <div className="flex justify-between">
                <span>Latency</span>
                <span className="font-mono">{device.telemetry.latency} ms</span>
              </div>
              <div className="flex justify-between">
                <span>Jitter</span>
                <span className="font-mono">{device.telemetry.jitter} ms</span>
              </div>
            </div>
          </div>
        </Html>
      )}
    </group>
  )
}

export function DeviceZone({ position, size, sliceId, sliceType, label, color, devices }: DeviceZoneProps) {
  const { selectedSlice, setSelectedSlice } = useCommShieldStore()
  const isSelected = selectedSlice === sliceId
  
  return (
    <group position={position}>
      {/* Zone floor */}
      <mesh rotation={[-Math.PI/2, 0, 0]} position={[0, 0.01, 0]} receiveShadow>
        <planeGeometry args={size} />
        <meshStandardMaterial 
          color={color}
          transparent
          opacity={isSelected ? 0.15 : 0.05}
          roughness={0.9}
        />
      </mesh>
      
      {/* Zone border */}
      <mesh rotation={[-Math.PI/2, 0, 0]} position={[0, 0.02, 0]}>
        <ringGeometry args={[Math.min(...size)/2 - 0.5, Math.min(...size)/2, 4, 1]} />
        <meshBasicMaterial 
          color={color}
          transparent
          opacity={isSelected ? 0.8 : 0.3}
          side={THREE.DoubleSide}
        />
      </mesh>
      
      {/* Zone walls (transparent) */}
      <mesh position={[0, 5, -size[1]/2]}>
        <planeGeometry args={[size[0], 10]} />
        <meshStandardMaterial 
          color={color}
          transparent
          opacity={0.1}
          side={THREE.DoubleSide}
        />
      </mesh>
      
      {/* Zone label */}
      <Billboard position={[0, 12, 0]}>
        <Html center distanceFactor={20}>
          <button
            onClick={() => setSelectedSlice(sliceId)}
            className={`
              px-4 py-2 rounded-lg border font-mono text-sm transition-all
              ${isSelected 
                ? 'bg-slate-800 border-slate-500 text-white' 
                : 'bg-slate-900/80 border-slate-700 text-slate-300 hover:border-slate-500'}
            `}
          >
            <div className="text-[10px] uppercase tracking-wider opacity-70">{sliceType}</div>
            <div className="font-semibold">{label}</div>
          </button>
        </Html>
      </Billboard>
      
      {/* Devices */}
      {devices.map((device) => (
        <Device 
          key={device.id} 
          device={device}
          onClick={() => console.log('Inspect device:', device.id)}
        />
      ))}
      
      {/* Slice metrics panel */}
      {isSelected && (
        <Html position={[size[0]/2 + 5, 5, 0]} transform distanceFactor={15}>
          <div className="bg-slate-900/95 backdrop-blur border border-slate-700 rounded-lg p-4 w-64">
            <h3 className="text-white font-semibold mb-3">{label} Metrics</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between text-slate-300">
                <span>Active Devices</span>
                <span className="font-mono text-white">{devices.length}</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Throughput</span>
                <span className="font-mono text-emerald-400">2.4 Gbps</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Latency (p99)</span>
                <span className="font-mono text-amber-400">12 ms</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Packet Loss</span>
                <span className="font-mono text-emerald-400">0.01%</span>
              </div>
            </div>
            
            {/* Mini chart */}
            <div className="mt-3 h-16 flex items-end gap-1">
              {[40, 65, 45, 80, 55, 90, 70, 60, 85, 75].map((h, i) => (
                <div 
                  key={i}
                  className="flex-1 bg-blue-500/50 rounded-t"
                  style={{ height: `${h}%` }}
                />
              ))}
            </div>
          </div>
        </Html>
      )}
    </group>
  )
}

// Zone configurations
export function DeviceZones() {
  const { devices, slices } = useCommShieldStore()
  void slices;
  
  return (
    <group>
      {/* Camera Array Zone - eMBB (Enhanced Mobile Broadband) */}
      <DeviceZone
        position={[-50, 0, 20]}
        size={[40, 30]}
        sliceId="sst-1-sd-010203"
        sliceType="embb"
        label="Camera Array"
        color="#3b82f6"
        devices={devices.filter(d => d.sliceId === 'sst-1-sd-010203')}
      />
      
      {/* AV Track Zone - URLLC (Ultra-Reliable Low-Latency) */}
      <DeviceZone
        position={[0, 0, 30]}
        size={[50, 25]}
        sliceId="sst-2-sd-010203"
        sliceType="urllc"
        label="Autonomous Vehicle Track"
        color="#f59e0b"
        devices={devices.filter(d => d.sliceId === 'sst-2-sd-010203')}
      />
      
      {/* Sensor Mesh Zone - mMTC (Massive Machine-Type) */}
      <DeviceZone
        position={[50, 0, 20]}
        size={[40, 30]}
        sliceId="sst-3-sd-010203"
        sliceType="mmtc"
        label="Industrial Sensor Mesh"
        color="#10b981"
        devices={devices.filter(d => d.sliceId === 'sst-3-sd-010203')}
      />
    </group>
  )
}

export default DeviceZones
// CommShield AI Core
