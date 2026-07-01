#pragma once
// Firmware version for the whole bench fleet (legs + receiver). Bump this on
// every release. Each board reports it; the Pi compares it against the version
// of the binary it has staged to show "flashed vs available" and to gate OTA
// (the device sends its current version, the Pi serves a newer image or 304s).
//
// v5: receiver was dropping leg packets (missing `fw` field → size mismatch).
// v6: receiver parses packets length-tolerantly (struct growth no longer
//     strands nodes); legs report esp_reset_reason() to diagnose the
//     wakes-every-cycle / RTC-not-retained issue.
// v7: removed the esp_now_deinit()/WiFi.mode(OFF) that panicked the C6 before
//     deep sleep (was resetting every cycle).
// v8: power saving — idle poll 5 s → 10 s, idle heartbeat 60 s → 120 s, single
//     HX711 sample when idle (median-3 only under load). Battery cutoff is now
//     runtime-configurable (NVS + "cutoff N mv" command) and reported in the
//     packet ("cut").
// v9: power saving — latch PD_SCK HIGH through deep sleep (gpio_hold) so the
//     HX711 + load-cell bridge actually power down (~1 µA) instead of drawing
//     several mA all sleep; re-adds the ~400 ms HX711 settle on every wake.
// v10: legs report their power state ("ps": 0 active/1s, 1 power-saving/10s,
//      2 low-battery/30min) so the UI can show it.
// v11: active poll cadence 1 s → 2 s (occupied) for a bit more battery margin.
// v12: receiver uses the external u.FL antenna (GPIO14 HIGH) instead of the
//      onboard PCB antenna. Leg binaries are unchanged except the version.
#define FW_VERSION 12
