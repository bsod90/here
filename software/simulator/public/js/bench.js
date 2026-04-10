import * as THREE from 'three';

// ── Dimensions from assembly.scad ──────────────────────────
const BENCH_L = 1219;  // 4ft
const BENCH_W = 300;   // 30cm
const BENCH_H = 350;   // 35cm
const PLY = 19;
const JOIST_H = 89;    // 2x4 subfloor height
const LEG_DIM = 89;    // 3.5" actual
const LEG_INSET = 250;
const BENCH_Z_OFFSET = -400;  // pushed toward back edge of platform

// Underglow
const CHAN_INSET = 80;
const UG_PITCH = 50;
const UG_STRIP_LEN = BENCH_L - 2 * PLY - 20;
const UG_COUNT_PER_STRIP = Math.floor(UG_STRIP_LEN / UG_PITCH);

function computeUnderglowPositions(angle) {
  const positions = [];
  const boxBottomY = JOIST_H + PLY + LEG_DIM;
  const ugY = boxBottomY; // flush with bench bottom
  const cosA = Math.cos(angle);
  const sinA = Math.sin(angle);

  for (const side of [-1, 1]) {
    const localZ = side * (BENCH_W / 2 - CHAN_INSET);
    for (let i = 0; i < UG_COUNT_PER_STRIP; i++) {
      const localX = -UG_STRIP_LEN / 2 + i * UG_PITCH + UG_PITCH / 2;
      const worldX = localX * cosA + localZ * sinA;
      const worldZ = -localX * sinA + localZ * cosA;
      positions.push(new THREE.Vector3(worldX, ugY, worldZ + BENCH_Z_OFFSET));
    }
  }
  return positions;
}

export function createBench() {
  const group = new THREE.Group();
  const loader = new THREE.TextureLoader();

  const osbTex = loader.load('assets/osb.jpg');
  osbTex.colorSpace = THREE.SRGBColorSpace;
  osbTex.wrapS = THREE.RepeatWrapping;
  osbTex.wrapT = THREE.RepeatWrapping;
  osbTex.repeat.set(2, 1);

  const woodMat = new THREE.MeshStandardMaterial({
    map: osbTex,
    roughness: 0.85,
    metalness: 0.0,
  });

  const osbTexLegs = osbTex.clone();
  osbTexLegs.repeat.set(0.5, 0.5);
  const darkWoodMat = new THREE.MeshStandardMaterial({
    map: osbTexLegs,
    color: 0xcccccc,
    roughness: 0.85,
    metalness: 0.0,
  });

  const boxBottomY = JOIST_H + PLY + LEG_DIM;

  // Box body
  const boxGeo = new THREE.BoxGeometry(BENCH_L, BENCH_H, BENCH_W);
  const box = new THREE.Mesh(boxGeo, woodMat);
  box.position.y = boxBottomY + BENCH_H / 2;
  box.castShadow = true;
  box.receiveShadow = true;
  group.add(box);

  // Legs
  const legGeo = new THREE.BoxGeometry(LEG_DIM, LEG_DIM, BENCH_W);
  for (const sx of [-1, 1]) {
    const leg = new THREE.Mesh(legGeo, darkWoodMat);
    leg.position.set(sx * (BENCH_L / 2 - LEG_INSET), JOIST_H + PLY + LEG_DIM / 2, 0);
    leg.castShadow = true;
    group.add(leg);
  }

  // ── Seated figure — 5'7" (1700mm) genderless grey person ──
  // Thinking pose: leaning forward, head tilted down, elbows on knees
  const seatY = boxBottomY + BENCH_H; // top of bench = 458mm
  const floorY = JOIST_H + PLY + 3; // platform surface (joists + plywood)
  const skinMat = new THREE.MeshStandardMaterial({
    color: 0x777777,
    roughness: 0.7,
    metalness: 0.1,
  });

  const person = new THREE.Group();

  // 5'7" seated proportions:
  // Torso (hips to shoulders): ~450mm
  // Head: ~150mm diameter
  // Thigh (hip to knee): ~430mm
  // Shin (knee to ankle): ~400mm
  // Foot: ~60mm tall, ~250mm long

  // Person sits centered on bench, facing +Z (front of bench)
  const lean = 0.35; // forward lean angle

  // Pelvis/hips — base reference on seat
  const hipZ = 0; // centered front-to-back on bench

  // Torso — leaned forward
  const torso = new THREE.Mesh(new THREE.BoxGeometry(140, 400, 160), skinMat);
  torso.position.set(0, seatY + 220, hipZ + 50);
  torso.rotation.x = lean;
  torso.castShadow = true;
  person.add(torso);

  // Neck
  const neck = new THREE.Mesh(new THREE.CylinderGeometry(28, 35, 70, 8), skinMat);
  neck.position.set(0, seatY + 440, hipZ + 120);
  neck.rotation.x = lean + 0.15;
  person.add(neck);

  // Head — tilted down, looking at floor
  const head = new THREE.Mesh(new THREE.SphereGeometry(80, 10, 8), skinMat);
  head.position.set(0, seatY + 510, hipZ + 150);
  head.castShadow = true;
  person.add(head);

  // Thighs — extend forward from hips, roughly horizontal
  const kneeZ = hipZ + 380; // knees are ~380mm forward of hips
  for (const side of [-1, 1]) {
    const thigh = new THREE.Mesh(new THREE.CylinderGeometry(45, 50, 430, 8), skinMat);
    thigh.position.set(side * 75, seatY - 10, hipZ + 190);
    thigh.rotation.x = Math.PI / 2 - 0.15; // nearly horizontal, slight downslope
    thigh.castShadow = true;
    person.add(thigh);
  }

  // Shins — hang down from knees to floor
  const kneeY = seatY - 40;
  const ankleY = floorY + 60; // ankle height
  const shinLen = kneeY - ankleY; // ~356mm
  for (const side of [-1, 1]) {
    const shin = new THREE.Mesh(new THREE.CylinderGeometry(38, 35, shinLen, 8), skinMat);
    shin.position.set(side * 75, (kneeY + ankleY) / 2, kneeZ + 20);
    shin.rotation.x = 0.08; // very slight forward angle
    shin.castShadow = true;
    person.add(shin);
  }

  // Feet — flat on platform
  for (const side of [-1, 1]) {
    const foot = new THREE.Mesh(new THREE.BoxGeometry(80, 45, 180), skinMat);
    foot.position.set(side * 75, floorY + 22, kneeZ + 60);
    foot.castShadow = true;
    person.add(foot);
  }

  // Upper arms — angled down from shoulders toward knees
  for (const side of [-1, 1]) {
    const upperArm = new THREE.Mesh(new THREE.CylinderGeometry(32, 30, 250, 8), skinMat);
    upperArm.position.set(side * 120, seatY + 260, hipZ + 140);
    upperArm.rotation.x = 0.8;
    upperArm.rotation.z = side * -0.25;
    upperArm.castShadow = true;
    person.add(upperArm);
  }

  // Forearms — resting on thighs/knees, angled inward
  for (const side of [-1, 1]) {
    const forearm = new THREE.Mesh(new THREE.CylinderGeometry(28, 25, 220, 8), skinMat);
    forearm.position.set(side * 55, seatY + 80, kneeZ - 60);
    forearm.rotation.x = 1.1;
    forearm.rotation.z = side * 0.35;
    forearm.castShadow = true;
    person.add(forearm);
  }

  // Hands — clasped together, resting between knees
  const hands = new THREE.Mesh(new THREE.SphereGeometry(38, 8, 6), skinMat);
  hands.position.set(0, seatY + 30, kneeZ - 10);
  hands.castShadow = true;
  person.add(hands);

  group.add(person);

  // Position: offset toward back edge, start parallel
  group.position.z = BENCH_Z_OFFSET;
  let currentAngle = 0;
  group.rotation.y = currentAngle;

  return {
    group,
    underglowPositions: computeUnderglowPositions(currentAngle),

    get angle() { return currentAngle; },

    setAngle(angle) {
      currentAngle = angle;
      group.rotation.y = angle;
      this.underglowPositions = computeUnderglowPositions(angle);
    },
  };
}
