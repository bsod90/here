#pragma once
// OTA network config.
//
// The WiFi SSID + password are SECRETS and must never be committed. They are
// injected at build time from the gitignored .env (OTA_WIFI_SSID / OTA_WIFI_PASS)
// via -D defines — see rpi/scripts/build-firmware.sh. If they're not provided
// the sketch still compiles (with empty creds); OTA just won't connect.
#define _OTA_STR2(x) #x
#define _OTA_STR(x) _OTA_STR2(x)
#ifdef OTA_WIFI_SSID_RAW
  #define OTA_WIFI_SSID _OTA_STR(OTA_WIFI_SSID_RAW)
#else
  #define OTA_WIFI_SSID ""
#endif
#ifdef OTA_WIFI_PASS_RAW
  #define OTA_WIFI_PASS _OTA_STR(OTA_WIFI_PASS_RAW)
#else
  #define OTA_WIFI_PASS ""
#endif

// The Pi's LAN address (not a secret).
#define OTA_HOST       "192.168.1.110"
#define OTA_PORT       8000

// How long to wait for the WiFi join before giving up and going back to sleep.
#define OTA_WIFI_TIMEOUT_MS 20000
