import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { TwinDevice, TwinLink, TwinNode, TwinSlice } from '../services/twinApi';
import { Camera, Eye, Zap, ShieldAlert, Cpu, Activity, ZoomIn, ZoomOut, RotateCcw, RotateCw, Maximize2 } from 'lucide-react';

interface ThreeTwinSceneProps {
  nodes: TwinNode[];
  links: TwinLink[];
  slices: TwinSlice[];
  devices: TwinDevice[];
  selectedId: string | null;
  onSelect: (id: string | null, type: 'node' | 'device' | 'link' | null) => void;
  onHover: (item: { id: string; name: string; type: string; status: string } | null) => void;
  attackPath?: string[];
  attackPaths?: string[][];
  attackerSources?: string[];
  isDistributed?: boolean;
  attackType?: string;
  mitigationActive?: boolean;
  reducedMotion?: boolean;
  activeCameraPreset?: string;
  onPresetChange?: (preset: string) => void;
  traceAttackPath?: boolean;
  lifecycleState?: string;
}

export const ThreeTwinScene: React.FC<ThreeTwinSceneProps> = ({
  nodes,
  links,
  slices,
  devices,
  selectedId,
  onSelect,
  onHover,
  attackPath = [],
  attackPaths = [],
  attackerSources = [],
  isDistributed = false,
  attackType = 'Volumetric DDoS',
  mitigationActive = false,
  reducedMotion = false,
  activeCameraPreset = 'full',
  onPresetChange,
  traceAttackPath = false,
  lifecycleState = 'NORMAL',
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const animFrameId = useRef<number | null>(null);
  const isLerpingRef = useRef<boolean>(false);

  // Group container holding dynamic campus entities that update with simulation state
  const contentGroupRef = useRef<THREE.Group>(new THREE.Group());
  const interactiveMeshesRef = useRef<THREE.Mesh[]>([]);
  const packetListRef = useRef<Array<{ mesh: THREE.Mesh; pair: any; progress: number }>>([]);
  const towerWaveMeshesRef = useRef<THREE.Mesh[]>([]);
  const sensorWaveMeshesRef = useRef<THREE.Mesh[]>([]);
  const enforcementMeshesRef = useRef<THREE.Mesh[]>([]);
  const aiEngineMeshRef = useRef<THREE.Mesh | null>(null);

  // 8-Layer Visibility Controls
  const [layers, setLayers] = useState<{
    physical: boolean;
    connectivity: boolean;
    security: boolean;
    legitimateTraffic: boolean;
    suspiciousTraffic: boolean;
    attackSources: boolean;
    enforcementPoints: boolean;
  }>({
    physical: true,
    connectivity: true,
    security: true,
    legitimateTraffic: true,
    suspiciousTraffic: true,
    attackSources: true,
    enforcementPoints: true,
  });

  const toggleLayer = (layerKey: keyof typeof layers) => {
    setLayers((prev) => ({ ...prev, [layerKey]: !prev[layerKey] }));
  };

  const toggleAllLayers = () => {
    const allOn = Object.values(layers).every(Boolean);
    setLayers({
      physical: !allOn,
      connectivity: !allOn,
      security: !allOn,
      legitimateTraffic: !allOn,
      suspiciousTraffic: !allOn,
      attackSources: !allOn,
      enforcementPoints: !allOn,
    });
  };

  // Target camera positions for smooth interpolation
  const targetCamPos = useRef<THREE.Vector3>(new THREE.Vector3(0, 52, 70));
  const targetLookAt = useRef<THREE.Vector3>(new THREE.Vector3(0, 0, 0));

  // Current selected preset
  const [currentPreset, setCurrentPreset] = useState<string>(activeCameraPreset);

  // Apply camera presets smoothly without overriding user orbit control
  const applyCameraPreset = useCallback((preset: string) => {
    setCurrentPreset(preset);
    if (onPresetChange) onPresetChange(preset);
    isLerpingRef.current = true;

    switch (preset) {
      case 'ran':
        targetCamPos.current.set(-25, 26, 26);
        targetLookAt.current.set(-14, 6, 0);
        break;
      case 'core':
        targetCamPos.current.set(8, 20, 16);
        targetLookAt.current.set(0, 4, -4);
        break;
      case 'edge':
        targetCamPos.current.set(24, 18, 30);
        targetLookAt.current.set(10, 2, 8);
        break;
      case 'attack':
        targetCamPos.current.set(-12, 22, 28);
        targetLookAt.current.set(-4, 3, 0);
        break;
      case 'full':
      default:
        targetCamPos.current.set(0, 52, 70);
        targetLookAt.current.set(0, 0, 0);
        break;
    }
  }, [onPresetChange]);

  const handleManualZoom = (delta: number) => {
    if (!cameraRef.current || !controlsRef.current) return;
    const cam = cameraRef.current;
    const target = controlsRef.current.target;
    const dir = new THREE.Vector3().subVectors(cam.position, target).normalize();
    const dist = cam.position.distanceTo(target);
    const newDist = Math.max(15, Math.min(180, dist + delta));
    targetCamPos.current.copy(target).addScaledVector(dir, newDist);
    targetLookAt.current.copy(target);
    isLerpingRef.current = true;
  };

  const handleManualRotate = (angleDeg: number) => {
    if (!cameraRef.current || !controlsRef.current) return;
    const cam = cameraRef.current;
    const target = controlsRef.current.target;
    const offset = new THREE.Vector3().subVectors(cam.position, target);
    const rad = THREE.MathUtils.degToRad(angleDeg);
    offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), rad);
    targetCamPos.current.copy(target).add(offset);
    targetLookAt.current.copy(target);
    isLerpingRef.current = true;
  };

  const handleFitNetwork = () => {
    targetCamPos.current.set(0, 52, 70);
    targetLookAt.current.set(0, 0, 0);
    isLerpingRef.current = true;
    setCurrentPreset('full');
    if (onPresetChange) onPresetChange('full');
  };

  useEffect(() => {
    if (activeCameraPreset && activeCameraPreset !== currentPreset) {
      applyCameraPreset(activeCameraPreset);
    }
  }, [activeCameraPreset, applyCameraPreset, currentPreset]);

  // Map 2D slice coordinates to 3D campus world coordinates
  const mapCoord = (x: number, y: number, zBase: number = 0): [number, number, number] => {
    const worldX = (x - 440) * 0.12;
    const worldZ = (y - 250) * 0.12;
    return [worldX, zBase, worldZ];
  };

  // 1. Permanent Scene & WebGLRenderer initialization (runs ONCE on mount)
  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 520;

    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color(0x08101e);
    scene.fog = new THREE.FogExp2(0x08101e, 0.007);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.5, 1200);
    cameraRef.current = camera;
    camera.position.set(0, 52, 70);
    camera.lookAt(0, 0, 0);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: false,
        powerPreference: 'default',
      });
    } catch {
      renderer = new THREE.WebGLRenderer({ antialias: false });
    }

    rendererRef.current = renderer;
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;

    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controlsRef.current = controls;
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.maxPolarAngle = Math.PI / 2 - 0.04;
    controls.minDistance = 12;
    controls.maxDistance = 180;
    controls.target.set(0, 0, 0);

    controls.addEventListener('start', () => {
      isLerpingRef.current = false;
    });

    // PBR Lighting System
    const ambientLight = new THREE.AmbientLight(0xdce7fe, 0.7);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0x7dd3fc, 1.4);
    sunLight.position.set(45, 75, 45);
    scene.add(sunLight);

    const fillLight = new THREE.DirectionalLight(0x818cf8, 0.6);
    fillLight.position.set(-45, 40, -40);
    scene.add(fillLight);

    // Ground Environment
    const platformGeo = new THREE.BoxGeometry(96, 1.2, 72);
    const platformMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      roughness: 0.85,
      metalness: 0.2,
    });
    const platform = new THREE.Mesh(platformGeo, platformMat);
    platform.position.y = -0.6;
    scene.add(platform);

    const roadMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.9 });
    const roadNSGeo = new THREE.PlaneGeometry(6, 68);
    const roadNS = new THREE.Mesh(roadNSGeo, roadMat);
    roadNS.rotation.x = -Math.PI / 2;
    roadNS.position.set(0, 0.03, 0);
    scene.add(roadNS);

    const roadEWGeo = new THREE.PlaneGeometry(90, 6);
    const roadEW = new THREE.Mesh(roadEWGeo, roadMat);
    roadEW.rotation.x = -Math.PI / 2;
    roadEW.position.set(0, 0.03, 0);
    scene.add(roadEW);

    const gridHelper = new THREE.GridHelper(96, 48, 0x1e3a8a, 0x0f2347);
    gridHelper.position.y = 0.04;
    scene.add(gridHelper);

    // Attach dynamic content group to scene
    scene.add(contentGroupRef.current);

    // Raycasting for Component Selection & Tooltip Hover
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handlePointerMove = (e: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(interactiveMeshesRef.current);

      if (intersects.length > 0) {
        const hit = intersects[0].object;
        renderer.domElement.style.cursor = 'pointer';
        onHover({
          id: hit.userData.id,
          name: hit.userData.label || hit.userData.id,
          type: hit.userData.role || hit.userData.type,
          status: hit.userData.status || 'Active',
        });
      } else {
        renderer.domElement.style.cursor = 'default';
        onHover(null);
      }
    };

    const handleClick = () => {
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(interactiveMeshesRef.current);
      if (intersects.length > 0) {
        const hit = intersects[0].object;
        onSelect(hit.userData.id, hit.userData.type);
      } else {
        onSelect(null, null);
      }
    };

    const domElement = renderer.domElement;
    domElement.addEventListener('pointermove', handlePointerMove);
    domElement.addEventListener('click', handleClick);

    // Animation Loop
    const animate = () => {
      controls.update();

      if (isLerpingRef.current && !reducedMotion) {
        camera.position.lerp(targetCamPos.current, 0.05);
        controls.target.lerp(targetLookAt.current, 0.05);
        if (
          camera.position.distanceTo(targetCamPos.current) < 0.1 &&
          controls.target.distanceTo(targetLookAt.current) < 0.1
        ) {
          camera.position.copy(targetCamPos.current);
          controls.target.copy(targetLookAt.current);
          isLerpingRef.current = false;
        }
      }

      // Animate Waves
      towerWaveMeshesRef.current.forEach((w) => {
        const s = (w.scale.x + 0.02) % 3.5;
        w.scale.set(s, s, s);
        (w.material as THREE.MeshBasicMaterial).opacity = Math.max(0.0, 0.7 - s / 3.5);
      });

      // Animate AI Diamond
      if (aiEngineMeshRef.current) {
        aiEngineMeshRef.current.rotation.y += 0.02;
        aiEngineMeshRef.current.rotation.z = Math.sin(Date.now() * 0.002) * 0.15;
        aiEngineMeshRef.current.position.y = 9.5 + Math.sin(Date.now() * 0.003) * 0.4;
      }

      // Animate Probes & Enforcement
      sensorWaveMeshesRef.current.forEach((s, idx) => {
        s.rotation.z += 0.015 * (idx % 2 === 0 ? 1 : -1);
      });
      enforcementMeshesRef.current.forEach((b) => {
        b.rotation.y += 0.01;
      });

      // Move packet particles along conduits
      packetListRef.current.forEach((p) => {
        if (p.pair.isAttack && mitigationActive) {
          p.mesh.position.lerpVectors(p.pair.start, p.pair.end, 0.42);
          (p.mesh.material as THREE.MeshBasicMaterial).opacity = 0.3 + Math.sin(Date.now() * 0.01) * 0.25;
        } else if (p.pair.isIsolated) {
          p.mesh.position.lerpVectors(p.pair.start, p.pair.end, 0.2);
        } else {
          p.progress = (p.progress + p.pair.speed) % 1.0;
          p.mesh.position.lerpVectors(p.pair.start, p.pair.end, p.progress);
          (p.mesh.material as THREE.MeshBasicMaterial).opacity = 0.9;
        }
      });

      renderer.render(scene, camera);
      animFrameId.current = requestAnimationFrame(animate);
    };

    animFrameId.current = requestAnimationFrame(animate);

    // Responsive Viewport Resize
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: w, height: h } = entry.contentRect;
        if (w > 0 && h > 0) {
          camera.aspect = w / h;
          camera.updateProjectionMatrix();
          renderer.setSize(w, h);
        }
      }
    });
    resizeObserver.observe(container);

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth || 800;
      const h = container.clientHeight || 520;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    // Permanent cleanup only when unmounting component
    return () => {
      if (animFrameId.current) cancelAnimationFrame(animFrameId.current);
      resizeObserver.disconnect();
      window.removeEventListener('resize', handleResize);
      domElement.removeEventListener('pointermove', handlePointerMove);
      domElement.removeEventListener('click', handleClick);
      controls.dispose();

      contentGroupRef.current.traverse((obj: THREE.Object3D) => {
        if (obj instanceof THREE.Mesh) {
          if (obj.geometry) obj.geometry.dispose();
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => m.dispose());
          } else if (obj.material) {
            obj.material.dispose();
          }
        }
      });

      platformGeo.dispose();
      platformMat.dispose();
      roadNSGeo.dispose();
      roadEWGeo.dispose();
      roadMat.dispose();
      renderer.dispose();
      if (container.contains(domElement)) {
        container.removeChild(domElement);
      }
    };
  }, []);

  // 2. Dynamic Entity Builder (Updates scene content when simulation telemetry changes)
  useEffect(() => {
    const group = contentGroupRef.current;
    if (!group) return;

    // Explicitly dispose old meshes in content group
    group.traverse((obj: THREE.Object3D) => {
      if (obj instanceof THREE.Mesh) {
        if (obj.geometry) obj.geometry.dispose();
        if (Array.isArray(obj.material)) {
          obj.material.forEach((m) => m.dispose());
        } else if (obj.material) {
          obj.material.dispose();
        }
      }
    });
    group.clear();

    const interactiveMeshes: THREE.Mesh[] = [];
    const nodePositionMap = new Map<string, THREE.Vector3>();
    const towerWaveMeshes: THREE.Mesh[] = [];
    const sensorWaveMeshes: THREE.Mesh[] = [];
    const enforcementMeshes: THREE.Mesh[] = [];
    let aiEngineMesh: THREE.Mesh | null = null;

    // Default fallback macro nodes if nodes list is temporarily empty
    const effectiveNodes: TwinNode[] = (nodes && nodes.length > 0) ? nodes : [
      { id: 'gnb-01', label: 'gNodeB-01 (North Tower)', type: 'ran', x: 220, y: 120, role: '5G-NR Cell Tower', operationalStatus: 'ACTIVE', coordinates3d: { x: -28.0, y: 0.0, z: -20.0 } },
      { id: 'gnb-02', label: 'gNodeB-02 (East Tower)', type: 'ran', x: 620, y: 120, role: '5G-NR Cell Tower', operationalStatus: 'ACTIVE', coordinates3d: { x: 28.0, y: 0.0, z: -20.0 } },
      { id: 'gnb-03', label: 'gNodeB-03 (South Tower)', type: 'ran', x: 620, y: 380, role: '5G-NR Cell Tower', operationalStatus: 'ACTIVE', coordinates3d: { x: 28.0, y: 0.0, z: 20.0 } },
      { id: 'gnb-04', label: 'gNodeB-04 (West Tower)', type: 'ran', x: 220, y: 380, role: '5G-NR Cell Tower', operationalStatus: 'ACTIVE', coordinates3d: { x: -28.0, y: 0.0, z: 20.0 } },
      { id: 'upf-01', label: 'UPF-01 (Data Center)', type: 'core_user', x: 440, y: 250, role: 'User Plane Gateway', operationalStatus: 'ACTIVE', coordinates3d: { x: 0.0, y: 0.0, z: -8.0 } },
      { id: 'edge-01', label: 'Edge-MEC-01', type: 'edge', x: 300, y: 250, role: 'Multi-access Edge Computing', operationalStatus: 'ACTIVE', coordinates3d: { x: -16.0, y: 0.0, z: 8.0 } },
      { id: 'amf-01', label: 'AMF-01 (Control Plane)', type: 'core_control', x: 440, y: 200, role: 'Access and Mobility Mgmt', operationalStatus: 'ACTIVE', coordinates3d: { x: 8.0, y: 0.0, z: -16.0 } },
      { id: 'smf-01', label: 'SMF-01 (Session Mgmt)', type: 'core_control', x: 480, y: 200, role: 'Session Mgmt Function', operationalStatus: 'ACTIVE', coordinates3d: { x: 16.0, y: 0.0, z: -16.0 } },
    ];

    const isThreat = lifecycleState === 'THREAT_DETECTED' || lifecycleState === 'ATTACK_INITIATED';
    const isAnalysing = lifecycleState === 'ANALYSING' || lifecycleState === 'SUSPICIOUS_ACTIVITY';
    const isRecoveredOrMit = mitigationActive || lifecycleState === 'RECOVERED' || lifecycleState === 'VERIFYING_MITIGATION';

    // 1. CommShield AI Detection & Decision Engine Core
    if (layers.security) {
      const aiGeo = new THREE.OctahedronGeometry(1.6);
      const aiColor = isRecoveredOrMit ? 0x10b981 : isThreat ? 0xef4444 : isAnalysing ? 0xf59e0b : 0x06b6d4;
      const aiMat = new THREE.MeshStandardMaterial({
        color: aiColor,
        roughness: 0.15,
        metalness: 0.85,
        emissive: aiColor,
        emissiveIntensity: 0.9,
      });
      aiEngineMesh = new THREE.Mesh(aiGeo, aiMat);
      aiEngineMesh.position.set(0, 9.5, 0);
      aiEngineMesh.userData = {
        id: 'sec-ai-engine',
        label: 'CommShield AI Detection & Decision Engine',
        role: 'Autonomous Cyber Defence Fabric',
        status: isThreat ? 'Threat Active' : isRecoveredOrMit ? 'Mitigated / Protected' : 'Monitoring',
      };
      group.add(aiEngineMesh);
      interactiveMeshes.push(aiEngineMesh);

      const haloGeo = new THREE.RingGeometry(2.2, 2.35, 32);
      const haloMat = new THREE.MeshBasicMaterial({ color: aiColor, side: THREE.DoubleSide, transparent: true, opacity: 0.7 });
      const haloMesh = new THREE.Mesh(haloGeo, haloMat);
      haloMesh.rotation.x = Math.PI / 2;
      aiEngineMesh.add(haloMesh);

      // Tower RF Probes
      const towerSensorPositions = [
        new THREE.Vector3(-28.0, 14.5, -20.0),
        new THREE.Vector3(28.0, 14.5, -20.0),
        new THREE.Vector3(28.0, 14.5, 20.0),
        new THREE.Vector3(-28.0, 14.5, 20.0),
      ];
      towerSensorPositions.forEach((pos, idx) => {
        const sGeo = new THREE.TorusGeometry(1.5, 0.07, 6, 24);
        const sMat = new THREE.MeshBasicMaterial({
          color: isThreat && idx === 0 ? 0xef4444 : 0x38bdf8,
          transparent: true,
          opacity: 0.8,
        });
        const sensorRing = new THREE.Mesh(sGeo, sMat);
        sensorRing.rotation.x = Math.PI / 2;
        sensorRing.position.copy(pos);
        sensorRing.userData = { id: `sensor-gnb-${idx + 1}`, label: `CommShield RF Sensor Probe #0${idx + 1}`, role: 'Security Telemetry Probe', status: 'Active' };
        group.add(sensorRing);
        sensorWaveMeshes.push(sensorRing);
        interactiveMeshes.push(sensorRing);
      });
    }

    // 2. Policy Enforcement Gateways
    if (layers.enforcementPoints) {
      const gateConfigs = [
        { pos: new THREE.Vector3(-14, 2.2, -10), label: 'N3 Policy Enforcement Gateway (UPF Ingress)' },
        { pos: new THREE.Vector3(14, 2.2, -4), label: 'N6 Policy Enforcement Gateway (Perimeter)' },
      ];
      gateConfigs.forEach((g) => {
        const bGeo = new THREE.CylinderGeometry(1.8, 1.8, 3.5, 16, 1, true);
        const bMat = new THREE.MeshBasicMaterial({
          color: mitigationActive ? 0x10b981 : 0x8b5cf6,
          wireframe: true,
          transparent: true,
          opacity: mitigationActive ? 0.95 : 0.45,
        });
        const barrier = new THREE.Mesh(bGeo, bMat);
        barrier.position.copy(g.pos);
        barrier.userData = {
          id: `barrier-${g.label}`,
          label: g.label,
          role: 'Enforcement Point',
          status: mitigationActive ? 'ACTIVE ENFORCEMENT (Dropping Attack Packets)' : 'PASSIVE MONITORING',
        };
        group.add(barrier);
        enforcementMeshes.push(barrier);
        interactiveMeshes.push(barrier);
      });
    }

    // 3. Render 5G Network Slices
    const effectiveSlices: TwinSlice[] = (slices && slices.length > 0) ? slices : [
      { slice_id: 'sst-1-sd-010203', name: 'eMBB Slice #1', device_class: 'eMBB', color: '#38bdf8', packet_rate_pps: 1200, throughput_mbps: 75, latency_ms: 2.1, health_status: 'NOMINAL', zone: { x: 220, y: 150, width: 280, height: 180, label: 'eMBB' } },
      { slice_id: 'sst-2-sd-020202', name: 'URLLC Slice #2', device_class: 'URLLC', color: '#ec4899', packet_rate_pps: 850, throughput_mbps: 45, latency_ms: 1.2, health_status: 'NOMINAL', zone: { x: 550, y: 150, width: 280, height: 180, label: 'URLLC' } },
      { slice_id: 'sst-3-sd-030303', name: 'mMTC Slice #3', device_class: 'mMTC', color: '#10b981', packet_rate_pps: 400, throughput_mbps: 15, latency_ms: 8.5, health_status: 'NOMINAL', zone: { x: 380, y: 350, width: 320, height: 160, label: 'mMTC' } },
    ];

    effectiveSlices.forEach((slice) => {
      const [zx, , zz] = mapCoord(slice.zone.x + slice.zone.width / 2, slice.zone.y + slice.zone.height / 2);
      const zw = slice.zone.width * 0.12;
      const zh = slice.zone.height * 0.12;

      const zoneGeo = new THREE.PlaneGeometry(zw, zh);
      const zoneMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(slice.color),
        transparent: true,
        opacity: 0.12,
        side: THREE.DoubleSide,
      });
      const zoneMesh = new THREE.Mesh(zoneGeo, zoneMat);
      zoneMesh.rotation.x = -Math.PI / 2;
      zoneMesh.position.set(zx, 0.06, zz);
      group.add(zoneMesh);

      const edgeGeo = new THREE.EdgesGeometry(zoneGeo);
      const edgeMat = new THREE.LineBasicMaterial({
        color: new THREE.Color(slice.color),
        transparent: true,
        opacity: 0.6,
      });
      const edgeLine = new THREE.LineSegments(edgeGeo, edgeMat);
      edgeLine.rotation.x = -Math.PI / 2;
      edgeLine.position.set(zx, 0.07, zz);
      group.add(edgeLine);
    });

    // 4. Cellular Tower Builder
    const buildCellularTower = (pos: THREE.Vector3, id: string, name: string, isAttacked: boolean, isSelected: boolean) => {
      const towerGroup = new THREE.Group();
      towerGroup.position.copy(pos);

      const baseGeo = new THREE.BoxGeometry(4.5, 0.8, 4.5);
      const baseMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.7 });
      const baseMesh = new THREE.Mesh(baseGeo, baseMat);
      baseMesh.position.y = 0.4;
      towerGroup.add(baseMesh);

      const mastHeight = 15.0;
      const legGeo = new THREE.CylinderGeometry(0.12, 0.22, mastHeight, 6);
      const steelMat = new THREE.MeshStandardMaterial({
        color: isAttacked ? 0xef4444 : isSelected ? 0x38bdf8 : 0x94a3b8,
        metalness: 0.85,
        roughness: 0.25,
      });

      const halfW = 1.1;
      const legPositions = [
        [-halfW, -halfW],
        [halfW, -halfW],
        [halfW, halfW],
        [-halfW, halfW],
      ];
      legPositions.forEach(([lx, lz]) => {
        const leg = new THREE.Mesh(legGeo, steelMat);
        leg.position.set(lx, mastHeight / 2 + 0.8, lz);
        towerGroup.add(leg);
      });

      const platGeo = new THREE.CylinderGeometry(1.8, 1.4, 0.4, 8);
      const platMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.9, roughness: 0.2 });
      const platMesh = new THREE.Mesh(platGeo, platMat);
      platMesh.position.y = mastHeight + 0.8;
      towerGroup.add(platMesh);

      const antGeo = new THREE.BoxGeometry(0.4, 2.4, 0.8);
      const antMat = new THREE.MeshStandardMaterial({
        color: isAttacked ? 0xff0000 : 0xf8fafc,
        emissive: isAttacked ? 0xef4444 : isSelected ? 0x38bdf8 : 0x0284c7,
        emissiveIntensity: isAttacked || isSelected ? 0.9 : 0.4,
      });

      for (let angleDeg = 0; angleDeg < 360; angleDeg += 120) {
        const rad = THREE.MathUtils.degToRad(angleDeg);
        const antMesh = new THREE.Mesh(antGeo, antMat);
        antMesh.position.set(Math.cos(rad) * 1.5, mastHeight + 2.2, Math.sin(rad) * 1.5);
        antMesh.rotation.y = -rad + Math.PI / 2;
        towerGroup.add(antMesh);
      }

      const beaconGeo = new THREE.SphereGeometry(0.25, 8, 8);
      const beaconMat = new THREE.MeshBasicMaterial({ color: isAttacked ? 0xef4444 : 0x38bdf8 });
      const beaconMesh = new THREE.Mesh(beaconGeo, beaconMat);
      beaconMesh.position.y = mastHeight + 5.1;
      towerGroup.add(beaconMesh);

      const waveGeo = new THREE.RingGeometry(2.5, 2.7, 32);
      const waveMat = new THREE.MeshBasicMaterial({
        color: isAttacked ? 0xef4444 : 0x38bdf8,
        transparent: true,
        opacity: 0.5,
        side: THREE.DoubleSide,
      });
      const waveMesh = new THREE.Mesh(waveGeo, waveMat);
      waveMesh.rotation.x = -Math.PI / 2;
      waveMesh.position.y = mastHeight + 2.2;
      towerGroup.add(waveMesh);
      towerWaveMeshes.push(waveMesh);

      const hitBoxGeo = new THREE.CylinderGeometry(2.5, 2.5, mastHeight + 5, 8);
      const hitBoxMat = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.0 });
      const hitBox = new THREE.Mesh(hitBoxGeo, hitBoxMat);
      hitBox.position.y = mastHeight / 2 + 1;
      hitBox.userData = {
        id,
        type: 'ran',
        label: name,
        role: `3GPP 5G-NR gNodeB (${id})`,
        status: isAttacked ? 'DEGRADED (Attacked)' : 'ACTIVE (Nominal)',
      };
      towerGroup.add(hitBox);
      interactiveMeshes.push(hitBox);

      group.add(towerGroup);
    };

    // Calculate Attack Scope
    const isAttackActive = (
      lifecycleState !== 'NORMAL' &&
      lifecycleState !== 'RECOVERED' &&
      (attackPath.length > 0 || (attackPaths && attackPaths.length > 0))
    );

    const attackNodeSet = new Set<string>();
    if (isAttackActive) {
      attackPath.forEach((id) => {
        attackNodeSet.add(id);
        if (id === 'upf-01') attackNodeSet.add('upf');
      });
      if (attackPaths) {
        attackPaths.forEach((path) => {
          path.forEach((id) => {
            attackNodeSet.add(id);
            if (id === 'upf-01') attackNodeSet.add('upf');
          });
        });
      }
      if (attackerSources) {
        attackerSources.forEach((id) => attackNodeSet.add(id));
      }
    }

    const attackLinkSet = new Set<string>();
    if (isAttackActive) {
      if (attackPaths && attackPaths.length > 0) {
        attackPaths.forEach((path) => {
          for (let i = 0; i < path.length - 1; i++) {
            attackLinkSet.add(`${path[i]}->${path[i + 1]}`);
            attackLinkSet.add(`${path[i + 1]}->${path[i]}`);
          }
        });
      } else if (attackPath.length > 0) {
        for (let i = 0; i < attackPath.length - 1; i++) {
          attackLinkSet.add(`${attackPath[i]}->${attackPath[i + 1]}`);
          attackLinkSet.add(`${attackPath[i + 1]}->${attackPath[i]}`);
        }
      }
    }

    // 5. Render Infrastructure Nodes & Technical Campus Buildings
    effectiveNodes.forEach((n) => {
      let pos: THREE.Vector3;
      if (n.coordinates3d) {
        pos = new THREE.Vector3(n.coordinates3d.x, n.coordinates3d.y, n.coordinates3d.z);
      } else {
        const [nx, ny, nz] = mapCoord(n.x, n.y, 0.0);
        pos = new THREE.Vector3(nx, ny, nz);
      }
      nodePositionMap.set(n.id, pos);

      const isUnderAttack = isAttackActive && (
        attackNodeSet.has(n.id) ||
        ((n.id === 'upf' || n.id === 'upf-01') && attackNodeSet.size > 0)
      );
      const isSelected = selectedId === n.id;

      if (n.type === 'ran') {
        buildCellularTower(pos, n.id, n.label, isUnderAttack, isSelected);
        return;
      }

      if (n.id === 'upf' || n.id === 'upf-01') {
        // UPF Core User Plane Building
        const bGroup = new THREE.Group();
        bGroup.position.copy(pos);

        const bGeo = new THREE.BoxGeometry(9.0, 5.0, 9.0);
        const bMat = new THREE.MeshStandardMaterial({
          color: isUnderAttack ? 0xef4444 : isSelected ? 0x38bdf8 : 0x1e293b,
          roughness: 0.3,
          metalness: 0.7,
          emissive: isUnderAttack ? 0x7f1d1d : isSelected ? 0x1d4ed8 : 0x0f172a,
          emissiveIntensity: isUnderAttack ? 0.8 : 0.2,
        });
        const bMesh = new THREE.Mesh(bGeo, bMat);
        bMesh.position.y = 2.5;
        bMesh.userData = { id: n.id, type: 'core_user', label: n.label, role: n.role, status: isUnderAttack ? 'CRITICAL (Under DDoS)' : 'Active' };
        bGroup.add(bMesh);
        interactiveMeshes.push(bMesh);

        const ringGeo = new THREE.RingGeometry(3.5, 3.8, 32);
        const ringMat = new THREE.MeshBasicMaterial({
          color: isUnderAttack ? 0xef4444 : 0x10b981,
          side: THREE.DoubleSide,
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = -Math.PI / 2;
        ring.position.y = 5.05;
        bGroup.add(ring);

        group.add(bGroup);
      } else if (n.type === 'edge') {
        // Edge MEC Facility
        const eGroup = new THREE.Group();
        eGroup.position.copy(pos);

        const eGeo = new THREE.BoxGeometry(6.5, 3.8, 5.5);
        const eMat = new THREE.MeshStandardMaterial({
          color: isSelected ? 0x38bdf8 : 0x1e293b,
          roughness: 0.35,
          metalness: 0.65,
        });
        const eMesh = new THREE.Mesh(eGeo, eMat);
        eMesh.position.y = 1.9;
        eMesh.userData = { id: n.id, type: 'edge', label: n.label, role: n.role, status: 'Active' };
        eGroup.add(eMesh);
        interactiveMeshes.push(eMesh);

        group.add(eGroup);
      } else {
        // Core Control Plane Servers (AMF, SMF, UDM, etc.)
        const cGroup = new THREE.Group();
        cGroup.position.copy(pos);

        const cGeo = new THREE.BoxGeometry(2.4, 2.8, 1.8);
        const cMat = new THREE.MeshStandardMaterial({
          color: isSelected ? 0x38bdf8 : isUnderAttack ? 0xf59e0b : 0x334155,
          metalness: 0.8,
          roughness: 0.25,
        });
        const cMesh = new THREE.Mesh(cGeo, cMat);
        cMesh.position.y = 1.4;
        cMesh.userData = { id: n.id, type: n.type, label: n.label, role: n.role, status: 'Active' };
        cGroup.add(cMesh);
        interactiveMeshes.push(cMesh);

        group.add(cGroup);
      }
    });

    // 6. Render UE Devices
    const effectiveDevices: TwinDevice[] = (devices && devices.length > 0) ? devices : [
      { id: 'ue-cam-01', device_id_hash: 'ue-cam-01', device_class: 'camera', slice_id: 'sst-1-sd-010203', x: 180, y: 160, rate_pps: 150, verdict: 'benign', action: 'none', status_label: 'Nominal', servingGnb: 'gnb-01', visible: true, is_onboarded: true, is_provisioned: true },
      { id: 'ue-cam-02', device_id_hash: 'ue-cam-02', device_class: 'camera', slice_id: 'sst-1-sd-010203', x: 260, y: 160, rate_pps: 150, verdict: 'benign', action: 'none', status_label: 'Nominal', servingGnb: 'gnb-01', visible: true, is_onboarded: true, is_provisioned: true },
      { id: 'ue-agv-01', device_id_hash: 'ue-agv-01', device_class: 'AGV', slice_id: 'sst-2-sd-020202', x: 580, y: 160, rate_pps: 200, verdict: 'benign', action: 'none', status_label: 'Nominal', servingGnb: 'gnb-02', visible: true, is_onboarded: true, is_provisioned: true },
      { id: 'ue-sensor-01', device_id_hash: 'ue-sensor-01', device_class: 'sensor', slice_id: 'sst-3-sd-030303', x: 420, y: 380, rate_pps: 50, verdict: 'benign', action: 'none', status_label: 'Nominal', servingGnb: 'gnb-04', visible: true, is_onboarded: true, is_provisioned: true },
    ];

    effectiveDevices.forEach((dev) => {
      const [dx, , dz] = mapCoord(dev.x, dev.y, 0.4);
      const isAttacker = isAttackActive && (
        dev.verdict === 'attack' ||
        attackNodeSet.has(dev.id) ||
        (attackerSources && attackerSources.includes(dev.id))
      );
      const isQuarantined = dev.verdict === 'quarantined' || dev.action === 'quarantine';
      const isSelected = selectedId === dev.id;

      const dGroup = new THREE.Group();
      dGroup.position.set(dx, 0.4, dz);

      let dGeo: THREE.BufferGeometry;
      if (dev.device_class === 'camera') {
        dGeo = new THREE.BoxGeometry(0.8, 0.6, 1.0);
      } else if (dev.device_class === 'AGV') {
        dGeo = new THREE.BoxGeometry(1.4, 0.7, 1.8);
      } else {
        dGeo = new THREE.CylinderGeometry(0.4, 0.4, 0.8, 12);
      }

      const dColor = isAttacker ? 0xef4444 : isQuarantined ? 0xa855f7 : isSelected ? 0x38bdf8 : 0x0ea5e9;
      const dMat = new THREE.MeshStandardMaterial({
        color: dColor,
        roughness: 0.3,
        metalness: 0.7,
        emissive: isAttacker ? 0xff0000 : 0x000000,
        emissiveIntensity: isAttacker ? 0.7 : 0.0,
      });

      const dMesh = new THREE.Mesh(dGeo, dMat);
      dMesh.userData = {
        id: dev.id,
        type: 'device',
        label: `${dev.device_class.toUpperCase()} (${dev.id})`,
        role: `5G UE Asset [Slice: ${dev.slice_id}]`,
        status: isAttacker ? 'ATTACKING BOTNET' : isQuarantined ? 'QUARANTINED' : 'NOMINAL',
      };
      dGroup.add(dMesh);
      interactiveMeshes.push(dMesh);

      // Flashing beacon for attacker devices
      if (isAttacker) {
        const bGeo = new THREE.SphereGeometry(0.3, 8, 8);
        const bMat = new THREE.MeshBasicMaterial({ color: 0xff0000 });
        const bMesh = new THREE.Mesh(bGeo, bMat);
        bMesh.position.y = 1.0;
        dGroup.add(bMesh);
      }

      nodePositionMap.set(dev.id, new THREE.Vector3(dx, 0.4, dz));
      group.add(dGroup);
    });

    // 7. Render Network Conduits & Flow Links
    const effectiveLinks: TwinLink[] = (links && links.length > 0) ? links : [
      { id: 'link-gnb01-upf', source: 'gnb-01', target: 'upf-01', label: 'N3 Interface', type: 'user_plane', status: 'NORMAL', active: true },
      { id: 'link-gnb02-upf', source: 'gnb-02', target: 'upf-01', label: 'N3 Interface', type: 'user_plane', status: 'NORMAL', active: true },
      { id: 'link-gnb03-upf', source: 'gnb-03', target: 'upf-01', label: 'N3 Interface', type: 'user_plane', status: 'NORMAL', active: true },
      { id: 'link-gnb04-upf', source: 'gnb-04', target: 'upf-01', label: 'N3 Interface', type: 'user_plane', status: 'NORMAL', active: true },
      { id: 'link-upf-edge', source: 'upf-01', target: 'edge-01', label: 'N6 Interface', type: 'user_plane', status: 'NORMAL', active: true },
      { id: 'link-cam01-gnb01', source: 'ue-cam-01', target: 'gnb-01', label: '5G-Uu Air Interface', type: 'user_plane', status: 'NORMAL', active: true },
      { id: 'link-cam02-gnb01', source: 'ue-cam-02', target: 'gnb-01', label: '5G-Uu Air Interface', type: 'user_plane', status: 'NORMAL', active: true },
      { id: 'link-agv01-gnb02', source: 'ue-agv-01', target: 'gnb-02', label: '5G-Uu Air Interface', type: 'user_plane', status: 'NORMAL', active: true },
      { id: 'link-sensor-gnb04', source: 'ue-sensor-01', target: 'gnb-04', label: '5G-Uu Air Interface', type: 'user_plane', status: 'NORMAL', active: true },
    ];

    const linkPairs: Array<{
      start: THREE.Vector3;
      end: THREE.Vector3;
      color: number;
      speed: number;
      isAttack: boolean;
      isIsolated: boolean;
    }> = [];

    effectiveLinks.forEach((link) => {
      const startPos = nodePositionMap.get(link.source);
      const endPos = nodePositionMap.get(link.target);
      if (!startPos || !endPos) return;

      const isAttackConduit = isAttackActive && (
        attackLinkSet.has(`${link.source}->${link.target}`) ||
        attackLinkSet.has(`${link.target}->${link.source}`) ||
        (attackNodeSet.has(link.source) && (link.target === 'upf-01' || link.target === 'upf'))
      );

      const isIsolated = Boolean(
        link.status === 'WARNING' ||
        (effectiveDevices.find((d) => d.id === link.source)?.action === 'quarantine')
      );

      const conduitColor = isAttackConduit ? 0xef4444 : isIsolated ? 0xa855f7 : link.type === 'control' ? 0x818cf8 : 0x06b6d4;

      // Clickable Conduit Tube
      const curve = new THREE.LineCurve3(startPos, endPos);
      const tubeGeo = new THREE.TubeGeometry(curve, 16, isAttackConduit ? 0.28 : 0.12, 8, false);
      const tubeMat = new THREE.MeshBasicMaterial({
        color: conduitColor,
        transparent: true,
        opacity: isAttackConduit ? 0.85 : 0.45,
      });
      const tubeMesh = new THREE.Mesh(tubeGeo, tubeMat);
      tubeMesh.userData = {
        id: link.id,
        type: 'link',
        label: `5G Conduit: ${link.id}`,
        role: `${link.type === 'control' ? 'Control Plane (N2/N4)' : 'User Plane (N3/N6)'} Conduit`,
        status: isAttackConduit ? 'COMPROMISED (Attack Conduit)' : isIsolated ? 'THROTTLED / ISOLATED' : 'ACTIVE',
      };
      group.add(tubeMesh);
      interactiveMeshes.push(tubeMesh);

      linkPairs.push({
        start: startPos.clone(),
        end: endPos.clone(),
        color: conduitColor,
        speed: isAttackConduit ? 0.024 : 0.012,
        isAttack: isAttackConduit,
        isIsolated,
      });
    });

    // 8. Clamped Packet Particles
    const particleCount = isAttackActive ? 96 : 48;
    const maxParticles = particleCount;
    const packetGeo = new THREE.SphereGeometry(0.32, 8, 8);
    const packetList: Array<{ mesh: THREE.Mesh; pair: typeof linkPairs[0]; progress: number }> = [];

    for (let i = 0; i < maxParticles; i++) {
      if (linkPairs.length === 0) break;
      const pair = linkPairs[i % linkPairs.length];
      const pMat = new THREE.MeshBasicMaterial({
        color: pair.color,
        transparent: true,
        opacity: 0.9,
      });
      const pMesh = new THREE.Mesh(packetGeo, pMat);
      group.add(pMesh);
      packetList.push({
        mesh: pMesh,
        pair,
        progress: (i / maxParticles),
      });
    }

    // Update active refs for continuous animation loop
    interactiveMeshesRef.current = interactiveMeshes;
    packetListRef.current = packetList;
    towerWaveMeshesRef.current = towerWaveMeshes;
    sensorWaveMeshesRef.current = sensorWaveMeshes;
    enforcementMeshesRef.current = enforcementMeshes;
    aiEngineMeshRef.current = aiEngineMesh;
  }, [nodes, links, slices, devices, selectedId, attackPath, attackPaths, attackerSources, isDistributed, attackType, mitigationActive, traceAttackPath, lifecycleState, layers]);

  return (
    <div className="w-full h-full relative overflow-hidden bg-[#08101e]">
      {/* Three.js Canvas Container */}
      <div ref={mountRef} className="w-full h-full" style={{ minHeight: '400px' }} />

      {/* Floating HUD: Camera Preset & Navigation Controls */}
      <div className="absolute top-3 left-3 z-10 flex flex-wrap items-center gap-1.5 bg-slate-900/90 backdrop-blur-md px-2.5 py-1 rounded-lg border border-slate-700/60 shadow-lg text-xs font-mono">
        <span className="text-slate-400 font-medium mr-1 flex items-center">
          <Camera className="w-3.5 h-3.5 mr-1 text-sky-400" /> View:
        </span>
        {[
          { id: 'full', label: 'Campus', icon: Eye },
          { id: 'ran', label: 'Towers', icon: Zap },
          { id: 'core', label: 'Core', icon: Cpu },
          { id: 'edge', label: 'MEC', icon: Activity },
          { id: 'attack', label: 'Attack', icon: ShieldAlert },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => applyCameraPreset(id)}
            className={`px-2 py-0.5 rounded flex items-center gap-1 transition-all ${
              currentPreset === id
                ? 'bg-sky-600 text-white font-medium shadow-sm'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            <Icon className="w-3 h-3" />
            <span>{label}</span>
          </button>
        ))}

        <div className="h-3 w-px bg-slate-700/70 mx-1" />

        {/* Manual Precision Navigation */}
        <button
          onClick={() => handleManualRotate(-25)}
          title="Rotate Left"
          className="p-1 rounded text-slate-300 hover:bg-slate-800 hover:text-white"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => handleManualRotate(25)}
          title="Rotate Right"
          className="p-1 rounded text-slate-300 hover:bg-slate-800 hover:text-white"
        >
          <RotateCw className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => handleManualZoom(-10)}
          title="Zoom In"
          className="p-1 rounded text-slate-300 hover:bg-slate-800 hover:text-white"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => handleManualZoom(10)}
          title="Zoom Out"
          className="p-1 rounded text-slate-300 hover:bg-slate-800 hover:text-white"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleFitNetwork}
          title="Fit Network Overview"
          className="p-1 rounded text-cyan-400 hover:bg-slate-800 hover:text-white flex items-center gap-1 font-bold"
        >
          <Maximize2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Layer Visibility Pills */}
      <div className="absolute bottom-3 left-3 z-10 flex flex-wrap items-center gap-1 bg-slate-900/80 backdrop-blur-md p-1 rounded-lg border border-slate-800 text-[10px] font-mono">
        <button
          onClick={toggleAllLayers}
          className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 hover:text-white font-bold"
        >
          LAYERS
        </button>
        {(
          [
            ['physical', 'TOWERS'],
            ['connectivity', 'CONDUITS'],
            ['security', 'AI FABRIC'],
            ['enforcementPoints', 'GATES'],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => toggleLayer(key)}
            className={`px-1.5 py-0.5 rounded transition-all font-semibold ${
              layers[key] ? 'bg-cyan-950 text-cyan-300 border border-cyan-800' : 'text-slate-500 hover:text-slate-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
};

export default ThreeTwinScene;
