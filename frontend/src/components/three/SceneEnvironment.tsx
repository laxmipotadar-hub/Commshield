// File: src/components/three/SceneEnvironment.tsx

import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { Environment, Lightformer, ContactShadows } from '@react-three/drei'
import * as THREE from 'three'

export interface SceneEnvironmentProps {
  theme?: 'dark' | 'light'
  fogDensity?: number
}

export function SceneEnvironment({ theme = 'dark', fogDensity = 1.0 }: SceneEnvironmentProps) {
  const meshRef = useRef<THREE.Mesh>(null)

  // Render frame update hook
  useFrame(() => {
    if (meshRef.current) {
      meshRef.current.position.y = 0
    }
  })
  
  // Factory floor with grid pattern
  const floorTexture = useMemo(() => {
    const canvas = document.createElement('canvas')
    canvas.width = 512
    canvas.height = 512
    const ctx = canvas.getContext('2d')!
    
    // Dark industrial floor
    ctx.fillStyle = theme === 'light' ? '#334155' : '#1a1a1a'
    ctx.fillRect(0, 0, 512, 512)
    
    // Grid lines
    ctx.strokeStyle = theme === 'light' ? '#475569' : '#2a2a2a'
    ctx.lineWidth = 2
    for (let i = 0; i <= 8; i++) {
      ctx.beginPath()
      ctx.moveTo(i * 64, 0)
      ctx.lineTo(i * 64, 512)
      ctx.stroke()
      ctx.beginPath()
      ctx.moveTo(0, i * 64)
      ctx.lineTo(512, i * 64)
      ctx.stroke()
    }
    
    const texture = new THREE.CanvasTexture(canvas)
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping
    texture.repeat.set(4, 2)
    return texture
  }, [theme])

  const isDark = theme !== 'light'
  const fogColor = isDark ? '#0a0a0a' : '#e2e8f0'
  const fogNear = Math.max(10, 50 / (fogDensity || 1.0))
  const fogFar = Math.max(50, 200 / (fogDensity || 1.0))

  return (
    <group>
      {/* Floor */}
      <mesh ref={meshRef} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} receiveShadow>
        <planeGeometry args={[200, 100]} />
        <meshStandardMaterial 
          map={floorTexture}
          roughness={0.8}
          metalness={0.2}
        />
      </mesh>
      
      {/* Walls */}
      <mesh position={[0, 10, -50]}>
        <boxGeometry args={[200, 20, 0.5]} />
        <meshStandardMaterial color={isDark ? '#0f172a' : '#94a3b8'} transparent opacity={0.3} />
      </mesh>
      
      {/* Ceiling with lights */}
      <mesh position={[0, 20, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <planeGeometry args={[200, 100]} />
        <meshStandardMaterial color={isDark ? '#0a0a0a' : '#cbd5e1'} />
      </mesh>
      
      {/* Industrial light fixtures */}
      {[-60, -20, 20, 60].map((x, i) => (
        <group key={i} position={[x, 19, 0]}>
          <mesh>
            <boxGeometry args={[8, 0.5, 2]} />
            <meshStandardMaterial color={isDark ? '#1a1a1a' : '#e2e8f0'} />
          </mesh>
          <pointLight 
            position={[0, -1, 0]} 
            intensity={2} 
            color="#fff5e6"
            distance={30}
            decay={2}
          />
        </group>
      ))}

      {/* Studio Environment & Lighting */}
      <Environment resolution={256}>
        <group rotation={[-Math.PI / 2, 0, 0]}>
          <Lightformer intensity={0.75} rotation-x={Math.PI / 2} position={[0, 5, -9]} scale={[10, 10, 1]} />
          <Lightformer intensity={2} rotation-y={Math.PI / 2} position={[-5, 1, -1]} scale={[20, 0.1, 1]} />
          <Lightformer intensity={2} rotation-y={Math.PI / 2} position={[-5, -1, -1]} scale={[20, 0.5, 1]} />
          <Lightformer intensity={1} rotation-y={-Math.PI / 2} position={[10, 1, 0]} scale={[20, 1, 1]} />
        </group>
      </Environment>
      
      {/* Fog for depth */}
      <fog attach="fog" args={[fogColor, fogNear, fogFar]} />
      
      {/* Contact shadows */}
      <ContactShadows 
        position={[0, 0.01, 0]} 
        opacity={0.5} 
        scale={200} 
        blur={2} 
        far={20} 
      />
    </group>
  )
}

export default SceneEnvironment
// CommShield AI Core
