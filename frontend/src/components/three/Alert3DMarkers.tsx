// File: src/components/three/Alert3DMarkers.tsx

import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import * as THREE from 'three'
import { useCommShieldStore } from '../../store/commshieldStore'

// Single 3D Alert Beacon Marker positioned in world space
function AlertMarker({
  position,
  severity,
  message,
}: {
  position: [number, number, number]
  severity: string
  message: string
}) {
  const ringRef = useRef<THREE.Mesh>(null)

  const isCritical = severity === 'critical' || severity === 'high'
  const color = isCritical ? '#ef4444' : '#f59e0b'

  useFrame((state) => {
    if (ringRef.current) {
      const s = 1 + (state.clock.elapsedTime * 2.5) % 2.5
      ringRef.current.scale.set(s, s, s)
      const mat = ringRef.current.material as THREE.MeshBasicMaterial
      mat.opacity = Math.max(0, 0.8 - (s - 1) / 2.5)
    }
  })

  return (
    <group position={[position[0], position[1] + 2.5, position[2]]}>
      {/* Central glowing alert diamond */}
      <mesh>
        <octahedronGeometry args={[0.45]} />
        <meshBasicMaterial color={color} />
      </mesh>

      {/* Pulsing horizontal radar wave */}
      <mesh ref={ringRef} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.6, 0.8, 24]} />
        <meshBasicMaterial color={color} transparent opacity={0.7} side={THREE.DoubleSide} />
      </mesh>

      {/* Floating 3D Alert Tag */}
      <Html center distanceFactor={22}>
        <div className="bg-slate-900/95 border border-rose-500/80 rounded-lg px-2.5 py-1 text-center shadow-2xl pointer-events-none whitespace-nowrap animate-bounce font-mono">
          <div className="flex items-center gap-1.5 justify-center">
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
            <span className="text-[10px] font-bold text-rose-300 uppercase tracking-wider">{severity} ALERT</span>
          </div>
          <div className="text-[9px] text-slate-300 max-w-[140px] truncate">{message}</div>
        </div>
      </Html>
    </group>
  )
}

export function Alert3DMarkers() {
  const { currentAlerts, devices } = useCommShieldStore()

  // Map alerts to 3D world coordinates
  const markers = currentAlerts.slice(0, 5).map((alert) => {
    const alertKey = alert.alertId || alert.id

    // 0. Explicit 3D coordinates provided in alert payload
    if (alert.position && Array.isArray(alert.position) && alert.position.length === 3) {
      return { id: alertKey, pos: alert.position, severity: alert.severity, msg: alert.message }
    }

    // 1. Check if alert references a specific device ID
    const targetDevId = alert.deviceId || alert.source || alert.target
    if (targetDevId) {
      const dev = devices.find((d) => d.id === targetDevId)
      if (dev) {
        return { id: alertKey, pos: dev.position, severity: alert.severity, msg: alert.message }
      }
    }

    // 2. Default node/zone locations for known entities
    if (alert.source?.includes('upf') || alert.target?.includes('upf')) {
      return { id: alertKey, pos: [-14, 5, -8] as [number, number, number], severity: alert.severity, msg: alert.message }
    }
    if (alert.source?.includes('amf') || alert.target?.includes('amf')) {
      return { id: alertKey, pos: [14, 5, -8] as [number, number, number], severity: alert.severity, msg: alert.message }
    }
    if (alert.source?.includes('gnb') || alert.target?.includes('gnb')) {
      return { id: alertKey, pos: [0, 16, 0] as [number, number, number], severity: alert.severity, msg: alert.message }
    }

    // 3. Fallback to center-north alert beacon
    return { id: alertKey, pos: [0, 4, 15] as [number, number, number], severity: alert.severity, msg: alert.message }
  })

  return (
    <group>
      {markers.map((m) => (
        <AlertMarker key={m.id} position={m.pos} severity={m.severity} message={m.msg} />
      ))}
    </group>
  )
}

export default Alert3DMarkers
// CommShield AI Core
