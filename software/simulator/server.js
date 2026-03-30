import express from 'express';
import { createServer } from 'http';
import { WebSocketServer } from 'ws';
import dgram from 'dgram';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3000;
const UDP_PORT = 21324; // WLED DNRGB port
const TOTAL_LEDS = 1936;
const FRAME_BYTES = TOTAL_LEDS * 3;
const BROADCAST_INTERVAL = 33; // ~30fps

// ── Express static server ──────────────────────────────────
const app = express();
app.use(express.static(join(__dirname, 'public')));
const server = createServer(app);

// ── WebSocket server ───────────────────────────────────────
const wss = new WebSocketServer({ server, path: '/ws' });
const clients = new Set();

wss.on('connection', (ws) => {
  clients.add(ws);
  console.log(`[ws] client connected (${clients.size} total)`);
  ws.on('close', () => {
    clients.delete(ws);
    console.log(`[ws] client disconnected (${clients.size} total)`);
  });
});

function broadcast(data) {
  for (const ws of clients) {
    if (ws.readyState === 1) { // OPEN
      ws.send(data);
    }
  }
}

// ── UDP DNRGB listener ─────────────────────────────────────
// DNRGB protocol: byte 0 = 2 (protocol ID), bytes 1-2 = start index (big-endian),
// then sequential RGB triplets
const frameBuffer = new Uint8Array(FRAME_BYTES);
let frameDirty = false;

const udp = dgram.createSocket('udp4');

udp.on('message', (msg) => {
  if (msg.length < 4) return;
  const protocol = msg[0];

  if (protocol === 2) {
    // DNRGB: start index + RGB data
    const startIndex = (msg[1] << 8) | msg[2];
    const rgbData = msg.subarray(3);
    const startByte = startIndex * 3;
    const copyLen = Math.min(rgbData.length, FRAME_BYTES - startByte);
    if (startByte >= 0 && startByte < FRAME_BYTES && copyLen > 0) {
      frameBuffer.set(rgbData.subarray(0, copyLen), startByte);
      frameDirty = true;
    }
  } else if (protocol === 4) {
    // DRGB: no start index, just RGB data from LED 0
    const rgbData = msg.subarray(1);
    const copyLen = Math.min(rgbData.length, FRAME_BYTES);
    if (copyLen > 0) {
      frameBuffer.set(rgbData.subarray(0, copyLen), 0);
      frameDirty = true;
    }
  }
});

udp.on('listening', () => {
  console.log(`[udp] DNRGB listener on port ${UDP_PORT}`);
});

udp.bind(UDP_PORT);

// ── Broadcast loop ─────────────────────────────────────────
setInterval(() => {
  if (frameDirty && clients.size > 0) {
    broadcast(frameBuffer);
    frameDirty = false;
  }
}, BROADCAST_INTERVAL);

// ── Live reload — watch public/ and notify browsers ────────
let reloadTimeout = null;
fs.watch(join(__dirname, 'public'), { recursive: true }, (event, filename) => {
  if (reloadTimeout) clearTimeout(reloadTimeout);
  reloadTimeout = setTimeout(() => {
    console.log(`[reload] ${filename} changed`);
    for (const ws of clients) {
      if (ws.readyState === 1) {
        ws.send('__reload__');
      }
    }
  }, 100); // debounce 100ms
});

// ── Start ──────────────────────────────────────────────────
server.listen(PORT, () => {
  console.log(`[here-simulator] http://localhost:${PORT}`);
  console.log(`[here-simulator] UDP DNRGB on port ${UDP_PORT}`);
  console.log(`[here-simulator] live reload active`);
});
