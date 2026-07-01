/*
 * HERE — bench leg node (battery + load cell → ESP-NOW)
 * Board: Seeed XIAO ESP32-C6
 *
 * One per bench leg, BATTERY POWERED, so it lives in deep sleep. Each wake:
 *   1. read battery (divider on A0) + load cell (HX711 on D3/D6),
 *   2. decide "occupied" via an ADAPTIVE baseline that slowly tracks the
 *      reading while idle — this absorbs the constant bench weight and slow
 *      thermal drift, so only a real change (someone sitting) trips it. A
 *      fixed baseline is what made the legs read "occupied" forever and burn
 *      battery at the 1 s rate around the clock.
 *   3. TRANSMIT only when it's worth it:
 *        - occupied          → every wake (1 s cadence),
 *        - occupancy changed → immediately (sit-down / stand-up),
 *        - idle, steady      → a heartbeat every IDLE_TX_INTERVAL_S (~60 s),
 *        - low battery       → one packet, then long-sleep.
 *      Otherwise it SKIPS the radio entirely (no WiFi power-up). Idle wakes
 *      doing no radio is the big battery win.
 *   4. deep-sleep: 2 s occupied, 10 s idle (poll cadence).
 *
 * Power: WiFi is only ever powered for an actual transmit; Bluetooth is
 * never initialised; CPU runs at 80 MHz (enough for WiFi, less active
 * current); the HX711 is powered down between wakes. A low-battery cutoff
 * protects the LiPo.
 *
 * ESP-NOW BROADCAST on a fixed channel — no pairing. Flash NODE_ID 1 / 2.
 */

#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <Preferences.h>
#include <HTTPUpdate.h>
#include "driver/gpio.h"      // gpio_hold_* — latch PD_SCK high through deep sleep
#include "fw_version.h"
#include "ota_config.h"

// ── Per-node identity (override at build time with -DNODE_ID=2) ──────
#ifndef NODE_ID
#define NODE_ID 1
#endif

// ── Tunables ────────────────────────────────────────────────────────
static const uint64_t SLEEP_OCCUPIED_S   = 2;     // poll/TX cadence under load
static const uint64_t SLEEP_IDLE_S       = 10;    // poll cadence when empty
static const uint32_t IDLE_TX_INTERVAL_S = 120;   // idle heartbeat TX period
static const int32_t  NODE_OCC_THRESHOLD_DEFAULT = 20000;  // raw-count delta =
                                                  // occupied (default; settable
                                                  // from the Pi, saved in NVS)
static const uint32_t CMD_LISTEN_MS      = 100;   // post-TX RX window for cmds
static const int32_t  BASELINE_TAU_S     = 180;   // baseline EMA time constant
                                                  // (s, wall-clock). The level
                                                  // tracks toward the reading
                                                  // over ~3 min so the node
                                                  // self-heals from a bad seed
                                                  // or a change in how the
                                                  // bench rests (e.g. flipped
                                                  // for flashing → stood up)
static const uint8_t  ESPNOW_CHANNEL = 1;         // must match the receiver
static const float    BATT_DIVIDER   = 2.0f;      // 100k/100k -> half of VBAT

// Low-battery safety cutoff — protect the LiPo from over-discharge. The
// threshold is runtime-configurable from the Pi ("cutoff N mv", saved in NVS);
// LOW_BATT_CUTOFF_MV is only the factory default before one is set.
static const uint16_t LOW_BATT_CUTOFF_MV = 3500;  // default shut-off level
static const uint16_t LOW_BATT_FLOOR_MV  = 3000;  // never set cutoff below this
static const uint16_t LOW_BATT_CEIL_MV   = 4000;  // …or above this (sanity)
static const uint16_t LOW_BATT_VALID_MV  = 2000;  // ignore implausible reads
static const uint64_t LOW_BATT_SLEEP_S   = 1800;  // re-check every 30 min

// ── Pins (XIAO ESP32-C6 silkscreen) ─────────────────────────────────
static const int BATT_PIN = A0;   // D0 / GPIO0  — battery divider midpoint
static const int HX_DATA  = D3;   // GPIO21      — HX711 DOUT
static const int HX_CLK   = D6;   // GPIO16      — HX711 PD_SCK

// ── Packet sent to the receiver (keep in sync with rpi_receiver) ────
typedef struct __attribute__((packed)) {
  uint8_t  node_id;
  uint8_t  occupied;
  uint16_t battery_mv;
  int32_t  weight_raw;
  uint16_t boot_count;
  uint8_t  ack_seq;     // last applied command seq (so the receiver can clear)
  int32_t  threshold;   // current occupancy threshold (raw counts)
  uint16_t fw;          // firmware version (FW_VERSION)
  uint8_t  reset_reason;// esp_reset_reason() — why this boot happened (diag)
  uint16_t cutoff_mv;   // active low-battery cutoff (mV), so the UI confirms it
  uint8_t  power_state; // 0 = active(1s) / 1 = power-saving(10s) / 2 = low-batt
} bench_msg_t;

// Power-state codes reported in `power_state` (for the UI).
#define PS_ACTIVE   0   // occupied → 2 s poll cadence
#define PS_SAVING   1   // idle → 10 s poll cadence
#define PS_LOWBATT  2   // below cutoff → 30 min sleep

// ── Command from the receiver (broadcast; keep in sync with receiver) ─
#define CMD_MAGIC      0xC1
#define CMD_TARE       1
#define CMD_THRESHOLD  2
#define CMD_OTA        3
#define CMD_REBOOT     4    // remote power-cycle (re-seeds baseline on boot)
#define CMD_CUTOFF     5    // set low-battery cutoff (mV), persisted in NVS
typedef struct __attribute__((packed)) {
  uint8_t  magic;    // CMD_MAGIC, distinguishes from a leg packet
  uint8_t  target;   // node_id (1/2); 0 = all
  uint8_t  seq;      // command sequence (per target)
  uint8_t  type;     // CMD_TARE / CMD_THRESHOLD
  int32_t  value;    // threshold (CMD_THRESHOLD)
} cmd_msg_t;

static const uint8_t BROADCAST_ADDR[6] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

RTC_DATA_ATTR uint16_t bootCount     = 0;        // survives deep sleep
RTC_DATA_ATTR int32_t  baseline      = 0;        // adaptive empty-bench level
RTC_DATA_ATTR bool     baselineValid = false;    // false on cold boot only
RTC_DATA_ATTR bool     wasOccupied   = false;    // for edge detection
RTC_DATA_ATTR uint32_t secsSinceTx   = 0xFFFFFF; // force a TX on first boot
RTC_DATA_ATTR int32_t  occThreshold  = NODE_OCC_THRESHOLD_DEFAULT;  // NVS-backed
RTC_DATA_ATTR uint16_t cutoffMv      = LOW_BATT_CUTOFF_MV;          // NVS-backed
RTC_DATA_ATTR uint8_t  lastAckSeq    = 0;         // last command seq applied

// A command caught in the post-TX RX window (applied back in setup()).
static volatile bool g_cmd_rx = false;
static cmd_msg_t     g_cmd;
static Preferences   g_prefs;
static bool          g_otaRequested = false;
static bool          g_rebootRequested = false;

// ── HX711 (bit-banged, no library) ──────────────────────────────────
// DOUT goes LOW when a conversion is ready; we clock out 24 bits MSB
// first, then one extra pulse selects channel A / gain 128 for the next
// reading. Interrupts are off during the read because the HX711 powers
// itself down if PD_SCK is held high longer than ~60us.
//
// A timed-out read returns HX_INVALID (NOT 0). This matters: since v9 the
// HX711 is power-gated in deep sleep, so it cold-starts each wake and an
// occasional read can miss its DRDY window. Returning 0 used to read as a
// huge load vs the baseline → false "occupied", and the baseline self-heal
// then chased 0 — permanently latching the leg "occupied" so it never slept.
// Callers must treat HX_INVALID as "no sample" and leave state untouched.
static const long HX_INVALID = (long)0x80000000;  // sentinel: DRDY timed out

static long hx711_read() {
  unsigned long start = millis();
  while (digitalRead(HX_DATA)) {            // wait until ready
    if (millis() - start > 300) return HX_INVALID;  // not ready (missing/slow)
    delay(1);
  }
  long value = 0;
  noInterrupts();
  for (int i = 0; i < 24; i++) {
    digitalWrite(HX_CLK, HIGH);
    delayMicroseconds(1);
    value = (value << 1) | digitalRead(HX_DATA);
    digitalWrite(HX_CLK, LOW);
    delayMicroseconds(1);
  }
  digitalWrite(HX_CLK, HIGH);               // 25th pulse: ch A, gain 128
  delayMicroseconds(1);
  digitalWrite(HX_CLK, LOW);
  delayMicroseconds(1);
  interrupts();
  if (value & 0x800000) value |= ~0xFFFFFFL;  // sign-extend 24 -> 32 bit
  return value;
}

// Hold PD_SCK high >60us to drop the HX711 to ~1uA for deep sleep.
static void hx711_powerdown() {
  digitalWrite(HX_CLK, LOW);
  delayMicroseconds(1);
  digitalWrite(HX_CLK, HIGH);
  delayMicroseconds(70);
}

static long hx711_read_median(int samples) {
  long buf[7];
  if (samples > 7) samples = 7;
  if (samples < 1) samples = 1;
  int n = 0;
  for (int i = 0; i < samples; i++) {       // collect only valid samples
    long v = hx711_read();
    if (v != HX_INVALID) buf[n++] = v;
  }
  if (n == 0) return HX_INVALID;            // every sample timed out
  for (int i = 1; i < n; i++) {             // insertion sort -> median
    long key = buf[i]; int j = i - 1;
    while (j >= 0 && buf[j] > key) { buf[j + 1] = buf[j]; j--; }
    buf[j + 1] = key;
  }
  return buf[n / 2];
}

// ── Battery ─────────────────────────────────────────────────────────
static uint16_t read_battery_mv() {
  uint32_t acc = 0;
  for (int i = 0; i < 8; i++) acc += analogReadMilliVolts(BATT_PIN);
  float pin_mv = acc / 8.0f;
  return (uint16_t)lround(pin_mv * BATT_DIVIDER);
}

// ── Sleep ───────────────────────────────────────────────────────────
static void deepSleep(uint64_t seconds) {
  digitalWrite(LED_BUILTIN, HIGH);   // LED off (active-low) before sleeping
  hx711_powerdown();                 // leaves PD_SCK HIGH (HX711 → ~1uA)
  // Latch PD_SCK HIGH for the whole sleep. Without this the pad floats once the
  // core powers down, the HX711 leaves power-down, and it (plus the load-cell
  // bridge excitation) keeps drawing several mA the entire sleep. On the C6 a
  // single digital pad is held through deep sleep by gpio_hold_en alone
  // (SOC_GPIO_SUPPORT_HOLD_SINGLE_IO_IN_DSLP); released on wake in setup.
  gpio_hold_en((gpio_num_t)HX_CLK);
  // NOTE: no explicit esp_now_deinit()/WiFi.mode(OFF) here — deep sleep powers
  // the radio domain down by itself, and doing that teardown right before
  // esp_deep_sleep_start() was panicking on the C6 (reset_reason=PANIC),
  // resetting every cycle. Just sleep.
  esp_sleep_enable_timer_wakeup(seconds * 1000000ULL);
  esp_deep_sleep_start();            // never returns; setup() runs on wake
}

// Command receive callback — runs during the post-TX listen window. Keep it
// tiny: stash the command for setup() to apply.
static void onCmd(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  if (len != (int)sizeof(cmd_msg_t) || data[0] != CMD_MAGIC) return;
  cmd_msg_t c;
  memcpy(&c, data, sizeof(c));
  if (c.target == 0 || c.target == NODE_ID) { g_cmd = c; g_cmd_rx = true; }
}

// ── Transmit + listen ───────────────────────────────────────────────
// Power the radio up, broadcast one packet, then hold RX briefly to catch a
// queued command from the receiver (poll/respond — the receiver fires the
// command the instant it hears our packet). Only called on wakes that
// transmit; idle wakes never touch WiFi (the battery win).
static void transmit(const bench_msg_t &msg) {
  // Onboard antenna: GPIO3 LOW powers the RF switch (REQUIRED), GPIO14 LOW
  // selects the built-in antenna.
  pinMode(3, OUTPUT);  digitalWrite(3, LOW);
  delay(10);
  pinMode(14, OUTPUT); digitalWrite(14, LOW);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  WiFi.setTxPower(WIFI_POWER_19_5dBm);   // pin max TX power for range/margin
  esp_wifi_set_channel(ESPNOW_CHANNEL, WIFI_SECOND_CHAN_NONE);
  if (esp_now_init() != ESP_OK) return;
  esp_now_register_recv_cb(onCmd);       // ready to catch a command reply

  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, BROADCAST_ADDR, 6);
  peer.channel = ESPNOW_CHANNEL;
  peer.ifidx   = WIFI_IF_STA;
  peer.encrypt = false;
  esp_now_add_peer(&peer);

  g_cmd_rx = false;
  esp_now_send(BROADCAST_ADDR, (uint8_t *)&msg, sizeof(msg));

  // Hold RX for a short window so the receiver can deliver a queued command.
  unsigned long t0 = millis();
  while (millis() - t0 < CMD_LISTEN_MS) {
    if (g_cmd_rx) break;   // got one — stop early to save power
    delay(2);
  }
}

// Apply a command caught during the listen window. `weight` is this wake's
// fresh reading (used as the new zero for a tare).
static void applyCommand(long weight) {
  if (g_cmd.seq == lastAckSeq) return;        // already applied (dup/retry)
  if (g_cmd.type == CMD_TARE) {
    baseline = weight;                        // zero to the current load
    baselineValid = true;
  } else if (g_cmd.type == CMD_THRESHOLD) {
    occThreshold = g_cmd.value;
    g_prefs.begin("bench", false);            // persist across power loss
    g_prefs.putInt("occ_thr", occThreshold);
    g_prefs.end();
  } else if (g_cmd.type == CMD_CUTOFF) {
    uint16_t mv = (uint16_t)g_cmd.value;      // clamp to a sane LiPo range
    if (mv < LOW_BATT_FLOOR_MV) mv = LOW_BATT_FLOOR_MV;
    if (mv > LOW_BATT_CEIL_MV)  mv = LOW_BATT_CEIL_MV;
    cutoffMv = mv;
    g_prefs.begin("bench", false);
    g_prefs.putUShort("cutoff_mv", cutoffMv);
    g_prefs.end();
  } else if (g_cmd.type == CMD_OTA) {
    g_otaRequested = true;                     // handled after setup() returns here
  } else if (g_cmd.type == CMD_REBOOT) {
    g_rebootRequested = true;                  // software reset → re-seeds baseline
  }
  lastAckSeq = g_cmd.seq;                      // reported back so receiver clears
}

// ── OTA: join the dev WiFi and pull a new image from the Pi ──────────
// Triggered by an OTA command. Leaves ESP-NOW, joins the hardcoded home
// network, and asks the Pi for firmware newer than ours (the GET doubles as
// the "I'm in OTA mode" handshake — the Pi logs it). HTTPUpdate reboots into
// the new image on success; on no-update/failure we just resume sleeping.
static void enterOta() {
  digitalWrite(LED_BUILTIN, LOW);   // LED solid on through the update
  WiFi.mode(WIFI_STA);
  WiFi.begin(OTA_WIFI_SSID, OTA_WIFI_PASS);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < OTA_WIFI_TIMEOUT_MS)
    delay(200);
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClient client;
    String url = String("http://") + OTA_HOST + ":" + OTA_PORT +
                 "/api/ota/firmware/leg/" + String(NODE_ID);
    httpUpdate.rebootOnUpdate(true);
    // currentVersion is sent as a header; the Pi 304s if we're already current.
    httpUpdate.update(client, url, String(FW_VERSION));
    // Reached here only on NO_UPDATES or FAILED — fall through and resume.
  }
  deepSleep(SLEEP_IDLE_S);
}

void setup() {
  bootCount++;
  setCpuFrequencyMhz(80);   // enough for WiFi; lower active current than 160

  // Only trust the RTC baseline across DEEP SLEEP. Any other reset — a fresh
  // flash, the reset button, or power-on — re-seeds from scratch, so we get a
  // clean settled baseline without needing a manual power-cycle each flash.
  if (esp_reset_reason() != ESP_RST_DEEPSLEEP) {
    baselineValid = false;
    wasOccupied   = false;
    secsSinceTx   = 0xFFFFFF;   // force a TX on the first wake after reset
    lastAckSeq    = 0;
    // Load the persisted settings (set from the Pi) from flash.
    g_prefs.begin("bench", true);
    occThreshold = g_prefs.getInt("occ_thr", NODE_OCC_THRESHOLD_DEFAULT);
    cutoffMv     = (uint16_t)g_prefs.getUShort("cutoff_mv", LOW_BATT_CUTOFF_MV);
    g_prefs.end();
  }

  // Alive heartbeat: LED on for the whole wake (flashes once per wake).
  // Diagnostic: flashing = running; dark = unpowered/bootloader; steady-on
  // = hung. XIAO LED is active-LOW; deepSleep() turns it off.
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  // Release the deep-sleep latch on PD_SCK so we can drive the clock again.
  // (deepSleep() held it HIGH to keep the HX711 powered down through sleep.)
  gpio_hold_dis((gpio_num_t)HX_CLK);

  // Sensor pins. PD_SCK LOW wakes the HX711 from power-down.
  pinMode(HX_DATA, INPUT);
  pinMode(HX_CLK, OUTPUT);
  digitalWrite(HX_CLK, LOW);

  analogReadResolution(12);

  // The HX711 is power-gated during deep sleep (PD_SCK held high), so it
  // cold-starts every wake and needs ~400 ms to produce a settled reading —
  // an early/timeout sample (often 0) would seed a bad baseline or read a
  // phantom load. Wait, then discard the first still-settling sample. This is
  // the cost of cutting the bridge excitation in sleep; idle wakes are only
  // every 10 s so the duty stays low.
  delay(400);                   // HX711 output settling (~400ms @ 10 SPS)
  hx711_read();                 // discard the first (still-settling) sample

  long weight;
  if (!baselineValid) {
    weight = hx711_read_median(5);
    if (weight != HX_INVALID && weight != 0) { baseline = weight; baselineValid = true; }
  } else {
    // A single sample is plenty when empty (the threshold is huge and the Pi
    // filters anyway); only spend a median once the cheap read looks loaded.
    weight = hx711_read();
    if (weight != HX_INVALID && labs(weight - baseline) > occThreshold)
      weight = hx711_read_median(3);
  }

  // A bad/timed-out read must NOT touch occupancy or the baseline (that was
  // what latched a leg "occupied" forever). Skip the wake entirely and retry
  // next time — keep the previous state and just sleep again.
  if (weight == HX_INVALID)
    deepSleep(wasOccupied ? SLEEP_OCCUPIED_S : SLEEP_IDLE_S);

  bool occupied = baselineValid &&
                  (labs(weight - baseline) > occThreshold);

  bench_msg_t msg;
  msg.node_id    = NODE_ID;
  msg.occupied   = occupied ? 1 : 0;
  msg.battery_mv = read_battery_mv();
  msg.weight_raw = weight;
  msg.boot_count = bootCount;
  msg.ack_seq    = lastAckSeq;
  msg.threshold  = occThreshold;
  msg.fw         = FW_VERSION;
  msg.reset_reason = (uint8_t)esp_reset_reason();
  msg.cutoff_mv  = cutoffMv;

  bool lowBatt = (msg.battery_mv >= LOW_BATT_VALID_MV &&
                  msg.battery_mv <  cutoffMv);
  bool changed = (occupied != wasOccupied);
  wasOccupied  = occupied;
  uint64_t interval = occupied ? SLEEP_OCCUPIED_S : SLEEP_IDLE_S;
  msg.power_state = lowBatt ? PS_LOWBATT : (occupied ? PS_ACTIVE : PS_SAVING);

  // Self-healing baseline: track toward the reading at a fixed wall-clock
  // rate (~BASELINE_TAU_S), occupied or not. Absorbs the static bench load +
  // drift and recovers from a bad seed or a change in how the bench rests
  // (flipped for flashing → stood upright), while still reading "occupied"
  // through the first few minutes of any real change (when fast updates
  // matter). The Pi gets the true raw weight regardless, so its own
  // occupancy logic is unaffected.
  if (baselineValid)
    baseline += (long)(weight - baseline) * (long)interval / BASELINE_TAU_S;

  // Transmit only when worth it; idle steady wakes skip the radio entirely.
  bool doTx = occupied || changed || lowBatt ||
              (secsSinceTx >= IDLE_TX_INTERVAL_S);
  if (doTx) {
    transmit(msg);            // broadcasts, then listens ~100ms for a command
    secsSinceTx = 0;
    if (g_cmd_rx) applyCommand(weight);   // tare / threshold / OTA from the Pi
  } else {
    secsSinceTx += (uint32_t)interval;
  }

  if (g_otaRequested) enterOta();             // never returns if it updates
  if (g_rebootRequested) ESP.restart();       // remote power-cycle (re-seeds)
  if (lowBatt) deepSleep(LOW_BATT_SLEEP_S);   // protect the cell
  deepSleep(interval);
}

void loop() {}   // unused — everything happens in setup() then deep sleep
