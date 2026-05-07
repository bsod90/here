import { scene, camera, composer, controls } from './scene.js';
import { createPlatform } from './platform.js';
import { createBench } from './bench.js';
import { createElecBox } from './elec-box.js';
import { createLedSystem } from './leds.js';
import { connectWebSocket } from './connection.js';
import { updateDemo } from './demo.js';

// ── Build scene ────────────────────────────────────────────
const platform = createPlatform();
scene.add(platform);

const bench = createBench();
scene.add(bench.group);

const elecBox = createElecBox();
scene.add(elecBox.group);

const leds = createLedSystem(scene);
const ws = connectWebSocket(leds);

// ── FPS counter ────────────────────────────────────────────
const fpsEl = document.getElementById('fps');
let frameCount = 0;
let lastFpsTime = performance.now();

// ── Animation loop ─────────────────────────────────────────
function animate(time) {
  requestAnimationFrame(animate);

  if (!ws.externalDataActive) {
    updateDemo(time, leds);
  }

  controls.update();
  composer.render();

  frameCount++;
  const now = performance.now();
  if (now - lastFpsTime >= 1000) {
    fpsEl.textContent = `${frameCount} fps`;
    frameCount = 0;
    lastFpsTime = now;
  }
}

requestAnimationFrame(animate);
