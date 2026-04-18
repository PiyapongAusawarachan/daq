/**
 * ESP32 — เปิดไฟแล้วทำงานเอง (ไม่ต้องกดรันจากคอมหลังอัปโหลดโค้ดแล้ว)
 *
 * 1) คัดลอก ../secrets.h.example เป็น ../secrets.h แล้วใส่ WiFi + MQTT
 * 2) ติดตั้งบอร์ด ESP32 ใน Arduino IDE / Arduino CLI
 * 3) อัปโหลดสเก็ตช์นี้ครั้งเดียว — หลังนั้นทุกครั้งที่จ่ายไฟบอร์ดจะเชื่อม WiFi แล้วส่ง MQTT ตามช่วงเวลา
 *
 * Payload เป็น JSON ให้ตรงกับ parser_utils.parse_payload ในโปรเจกต์ Python
 */

#include <WiFi.h>
#include <PubSubClient.h>

#include "secrets.h"

#ifndef MQTT_TOPIC
#define MQTT_TOPIC "b6710545709/field_monitoring"
#endif

#ifndef PUBLISH_INTERVAL_MS
#define PUBLISH_INTERVAL_MS 10000UL
#endif

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

unsigned long lastPublishMs = 0;

static void setupWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

static bool ensureMqtt() {
  if (mqtt.connected()) {
    return true;
  }
  String clientId = "esp32-" + WiFi.macAddress();
  clientId.replace(":", "");
#if defined(MQTT_USER) && (MQTT_USER[0] != '\0')
  bool ok = mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASS);
#else
  bool ok = mqtt.connect(clientId.c_str());
#endif
  return ok;
}

// TODO: อ่านเซ็นเซอร์จริงแทนค่าจำลอง
static void readSensors(int *soil, float *tempC, float *humPct, int *pm1, int *pm25, int *pm10) {
  *soil = analogRead(SOIL_PIN) / 16;
  *tempC = 30.0f;
  *humPct = 55.0f;
  *pm1 = 12;
  *pm25 = 18;
  *pm10 = 22;
}

void setup() {
  pinMode(SOIL_PIN, INPUT);
  setupWiFi();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  lastPublishMs = 0;
}

void loop() {
  if (!ensureMqtt()) {
    delay(2000);
    return;
  }

  mqtt.loop();

  unsigned long now = millis();
  if (now - lastPublishMs < PUBLISH_INTERVAL_MS) {
    delay(50);
    return;
  }
  lastPublishMs = now;

  int soil, pm1, pm25, pm10;
  float tempC, humPct;
  readSensors(&soil, &tempC, &humPct, &pm1, &pm25, &pm10);

  char payload[384];
  snprintf(
      payload,
      sizeof(payload),
      "{\"device_id\":\"%s\",\"soil_moisture\":%d,\"temperature\":%.2f,\"humidity\":%.2f,"
      "\"dust\":{\"pm1_0\":%d,\"pm2_5\":%d,\"pm10\":%d}}",
      DEVICE_ID,
      soil,
      tempC,
      humPct,
      pm1,
      pm25,
      pm10);

  mqtt.publish(MQTT_TOPIC, payload, true);
}
