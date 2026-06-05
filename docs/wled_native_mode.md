# WLED Native Effects mode

Hand the LED matrix over to the WLED controller's own built-in effects,
driven from WLED's native web UI re-served *inside* the HERE admin panel
(the **WLED** tab). Switch back to Pi-driven animations any time.

## Why a reverse proxy (the non-obvious part)

The Pi has two networks:

| Interface | Address          | Reaches                          |
|-----------|------------------|----------------------------------|
| `wlan0`   | `192.168.1.x`    | your phone/laptop → HERE admin   |
| `eth0`    | `192.168.10.10`  | the WLED controller `192.168.10.20` |

**WLED is only reachable from the Pi**, not from the browser's WiFi LAN.
So a plain `<iframe src="http://192.168.10.20/">` fails. Instead the HERE
app reverse-proxies WLED under `/wled/` — the browser only ever talks to
the Pi, which relays to WLED over Ethernet.

### One-line URL rewrite — and WLED cooperates

WLED builds **every** URL (assets, JSON API, page navigation, form
`action`s, the live WebSocket) through a single helper:
`getURL(p) = (loc ? locproto+"//"+locip : "") + p`. It derives `loc`/`locip`
from `window.location.pathname` in `onLoad()`. That's fine for the
single-page main UI (path `/wled/` → `locip="<host>/wled"`), but on deeper
pages like `/wled/settings/leds` it computes `locip="<host>/wled/settings/leds"`,
which then **doubles** paths ("Incomplete page data!") or, where it ends up
empty, **escapes** back to our origin root (FastAPI `{"detail":"Not found"}`).

Fix: the proxy rewrites the relayed HTML/JS, replacing the `getURL` prefix
expression `(loc?locproto+"//"+locip:"")` with
`(location.protocol+"//"+location.host+"/wled")`. Now `getURL` always points
at `<origin>/wled` regardless of page depth — main UI, settings, nav, form
posts, and the `ws://…/wled/ws` socket all route back through the proxy.
WLED gzips these responses, so the proxy decompresses them, rewrites, and
relays plain (dropping `Content-Encoding`). All other responses (JSON,
binary assets, the WS frames) pass through untouched.

## Pieces

- **`admin/routes/wled.py`** — `register(app, config)`. HTTP catch-all
  `/wled/{path}` → `http://<wled-ip>/{path}` (stdlib `urllib` in a thread;
  strips `X-Frame-Options`/CSP so it can live in an iframe; rewrites
  `getURL` in HTML/JS as above), plus a WebSocket bridge `/wled/ws` ↔ WLED
  `/ws` (via the `websockets` lib). WLED IP comes from the first enabled
  `config.targets` entry.
- **`wled` engine mode** (`animation_engine.py`) — `ModeSpec` with
  `suppress_output=True`. The frame loop renders black locally but **stops
  transmitting DDP**. With no realtime packets, WLED leaves realtime
  override (after its configured *Realtime timeout*, default ~2.5 s) and
  runs its own effect. Switching back to any Pi mode resumes the DDP
  stream and WLED re-enters realtime instantly.
- **WLED tab** (`index.html` / `admin.js`) — lazy-loaded iframe at
  `/wled/`, a `data-mode="wled"` button to hand off, a `data-mode="standby"`
  button to resume, and a status line showing who's driving the LEDs.

## Caveats

- Requires WLED's **Realtime timeout** (Config → Sync Interfaces) to be
  non-zero, else WLED never leaves realtime when the Pi pauses.
- The `getURL` rewrite is anchored on WLED's minified prefix expression
  `(loc?locproto+"//"+locip:"")`. If a future WLED release changes that
  expression, settings pages would regress (the main UI would still work
  via its sub-path `locip`); re-check the anchor string after a WLED
  firmware update.
