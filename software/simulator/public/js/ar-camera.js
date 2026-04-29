import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { createBench } from './bench.js';
import { createElecBox } from './elec-box.js';
import { createLedSystem } from './leds.js';
import { updateDemo } from './demo.js';

// ── Constants ──────────────────────────────────────────────
const PLATFORM_SIZE = 2438;
const PLY = 19;
const JOIST_H = 89;
const BASE_SCALE = 0.001; // mm → meters

const startScreen = document.getElementById('start-screen');
const startButton = document.getElementById('start-button');
const infoEl = document.getElementById('info');
const scaleSlider = document.getElementById('scale-slider');
const sizeRange = document.getElementById('size-range');
const sizeVal = document.getElementById('size-val');
const video = document.getElementById('camera-feed');
const canvas = document.getElementById('canvas');

// ── Start camera + 3D scene ────────────────────────────────
startButton.addEventListener('click', async () => {
  // Request rear camera
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();
  } catch (e) {
    infoEl.textContent = 'Camera access denied';
    return;
  }

  startScreen.style.display = 'none';
  scaleSlider.style.display = 'flex';
  initScene();
});

function initScene() {
  // ── Renderer — transparent background so camera shows through ──
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(0x000000, 0); // fully transparent
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.7;

  // ── Scene ────────────────────────────────────────────────
  const scene = new THREE.Scene();

  // ── Camera ───────────────────────────────────────────────
  const camera = new THREE.PerspectiveCamera(
    60, window.innerWidth / window.innerHeight, 0.01, 100
  );
  camera.position.set(2, 1.5, 2);
  camera.lookAt(0, 0.2, 0);

  // ── Controls — touch-friendly ────────────────────────────
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.1;
  controls.target.set(0, 0.2, 0);
  controls.enablePan = true;
  controls.minDistance = 0.5;
  controls.maxDistance = 10;

  // ── Lighting — dim so LEDs are the star, model still visible ──
  scene.add(new THREE.AmbientLight(0x334455, 0.15));
  const dirLight = new THREE.DirectionalLight(0x8899bb, 0.3);
  dirLight.position.set(2, 4, 1);
  scene.add(dirLight);

  // ── Build installation ───────────────────────────────────
  const installation = new THREE.Group();

  // Platform surface
  const platGeo = new THREE.PlaneGeometry(PLATFORM_SIZE, PLATFORM_SIZE);
  const platMat = new THREE.MeshStandardMaterial({
    color: 0x1a1a1a,
    roughness: 0.85,
    transparent: true,
    opacity: 0.6,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  const platform = new THREE.Mesh(platGeo, platMat);
  platform.rotation.x = -Math.PI / 2;
  platform.position.y = JOIST_H + PLY + 3;
  platform.renderOrder = 10;
  installation.add(platform);

  // Platform edge
  const edgeMat = new THREE.MeshStandardMaterial({ color: 0x444444, roughness: 0.8 });
  const edge = new THREE.Mesh(
    new THREE.BoxGeometry(PLATFORM_SIZE, PLY, PLATFORM_SIZE), edgeMat
  );
  edge.position.y = JOIST_H + PLY / 2;
  installation.add(edge);

  // Simplified subfloor
  const subMat = new THREE.MeshStandardMaterial({ color: 0x9a7d5a, roughness: 0.9 });
  const sub = new THREE.Mesh(
    new THREE.BoxGeometry(PLATFORM_SIZE - 100, JOIST_H, PLATFORM_SIZE - 100), subMat
  );
  sub.position.y = JOIST_H / 2;
  installation.add(sub);

  // Ground shadow catcher — semi-transparent dark disc
  const shadowGeo = new THREE.CircleGeometry(PLATFORM_SIZE * 0.8, 32);
  const shadowMat = new THREE.MeshBasicMaterial({
    color: 0x000000,
    transparent: true,
    opacity: 0.3,
  });
  const shadow = new THREE.Mesh(shadowGeo, shadowMat);
  shadow.rotation.x = -Math.PI / 2;
  shadow.position.y = -1;
  installation.add(shadow);

  // Bench + person
  const bench = createBench();
  installation.add(bench.group);

  // Side electronics box
  const elecBox = createElecBox();
  installation.add(elecBox.group);

  // LEDs
  const leds = createLedSystem(installation);

  // Scale to meters
  installation.scale.setScalar(BASE_SCALE);
  scene.add(installation);

  // ── Size slider ──────────────────────────────────────────
  sizeRange.addEventListener('input', () => {
    const pct = parseInt(sizeRange.value);
    sizeVal.textContent = pct + '%';
    installation.scale.setScalar(BASE_SCALE * pct / 100);
  });

  // ── Resize ───────────────────────────────────────────────
  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  // ── Render loop ──────────────────────────────────────────
  function animate(time) {
    requestAnimationFrame(animate);
    updateDemo(time, leds);
    controls.update();
    renderer.render(scene, camera);
  }

  requestAnimationFrame(animate);

  // Hide info after a few seconds
  setTimeout(() => { infoEl.style.display = 'none'; }, 4000);
}
