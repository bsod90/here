// Export the installation as a GLB file for AR Quick Look.
// Converts InstancedMesh → regular meshes since GLTFExporter
// doesn't support instanced geometry.

import * as THREE from 'three';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { createLedSystem } from './leds.js';
import { updateDemo } from './demo.js';

const PLATFORM_SIZE = 2438;
const PLY = 19;
const JOIST_H = 89;
const SCALE = 0.001;

// Convert InstancedMesh to a Group of individual meshes
// Only include LEDs that are visibly lit (skip black ones)
function flattenInstancedMesh(instMesh) {
  const group = new THREE.Group();
  const dummy = new THREE.Matrix4();
  const color = new THREE.Color();

  for (let i = 0; i < instMesh.count; i++) {
    instMesh.getMatrixAt(i, dummy);
    if (instMesh.instanceColor) {
      instMesh.getColorAt(i, color);
      // Skip dark LEDs and every other LED for performance
      if (color.r < 0.05 && color.g < 0.05 && color.b < 0.05) continue;
      if (i % 2 !== 0) continue; // export every other LED
    }

    const mat = new THREE.MeshStandardMaterial({
      color: instMesh.instanceColor ? color.clone() : new THREE.Color(1, 1, 1),
      emissive: instMesh.instanceColor ? color.clone() : new THREE.Color(1, 1, 1),
      emissiveIntensity: 0.8,
      roughness: 1,
      metalness: 0,
    });

    const mesh = new THREE.Mesh(instMesh.geometry.clone(), mat);
    mesh.applyMatrix4(dummy);
    group.add(mesh);
  }

  return group;
}

export async function exportGLB() {
  try {
    const exportScene = new THREE.Scene();

    // Platform
    const platGeo = new THREE.PlaneGeometry(PLATFORM_SIZE, PLATFORM_SIZE);
    const platMat = new THREE.MeshStandardMaterial({
      color: 0x333333,
      roughness: 0.85,
      side: THREE.DoubleSide,
    });
    const platform = new THREE.Mesh(platGeo, platMat);
    platform.rotation.x = -Math.PI / 2;
    platform.position.y = JOIST_H + PLY + 3;
    exportScene.add(platform);

    // Edge
    const edge = new THREE.Mesh(
      new THREE.BoxGeometry(PLATFORM_SIZE, PLY, PLATFORM_SIZE),
      new THREE.MeshStandardMaterial({ color: 0x444444, roughness: 0.8 })
    );
    edge.position.y = JOIST_H + PLY / 2;
    exportScene.add(edge);

    // Subfloor
    const sub = new THREE.Mesh(
      new THREE.BoxGeometry(PLATFORM_SIZE - 100, JOIST_H, PLATFORM_SIZE - 100),
      new THREE.MeshStandardMaterial({ color: 0x9a7d5a, roughness: 0.9 })
    );
    sub.position.y = JOIST_H / 2;
    exportScene.add(sub);

    // Bench — build inline without textures (GLTFExporter chokes on cross-origin textures)
    const BENCH_L = 1219, BENCH_W = 300, BENCH_H = 350;
    const LEG_DIM = 89, LEG_INSET = 250;
    const boxBottomY = JOIST_H + PLY + LEG_DIM;

    const benchGroup = new THREE.Group();
    const benchMat = new THREE.MeshStandardMaterial({ color: 0xc8a564, roughness: 0.85 });
    const legMat = new THREE.MeshStandardMaterial({ color: 0xb09050, roughness: 0.85 });

    const box = new THREE.Mesh(new THREE.BoxGeometry(BENCH_L, BENCH_H, BENCH_W), benchMat);
    box.position.y = boxBottomY + BENCH_H / 2;
    benchGroup.add(box);

    for (const sx of [-1, 1]) {
      const leg = new THREE.Mesh(new THREE.BoxGeometry(LEG_DIM, LEG_DIM, BENCH_W), legMat);
      leg.position.set(sx * (BENCH_L / 2 - LEG_INSET), JOIST_H + PLY + LEG_DIM / 2, 0);
      benchGroup.add(leg);
    }
    benchGroup.rotation.y = 0;
    exportScene.add(benchGroup);

    // LEDs — create in a temp group, bake one frame, then flatten
    // Skip underglow for AR export (they're under the bench, not visible)
    const tempGroup = new THREE.Group();
    const leds = createLedSystem(tempGroup, []);
    updateDemo(2000, leds); // bake at mid-breath

    // Flatten InstancedMeshes to regular meshes for GLB export
    if (leds.mesh) {
      const flatFloor = flattenInstancedMesh(leds.mesh);
      exportScene.add(flatFloor);
    }
    if (leds.underglowMesh) {
      const flatUG = flattenInstancedMesh(leds.underglowMesh);
      exportScene.add(flatUG);
    }

    // Scale to meters
    const wrapper = new THREE.Group();
    wrapper.add(exportScene);
    wrapper.scale.setScalar(SCALE);

    console.log('[export] starting GLB export...');
    const exporter = new GLTFExporter();
    const glb = await exporter.parseAsync(wrapper, { binary: true });
    console.log('[export] GLB generated,', glb.byteLength, 'bytes');

    // Upload to server
    const resp = await fetch('/upload-model', {
      method: 'POST',
      headers: { 'Content-Type': 'application/octet-stream' },
      body: glb,
    });

    if (!resp.ok) throw new Error('Upload failed: ' + resp.status);
    console.log('[export] uploaded to server');

    return new Blob([glb], { type: 'model/gltf-binary' });
  } catch (e) {
    console.error('[export] failed:', e);
    alert('Export failed: ' + e.message);
    throw e;
  }
}
