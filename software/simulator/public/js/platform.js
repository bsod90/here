import * as THREE from 'three';

const PLATFORM_SIZE = 2438; // 8ft square
const PLY = 19;
const JOIST_W = 38;   // 2x4 actual: 1.5"
const JOIST_H = 89;   // 2x4 actual: 3.5"
const JOIST_INSET = 51; // 2" inset from platform edge

export function createPlatform() {
  const group = new THREE.Group();
  const loader = new THREE.TextureLoader();

  // ── Sky dome — desert night photo on a large sphere ──────
  const skyTex = loader.load('assets/desert-night.png');
  skyTex.colorSpace = THREE.SRGBColorSpace;
  const skyGeo = new THREE.SphereGeometry(10000, 32, 16);
  const skyMat = new THREE.MeshBasicMaterial({
    map: skyTex,
    side: THREE.BackSide, // render on inside of sphere
    fog: false,
  });
  const sky = new THREE.Mesh(skyGeo, skyMat);
  // Rotate so the horizon band sits at eye level
  sky.rotation.y = Math.PI * 0.3;
  group.add(sky);

  // ── White polycarbonate platform surface ─────────────────
  const platGeo = new THREE.PlaneGeometry(PLATFORM_SIZE, PLATFORM_SIZE);
  const platMat = new THREE.MeshStandardMaterial({
    color: 0x1a1a1a,
    roughness: 0.85,
    metalness: 0.0,
    transparent: true,
    opacity: 0.6,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  const platform = new THREE.Mesh(platGeo, platMat);
  platform.rotation.x = -Math.PI / 2;
  platform.position.y = JOIST_H + PLY + 3; // on top of joists + plywood + slight offset
  platform.renderOrder = 10;
  group.add(platform);

  // ── Platform edge (plywood thickness) ─────────────────────
  const edgeGeo = new THREE.BoxGeometry(PLATFORM_SIZE, PLY, PLATFORM_SIZE);
  const edgeMat = new THREE.MeshStandardMaterial({
    color: 0x888888,
    roughness: 0.8,
  });
  const edge = new THREE.Mesh(edgeGeo, edgeMat);
  edge.position.y = JOIST_H + PLY / 2; // sits on top of joists
  edge.castShadow = true;
  edge.receiveShadow = true;
  group.add(edge);

  // ── 2x4 subfloor joists ─────────────────────────────────
  const joistMat = new THREE.MeshStandardMaterial({
    color: 0x9a7d5a, // raw lumber color
    roughness: 0.9,
  });

  const joistSpan = PLATFORM_SIZE - 2 * JOIST_INSET;
  const joistCount = 7; // evenly spaced joists
  const joistGap = joistSpan / (joistCount - 1);

  for (let i = 0; i < joistCount; i++) {
    const joist = new THREE.Mesh(
      new THREE.BoxGeometry(PLATFORM_SIZE - 2 * JOIST_INSET, JOIST_H, JOIST_W),
      joistMat
    );
    const z = -joistSpan / 2 + i * joistGap;
    joist.position.set(0, JOIST_H / 2, z);
    joist.castShadow = true;
    joist.receiveShadow = true;
    group.add(joist);
  }

  // Perimeter rim joists (2 along each edge, inset 2")
  for (const axis of ['x', 'z']) {
    for (const side of [-1, 1]) {
      const rimJoist = new THREE.Mesh(
        new THREE.BoxGeometry(
          axis === 'x' ? JOIST_W : PLATFORM_SIZE - 2 * JOIST_INSET,
          JOIST_H,
          axis === 'z' ? JOIST_W : PLATFORM_SIZE - 2 * JOIST_INSET
        ),
        joistMat
      );
      const pos = side * (PLATFORM_SIZE / 2 - JOIST_INSET);
      rimJoist.position.set(
        axis === 'x' ? pos : 0,
        JOIST_H / 2,
        axis === 'z' ? pos : 0
      );
      rimJoist.castShadow = true;
      group.add(rimJoist);
    }
  }

  // ── Desert ground — cracked playa surface ─────────────────
  const playaTex = loader.load('assets/playa.png');
  playaTex.colorSpace = THREE.SRGBColorSpace;
  playaTex.wrapS = THREE.RepeatWrapping;
  playaTex.wrapT = THREE.RepeatWrapping;
  playaTex.repeat.set(8, 8);

  const groundGeo = new THREE.PlaneGeometry(16000, 16000);
  const groundMat = new THREE.MeshStandardMaterial({
    map: playaTex,
    color: 0x222222, // very dark — deep nighttime
    roughness: 0.95,
  });
  const ground = new THREE.Mesh(groundGeo, groundMat);
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -2;
  ground.receiveShadow = true;
  group.add(ground);

  return group;
}
