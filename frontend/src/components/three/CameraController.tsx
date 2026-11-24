// File: src/components/three/CameraController.tsx

import { useRef, useEffect } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { useCommShieldStore } from '../../store/commshieldStore'

export function CameraController() {
  const { selectedSlice, selectedDevice, cameraPreset, devices } = useCommShieldStore()
  const { camera, controls } = useThree()
  
  const targetPos = useRef<THREE.Vector3>(new THREE.Vector3(50, 40, 50))
  const targetLook = useRef<THREE.Vector3>(new THREE.Vector3(0, 5, 0))
  const isTransitioning = useRef<boolean>(false)

  // Calculate target camera destination whenever focus state changes
  useEffect(() => {
    // 1. Device Inspection takes highest priority
    if (selectedDevice) {
      const dev = devices.find((d) => d.id === selectedDevice)
      if (dev) {
        targetPos.current.set(dev.position[0] + 4, dev.position[1] + 5, dev.position[2] + 8)
        targetLook.current.set(dev.position[0], dev.position[1] + 1, dev.position[2])
        isTransitioning.current = true
        return
      }
    }

    // 2. Slice Selection Focus
    if (selectedSlice) {
      if (selectedSlice === 'sst-1-sd-010203' || selectedSlice === 'sst-1') {
        targetPos.current.set(-50, 25, 55)
        targetLook.current.set(-50, 2, 20)
        isTransitioning.current = true
        return
      } else if (selectedSlice === 'sst-2-sd-010203' || selectedSlice === 'sst-2') {
        targetPos.current.set(0, 22, 60)
        targetLook.current.set(0, 2, 30)
        isTransitioning.current = true
        return
      } else if (selectedSlice === 'sst-3-sd-010203' || selectedSlice === 'sst-3') {
        targetPos.current.set(50, 25, 55)
        targetLook.current.set(50, 2, 20)
        isTransitioning.current = true
        return
      }
    }

    // 3. Camera Presets
    switch (cameraPreset) {
      case 'embb':
        targetPos.current.set(-50, 25, 55)
        targetLook.current.set(-50, 2, 20)
        break
      case 'urllc':
        targetPos.current.set(0, 22, 60)
        targetLook.current.set(0, 2, 30)
        break
      case 'mmtc':
        targetPos.current.set(50, 25, 55)
        targetLook.current.set(50, 2, 20)
        break
      case 'core':
        targetPos.current.set(0, 16, 18)
        targetLook.current.set(0, 4, 0)
        break
      case 'overview':
      default:
        targetPos.current.set(50, 40, 50)
        targetLook.current.set(0, 5, 0)
        break
    }
    isTransitioning.current = true
  }, [selectedSlice, selectedDevice, cameraPreset, devices])

  // Smooth lerp transition towards target on each frame
  useFrame(() => {
    if (!isTransitioning.current) return

    const orbit = controls as unknown as OrbitControlsImpl | null
    camera.position.lerp(targetPos.current, 0.05)
    
    if (orbit && orbit.target) {
      orbit.target.lerp(targetLook.current, 0.05)
      orbit.update()
    }

    if (
      camera.position.distanceTo(targetPos.current) < 0.2 &&
      (!orbit || orbit.target.distanceTo(targetLook.current) < 0.2)
    ) {
      camera.position.copy(targetPos.current)
      if (orbit && orbit.target) {
        orbit.target.copy(targetLook.current)
      }
      isTransitioning.current = false
    }
  })

  return null
}

export default CameraController
// CommShield AI Core
