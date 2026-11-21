import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { TwinDevice, TwinLink, TwinNode, TwinSlice } from '../services/twinApi';

interface ThreeTwinSceneProps {
  nodes: TwinNode[];
  links: TwinLink[];
  slices: TwinSlice[];
  devices: TwinDevice[];
  selectedId: string | null;
  onSelect: (id: string | null, type: 'node' | 'device' | null) => void;
  onHover: (item: { id: string; name: string; type: string; status: string } | null) => void;
  attackPath?: string[];
  mitigationActive?: boolean;
  reducedMotion?: boolean;
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
  mitigationActive = false,
  reducedMotion = false,
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const animFrameId = useRef<number | null>(null);

  // Map 2D coordinates into 3D world coordinates
  const mapCoord = (x: number, y: number, zBase: number = 0): [number, number, number] => {
    // Canvas dimensions are 880 x 500, map to approx [-44, 44] and [-25, 25]
    const worldX = (x - 440) * 0.12;
    const worldZ = (y - 250) * 0.12;
    return [worldX, zBase, worldZ];
  };

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // 1. Scene, Camera, Renderer Setup
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 560;

    const scene = new THREE.Scene();
    sceneRef.current = scene;
    scene.background = new THREE.Color(0x0a1628);
    scene.fog = new THREE.FogExp2(0x0a1628, 0.008);

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 52, 68);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
    rendererRef.current = renderer;
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // 2. Lighting Setup
    const ambientLight = new THREE.AmbientLight(0xdbe1ff, 0.7);
    scene.add(ambientLight);

    const dirLight1 = new THREE.DirectionalLight(0x38bdf8, 1.2);
    dirLight1.position.set(30, 60, 40);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x818cf8, 0.6);
    dirLight2.position.set(-30, 40, -30);
    scene.add(dirLight2);

    // 3. Grid Floor / Pedestal
    const gridHelper = new THREE.GridHelper(100, 40, 0x1e3a8a, 0x111e38);
    gridHelper.position.y = -0.1;
    scene.add(gridHelper);

    // Subtle Outer Floor Boundary Ring
    const borderGeo = new THREE.RingGeometry(48, 48.5, 64);
    const borderMat = new THREE.MeshBasicMaterial({ color: 0x1e293b, side: THREE.DoubleSide });
    const borderMesh = new THREE.Mesh(borderGeo, borderMat);
    borderMesh.rotation.x = -Math.PI / 2;
    borderMesh.position.y = -0.05;
    scene.add(borderMesh);

    // 4. Interactive Object Containers
    const interactiveMeshes: THREE.Mesh[] = [];
    const nodePositionMap = new Map<string, THREE.Vector3>();

    // A. Render Slice Zones (Translucent Pedestals)
    slices.forEach((slice) => {
      const [zx, , zz] = mapCoord(slice.zone.x + slice.zone.width / 2, slice.zone.y + slice.zone.height / 2);
      const zw = slice.zone.width * 0.12;
      const zh = slice.zone.height * 0.12;

      const zoneGeo = new THREE.PlaneGeometry(zw, zh);
      const zoneMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(slice.color),
        transparent: true,
        opacity: 0.08,
        side: THREE.DoubleSide,
      });
      const zoneMesh = new THREE.Mesh(zoneGeo, zoneMat);
      zoneMesh.rotation.x = -Math.PI / 2;
      zoneMesh.position.set(zx, 0.02, zz);
      scene.add(zoneMesh);

      // Zone Outline
      const edgeGeo = new THREE.EdgesGeometry(zoneGeo);
      const edgeMat = new THREE.LineBasicMaterial({ color: new THREE.Color(slice.color), transparent: true, opacity: 0.4 });
      const edgeLine = new THREE.LineSegments(edgeGeo, edgeMat);
      edgeLine.rotation.x = -Math.PI / 2;
      edgeLine.position.set(zx, 0.03, zz);
      scene.add(edgeLine);
    });

    // B. Render Core Infrastructure Nodes (gNodeB, AMF, SMF, UPF)
    nodes.forEach((n) => {
      const [nx, ny, nz] = mapCoord(n.x, n.y, 1.5);
      const pos = new THREE.Vector3(nx, ny, nz);
      nodePositionMap.set(n.id, pos);

      const isRAN = n.type === 'ran';
      const isUPF = n.id === 'upf';
      const nodeColor = isRAN ? 0x0284c7 : isUPF ? 0x10b981 : 0x3b82f6;

      let geo: THREE.BufferGeometry;
      if (isRAN) {
        // Slim base-station tower / cylinder
        geo = new THREE.CylinderGeometry(0.8, 1.4, 4.5, 8);
      } else {
        // Glowing Core Cube
        geo = new THREE.BoxGeometry(3.2, 2.4, 3.2);
      }

      const isSelected = selectedId === n.id;
      const isUnderAttack = attackPath.includes(n.id);

      const mat = new THREE.MeshStandardMaterial({
        color: isUnderAttack ? 0xef4444 : isSelected ? 0xffffff : nodeColor,
        roughness: 0.3,
        metalness: 0.6,
        emissive: isUnderAttack ? 0x991b1b : isSelected ? 0x2563eb : nodeColor,
        emissiveIntensity: isSelected || isUnderAttack ? 0.6 : 0.2,
      });

      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.copy(pos);
      mesh.userData = { id: n.id, type: 'node', label: n.label, role: n.role, status: 'Active' };
      scene.add(mesh);
      interactiveMeshes.push(mesh);

      // Pulsing Base Ring
      const ringGeo = new THREE.RingGeometry(2.2, 2.5, 32);
      const ringMat = new THREE.MeshBasicMaterial({
        color: isUnderAttack ? 0xef4444 : nodeColor,
        transparent: true,
        opacity: 0.6,
        side: THREE.DoubleSide,
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = -Math.PI / 2;
      ring.position.set(nx, 0.05, nz);
      scene.add(ring);
    });

    // C. Render Network Links & Connecting Beams
    const linkPairs: Array<{ start: THREE.Vector3; end: THREE.Vector3; color: number; speed: number }> = [];

    links.forEach((l) => {
      const sPos = nodePositionMap.get(l.source);
      const tPos = nodePositionMap.get(l.target);
      if (!sPos || !tPos) return;

      const isAttackLink = attackPath.includes(l.source) && attackPath.includes(l.target);
      const linkColor = isAttackLink ? 0xef4444 : l.type === 'user_plane' ? 0x10b981 : 0x38bdf8;

      const lineMat = new THREE.LineBasicMaterial({
        color: linkColor,
        transparent: true,
        opacity: isAttackLink ? 0.9 : 0.6,
        linewidth: 2,
      });

      const lineGeo = new THREE.BufferGeometry().setFromPoints([sPos, tPos]);
      const line = new THREE.Line(lineGeo, lineMat);
      scene.add(line);

      linkPairs.push({
        start: sPos.clone(),
        end: tPos.clone(),
        color: linkColor,
        speed: l.type === 'user_plane' ? 0.025 : 0.015,
      });
    });

    // Uplinks from Slice Zones to gNodeB
    const gnbPos = nodePositionMap.get('gnb');
    if (gnbPos) {
      slices.forEach((s) => {
        const [zx, , zz] = mapCoord(s.zone.x + s.zone.width - 10, s.zone.y + s.zone.height / 2, 0.5);
        const zPos = new THREE.Vector3(zx, 0.5, zz);
        const upMat = new THREE.LineDashedMaterial({
          color: 0x475569,
          dashSize: 1,
          gapSize: 0.8,
          transparent: true,
          opacity: 0.5,
        });
        const upGeo = new THREE.BufferGeometry().setFromPoints([zPos, gnbPos]);
        const upLine = new THREE.Line(upGeo, upMat);
        upLine.computeLineDistances();
        scene.add(upLine);
      });
    }

    // D. Render Slice Devices (Cameras, AGVs, Sensors)
    devices.forEach((d) => {
      if (!d.visible) return;
      const [dx, dy, dz] = mapCoord(d.x, d.y, 0.6);
      const dPos = new THREE.Vector3(dx, dy, dz);

      const isQuarantined = d.action === 'quarantine' || d.verdict === 'quarantined';
      const isAttack = d.verdict === 'attack';
      const isUncertain = d.verdict === 'uncertain';
      const isSelected = selectedId === d.id;

      const devColor = isQuarantined
        ? 0x8b5cf6
        : isAttack
        ? 0xef4444
        : isUncertain
        ? 0xf59e0b
        : 0x10b981;

      let devGeo: THREE.BufferGeometry;
      if (d.device_class === 'camera') {
        // Small optical cube
        devGeo = new THREE.BoxGeometry(1.2, 1.0, 1.2);
      } else if (d.device_class === 'AGV') {
        // Low robotic rover box
        devGeo = new THREE.BoxGeometry(1.8, 0.8, 1.2);
      } else {
        // Cylindrical sensor node
        devGeo = new THREE.CylinderGeometry(0.6, 0.6, 1.0, 8);
      }

      const devMat = new THREE.MeshStandardMaterial({
        color: isSelected ? 0xffffff : devColor,
        roughness: 0.4,
        metalness: 0.5,
        emissive: isSelected ? 0x38bdf8 : devColor,
        emissiveIntensity: isSelected || isAttack ? 0.8 : 0.25,
      });

      const devMesh = new THREE.Mesh(devGeo, devMat);
      devMesh.position.copy(dPos);
      devMesh.userData = {
        id: d.id,
        type: 'device',
        label: d.id,
        role: `${d.device_class.toUpperCase()} (${d.slice_id})`,
        status: d.status_label,
      };
      scene.add(devMesh);
      interactiveMeshes.push(devMesh);

      // Quarantine Barrier Cylinder if isolated
      if (isQuarantined) {
        const barrierGeo = new THREE.CylinderGeometry(1.6, 1.6, 2.2, 16, 1, true);
        const barrierMat = new THREE.MeshBasicMaterial({
          color: 0x8b5cf6,
          wireframe: true,
          transparent: true,
          opacity: 0.7,
        });
        const barrierMesh = new THREE.Mesh(barrierGeo, barrierMat);
        barrierMesh.position.copy(dPos);
        scene.add(barrierMesh);
      }
    });

    // E. Traffic Flow Particles (Capped at 12 particles max for high performance)
    const particleCount = Math.min(12, linkPairs.length * 2);
    const particleGeo = new THREE.SphereGeometry(0.35, 8, 8);
    const particles: Array<{ mesh: THREE.Mesh; pair: typeof linkPairs[0]; progress: number }> = [];

    for (let i = 0; i < particleCount; i++) {
      const pair = linkPairs[i % linkPairs.length];
      const pMat = new THREE.MeshBasicMaterial({
        color: pair.color,
        transparent: true,
        opacity: 0.85,
      });
      const pMesh = new THREE.Mesh(particleGeo, pMat);
      scene.add(pMesh);
      particles.push({
        mesh: pMesh,
        pair,
        progress: (i / particleCount),
      });
    }

    // 5. Raycasting for Hover & Click Selection
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
          name: hit.userData.label,
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

    // 6. Smooth Animation Loop
    const animate = () => {
      const now = performance.now();

      // Update particle positions along links
      if (!reducedMotion) {
        particles.forEach((p) => {
          p.progress = (p.progress + p.pair.speed * (mitigationActive ? 0.4 : 1.0)) % 1.0;
          p.mesh.position.lerpVectors(p.pair.start, p.pair.end, p.progress);
        });

        // Gentle camera orbit if idle
        if (!selectedId) {
          const orbitAngle = now * 0.00015;
          camera.position.x = Math.sin(orbitAngle) * 65;
          camera.position.z = Math.cos(orbitAngle) * 65;
          camera.lookAt(0, 0, 0);
        }
      }

      renderer.render(scene, camera);
      animFrameId.current = requestAnimationFrame(animate);
    };

    animFrameId.current = requestAnimationFrame(animate);

    // 7. Resize Handler
    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth || 800;
      const h = container.clientHeight || 560;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    // 8. Explicit Cleanup on Unmount
    return () => {
      if (animFrameId.current) cancelAnimationFrame(animFrameId.current);
      window.removeEventListener('resize', handleResize);
      domElement.removeEventListener('pointermove', handlePointerMove);
      domElement.removeEventListener('click', handleClick);

      // Dispose Three.js objects
      scene.traverse((obj) => {
        if (obj instanceof THREE.Mesh) {
          if (obj.geometry) obj.geometry.dispose();
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => m.dispose());
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
  }, [nodes, links, slices, devices, selectedId, attackPath, mitigationActive, reducedMotion]);

  return (
    <div
      ref={mountRef}
      className="w-full h-full relative rounded-xl overflow-hidden shadow-2xl bg-[#0a1628]"
      style={{ minHeight: '560px' }}
    />
  );
};
