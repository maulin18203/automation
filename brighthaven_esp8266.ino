/*
 * ╔══════════════════════════════════════════════════════════╗
 * ║          BrightHaven — ESP8266 Blynk Edition            ║
 * ║  Virtual Pin → Device mapping:                          ║
 * ║   V0 → Main Room Fan    (D1 / GPIO5)                   ║
 * ║   V1 → Main Room Light  (D2 / GPIO4)                   ║
 * ║   V2 → Main Room TV     (D5 / GPIO14)                  ║
 * ║   V3 → Main Room WiFi   (D6 / GPIO12)                  ║
 * ║   V4 → Bedroom1 Fan     (D7 / GPIO13)                  ║
 * ║   V5 → Bedroom1 Light   (D8 / GPIO15)                  ║
 * ║   V6 → Bedroom1 AC      (D4 / GPIO2)                   ║
 * ║   V7 → Bedroom1 TV      (D3 / GPIO0)                   ║
 * ║   V8 → Bedroom1 Geyser  (SD3 / GPIO10)                 ║
 * ╚══════════════════════════════════════════════════════════╝
 *
 * SETUP (one-time):
 *  1. Go to https://blynk.cloud → Create Template "BrightHaven"
 *  2. Add Datastreams V0–V8 → Integer, min=0, max=1
 *  3. Create a Device → copy Auth Token → paste below
 *  4. Install "Blynk" library in Arduino IDE
 *  5. Set your WiFi credentials below → Flash!
 *
 * RELAY WIRING: Active-LOW module assumed
 *   ON  → digitalWrite(pin, LOW)
 *   OFF → digitalWrite(pin, HIGH)
 */

// ── Blynk Credentials ──────────────────────────────────────────
#define BLYNK_TEMPLATE_ID   "YOUR_TEMPLATE_ID"       // e.g. "TMPLxxxxxx"
#define BLYNK_TEMPLATE_NAME "BrightHaven"
#define BLYNK_AUTH_TOKEN    "B5a6tgOxySyna1GKlB3k_ZKhhJefttXM"

// ── Wi-Fi Credentials ──────────────────────────────────────────
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";

// ── Libraries ──────────────────────────────────────────────────
#include <ESP8266WiFi.h>
#include <BlynkSimpleEsp8266.h>

// ── GPIO Pin Map (GPIO numbers, not D-numbers) ─────────────────
//              V0  V1  V2  V3  V4  V5  V6  V7  V8
const int PINS[] = { 5,  4, 14, 12, 13, 15,  2,  0, 10 };
#define NUM_PINS 9

BlynkTimer timer;

// ── Setup ──────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("\n[BrightHaven] Booting...");

  // All relays OFF at start (HIGH = relay off for active-LOW modules)
  for (int i = 0; i < NUM_PINS; i++) {
    pinMode(PINS[i], OUTPUT);
    digitalWrite(PINS[i], HIGH);
  }

  Blynk.begin(BLYNK_AUTH_TOKEN, WIFI_SSID, WIFI_PASS);

  Serial.print("[WiFi] Connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Connected! IP: " + WiFi.localIP().toString());
  Serial.println("[Blynk] Ready. Waiting for commands...");
}

// ── Main Loop ──────────────────────────────────────────────────
void loop() {
  Blynk.run();
  timer.run();
}

// ── Relay Helper ───────────────────────────────────────────────
void setRelay(int index, int state) {
  if (index < 0 || index >= NUM_PINS) return;
  digitalWrite(PINS[index], state ? LOW : HIGH);
  Serial.printf("[Relay] V%d (GPIO%d) → %s\n",
                index, PINS[index], state ? "ON" : "OFF");
}

// ── Blynk Virtual Pin Handlers ─────────────────────────────────
BLYNK_WRITE(V0) { setRelay(0, param.asInt()); }  // Main Room Fan
BLYNK_WRITE(V1) { setRelay(1, param.asInt()); }  // Main Room Light
BLYNK_WRITE(V2) { setRelay(2, param.asInt()); }  // Main Room TV
BLYNK_WRITE(V3) { setRelay(3, param.asInt()); }  // Main Room WiFi
BLYNK_WRITE(V4) { setRelay(4, param.asInt()); }  // Bedroom1 Fan
BLYNK_WRITE(V5) { setRelay(5, param.asInt()); }  // Bedroom1 Light
BLYNK_WRITE(V6) { setRelay(6, param.asInt()); }  // Bedroom1 AC
BLYNK_WRITE(V7) { setRelay(7, param.asInt()); }  // Bedroom1 TV
BLYNK_WRITE(V8) { setRelay(8, param.asInt()); }  // Bedroom1 Geyser

// ── Blynk Connected: sync all states from cloud ────────────────
BLYNK_CONNECTED() {
  Serial.println("[Blynk] Connected to cloud ✅");
  Blynk.syncAll();
}
