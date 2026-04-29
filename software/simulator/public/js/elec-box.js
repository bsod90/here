import * as THREE from 'three';

// ── Dimensions from assembly.scad ──────────────────────────
const ELEC_L = 870;        // fits 2 batteries end-to-end with margin
const ELEC_W = 350;        // battery width + side margin
const ELEC_H = 280;
const ELEC_OFFSET = 0;     // box stands directly against the platform edge
const SPK_DIA = 130;
const PLY = 19;

const PLATFORM_SIZE = 2438;
const BENCH_Z_OFFSET = -810; // matches BENCH_Z_OFFSET in bench.js

export function createElecBox() {
  const group = new THREE.Group();
  const loader = new THREE.TextureLoader();

  const osbTex = loader.load('assets/osb.jpg');
  osbTex.colorSpace = THREE.SRGBColorSpace;
  osbTex.wrapS = THREE.RepeatWrapping;
  osbTex.wrapT = THREE.RepeatWrapping;
  osbTex.repeat.set(1, 1);

  const boxMat = new THREE.MeshStandardMaterial({
    map: osbTex,
    color: 0xc8a564,
    roughness: 0.85,
    metalness: 0.0,
  });

  // Box body sits directly on the desert floor (no feet).
  const box = new THREE.Mesh(
    new THREE.BoxGeometry(ELEC_L, ELEC_H, ELEC_W),
    boxMat
  );
  box.position.y = ELEC_H / 2;
  box.castShadow = true;
  box.receiveShadow = true;
  group.add(box);

  // ── Speaker grilles on the +Z face (the face nearest the platform/bench) ──
  const grilleMat = new THREE.MeshStandardMaterial({
    color: 0x111111,
    roughness: 0.9,
    metalness: 0.2,
  });
  const grilleGeo = new THREE.CircleGeometry(SPK_DIA / 2, 24);

  const grilleZ = ELEC_W / 2 + 0.5; // a hair proud of the wall
  const grilleY = ELEC_H - SPK_DIA / 2 - 12; // near the top, matches SCAD spk_z
  for (const sx of [-1, 1]) {
    const grille = new THREE.Mesh(grilleGeo, grilleMat);
    grille.position.set(sx * (ELEC_L / 4), grilleY, grilleZ);
    // CircleGeometry faces +Z by default, which is exactly what we want.
    grille.castShadow = false;
    group.add(grille);
  }

  // Position the box on the west side of the platform:
  // — long axis runs along Z (parallel to the platform's west edge)
  // — centered along the edge (Z=0)
  // — the speaker face points in +X direction (toward the platform/bench)
  group.rotation.y = Math.PI / 2;
  group.position.x = -(PLATFORM_SIZE / 2 + ELEC_OFFSET + ELEC_W / 2);

  return {
    group,
    dims: { ELEC_L, ELEC_W, ELEC_H },
  };
}
