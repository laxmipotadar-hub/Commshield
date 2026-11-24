// File: src/store/commshieldStore.ts

import { create } from 'zustand'

export interface DeviceTelemetry {
  packetRate: number
  latency: number
  jitter: number
}

export interface Device {
  id: string
  type: 'camera' | 'agv' | 'sensor'
  position: [number, number, number]
  status: 'normal' | 'warning' | 'critical' | 'quarantined'
  sliceId: string
  telemetry: DeviceTelemetry
}

export interface SliceInfo {
  sliceId: string
  name: string
  type: 'embb' | 'urllc' | 'mmtc'
  color: string
  allocatedBandwidthMbps: number
  currentThroughputMbps: number
  latencyMs: number
}

interface CommShieldStoreState {
  selectedSlice: string | null
  selectedDeviceId: string | null
  devices: Device[]
  slices: SliceInfo[]
  setSelectedSlice: (sliceId: string | null) => void
  setSelectedDeviceId: (id: string | null) => void
  setDevices: (devices: Device[]) => void
  updateDeviceTelemetry: (id: string, telemetry: Partial<DeviceTelemetry>) => void
  setDeviceStatus: (id: string, status: Device['status']) => void
}

// Initial devices distributed realistically across the 3 smart factory zones
const initialDevices: Device[] = [
  // --- eMBB Slice: 8 Surveillance Cameras (Zone [-50, 0, 20], size 40x30) ---
  { id: 'ue-cam-01', type: 'camera', position: [-62, 3.5, 12], status: 'normal', sliceId: 'sst-1-sd-010203', telemetry: { packetRate: 1250, latency: 4.2, jitter: 0.8 } },
  { id: 'ue-cam-02', type: 'camera', position: [-50, 3.5, 10], status: 'normal', sliceId: 'sst-1-sd-010203', telemetry: { packetRate: 1180, latency: 4.5, jitter: 0.9 } },
  { id: 'ue-cam-03', type: 'camera', position: [-38, 3.5, 12], status: 'normal', sliceId: 'sst-1-sd-010203', telemetry: { packetRate: 1220, latency: 4.1, jitter: 0.7 } },
  { id: 'ue-cam-04', type: 'camera', position: [-62, 3.5, 24], status: 'normal', sliceId: 'sst-1-sd-010203', telemetry: { packetRate: 1290, latency: 4.8, jitter: 1.1 } },
  { id: 'ue-cam-05', type: 'camera', position: [-50, 3.5, 28], status: 'normal', sliceId: 'sst-1-sd-010203', telemetry: { packetRate: 1150, latency: 4.3, jitter: 0.8 } },
  { id: 'ue-cam-06', type: 'camera', position: [-38, 3.5, 26], status: 'normal', sliceId: 'sst-1-sd-010203', telemetry: { packetRate: 1240, latency: 4.4, jitter: 0.8 } },
  { id: 'ue-cam-07', type: 'camera', position: [-56, 3.5, 18], status: 'normal', sliceId: 'sst-1-sd-010203', telemetry: { packetRate: 1210, latency: 4.2, jitter: 0.7 } },
  { id: 'ue-cam-08', type: 'camera', position: [-44, 3.5, 20], status: 'normal', sliceId: 'sst-1-sd-010203', telemetry: { packetRate: 1270, latency: 4.6, jitter: 1.0 } },

  // --- URLLC Slice: 4 Autonomous Vehicles (Zone [0, 0, 30], size 50x25) ---
  { id: 'ue-agv-01', type: 'agv', position: [-18, 0.4, 26], status: 'normal', sliceId: 'sst-2-sd-010203', telemetry: { packetRate: 480, latency: 1.2, jitter: 0.2 } },
  { id: 'ue-agv-02', type: 'agv', position: [-6, 0.4, 34], status: 'normal', sliceId: 'sst-2-sd-010203', telemetry: { packetRate: 510, latency: 1.4, jitter: 0.3 } },
  { id: 'ue-agv-03', type: 'agv', position: [8, 0.4, 25], status: 'normal', sliceId: 'sst-2-sd-010203', telemetry: { packetRate: 495, latency: 1.1, jitter: 0.2 } },
  { id: 'ue-agv-04', type: 'agv', position: [20, 0.4, 32], status: 'normal', sliceId: 'sst-2-sd-010203', telemetry: { packetRate: 520, latency: 1.5, jitter: 0.3 } },

  // --- mMTC Slice: 20 Industrial Sensor Pods (Zone [50, 0, 20], size 40x30) ---
  { id: 'ue-sns-01', type: 'sensor', position: [38, 0.3, 10], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 25, latency: 12.1, jitter: 1.8 } },
  { id: 'ue-sns-02', type: 'sensor', position: [44, 0.3, 12], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 28, latency: 11.8, jitter: 1.6 } },
  { id: 'ue-sns-03', type: 'sensor', position: [50, 0.3, 10], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 24, latency: 13.0, jitter: 2.1 } },
  { id: 'ue-sns-04', type: 'sensor', position: [56, 0.3, 12], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 26, latency: 12.5, jitter: 1.9 } },
  { id: 'ue-sns-05', type: 'sensor', position: [62, 0.3, 10], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 30, latency: 11.5, jitter: 1.7 } },
  { id: 'ue-sns-06', type: 'sensor', position: [38, 0.3, 18], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 22, latency: 14.2, jitter: 2.3 } },
  { id: 'ue-sns-07', type: 'sensor', position: [44, 0.3, 16], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 27, latency: 12.0, jitter: 1.8 } },
  { id: 'ue-sns-08', type: 'sensor', position: [50, 0.3, 18], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 29, latency: 11.9, jitter: 1.6 } },
  { id: 'ue-sns-09', type: 'sensor', position: [56, 0.3, 16], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 25, latency: 13.1, jitter: 2.0 } },
  { id: 'ue-sns-10', type: 'sensor', position: [62, 0.3, 18], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 28, latency: 12.4, jitter: 1.8 } },
  { id: 'ue-sns-11', type: 'sensor', position: [38, 0.3, 24], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 23, latency: 13.8, jitter: 2.2 } },
  { id: 'ue-sns-12', type: 'sensor', position: [44, 0.3, 22], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 26, latency: 12.6, jitter: 1.9 } },
  { id: 'ue-sns-13', type: 'sensor', position: [50, 0.3, 24], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 31, latency: 11.7, jitter: 1.7 } },
  { id: 'ue-sns-14', type: 'sensor', position: [56, 0.3, 22], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 25, latency: 12.9, jitter: 2.0 } },
  { id: 'ue-sns-15', type: 'sensor', position: [62, 0.3, 24], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 27, latency: 12.3, jitter: 1.8 } },
  { id: 'ue-sns-16', type: 'sensor', position: [40, 0.3, 28], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 24, latency: 13.4, jitter: 2.1 } },
  { id: 'ue-sns-17', type: 'sensor', position: [46, 0.3, 29], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 28, latency: 12.1, jitter: 1.7 } },
  { id: 'ue-sns-18', type: 'sensor', position: [52, 0.3, 28], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 29, latency: 11.8, jitter: 1.6 } },
  { id: 'ue-sns-19', type: 'sensor', position: [58, 0.3, 29], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 26, latency: 12.7, jitter: 1.9 } },
  { id: 'ue-sns-20', type: 'sensor', position: [64, 0.3, 28], status: 'normal', sliceId: 'sst-3-sd-010203', telemetry: { packetRate: 32, latency: 11.4, jitter: 1.5 } },
]

const initialSlices: SliceInfo[] = [
  {
    sliceId: 'sst-1-sd-010203',
    name: 'Camera Array (eMBB)',
    type: 'embb',
    color: '#3b82f6',
    allocatedBandwidthMbps: 500.0,
    currentThroughputMbps: 75.0,
    latencyMs: 4.5,
  },
  {
    sliceId: 'sst-2-sd-010203',
    name: 'Autonomous Vehicle Track (URLLC)',
    type: 'urllc',
    color: '#f59e0b',
    allocatedBandwidthMbps: 200.0,
    currentThroughputMbps: 24.0,
    latencyMs: 1.3,
  },
  {
    sliceId: 'sst-3-sd-010203',
    name: 'Industrial Sensor Mesh (mMTC)',
    type: 'mmtc',
    color: '#10b981',
    allocatedBandwidthMbps: 100.0,
    currentThroughputMbps: 8.5,
    latencyMs: 12.5,
  },
]

export const useCommShieldStore = create<CommShieldStoreState>((set) => ({
  selectedSlice: null,
  selectedDeviceId: null,
  devices: initialDevices,
  slices: initialSlices,
  setSelectedSlice: (sliceId) => set({ selectedSlice: sliceId }),
  setSelectedDeviceId: (id) => set({ selectedDeviceId: id }),
  setDevices: (devices) => set({ devices }),
  updateDeviceTelemetry: (id, telemetry) =>
    set((state) => ({
      devices: state.devices.map((d) =>
        d.id === id ? { ...d, telemetry: { ...d.telemetry, ...telemetry } } : d
      ),
    })),
  setDeviceStatus: (id, status) =>
    set((state) => ({
      devices: state.devices.map((d) => (d.id === id ? { ...d, status } : d)),
    })),
}))

export default useCommShieldStore
// CommShield AI Core
