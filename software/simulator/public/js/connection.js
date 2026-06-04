// WebSocket client with auto-reconnect.
// Receives binary LED frame data and applies it to the LED system.

const statusEl = document.getElementById('status');

export function connectWebSocket(leds) {
  const state = {
    externalDataActive: false,
    connected: false,
    leds, // mutable reference — can be swapped when bench orientation changes
  };

  let ws = null;
  let retryDelay = 1000;
  const MAX_RETRY = 10000;

  function connect() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Resolve /ws relative to wherever this page is hosted:
    //   served by the standalone Node sim → /ws
    //   embedded in the HERE orchestrator at /sim/ → /sim/ws
    const base = location.pathname.replace(/\/[^/]*$/, '');
    ws = new WebSocket(`${protocol}//${location.host}${base}/ws`);
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {
      state.connected = true;
      retryDelay = 1000;
      statusEl.textContent = 'connected';
      statusEl.className = 'connected';
    };

    ws.onmessage = (event) => {
      // Live reload signal
      if (typeof event.data === 'string' && event.data === '__reload__') {
        console.log('[reload] reloading...');
        location.reload();
        return;
      }
      // LED frame data (binary)
      if (event.data instanceof ArrayBuffer) {
        const buf = new Uint8Array(event.data);
        if (buf.length >= state.leds.TOTAL * 3) {
          // Switch to external mode on the first frame that has data (so
          // the built-in demo keeps running until the orchestrator sends
          // something). But once external, apply EVERY frame — including
          // all-zero ones — otherwise a reset / fade-out / blank scene
          // can't clear the display and the last frame sticks.
          if (buf.some(v => v > 0)) {
            state.externalDataActive = true;
          }
          if (state.externalDataActive) {
            state.leds.applyFrame(buf);
          }
        }
      }
    };

    ws.onclose = () => {
      state.connected = false;
      statusEl.textContent = 'disconnected';
      statusEl.className = 'disconnected';
      // Auto-reconnect with backoff
      setTimeout(() => {
        retryDelay = Math.min(retryDelay * 2, MAX_RETRY);
        connect();
      }, retryDelay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }

  connect();
  return state;
}
