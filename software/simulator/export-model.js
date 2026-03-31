#!/usr/bin/env node
// Pre-generate the GLB model for AR Quick Look.
// Usage: node export-model.js
//
// Uses puppeteer-like approach: starts the server, opens the export
// page in a headless-ish way. But actually, simplest: just build
// a basic GLB with the gltf-transform library.

// For now: generate the model via the browser.
// Start the server, open the page, click export.

import { execSync } from 'child_process';
import fs from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const outPath = join(__dirname, 'public', 'assets', 'here-installation.glb');

// Quick check: try using the existing Three.js scene from the browser
// Since Node polyfills are painful, let's use a different approach:
// Build a simple OBJ-like representation and convert it.

// Actually, simplest approach that works: use the `export-glb.js` from
// the browser by opening it with `open` command.

console.log('');
console.log('To generate the AR model:');
console.log('  1. Start the server: npm run dev');
console.log('  2. Open in browser: http://localhost:3000/ar-quicklook.html');
console.log('  3. Click "Generate 3D Model"');
console.log('  4. The GLB will be saved to public/assets/');
console.log('');

// Alternative: if the server is already running, open the page
if (process.argv.includes('--open')) {
  execSync('open http://localhost:3000/ar-quicklook.html');
}
