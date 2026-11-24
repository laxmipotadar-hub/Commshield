// File: src/components/three/NetworkInfrastructure.tsx

import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { Html } from '@react-three/drei'
import * as THREE from 'three'
import { useCommShieldStore } from '../../store/commshieldStore'

// Single cellular tower model
function Tower({ position, label, isCenter }: { position: [number, number, number]; label: string; isCenter?: boolean }) {
  const waveRef = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    if (waveRef.current) {
      const s = 1 + (state.clock.elapsedTime * 1.5) % 3.0
      waveRef.current.scale.set(s, s, s)
      const mat = waveRef.current.material as THREE.MeshBasicMaterial
      mat.opacity = Math.max(0, 0.7 - (s - 1) / 3.0)
    }
  })

  return (
    <group position={position}>
      {/* Concrete foundation base */}
      <mesh position={[0, 0.4, 0]} castShadow receiveShadow>
        <boxGeometry args={[4, 0.8, 4]} />
        <meshStandardMaterial color="#334155" roughness={0.7} />
      </mesh>

      {/* Base shelter cabinet */}
      <mesh position={[1, 1.3, 1]} castShadow>
        <boxGeometry args={[1.8, 1.8, 1.4]} />
        <meshStandardMaterial color="#475569" metalness={0.6} roughness={0.3} />
      </mesh>

      {/* Mast vertical column */}
      <mesh position={[0, 8, 0]} castShadow>
        <cylinderGeometry args={[0.3, 0.6, 16, 8]} />
        <meshStandardMaterial color={isCenter ? '#38bdf8' : '#94a3b8'} metalness={0.8} roughness={0.3} />
      </mesh>

      {/* Top platform */}
      <mesh position={[0, 16, 0]}>
        <cylinderGeometry args={[1.6, 1.2, 0.4, 8]} />
        <meshStandardMaterial color="#1e293b" metalness={0.9} roughness={0.2} />
      </mesh>

      {/* Panel antennas (3 sectors 120 deg apart) */}
      {[0, 120, 240].map((angle, i) => {
        const rad = (angle * Math.PI) / 180
        return (
          <mesh
            key={i}
            position={[Math.cos(rad) * 1.4, 17.2, Math.sin(rad) * 1.4]}
            rotation={[0, -rad + Math.PI / 2, 0]}
          >
            <boxGeometry args={[0.3, 2.2, 0.7]} />
            <meshStandardMaterial color="#f8fafc" emissive="#0284c7" emissiveIntensity={0.5} />
          </mesh>
        )
      })}

      {/* Pulsing signal beacon on lightning rod */}
      <mesh position={[0, 19.5, 0]}>
        <sphereGeometry args={[0.25, 12, 12]} />
        <meshBasicMaterial color="#38bdf8" />
      </mesh>

      {/* Concentric RF wave */}
      <mesh ref={waveRef} position={[0, 17.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[2, 2.3, 32]} />
        <meshBasicMaterial color="#38bdf8" transparent opacity={0.6} side={THREE.DoubleSide} />
      </mesh>

      {/* Billboard label */}
      <Html position={[0, 21, 0]} center distanceFactor={25}>
        <div className="bg-slate-900/90 border border-slate-700 px-2 py-0.5 rounded text-[10px] font-mono text-cyan-300 whitespace-nowrap shadow-md pointer-events-none">
          {label}
        </div>
      </Html>
    </group>
  )
}

// Server rack unit
function ServerRack({ position, label, role, color }: { position: [number, number, number]; label: string; role: string; color: string }) {
  const ringRef = useRef<THREE.Mesh>(null)

  useFrame((state) => {
    if (ringRef.current) {
      ringRef.current.rotation.z += 0.02
      const s = 1 + Math.sin(state.clock.elapsedTime * 2) * 0.05
      ringRef.current.scale.set(s, s, s)
    }
  })

  return (
    <group position={position}>
      {/* Rack enclosure */}
      <mesh position={[0, 2.5, 0]} castShadow receiveShadow>
        <boxGeometry args={[5, 5, 5]} />
        <meshStandardMaterial color="#1e293b" metalness={0.7} roughness={0.3} emissive="#0f172a" />
      </mesh>

      {/* Front glass panel with indicator LEDs */}
      <mesh position={[0, 2.5, 2.52]}>
        <planeGeometry args={[4, 4.2]} />
        <meshBasicMaterial color={color} transparent opacity={0.35} />
      </mesh>

      {/* Floating status octahedron */}
      <mesh position={[0, 6.2, 0]}>
        <octahedronGeometry args={[0.9]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} />
      </mesh>

      {/* Halo ring */}
      <mesh ref={ringRef} position={[0, 6.2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[1.3, 1.45, 24]} />
        <meshBasicMaterial color={color} transparent opacity={0.7} side={THREE.DoubleSide} />
      </mesh>

      {/* Label */}
      <Html position={[0, 7.8, 0]} center distanceFactor={20}>
        <div className="bg-slate-900/95 border border-slate-700 px-2.5 py-1 rounded-md text-center shadow-lg pointer-events-none">
          <div className="text-[11px] font-bold text-white font-mono">{label}</div>
          <div className="text-[9px] text-slate-400 font-mono">{role}</div>
        </div>
      </Html>
    </group>
  )
}

// Glowing fiber conduit line between two points
function FiberConduit({ start, end, color = '#38bdf8' }: { start: [number, number, number]; end: [number, number, number]; color?: string }) {
  const curve = useMemo(() => {
    const vStart = new THREE.Vector3(...start)
    const vEnd = new THREE.Vector3(...end)
    const mid = new THREE.Vector3().lerpVectors(vStart, vEnd, 0.5)
    mid.y += 0.8 // slight arch
    return new THREE.QuadraticBezierCurve3(vStart, mid, vEnd)
  }, [start, end])

  const tubeGeo = useMemo(() => new THREE.TubeGeometry(curve, 24, 0.12, 6, false), [curve])

  return (
    <mesh geometry={tubeGeo}>
      <meshBasicMaterial color={color} transparent opacity={0.75} />
    </mesh>
  )
}

export function NetworkInfrastructure() {
  const { networkStatus } = useCommShieldStore()
  void networkStatus

  // Towers layout
  const towers = [
    { pos: [0, 0, 0] as [number, number, number], label: 'gNodeB-Center (Macro Core)', isCenter: true },
    { pos: [-35, 0, -25] as [number, number, number], label: 'gNodeB-NorthWest (Tower 1)' },
    { pos: [35, 0, -25] as [number, number, number], label: 'gNodeB-NorthEast (Tower 2)' },
    { pos: [35, 0, 25] as [number, number, number], label: 'gNodeB-SouthEast (Tower 3)' },
    { pos: [-35, 0, 25] as [number, number, number], label: 'gNodeB-SouthWest (Tower 4)' },
  ]

  // Conduits from center tower to perimeter servers and towers
  const conduits: Array<{ start: [number, number, number]; end: [number, number, number]; color?: string }> = [
    { start: [0, 0.5, 0], end: [-14, 0.5, -8], color: '#38bdf8' }, // to UPF
    { start: [0, 0.5, 0], end: [14, 0.5, -8], color: '#8b5cf6' },  // to AMF/SMF
    { start: [0, 0.5, 0], end: [-35, 0.5, -25], color: '#0ea5e9' },
    { start: [0, 0.5, 0], end: [35, 0.5, -25], color: '#0ea5e9' },
    { start: [0, 0.5, 0], end: [35, 0.5, 25], color: '#0ea5e9' },
    { start: [0, 0.5, 0], end: [-35, 0.5, 25], color: '#0ea5e9' },
    { start: [-14, 0.5, -8], end: [14, 0.5, -8], color: '#10b981' }, // UPF to AMF N11
  ]

  return (
    <group>
      {/* 5G Radio Access Network Towers */}
      {towers.map((t, idx) => (
        <Tower key={idx} position={t.pos} label={t.label} isCenter={t.isCenter} />
      ))}

      {/* 5G Core User Plane Gateway (UPF) */}
      <ServerRack
        position={[-14, 0, -8]}
        label="UPF-01"
        role="User Plane Gateway (GTP-U)"
        color="#10b981"
      />

      {/* 5G Core Control Functions (AMF / SMF) */}
      <ServerRack
        position={[14, 0, -8]}
        label="AMF / SMF Core"
        role="Control Plane SBI (TS 29.500)"
        color="#8b5cf6"
      />

      {/* Optical Fiber Conduits */}
      {conduits.map((c, idx) => (
        <FiberConduit key={idx} start={c.start} end={c.end} color={c.color} />
      ))}
    </group>
  )
}

export default NetworkInfrastructure
// CommShield AI Core
