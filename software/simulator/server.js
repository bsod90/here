import express from 'express';
import { createServer } from 'http';
import { createServer as createHttpsServer } from 'https';
import { WebSocketServer } from 'ws';
import dgram from 'dgram';
import crypto from 'crypto';
import { execSync } from 'child_process';
import fs from 'fs';
import os from 'os';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3000;
const HTTPS_PORT = process.env.HTTPS_PORT || 3443;
const UDP_PORT = 21324;
const TOTAL_LEDS = 1936;
const FRAME_BYTES = TOTAL_LEDS * 3;
const BROADCAST_INTERVAL = 33;

// ── Self-signed cert for HTTPS (needed for WebXR on LAN) ──
function getOrCreateCert() {
  const certDir = join(__dirname, '.certs');
  const certPath = join(certDir, 'cert.pem');
  const keyPath = join(certDir, 'key.pem');

  if (fs.existsSync(certPath) && fs.existsSync(keyPath)) {
    return { cert: fs.readFileSync(certPath), key: fs.readFileSync(keyPath) };
  }

  console.log('[ssl] generating self-signed certificate...');
  fs.mkdirSync(certDir, { recursive: true });

  // Generate via openssl CLI
  try {
    execSync(`openssl req -x509 -newkey rsa:2048 -keyout "${keyPath}" -out "${certPath}" -days 365 -nodes -subj "/CN=here-simulator" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null`, {
      stdio: ['pipe', 'pipe', 'pipe'],
    });
  } catch {
    execSync(`openssl req -x509 -newkey rsa:2048 -keyout "${keyPath}" -out "${certPath}" -days 365 -nodes -subj "/CN=here-simulator"`, {
      stdio: ['pipe', 'pipe', 'pipe'],
    });
  }

  return { cert: fs.readFileSync(certPath), key: fs.readFileSync(keyPath) };
}

// ── Express static server ──────────────────────────────────
const app = express();
app.use(express.static(join(__dirname, 'public')));

// Upload endpoint for GLB model export (from browser → save to assets/)
app.post('/upload-model', express.raw({ type: '*/*', limit: '50mb' }), (req, res) => {
  const dest = join(__dirname, 'public', 'assets', 'here-installation.glb');
  fs.writeFileSync(dest, req.body);
  console.log(`[upload] saved GLB model (${req.body.length} bytes)`);
  res.sendStatus(200);
});

// HTTP server
const server = createServer(app);

// HTTPS server (for WebXR AR on phones)
let httpsServer;
try {
  const certs = await getOrCreateCert();
  httpsServer = createHttpsServer(certs, app);
} catch (e) {
  console.warn('[ssl] could not create HTTPS server:', e.message);
  console.warn('[ssl] AR mode will not work on phones. Install openssl to fix.');
}

// ── WebSocket server (on both HTTP and HTTPS) ──────────────
const clients = new Set();

function setupWss(srv) {
  const wss = new WebSocketServer({ server: srv, path: '/ws' });
  wss.on('connection', (ws) => {
    clients.add(ws);
    console.log(`[ws] client connected (${clients.size} total)`);
    ws.on('close', () => {
      clients.delete(ws);
      console.log(`[ws] client disconnected (${clients.size} total)`);
    });
  });
}

setupWss(server);
if (httpsServer) setupWss(httpsServer);

function broadcast(data) {
  for (const ws of clients) {
    if (ws.readyState === 1) ws.send(data);
  }
}

// ── UDP listener (DNRGB on 21324, DDP on 4048) ────────────
const frameBuffer = new Uint8Array(FRAME_BYTES);
let frameDirty = false;

// DNRGB listener (port 21324)
const udp = dgram.createSocket('udp4');

udp.on('message', (msg) => {
  if (msg.length < 4) return;
  const protocol = msg[0];

  if (protocol === 4) {
    // DNRGB: [4, timeout, startHi, startLo, R,G,B,...]
    if (msg.length < 5) return;
    const startIndex = (msg[2] << 8) | msg[3];
    const rgbData = msg.subarray(4);
    const startByte = startIndex * 3;
    const copyLen = Math.min(rgbData.length, FRAME_BYTES - startByte);
    if (startByte >= 0 && startByte < FRAME_BYTES && copyLen > 0) {
      frameBuffer.set(rgbData.subarray(0, copyLen), startByte);
      frameDirty = true;
    }
  }
});

udp.on('listening', () => console.log(`[udp] DNRGB on port ${UDP_PORT}`));
udp.bind(UDP_PORT);

// DDP listener (port 4048)
const DDP_PORT = 4048;
const ddp = dgram.createSocket('udp4');

ddp.on('message', (msg) => {
  if (msg.length < 10) return; // DDP header is 10 bytes
  // DDP header: flags(1) seq(1) type(1) source(1) offset(4) length(2) data...
  const offset = (msg[4] << 24) | (msg[5] << 16) | (msg[6] << 8) | msg[7];
  const length = (msg[8] << 8) | msg[9];
  const rgbData = msg.subarray(10);
  const copyLen = Math.min(rgbData.length, length, FRAME_BYTES - offset);
  if (offset >= 0 && offset < FRAME_BYTES && copyLen > 0) {
    frameBuffer.set(rgbData.subarray(0, copyLen), offset);
    frameDirty = true;
  }
});

ddp.on('listening', () => console.log(`[udp] DDP on port ${DDP_PORT}`));
ddp.bind(DDP_PORT);

// ── Broadcast loop ─────────────────────────────────────────
setInterval(() => {
  if (frameDirty && clients.size > 0) {
    broadcast(frameBuffer);
    frameDirty = false;
  }
}, BROADCAST_INTERVAL);

// ── Live reload ────────────────────────────────────────────
let reloadTimeout = null;
fs.watch(join(__dirname, 'public'), { recursive: true }, (event, filename) => {
  if (reloadTimeout) clearTimeout(reloadTimeout);
  reloadTimeout = setTimeout(() => {
    console.log(`[reload] ${filename} changed`);
    for (const ws of clients) {
      if (ws.readyState === 1) ws.send('__reload__');
    }
  }, 100);
});

// ── Get LAN IP ─────────────────────────────────────────────
function getLanIp() {
  for (const ifaces of Object.values(os.networkInterfaces())) {
    for (const iface of ifaces) {
      if (iface.family === 'IPv4' && !iface.internal) return iface.address;
    }
  }
  return 'localhost';
}

// ── Start ──────────────────────────────────────────────────
const lanIp = getLanIp();

server.listen(PORT, () => {
  console.log(`[here-simulator] http://localhost:${PORT}`);
  console.log(`[here-simulator] http://${lanIp}:${PORT}`);
});

if (httpsServer) {
  httpsServer.listen(HTTPS_PORT, () => {
    console.log(`[here-simulator] https://localhost:${HTTPS_PORT}`);
    console.log(`[here-simulator] https://${lanIp}:${HTTPS_PORT}  ← open on phone for AR`);
  });
}

console.log(`[here-simulator] UDP DNRGB on port ${UDP_PORT}`);
console.log(`[here-simulator] live reload active`);
