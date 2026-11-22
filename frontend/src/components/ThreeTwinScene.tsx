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
  attackType = 'volumetric_ddos',
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

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // 1. Scene, Camera & WebGL Renderer Setup
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 580;

    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color(0x08101e);
    scene.fog = new THREE.FogExp2(0x08101e, 0.007);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.5, 1200);
    cameraRef.current = camera;
    camera.position.set(0, 52, 70);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: 'high-performance',
    });
    rendererRef.current = renderer;
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // 2. Interactive OrbitControls (Zoom, Pan, Rotate)
    const controls = new OrbitControls(camera, renderer.domElement);
    controlsRef.current = controls;
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.maxPolarAngle = Math.PI / 2 - 0.04; // Prevent going below campus ground
    controls.minDistance = 12;
    controls.maxDistance = 180;
    controls.target.set(0, 0, 0);

    // Stop programmatic lerp immediately whenever user manually orbits, pans, or zooms
    controls.addEventListener('start', () => {
      isLerpingRef.current = false;
    });

    // 3. PBR Lighting System
    const ambientLight = new THREE.AmbientLight(0xdce7fe, 0.65);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0x7dd3fc, 1.4);
    sunLight.position.set(45, 75, 45);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 200;
    const d = 50;
    sunLight.shadow.camera.left = -d;
    sunLight.shadow.camera.right = d;
    sunLight.shadow.camera.top = d;
    sunLight.shadow.camera.bottom = -d;
    scene.add(sunLight);

    const fillLight = new THREE.DirectionalLight(0x818cf8, 0.6);
    fillLight.position.set(-45, 40, -40);
    scene.add(fillLight);

    // Core NOC Glow Light
    const nocPointLight = new THREE.PointLight(0x38bdf8, 2.0, 35);
    nocPointLight.position.set(0, 6, 0);
    scene.add(nocPointLight);

    // 4. Ground Environment (Engineered 5G Campus Platform)
    // Main campus concrete platform
    const platformGeo = new THREE.BoxGeometry(96, 1.2, 72);
    const platformMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      roughness: 0.85,
      metalness: 0.2,
    });
    const platform = new THREE.Mesh(platformGeo, platformMat);
    platform.position.y = -0.6;
    platform.receiveShadow = true;
    scene.add(platform);

    // Chamfered platform border
    const borderMat = new THREE.MeshBasicMaterial({ color: 0x1e293b, wireframe: false });
    const borderGeo = new THREE.RingGeometry(48, 49.5, 64);
    const borderMesh = new THREE.Mesh(borderGeo, borderMat);
    borderMesh.rotation.x = -Math.PI / 2;
    borderMesh.position.y = 0.02;
    scene.add(borderMesh);

    // Campus Roadways / Access Pathways
    const roadMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.9 });
    // North-South Main Road
    const roadNSGeo = new THREE.PlaneGeometry(6, 68);
    const roadNS = new THREE.Mesh(roadNSGeo, roadMat);
    roadNS.rotation.x = -Math.PI / 2;
    roadNS.position.set(0, 0.03, 0);
    roadNS.receiveShadow = true;
    scene.add(roadNS);

    // East-West Main Road
    const roadEWGeo = new THREE.PlaneGeometry(90, 6);
    const roadEW = new THREE.Mesh(roadEWGeo, roadMat);
    roadEW.rotation.x = -Math.PI / 2;
    roadEW.position.set(0, 0.03, 0);
    roadEW.receiveShadow = true;
    scene.add(roadEW);

    // Technical campus grid
    const gridHelper = new THREE.GridHelper(96, 48, 0x1e3a8a, 0x0f2347);
    gridHelper.position.y = 0.04;
    scene.add(gridHelper);

    // Interactive object lookup containers
    const interactiveMeshes: THREE.Mesh[] = [];
    const nodePositionMap = new Map<string, THREE.Vector3>();

    // CommShield Security Fabric Entities
    let aiEngineMesh: THREE.Mesh | null = null;
    const sensorWaveMeshes: THREE.Mesh[] = [];
    const enforcementMeshes: THREE.Mesh[] = [];

    if (layers.security) {
      // 1. CommShield AI Detection & Decision Engine Core (Floating Diamond above Data Center)
      const aiGeo = new THREE.OctahedronGeometry(1.6);
      const isThreat = lifecycleState === 'THREAT_DETECTED' || lifecycleState === 'ATTACK_INITIATED';
      const isAnalysing = lifecycleState === 'ANALYSING' || lifecycleState === 'SUSPICIOUS_ACTIVITY';
      const isRecoveredOrMit = mitigationActive || lifecycleState === 'RECOVERED' || lifecycleState === 'VERIFYING_MITIGATION';
      
      const aiColor = isRecoveredOrMit ? 0x10b981 : isThreat ? 0xef4444 : isAnalysing ? 0xf59e0b : 0x06b6d4;
      const aiMat = new THREE.MeshStandardMaterial({
        color: aiColor,
        roughness: 0.15,
        metalness: 0.85,
        emissive: aiColor,
        emissiveIntensity: 0.9,
      });
      aiEngineMesh = new THREE.Mesh(aiGeo, aiMat);
      aiEngineMesh.position.set(0, 9.5, 0); // Directly above 5G Core NOC
      aiEngineMesh.userData = {
        id: 'sec-ai-engine',
        label: 'CommShield AI Detection & Decision Engine',
        role: 'Autonomous Cyber Defence Fabric',
        status: isThreat ? 'Threat Active' : isRecoveredOrMit ? 'Mitigated / Protected' : 'Monitoring',
      };
      scene.add(aiEngineMesh);
      interactiveMeshes.push(aiEngineMesh);

      // AI Halo Ring
      const haloGeo = new THREE.RingGeometry(2.2, 2.35, 32);
      const haloMat = new THREE.MeshBasicMaterial({ color: aiColor, side: THREE.DoubleSide, transparent: true, opacity: 0.7 });
      const haloMesh = new THREE.Mesh(haloGeo, haloMat);
      haloMesh.rotation.x = Math.PI / 2;
      aiEngineMesh.add(haloMesh);

      // 2. Monitoring Sensor Probes on Macro Cell Towers
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
        scene.add(sensorRing);
        sensorWaveMeshes.push(sensorRing);
        interactiveMeshes.push(sensorRing);
      });
    }

    // 3. Policy Enforcement Gateways (Visual Barrier Shields)
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
        scene.add(barrier);
        enforcementMeshes.push(barrier);
        interactiveMeshes.push(barrier);
      });
    }

    // 4. Illuminated Attack Path Trace
    if ((traceAttackPath || attackPath.length > 0) && layers.suspiciousTraffic) {
      const tracePoints = [
        new THREE.Vector3(-28.0, 0.8, -16.0), // Rogue Camera
        new THREE.Vector3(-28.0, 14.5, -20.0), // gNodeB-01 Tower
        new THREE.Vector3(-14.0, 2.2, -10.0), // N3 Enforcement Barrier
        new THREE.Vector3(0.0, 3.5, -12.0), // UPF Data Center
      ];
      const traceCurve = new THREE.CatmullRomCurve3(tracePoints);
      const traceTubeGeo = new THREE.TubeGeometry(traceCurve, 32, 0.35, 8, false);
      const traceMat = new THREE.MeshBasicMaterial({
        color: 0xff0044,
        transparent: true,
        opacity: 0.92,
      });
      const traceTube = new THREE.Mesh(traceTubeGeo, traceMat);
      scene.add(traceTube);
    }

    // 5. Render 5G Network Slices (Translucent Pedestal Zones)
    slices.forEach((slice) => {
      const [zx, , zz] = mapCoord(slice.zone.x + slice.zone.width / 2, slice.zone.y + slice.zone.height / 2);
      const zw = slice.zone.width * 0.12;
      const zh = slice.zone.height * 0.12;

      const zoneGeo = new THREE.PlaneGeometry(zw, zh);
      const zoneMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(slice.color),
        transparent: true,
        opacity: 0.09,
        side: THREE.DoubleSide,
      });
      const zoneMesh = new THREE.Mesh(zoneGeo, zoneMat);
      zoneMesh.rotation.x = -Math.PI / 2;
      zoneMesh.position.set(zx, 0.06, zz);
      scene.add(zoneMesh);

      // Zone Luminous Border
      const edgeGeo = new THREE.EdgesGeometry(zoneGeo);
      const edgeMat = new THREE.LineBasicMaterial({
        color: new THREE.Color(slice.color),
        transparent: true,
        opacity: 0.6,
      });
      const edgeLine = new THREE.LineSegments(edgeGeo, edgeMat);
      edgeLine.rotation.x = -Math.PI / 2;
      edgeLine.position.set(zx, 0.07, zz);
      scene.add(edgeLine);
    });

    // 6. Realistic 5G Cellular Tower Builder Helper
    const towerWaveMeshes: THREE.Mesh[] = [];

    const buildCellularTower = (pos: THREE.Vector3, id: string, name: string, isAttacked: boolean, isSelected: boolean) => {
      const towerGroup = new THREE.Group();
      towerGroup.position.copy(pos);

      // Concrete foundation base
      const baseGeo = new THREE.BoxGeometry(4.5, 0.8, 4.5);
      const baseMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.7 });
      const baseMesh = new THREE.Mesh(baseGeo, baseMat);
      baseMesh.position.y = 0.4;
      baseMesh.castShadow = true;
      baseMesh.receiveShadow = true;
      towerGroup.add(baseMesh);

      // Base Equipment Cabinet / Shelter (Power + Fiber Breakout)
      const cabGeo = new THREE.BoxGeometry(2.0, 1.8, 1.6);
      const cabMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.6, roughness: 0.3 });
      const cabMesh = new THREE.Mesh(cabGeo, cabMat);
      cabMesh.position.set(1.2, 1.3, 1.2);
      cabMesh.castShadow = true;
      towerGroup.add(cabMesh);

      // Steel Lattice Mast (4 corner vertical columns + diagonal bracing)
      const mastHeight = 16.0;
      const legGeo = new THREE.CylinderGeometry(0.12, 0.16, mastHeight, 6);
      const steelMat = new THREE.MeshStandardMaterial({
        color: isAttacked ? 0xef4444 : isSelected ? 0x38bdf8 : 0x94a3b8,
        metalness: 0.85,
        roughness: 0.25,
      });

      const halfW = 1.0;
      const legPositions = [
        [-halfW, -halfW],
        [halfW, -halfW],
        [halfW, halfW],
        [-halfW, halfW],
      ];

      legPositions.forEach(([lx, lz]) => {
        const leg = new THREE.Mesh(legGeo, steelMat);
        leg.position.set(lx, mastHeight / 2 + 0.8, lz);
        leg.castShadow = true;
        towerGroup.add(leg);
      });

      // Horizontal and diagonal cross struts every 2 units
      const strutGeo = new THREE.BoxGeometry(halfW * 2, 0.08, 0.08);
      for (let h = 2.5; h < mastHeight; h += 2.2) {
        const strut1 = new THREE.Mesh(strutGeo, steelMat);
        strut1.position.set(0, h, halfW);
        towerGroup.add(strut1);

        const strut2 = new THREE.Mesh(strutGeo, steelMat);
        strut2.position.set(0, h, -halfW);
        towerGroup.add(strut2);
      }

      // Upper Maintenance Platform at masthead
      const platGeo = new THREE.CylinderGeometry(1.8, 1.4, 0.4, 8);
      const platMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.9, roughness: 0.2 });
      const platMesh = new THREE.Mesh(platGeo, platMat);
      platMesh.position.y = mastHeight + 0.8;
      towerGroup.add(platMesh);

      // Antenna Array Mount Head + 3 Sector Panel Antennas (120 deg apart)
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

        // Remote Radio Unit (RRU) box mounted behind panel
        const rruGeo = new THREE.BoxGeometry(0.3, 0.8, 0.5);
        const rruMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.7 });
        const rruMesh = new THREE.Mesh(rruGeo, rruMat);
        rruMesh.position.set(Math.cos(rad) * 0.9, mastHeight + 2.0, Math.sin(rad) * 0.9);
        towerGroup.add(rruMesh);
      }

      // Lightning Rod Tip with Flashing Beacon
      const rodGeo = new THREE.CylinderGeometry(0.04, 0.08, 2.5, 6);
      const rodMesh = new THREE.Mesh(rodGeo, steelMat);
      rodMesh.position.y = mastHeight + 3.8;
      towerGroup.add(rodMesh);

      const beaconGeo = new THREE.SphereGeometry(0.2, 8, 8);
      const beaconMat = new THREE.MeshBasicMaterial({ color: isAttacked ? 0xef4444 : 0x38bdf8 });
      const beaconMesh = new THREE.Mesh(beaconGeo, beaconMat);
      beaconMesh.position.y = mastHeight + 5.1;
      towerGroup.add(beaconMesh);

      // Concentric Pulsing RF Signal Waves
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
      waveMesh.userData = { isWave: true, baseScale: 1.0, maxScale: 4.5 };
      towerGroup.add(waveMesh);
      towerWaveMeshes.push(waveMesh);

      // Raycasting Hit Box (Covers whole tower)
      const hitBoxGeo = new THREE.CylinderGeometry(2.5, 2.5, mastHeight + 5, 8);
      const hitBoxMat = new THREE.MeshBasicMaterial({ transparent: true, opacity: 0.0, wireframe: false });
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

      scene.add(towerGroup);
    };

    // 7. Calculate Attack and Threat Scope from Single Source of Truth
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

    // Render Infrastructure Nodes & Technical Campus Buildings
    nodes.forEach((n) => {
      // Determine world position
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

      // Check if this node is one of the 4 RAN Towers
      if (n.type === 'ran') {
        buildCellularTower(pos, n.id, n.label, isUnderAttack, isSelected);
        return;
      }

      // Otherwise build architectural tech buildings or core function racks
      if (n.id === 'upf' || n.id === 'upf-01') {
        // High-Throughput Core User Plane Facility (UPF Building)
        const bGroup = new THREE.Group();
        bGroup.position.copy(pos);

        // Building Body
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
        bMesh.castShadow = true;
        bMesh.receiveShadow = true;
        bMesh.userData = { id: n.id, type: 'core_user', label: n.label, role: n.role, status: isUnderAttack ? 'CRITICAL' : 'Active' };
        bGroup.add(bMesh);
        interactiveMeshes.push(bMesh);

        // Glass Curtain Wall Accents
        const glassGeo = new THREE.PlaneGeometry(7.0, 3.5);
        const glassMat = new THREE.MeshBasicMaterial({ color: isUnderAttack ? 0xff4d4f : 0x38bdf8, transparent: true, opacity: 0.45 });
        const glassFront = new THREE.Mesh(glassGeo, glassMat);
        glassFront.position.set(0, 2.5, 4.55);
        bGroup.add(glassFront);

        // Rooftop HVAC Chiller units
        const hvacGeo = new THREE.BoxGeometry(2.0, 1.2, 2.0);
        const hvacMat = new THREE.MeshStandardMaterial({ color: 0x475569 });
        const hvac1 = new THREE.Mesh(hvacGeo, hvacMat);
        hvac1.position.set(-2.2, 5.6, -2.0);
        bGroup.add(hvac1);
        const hvac2 = new THREE.Mesh(hvacGeo, hvacMat);
        hvac2.position.set(2.2, 5.6, -2.0);
        bGroup.add(hvac2);

        // Rooftop Satellite Communication Dish
        const dishGeo = new THREE.SphereGeometry(1.2, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2);
        const dishMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, side: THREE.DoubleSide });
        const dish = new THREE.Mesh(dishGeo, dishMat);
        dish.position.set(0, 6.2, 1.8);
        dish.rotation.x = -Math.PI / 4;
        bGroup.add(dish);

        // Pulsing status ring on roof
        const ringGeo = new THREE.RingGeometry(3.5, 3.8, 32);
        const ringMat = new THREE.MeshBasicMaterial({
          color: isUnderAttack ? 0xef4444 : 0x10b981,
          side: THREE.DoubleSide,
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = -Math.PI / 2;
        ring.position.y = 5.05;
        bGroup.add(ring);

        scene.add(bGroup);
      } else if (n.type === 'edge') {
        // Edge Computing Facility (MEC Micro Datacenter)
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
        eMesh.castShadow = true;
        eMesh.receiveShadow = true;
        eMesh.userData = { id: n.id, type: 'edge', label: n.label, role: n.role, status: 'Active' };
        eGroup.add(eMesh);
        interactiveMeshes.push(eMesh);

        // Edge Datacenter LED Vent Strip
        const ventGeo = new THREE.PlaneGeometry(5.0, 1.0);
        const ventMat = new THREE.MeshBasicMaterial({ color: 0x10b981, transparent: true, opacity: 0.85 });
        const vent = new THREE.Mesh(ventGeo, ventMat);
        vent.position.set(0, 2.0, 2.8);
        eGroup.add(vent);

        scene.add(eGroup);
      } else if (n.type === 'gateway' || n.type === 'switch') {
        // Perimeter Gateway / Core Switch Infrastructure
        const gGroup = new THREE.Group();
        gGroup.position.copy(pos);

        const gGeo = new THREE.BoxGeometry(5.5, 3.2, 4.5);
        const gMat = new THREE.MeshStandardMaterial({
          color: isSelected ? 0x38bdf8 : isUnderAttack ? 0xf59e0b : 0x334155,
          roughness: 0.4,
          metalness: 0.6,
        });
        const gMesh = new THREE.Mesh(gGeo, gMat);
        gMesh.position.y = 1.6;
        gMesh.castShadow = true;
        gMesh.receiveShadow = true;
        gMesh.userData = { id: n.id, type: n.type, label: n.label, role: n.role, status: 'Active' };
        gGroup.add(gMesh);
        interactiveMeshes.push(gMesh);

        scene.add(gGroup);
      } else {
        // 5G Core Control Plane Server Blade (AMF, SMF, UDM, AUSF, etc.)
        const cGeo = new THREE.BoxGeometry(2.4, 2.8, 1.8);
        const cMat = new THREE.MeshStandardMaterial({
          color: isSelected ? 0x38bdf8 : 0x0284c7,
          roughness: 0.3,
          metalness: 0.7,
          emissive: isSelected ? 0x0284c7 : 0x0369a1,
          emissiveIntensity: isSelected ? 0.8 : 0.25,
        });
        const cMesh = new THREE.Mesh(cGeo, cMat);
        cMesh.position.copy(pos);
        cMesh.position.y = 1.4;
        cMesh.castShadow = true;
        cMesh.userData = { id: n.id, type: 'core_control', label: n.label, role: n.role, status: 'Active' };
        scene.add(cMesh);
        interactiveMeshes.push(cMesh);

        // Blinking Status LED
        const ledGeo = new THREE.SphereGeometry(0.12, 6, 6);
        const ledMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });
        const led = new THREE.Mesh(ledGeo, ledMat);
        led.position.set(pos.x, 2.2, pos.z + 0.95);
        scene.add(led);
      }
    });

    // 8. Render Connected UE Devices (Cameras, AGVs, Sensors)
    devices.forEach((d) => {
      if (!d.visible) return;
      const [dx, dy, dz] = mapCoord(d.x, d.y, 0.6);
      const dPos = new THREE.Vector3(dx, dy, dz);

      const isQuarantined = d.action === 'quarantine' || d.verdict === 'quarantined';
      const isAttack = d.verdict === 'attack';
      const isSelected = selectedId === d.id;

      const devColor = isQuarantined
        ? 0x8b5cf6
        : isAttack
        ? 0xef4444
        : 0x10b981;

      let devGeo: THREE.BufferGeometry;
      if (d.device_class === 'camera') {
        // High-definition surveillance camera pole & housing
        devGeo = new THREE.BoxGeometry(1.2, 0.9, 1.2);
      } else if (d.device_class === 'AGV') {
        // Sleek autonomous robot rover
        devGeo = new THREE.BoxGeometry(1.8, 0.7, 1.3);
      } else {
        // Cylindrical telemetry sensor pod
        devGeo = new THREE.CylinderGeometry(0.6, 0.6, 1.0, 8);
      }

      const devMat = new THREE.MeshStandardMaterial({
        color: isSelected ? 0xffffff : devColor,
        roughness: 0.4,
        metalness: 0.5,
        emissive: isSelected ? 0x38bdf8 : devColor,
        emissiveIntensity: isSelected || isAttack ? 0.85 : 0.25,
      });

      const devMesh = new THREE.Mesh(devGeo, devMat);
      devMesh.position.copy(dPos);
      devMesh.castShadow = true;
      devMesh.userData = {
        id: d.id,
        type: 'device',
        label: d.id,
        role: `${d.device_class.toUpperCase()} (Serving: ${d.servingGnb || 'gNB-01'})`,
        status: d.status_label,
      };
      scene.add(devMesh);
      interactiveMeshes.push(devMesh);

      // Quarantine Barrier Wireframe Cage if isolated
      if (isQuarantined) {
        const barrierGeo = new THREE.CylinderGeometry(1.8, 1.8, 2.5, 16, 1, true);
        const barrierMat = new THREE.MeshBasicMaterial({
          color: 0x8b5cf6,
          wireframe: true,
          transparent: true,
          opacity: 0.8,
        });
        const barrier = new THREE.Mesh(barrierGeo, barrierMat);
        barrier.position.copy(dPos);
        scene.add(barrier);
      }
    });

    // 9. Render Live Network Links & Active Conduits
    const linkPairs: Array<{
      start: THREE.Vector3;
      end: THREE.Vector3;
      color: number;
      speed: number;
      isAttack: boolean;
      isIsolated: boolean;
    }> = [];

    links.forEach((l) => {
      const sPos = nodePositionMap.get(l.source);
      const tPos = nodePositionMap.get(l.target);
      if (!sPos || !tPos) return;

      const isAttackLink = (attackPath.includes(l.source) && attackPath.includes(l.target)) ||
                           (l.source === 'gnb-01' && l.target === 'upf' && attackPath.length > 0);
      const isIsolated = mitigationActive && (l.source === 'gnb-01' || l.target === 'gnb-01');

      let linkColor = 0x38bdf8; // Default Control Plane Cyan
      if (isAttackLink) {
        linkColor = 0xef4444; // Red
      } else if (isIsolated) {
        linkColor = 0x8b5cf6; // Purple
      } else if (l.type === 'user_plane') {
        linkColor = 0x10b981; // Green
      } else if (l.type === 'edge') {
        linkColor = 0x6366f1; // Indigo
      }

      // 3D Tube / Beam conduit
      const curve = new THREE.LineCurve3(
        new THREE.Vector3(sPos.x, Math.max(1.0, sPos.y), sPos.z),
        new THREE.Vector3(tPos.x, Math.max(1.0, tPos.y), tPos.z)
      );

      const tubeGeo = new THREE.TubeGeometry(curve, 12, isAttackLink ? 0.22 : 0.12, 6, false);
      const tubeMat = new THREE.MeshBasicMaterial({
        color: linkColor,
        transparent: true,
        opacity: isAttackLink ? 0.95 : isIsolated ? 0.25 : 0.65,
      });
      const tube = new THREE.Mesh(tubeGeo, tubeMat);
      scene.add(tube);

      linkPairs.push({
        start: curve.v1.clone(),
        end: curve.v2.clone(),
        color: linkColor,
        speed: isAttackLink ? 0.035 : l.type === 'user_plane' ? 0.022 : 0.014,
        isAttack: isAttackLink,
        isIsolated,
      });
    });

    // 10. Live Packet & Traffic Simulation Particles
    // High-performance instanced packet particles with clamped particle count
    const particleCount = attackPath.length > 0 ? 96 : 48;
    const maxParticles = particleCount;
    const packetGeo = new THREE.SphereGeometry(0.32, 8, 8);
    const packetList: Array<{
      mesh: THREE.Mesh;
      pair: typeof linkPairs[0];
      progress: number;
    }> = [];

    for (let i = 0; i < maxParticles; i++) {
      if (linkPairs.length === 0) break;
      const pair = linkPairs[i % linkPairs.length];
      const pMat = new THREE.MeshBasicMaterial({
        color: pair.color,
        transparent: true,
        opacity: 0.9,
      });
      const pMesh = new THREE.Mesh(packetGeo, pMat);
      scene.add(pMesh);
      packetList.push({
        mesh: pMesh,
        pair,
        progress: (i / maxParticles),
      });
    }

    // 11. Raycasting for Component Selection & Tooltip Hover
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const handlePointerMove = (e: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(interactiveMeshes);

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
      const intersects = raycaster.intersectObjects(interactiveMeshes);
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

    // 12. Smooth Animation Loop
    const animate = () => {
      controls.update();

      // Smooth camera interpolation towards target presets only when triggered
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

      // Animate Tower Signal Waves
      towerWaveMeshes.forEach((w) => {
        const s = (w.scale.x + 0.02) % 3.5;
        w.scale.set(s, s, s);
        (w.material as THREE.MeshBasicMaterial).opacity = Math.max(0.0, 0.7 - s / 3.5);
      });

      // Animate CommShield AI Detection Engine (Spin & Bob)
      if (aiEngineMesh) {
        aiEngineMesh.rotation.y += 0.02;
        aiEngineMesh.rotation.z = Math.sin(Date.now() * 0.002) * 0.15;
        aiEngineMesh.position.y = 9.5 + Math.sin(Date.now() * 0.003) * 0.4;
      }

      // Animate Security Probes & Enforcement Gateways
      sensorWaveMeshes.forEach((s, idx) => {
        s.rotation.z += 0.015 * (idx % 2 === 0 ? 1 : -1);
      });
      enforcementMeshes.forEach((b) => {
        b.rotation.y += 0.01;
      });

      // Move packet particles along conduits (Dual stream: cyan legitimate continues vs red attack dropped at barrier)
      packetList.forEach((p) => {
        if (p.pair.isAttack && mitigationActive) {
          // Drop and filter malicious traffic at the N3 Enforcement Gateway (halt at 0.42 progress)
          p.mesh.position.lerpVectors(p.pair.start, p.pair.end, 0.42);
          (p.mesh.material as THREE.MeshBasicMaterial).opacity = 0.3 + Math.sin(Date.now() * 0.01) * 0.25;
        } else if (p.pair.isIsolated) {
          // Quarantined device link halted
          p.mesh.position.lerpVectors(p.pair.start, p.pair.end, 0.2);
        } else {
          // Legitimate traffic continues unobstructed
          p.progress = (p.progress + p.pair.speed) % 1.0;
          p.mesh.position.lerpVectors(p.pair.start, p.pair.end, p.progress);
          (p.mesh.material as THREE.MeshBasicMaterial).opacity = 0.9;
        }
      });

      renderer.render(scene, camera);
      animFrameId.current = requestAnimationFrame(animate);
    };

    animFrameId.current = requestAnimationFrame(animate);

    // 13. Dynamic ResizeObserver for Fluid Viewport
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
      const h = container.clientHeight || 580;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    // 14. Explicit Resource Disposal
    return () => {
      if (animFrameId.current) cancelAnimationFrame(animFrameId.current);
      resizeObserver.disconnect();
      window.removeEventListener('resize', handleResize);
      domElement.removeEventListener('pointermove', handlePointerMove);
      domElement.removeEventListener('click', handleClick);
      controls.dispose();

      scene.traverse((obj: THREE.Object3D) => {
        if (obj instanceof THREE.Mesh) {
          if (obj.geometry) obj.geometry.dispose();
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m: THREE.Material) => m.dispose());
          } else if (obj.material) {
            obj.material.dispose();
          }
        }
      });

      renderer.dispose();
      if (container.contains(domElement)) {
        container.removeChild(domElement);
      }
    };
  }, [nodes, links, slices, devices, selectedId, attackPath, attackPaths, attackerSources, isDistributed, attackType, mitigationActive, reducedMotion, traceAttackPath, lifecycleState, layers]);

  return (
    <div className="w-full h-full relative rounded-xl overflow-hidden shadow-2xl bg-[#08101e] border border-slate-800">
      {/* Three.js Canvas Container */}
      <div ref={mountRef} className="w-full h-full" style={{ minHeight: '580px' }} />

      {/* Floating HUD: Camera Preset & Navigation Controls */}
      <div className="absolute top-4 left-4 z-10 flex flex-wrap items-center gap-1.5 bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-700/60 shadow-lg text-xs">
        <span className="text-slate-400 font-medium mr-1 flex items-center">
          <Camera className="w-3.5 h-3.5 mr-1 text-sky-400" /> View:
        </span>
        {[
          { id: 'full', label: 'Full Campus', icon: Eye },
          { id: 'ran', label: 'Towers', icon: Zap },
          { id: 'core', label: 'Core', icon: Cpu },
          { id: 'edge', label: 'MEC', icon: Activity },
          { id: 'attack', label: 'Attack Focus', icon: ShieldAlert },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => applyCameraPreset(id)}
            className={`px-2 py-1 rounded flex items-center space-x-1 transition-all ${
              currentPreset === id
                ? 'bg-sky-600 text-white font-medium shadow-sm'
                : 'text-slate-300 hover:bg-slate-800 hover:text-white'
            }`}
          >
            <Icon className="w-3 h-3" />
            <span>{label}</span>
          </button>
        ))}

        <div className="h-4 w-px bg-slate-700/70 mx-1" />

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
          onClick={() => handleManualZoom(-12)}
          title="Zoom In"
          className="p-1 rounded text-slate-300 hover:bg-slate-800 hover:text-white"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => handleManualZoom(12)}
          title="Zoom Out"
          className="p-1 rounded text-slate-300 hover:bg-slate-800 hover:text-white"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleFitNetwork}
          title="Fit Entire Network"
          className="px-2 py-1 rounded text-sky-400 bg-sky-950/60 border border-sky-800/60 hover:bg-sky-900/80 flex items-center space-x-1 font-medium"
        >
          <Maximize2 className="w-3 h-3" />
          <span>Fit Network</span>
        </button>
      </div>

      {/* Floating HUD: 8-Layer Visibility Controls */}
      <div className="absolute top-4 right-4 z-10 hidden md:flex flex-wrap items-center gap-1 bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-700/60 shadow-lg text-xs max-w-lg justify-end">
        <span className="text-slate-400 font-medium mr-1 text-[11px]">3D Layers:</span>
        {[
          { key: 'physical', label: 'Physical' },
          { key: 'connectivity', label: 'Conduits' },
          { key: 'security', label: 'Security Fabric' },
          { key: 'legitimateTraffic', label: 'Legitimate (Cyan)' },
          { key: 'suspiciousTraffic', label: 'Suspicious (Red)' },
          { key: 'enforcementPoints', label: 'Enforcement Gateways' },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => toggleLayer(key as keyof typeof layers)}
            className={`px-2 py-0.5 rounded text-[11px] transition-all ${
              layers[key as keyof typeof layers]
                ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/50 font-medium'
                : 'bg-slate-800 text-slate-500 border border-slate-700/50'
            }`}
          >
            {label}
          </button>
        ))}
        <button
          onClick={toggleAllLayers}
          className="px-2 py-0.5 rounded text-[11px] bg-sky-950 text-sky-400 border border-sky-700/60 font-medium hover:bg-sky-900 ml-1"
        >
          All Layers
        </button>
      </div>

      {/* Floating Navigation Tip */}
      <div className="absolute bottom-4 left-4 z-10 text-[11px] text-slate-400 bg-slate-950/70 backdrop-blur-sm px-2.5 py-1 rounded border border-slate-800 pointer-events-none">
        Left Click: Rotate • Right Click: Pan • Scroll: Zoom • Click Object: Inspect & Focus
      </div>
    </div>
  );
};
