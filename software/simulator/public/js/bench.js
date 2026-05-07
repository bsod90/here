import * as THREE from 'three';

// ── Dimensions from assembly.scad ──────────────────────────
const SLAB_L = 1524;       // 5ft
const SLAB_W = 305;        // 12in
const SLAB_H = 102;        // 4in glue-up
const PLY = 19;
const JOIST_H = 89;
const LEG_DIM = 89;        // 4×4 lumber
const LEG_H = 233;         // legs lowered by 1/3 (was 350)
const LEG_INSET = 250;
const BENCH_Z_OFFSET = -810;  // pushed toward back edge of platform

export function createBench() {
  const group = new THREE.Group();
  const loader = new THREE.TextureLoader();

  // OSB texture — used here as a stand-in for the layered plywood face.
  // The slab is shown a touch lighter to reflect the birch-faced glue-up.
  const osbTex = loader.load('assets/osb.jpg');
  osbTex.colorSpace = THREE.SRGBColorSpace;
  osbTex.wrapS = THREE.RepeatWrapping;
  osbTex.wrapT = THREE.RepeatWrapping;
  osbTex.repeat.set(2, 1);

  const slabMat = new THREE.MeshStandardMaterial({
    map: osbTex,
    color: 0xe6c89a,
    roughness: 0.8,
    metalness: 0.0,
  });

  const legTex = osbTex.clone();
  legTex.repeat.set(0.5, 1.5);
  const legMat = new THREE.MeshStandardMaterial({
    map: legTex,
    color: 0xc8a878,
    roughness: 0.85,
    metalness: 0.0,
  });

  const slabBottomY = JOIST_H + PLY + LEG_H;

  // ── Slab seat ──
  const slab = new THREE.Mesh(
    new THREE.BoxGeometry(SLAB_L, SLAB_H, SLAB_W),
    slabMat
  );
  slab.position.y = slabBottomY + SLAB_H / 2;
  slab.castShadow = true;
  slab.receiveShadow = true;
  group.add(slab);

  // ── Legs (4×4 lumber, span full slab width) ──
  const legGeo = new THREE.BoxGeometry(LEG_DIM, LEG_H, SLAB_W);
  for (const sx of [-1, 1]) {
    const leg = new THREE.Mesh(legGeo, legMat);
    leg.position.set(
      sx * (SLAB_L / 2 - LEG_INSET),
      JOIST_H + PLY + LEG_H / 2,
      0
    );
    leg.castShadow = true;
    leg.receiveShadow = true;
    group.add(leg);
  }

  // Bench is fixed parallel (long axis along world X) at the back of
  // the platform. Orientation is no longer user-toggleable.
  group.position.z = BENCH_Z_OFFSET;
  group.rotation.y = 0;

  return { group };
}
