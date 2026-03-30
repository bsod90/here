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
    ws = new WebSocket(`${protocol}//${location.host}/ws`);
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
          // Only switch to external mode if the frame has actual data (not all zeros)
          const hasData = buf.some(v => v > 0);
          if (hasData) {
            state.externalDataActive = true;
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
