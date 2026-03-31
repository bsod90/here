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

// ── Serpentine mapping ─────────────────────────────────────
function linearToGrid(index) {
  const channel = index < GRID * HALF ? 0 : 1;
  const localIndex = index - channel * (GRID * HALF);
  const row = Math.floor(localIndex / HALF);
  let localCol = localIndex % HALF;
  if (row % 2 !== 0) localCol = HALF - 1 - localCol;
  const col = channel === 0 ? localCol : localCol + HALF;
  return [row, col];
}

// Pre-compute grid positions for each linear index
const gridPositions = new Array(TOTAL);
for (let i = 0; i < TOTAL; i++) {
  gridPositions[i] = linearToGrid(i);
}

// ── LED InstancedMesh ──────────────────────────────────────
export function createLedSystem(scene, underglowPositions, existingSystem) {
  const dummy = new THREE.Object3D();

  // ── Floor LEDs — reuse from existing system if available ──
  let mesh;
  if (existingSystem && existingSystem.mesh) {
    mesh = existingSystem.mesh;
  } else {
    const ledGeo = new THREE.SphereGeometry(15, 8, 6);
    const ledMat = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      toneMapped: false,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    mesh = new THREE.InstancedMesh(ledGeo, ledMat, TOTAL);
    mesh.instanceMatrix.setUsage(THREE.StaticDrawUsage);
    const colorArray = new Float32Array(TOTAL * 3);
    mesh.instanceColor = new THREE.InstancedBufferAttribute(colorArray, 3);

    for (let i = 0; i < TOTAL; i++) {
      const [row, col] = gridPositions[i];
      dummy.position.set(
        OFFSET + col * PITCH,
        JOIST_H + PLY - 2,  // under polycarbonate, on top of joists
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
  }

  // ── Underglow LEDs ─────────────────────────────────────
  let underglowMesh = null;
  const underglowCount = underglowPositions ? underglowPositions.length : 0;

  // Underglow point lights — actual lights that illuminate the floor
  const ugPointLights = [];

  if (underglowCount > 0) {
    // Very diffused — large, faint, blended into nothing
    const ugGeo = new THREE.SphereGeometry(35, 6, 4);
    const ugMat = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      toneMapped: false,
      transparent: true,
      opacity: 0.15,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    underglowMesh = new THREE.InstancedMesh(ugGeo, ugMat, underglowCount);
    const ugColors = new Float32Array(underglowCount * 3);
    underglowMesh.instanceColor = new THREE.InstancedBufferAttribute(ugColors, 3);

    for (let i = 0; i < underglowCount; i++) {
      const p = underglowPositions[i];
      dummy.position.set(p.x, p.y, p.z);
      dummy.updateMatrix();
      underglowMesh.setMatrixAt(i, dummy.matrix);
      underglowMesh.setColorAt(i, new THREE.Color(0, 0, 0));
    }

    underglowMesh.instanceMatrix.needsUpdate = true;
    underglowMesh.instanceColor.needsUpdate = true;
    underglowMesh.renderOrder = 1;
    scene.add(underglowMesh);

    // Few wide-range lights, evenly spaced — overlap into a smooth wash
    // Use every 6th LED position, higher intensity + longer range to fill gaps
    const LIGHT_EVERY = 6;
    for (let i = 0; i < underglowCount; i += LIGHT_EVERY) {
      const p = underglowPositions[i];
      const pl = new THREE.PointLight(0xffaa44, 9600, 500, 1.5); // decay 1.5 = softer falloff than physical
      pl.position.set(p.x, p.y - 15, p.z);
      scene.add(pl);
      ugPointLights.push(pl);
    }
  }

  // ── API ────────────────────────────────────────────────
  const tempColor = new THREE.Color();

  return {
    TOTAL,
    GRID,
    PITCH,
    OFFSET,
    mesh,
    underglowMesh,
    underglowCount,
    ugPointLights,
    gridPositions,
    HALF,

    setLedColor(index, r, g, b) {
      tempColor.setRGB(r / 255, g / 255, b / 255);
      mesh.setColorAt(index, tempColor);
    },

    setUnderglowColor(index, r, g, b) {
      if (!underglowMesh || index >= underglowCount) return;
      tempColor.setRGB(r / 255, g / 255, b / 255);
      underglowMesh.setColorAt(index, tempColor);
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
      if (underglowMesh) underglowMesh.instanceColor.needsUpdate = true;
    },
  };
}
