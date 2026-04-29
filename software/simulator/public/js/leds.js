import * as THREE from 'three';

// ── Grid constants (from assembly.scad) ────────────────────
const GRID = 44;
const PITCH = 50; // mm
const SPAN = (GRID - 1) * PITCH; // 2150mm
const OFFSET = -SPAN / 2; // -1075mm
const TOTAL = GRID * GRID; // 1936
const PLY = 19;
const JOIST_H = 89; // 2x4 subfloor height
const HALF = GRID / 2; // 22 — columns per channel

// ── Simple row-major mapping ────────────────────────────────
// WLED handles serpentine/panel remapping internally.
function linearToGrid(index) {
  return [Math.floor(index / GRID), index % GRID];
}

const gridPositions = new Array(TOTAL);
for (let i = 0; i < TOTAL; i++) {
  gridPositions[i] = linearToGrid(i);
}

// ── LED InstancedMesh ──────────────────────────────────────
export function createLedSystem(scene) {
  const dummy = new THREE.Object3D();

  const ledGeo = new THREE.SphereGeometry(15, 8, 6);
  const ledMat = new THREE.MeshBasicMaterial({
    color: 0xffffff,
    toneMapped: false,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });

  const mesh = new THREE.InstancedMesh(ledGeo, ledMat, TOTAL);
  mesh.instanceMatrix.setUsage(THREE.StaticDrawUsage);
  const colorArray = new Float32Array(TOTAL * 3);
  mesh.instanceColor = new THREE.InstancedBufferAttribute(colorArray, 3);

  for (let i = 0; i < TOTAL; i++) {
    const [row, col] = gridPositions[i];
    dummy.position.set(
      OFFSET + col * PITCH,
      JOIST_H + PLY - 2,
      OFFSET + row * PITCH
    );
    dummy.updateMatrix();
    mesh.setMatrixAt(i, dummy.matrix);
    mesh.setColorAt(i, new THREE.Color(0, 0, 0));
  }

  mesh.instanceMatrix.needsUpdate = true;
  mesh.instanceColor.needsUpdate = true;
  mesh.renderOrder = 1;
  scene.add(mesh);

  const tempColor = new THREE.Color();

  return {
    TOTAL,
    GRID,
    PITCH,
    OFFSET,
    mesh,
    gridPositions,
    HALF,

    setLedColor(index, r, g, b) {
      tempColor.setRGB(r / 255, g / 255, b / 255);
      mesh.setColorAt(index, tempColor);
    },

    applyFrame(buffer) {
      for (let i = 0; i < TOTAL; i++) {
        const off = i * 3;
        tempColor.setRGB(buffer[off] / 255, buffer[off + 1] / 255, buffer[off + 2] / 255);
        mesh.setColorAt(i, tempColor);
      }
      mesh.instanceColor.needsUpdate = true;
    },

    flush() {
      mesh.instanceColor.needsUpdate = true;
    },
  };
}
