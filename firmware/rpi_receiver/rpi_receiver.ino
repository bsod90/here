/*
 * HERE — RPi-side receiver (ESP-NOW ⇄ UART ⇄ Raspberry Pi)
 * Board: Seeed XIAO ESP32-C6
 *
 * Wired to the Raspberry Pi with FOUR wires:
 *   - 5V  (XIAO "5V")        -> Pi 5V   (pin 2/4)   [or 3V3 pad -> Pi 3V3]
 *   - GND (XIAO "GND")       -> Pi GND  (pin 6)
 *   - D3  (GPIO21, UART TX)  -> Pi RXD  (GPIO15, pin 10)   receiver → Pi
 *   - D1  (GPIO1,  UART RX)  <- Pi TXD0 (GPIO14, pin 8)    Pi → receiver
 *
 * Always powered. Two jobs:
 *   1. Receive ESP-NOW broadcasts from the legs and print one JSON line per
 *      packet to the Pi (and USB), plus a periodic heartbeat.
 *   2. Take commands FROM the Pi ("tare N", "thresh N V"), queue them per
 *      leg, and deliver them over ESP-NOW. The legs are asleep, so we can't
 *      push at will — instead we broadcast the queued command the instant a
 *      leg checks in (it holds an RX window right after each TX), and retry
 *      on every contact until the leg echoes the matching ack_seq.
 *
 * Both UART directions are 115200 8N1, 3.3V (no level shifter needed).
 */

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <HTTPUpdate.h>
#include "fw_version.h"
#include "ota_config.h"

static const uint8_t  ESPNOW_CHANNEL = 1;   // must match the bench nodes
static const int      PI_TX_PIN = D3;       // GPIO21 -> Pi RXD (pin 10)
static const int      PI_RX_PIN = D1;       // GPIO1  <- Pi TXD0 (pin 8)
static const uint32_t HEARTBEAT_MS = 2000;

HardwareSerial PiLink(1);                    // UART1, now bidirectional

// ── Wire formats (keep in sync with bench_node) ─────────────────────
typedef struct __attribute__((packed)) {
  uint8_t  node_id;
  uint8_t  occupied;
  uint16_t battery_mv;
  int32_t  weight_raw;
  uint16_t boot_count;
  uint8_t  ack_seq;
  int32_t  threshold;
  uint16_t fw;
  uint8_t  reset_reason;   // esp_reset_reason() on the leg (diagnostic)
  uint16_t cutoff_mv;      // active low-battery cutoff (mV)
  uint8_t  power_state;    // 0 active / 1 power-saving / 2 low-batt
} bench_msg_t;
// Bytes through `threshold` — the stable base every firmware shares. Packets
// at least this long are accepted; newer trailing fields are read only if the
// packet is long enough (so struct growth never strands a mismatched node).
#define BENCH_MSG_BASE  15

#define CMD_MAGIC      0xC1
#define CMD_TARE       1
#define CMD_THRESHOLD  2
#define CMD_OTA        3
#define CMD_REBOOT     4
#define CMD_CUTOFF     5
typedef struct __attribute__((packed)) {
  uint8_t  magic;
  uint8_t  target;
  uint8_t  seq;
  uint8_t  type;
  int32_t  value;
} cmd_msg_t;

static const uint8_t BROADCAST_ADDR[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

// Per-leg pending command (index by node id; we support nodes 1..2).
struct Pending { bool active; uint8_t seq; uint8_t type; int32_t value; };
static Pending pending[3];        // [1], [2]
static uint8_t seqCounter[3];     // per-node command sequence

typedef struct { bench_msg_t msg; int rssi; } rx_item_t;
static QueueHandle_t rxq = nullptr;

static void emit(Print &out, const bench_msg_t &m, int rssi) {
  out.print("{\"node\":");     out.print(m.node_id);
  out.print(",\"occ\":");      out.print(m.occupied);
  out.print(",\"batt_mv\":");  out.print(m.battery_mv);
  out.print(",\"weight\":");   out.print(m.weight_raw);
  out.print(",\"boot\":");     out.print(m.boot_count);
  out.print(",\"ack\":");      out.print(m.ack_seq);
  out.print(",\"thr\":");      out.print(m.threshold);
  out.print(",\"fw\":");       out.print(m.fw);
  out.print(",\"rr\":");       out.print(m.reset_reason);
  out.print(",\"cut\":");      out.print(m.cutoff_mv);
  out.print(",\"ps\":");       out.print(m.power_state);
  out.print(",\"rssi\":");     out.print(rssi);
  out.println("}");
}

static void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  // Length-tolerant: accept any packet with at least the stable base; copy
  // what's there into a zeroed struct so missing trailing fields read as 0.
  if (len < BENCH_MSG_BASE || rxq == nullptr) return;
  rx_item_t it;
  memset(&it.msg, 0, sizeof(it.msg));
  memcpy(&it.msg, data, len < (int)sizeof(it.msg) ? len : (int)sizeof(it.msg));
  it.rssi = info->rx_ctrl ? info->rx_ctrl->rssi : 0;
  xQueueSend(rxq, &it, 0);
}

// Queue a command for a leg (called from the Pi-command parser).
static void queueCommand(uint8_t node, uint8_t type, int32_t value) {
  if (node < 1 || node > 2) return;
  uint8_t s = ++seqCounter[node];
  if (s == 0) s = ++seqCounter[node];   // never use 0 (legs init lastAckSeq=0)
  pending[node] = {true, s, type, value};
  PiLink.printf("# queued node=%u seq=%u type=%u val=%ld\n",
                node, s, type, (long)value);
}

// Join the dev WiFi and pull a new image from the Pi (HTTPUpdate reboots on
// success). Used to OTA the receiver itself.
static void enterOta() {
  esp_now_deinit();
  WiFi.mode(WIFI_STA);
  WiFi.begin(OTA_WIFI_SSID, OTA_WIFI_PASS);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < OTA_WIFI_TIMEOUT_MS)
    delay(200);
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClient client;
    String url = String("http://") + OTA_HOST + ":" + OTA_PORT +
                 "/api/ota/firmware/receiver";
    httpUpdate.rebootOnUpdate(true);
    httpUpdate.update(client, url, String(FW_VERSION));
  }
  // No update / failed → reboot back into the normal receiver role.
  ESP.restart();
}

// Parse one command line from the Pi: "tare N", "thresh N V", "ota N|r".
static void handlePiLine(char *line) {
  char *cmd = strtok(line, " \t");
  if (!cmd) return;
  if (!strcmp(cmd, "tare")) {
    char *n = strtok(nullptr, " \t");
    if (n) queueCommand((uint8_t)atoi(n), CMD_TARE, 0);
  } else if (!strcmp(cmd, "thresh")) {
    char *n = strtok(nullptr, " \t");
    char *v = strtok(nullptr, " \t");
    if (n && v) queueCommand((uint8_t)atoi(n), CMD_THRESHOLD, (int32_t)atol(v));
  } else if (!strcmp(cmd, "cutoff")) {
    char *n = strtok(nullptr, " \t");
    char *v = strtok(nullptr, " \t");
    if (n && v) queueCommand((uint8_t)atoi(n), CMD_CUTOFF, (int32_t)atol(v));
  } else if (!strcmp(cmd, "ota")) {
    char *t = strtok(nullptr, " \t");
    if (!t) return;
    if (t[0] == 'r') { PiLink.println("# receiver entering OTA"); enterOta(); }
    else queueCommand((uint8_t)atoi(t), CMD_OTA, 0);
  } else if (!strcmp(cmd, "reboot")) {
    char *t = strtok(nullptr, " \t");
    if (!t) return;
    if (t[0] == 'r') { PiLink.println("# receiver rebooting"); delay(50); ESP.restart(); }
    else queueCommand((uint8_t)atoi(t), CMD_REBOOT, 0);
  }
}

static void readPiCommands() {
  static char buf[64];
  static uint8_t len = 0;
  while (PiLink.available()) {
    char c = (char)PiLink.read();
    if (c == '\n' || c == '\r') {
      if (len) { buf[len] = 0; handlePiLine(buf); len = 0; }
    } else if (len < sizeof(buf) - 1) {
      buf[len++] = c;
    }
  }
}

static void broadcastCommand(const Pending &p, uint8_t node) {
  cmd_msg_t c = {CMD_MAGIC, node, p.seq, p.type, p.value};
  esp_now_send(BROADCAST_ADDR, (uint8_t *)&c, sizeof(c));
}

void setup() {
  Serial.begin(115200);
  PiLink.begin(115200, SERIAL_8N1, PI_RX_PIN, PI_TX_PIN);   // RX + TX
  delay(200);

  rxq = xQueueCreate(16, sizeof(rx_item_t));

  // External u.FL antenna: GPIO3 LOW powers the RF switch, GPIO14 HIGH selects
  // the external connector (LOW would be the onboard PCB antenna).
  pinMode(3, OUTPUT);  digitalWrite(3, LOW);
  delay(100);
  pinMode(14, OUTPUT); digitalWrite(14, HIGH);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  esp_wifi_set_channel(ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE);

  PiLink.print("# receiver mac="); PiLink.print(WiFi.macAddress());
  PiLink.print(" channel=");       PiLink.println(ESPNOW_CHANNEL);

  if (esp_now_init() != ESP_OK) {
    PiLink.println("# ERROR esp_now_init failed");
    return;
  }
  esp_now_register_recv_cb(onRecv);

  esp_now_peer_info_t peer = {};         // broadcast peer for sending commands
  memcpy(peer.peer_addr, BROADCAST_ADDR, 6);
  peer.channel = ESPNOW_CHANNEL;
  peer.ifidx   = WIFI_IF_STA;
  peer.encrypt = false;
  esp_now_add_peer(&peer);

  PiLink.println("# listening");
}

void loop() {
  static uint32_t rxCount = 0;
  static uint32_t lastHb = 0;

  readPiCommands();   // ingest any queued tare/threshold from the Pi

  rx_item_t it;
  if (xQueueReceive(rxq, &it, pdMS_TO_TICKS(200)) == pdTRUE) {
    rxCount++;
    emit(PiLink, it.msg, it.rssi);
    emit(Serial, it.msg, it.rssi);

    // Command delivery: a leg just checked in (its RX window is open now).
    uint8_t n = it.msg.node_id;
    if (n >= 1 && n <= 2 && pending[n].active) {
      if (it.msg.ack_seq == pending[n].seq) {
        pending[n].active = false;                    // confirmed applied
        PiLink.printf("{\"ack\":%u,\"seq\":%u}\n", n, pending[n].seq);
      } else {
        broadcastCommand(pending[n], n);              // (re)send; leg is awake
        // OTA and reboot are fire-and-forget: the leg leaves ESP-NOW (for
        // WiFi / a restart) and won't ack — don't retry into a loop.
        if (pending[n].type == CMD_OTA || pending[n].type == CMD_REBOOT)
          pending[n].active = false;
      }
    }
  }

  uint32_t now = millis();
  if (now - lastHb >= HEARTBEAT_MS) {
    lastHb = now;
    PiLink.printf("{\"hb\":1,\"up_ms\":%lu,\"rx\":%lu,\"fw\":%d}\n",
                  (unsigned long)now, (unsigned long)rxCount, FW_VERSION);
  }
}
