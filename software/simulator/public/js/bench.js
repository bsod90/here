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

  // ── Seated figure — 5'7" (1700mm) genderless grey person ──
  // Thinking pose: leaning forward, head tilted down, elbows on knees
  const seatY = slabBottomY + SLAB_H; // top of slab
  const floorY = JOIST_H + PLY + 3;
  const skinMat = new THREE.MeshStandardMaterial({
    color: 0x777777,
    roughness: 0.7,
    metalness: 0.1,
  });

  const person = new THREE.Group();
  const lean = 0.35;
  const hipZ = 0;

  const torso = new THREE.Mesh(new THREE.BoxGeometry(140, 400, 160), skinMat);
  torso.position.set(0, seatY + 220, hipZ + 50);
  torso.rotation.x = lean;
  torso.castShadow = true;
  person.add(torso);

  const neck = new THREE.Mesh(new THREE.CylinderGeometry(28, 35, 70, 8), skinMat);
  neck.position.set(0, seatY + 440, hipZ + 120);
  neck.rotation.x = lean + 0.15;
  person.add(neck);

  const head = new THREE.Mesh(new THREE.SphereGeometry(80, 10, 8), skinMat);
  head.position.set(0, seatY + 510, hipZ + 150);
  head.castShadow = true;
  person.add(head);

  const kneeZ = hipZ + 380;
  for (const side of [-1, 1]) {
    const thigh = new THREE.Mesh(new THREE.CylinderGeometry(45, 50, 430, 8), skinMat);
    thigh.position.set(side * 75, seatY - 10, hipZ + 190);
    thigh.rotation.x = Math.PI / 2 - 0.15;
    thigh.castShadow = true;
    person.add(thigh);
  }

  const kneeY = seatY - 40;
  const ankleY = floorY + 60;
  const shinLen = kneeY - ankleY;
  for (const side of [-1, 1]) {
    const shin = new THREE.Mesh(new THREE.CylinderGeometry(38, 35, shinLen, 8), skinMat);
    shin.position.set(side * 75, (kneeY + ankleY) / 2, kneeZ + 20);
    shin.rotation.x = 0.08;
    shin.castShadow = true;
    person.add(shin);
  }

  for (const side of [-1, 1]) {
    const foot = new THREE.Mesh(new THREE.BoxGeometry(80, 45, 180), skinMat);
    foot.position.set(side * 75, floorY + 22, kneeZ + 60);
    foot.castShadow = true;
    person.add(foot);
  }

  for (const side of [-1, 1]) {
    const upperArm = new THREE.Mesh(new THREE.CylinderGeometry(32, 30, 250, 8), skinMat);
    upperArm.position.set(side * 120, seatY + 260, hipZ + 140);
    upperArm.rotation.x = 0.8;
    upperArm.rotation.z = side * -0.25;
    upperArm.castShadow = true;
    person.add(upperArm);
  }

  for (const side of [-1, 1]) {
    const forearm = new THREE.Mesh(new THREE.CylinderGeometry(28, 25, 220, 8), skinMat);
    forearm.position.set(side * 55, seatY + 80, kneeZ - 60);
    forearm.rotation.x = 1.1;
    forearm.rotation.z = side * 0.35;
    forearm.castShadow = true;
    person.add(forearm);
  }

  const hands = new THREE.Mesh(new THREE.SphereGeometry(38, 8, 6), skinMat);
  hands.position.set(0, seatY + 30, kneeZ - 10);
  hands.castShadow = true;
  person.add(hands);

  group.add(person);

  group.position.z = BENCH_Z_OFFSET;
  let currentAngle = 0;
  group.rotation.y = currentAngle;

  return {
    group,
    get angle() { return currentAngle; },
    setAngle(angle) {
      currentAngle = angle;
      group.rotation.y = angle;
    },
  };
}
