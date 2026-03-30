import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const canvas = document.getElementById('canvas');

// ── Renderer ───────────────────────────────────────────────
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.7;

// ── Scene ──────────────────────────────────────────────────
const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x060610, 0.00004);

// ── Camera ─────────────────────────────────────────────────
const camera = new THREE.PerspectiveCamera(
  45, window.innerWidth / window.innerHeight, 10, 30000
);
camera.position.set(3500, 2000, 3500);
camera.lookAt(0, 50, 0);

// ── Controls ───────────────────────────────────────────────
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.target.set(0, 50, 0);
controls.minDistance = 500;
controls.maxDistance = 15000;

// ── Lighting ───────────────────────────────────────────────
// In Three.js r155+, PointLight/SpotLight use physically-based units
// (candela). Scene units are mm, so distances are large numbers.
// Need high intensity values to compensate.

// Ambient — base fill so nothing is pure black
const ambient = new THREE.AmbientLight(0x223344, 0.2);
scene.add(ambient);

// Moon — directional (lux-based, not distance-dependent)
const moon = new THREE.DirectionalLight(0x8899bb, 0.4);
moon.position.set(4000, 6000, -3000);
moon.castShadow = true;
moon.shadow.mapSize.set(2048, 2048);
moon.shadow.camera.left = -3000;
moon.shadow.camera.right = 3000;
moon.shadow.camera.top = 3000;
moon.shadow.camera.bottom = -3000;
moon.shadow.camera.near = 1000;
moon.shadow.camera.far = 12000;
moon.shadow.bias = -0.001;
scene.add(moon);

// Hemisphere: cool sky above, warm playa below
const hemi = new THREE.HemisphereLight(0x111122, 0x0a0a08, 0.1);
scene.add(hemi);

// ── Street light — 1m from installation edge ──────────────
const PLATFORM_EDGE = 2438 / 2;
const poleHeight = 2500;
// Pole 1m diagonally from the +X, +Z corner
const cornerOffset = 2000 / Math.sqrt(2); // 2m along diagonal from corner
const poleX = PLATFORM_EDGE + cornerOffset;
const poleZ = PLATFORM_EDGE + cornerOffset;

// Pole geometry
const poleMat = new THREE.MeshStandardMaterial({ color: 0x444444, roughness: 0.7, metalness: 0.3 });
const shaft = new THREE.Mesh(new THREE.CylinderGeometry(15, 20, poleHeight, 8), poleMat);
shaft.position.set(poleX, poleHeight / 2, poleZ);
shaft.castShadow = true;
scene.add(shaft);

// Lamp head
const headMat = new THREE.MeshStandardMaterial({ color: 0x555555, roughness: 0.6, metalness: 0.4 });
const head = new THREE.Mesh(new THREE.BoxGeometry(80, 30, 60), headMat);
head.position.set(poleX, poleHeight + 15, poleZ);
scene.add(head);

// Warm bulb glow
const bulbGeo = new THREE.SphereGeometry(20, 8, 6);
const bulbMat = new THREE.MeshBasicMaterial({ color: 0xeebb77 });
const bulb = new THREE.Mesh(bulbGeo, bulbMat);
bulb.position.set(poleX, poleHeight - 5, poleZ);
scene.add(bulb);

// SpotLight — wide, diffused wash aimed at the ground below
const streetLight = new THREE.SpotLight(0xeebb77, 50000000, 15000, Math.PI / 2, 1.0, 2);
streetLight.position.set(poleX, poleHeight, poleZ);
streetLight.target.position.set(poleX * 0.3, 0, poleZ * 0.3); // aimed at nearby ground
streetLight.castShadow = true;
streetLight.shadow.mapSize.set(1024, 1024);
streetLight.shadow.bias = -0.002;
scene.add(streetLight);
scene.add(streetLight.target);

// ── Street light sliders ──────────────────────────────────
function createSlider(label, min, max, value, step, onChange) {
  const row = document.createElement('div');
  row.className = 'slider-row';
  const lbl = document.createElement('label');
  lbl.textContent = label;
  const input = document.createElement('input');
  input.type = 'range';
  input.min = min;
  input.max = max;
  input.value = value;
  input.step = step;
  const val = document.createElement('span');
  val.textContent = value;
  input.addEventListener('input', () => {
    val.textContent = input.value;
    onChange(parseFloat(input.value));
  });
  row.append(lbl, input, val);
  return row;
}

const sliderPanel = document.createElement('div');
sliderPanel.id = 'sliders';
document.body.appendChild(sliderPanel);

sliderPanel.appendChild(createSlider('Light', 0, 200, 50, 1, (v) => {
  streetLight.intensity = v * 1000000;
}));

// ── Nearby art installations ──────────────────────────────
// PointLight intensity in candela, distance in mm → need large values
const nearbyArt = [
  { pos: [-4500, 600, -3500], color: 0xff6622, intensity: 15000000, size: 180 },
  { pos: [5000, 800, -3000],  color: 0x22aaff, intensity: 12000000, size: 150 },
  { pos: [-3000, 500, 5000],  color: 0xff44aa, intensity: 8000000,  size: 120 },
  { pos: [4000, 550, 4500],   color: 0x44ff88, intensity: 6000000,  size: 110 },
  { pos: [-5500, 400, 1500],  color: 0xffaa22, intensity: 12000000, size: 140 },
];

nearbyArt.forEach(({ pos, color, intensity, size }) => {
  const light = new THREE.PointLight(color, intensity, 0, 2); // 0 = infinite range, decay=2 (physical)
  light.position.set(...pos);
  scene.add(light);

  const glowGeo = new THREE.SphereGeometry(size, 8, 6);
  const glowMat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.9 });
  const glow = new THREE.Mesh(glowGeo, glowMat);
  glow.position.set(...pos);
  scene.add(glow);
});

// ── Post-processing — bloom ────────────────────────────────
const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));

const bloomPass = new UnrealBloomPass(
  new THREE.Vector2(window.innerWidth, window.innerHeight),
  0.6,  // strength
  0.5,  // radius
  0.4   // threshold
);
composer.addPass(bloomPass);
composer.addPass(new OutputPass());

// ── Resize ─────────────────────────────────────────────────
window.addEventListener('resize', () => {
  const w = window.innerWidth;
  const h = window.innerHeight;
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  renderer.setSize(w, h);
  composer.setSize(w, h);
  bloomPass.resolution.set(w, h);
});

export { renderer, scene, camera, controls, composer };
