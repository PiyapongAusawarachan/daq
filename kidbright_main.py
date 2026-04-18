# MicroPython (KidBright) — อัปโหลดบนบอร์ดเป็น main.py
# ไฟล์เดียวรันได้ (ค่า DEFAULT อยู่ใน _BOARD); มี secrets.py ก็ทับได้
# สำเนาเดียวกับ firmware/kidbright_micropython/main.py

"""
KidBright + MicroPython — เปิดไฟ / กด Run ใน Thonny แล้วทำงาน

- มีค่า DEFAULT ครบในไฟล์นี้ (ไม่ต้องมี secrets.py ก็รันได้)
- ถ้ามี secrets.py บนบอร์ด จะทับค่าจากไฟล์นั้นแทน
- Payload ตรงกับ parser_utils.parse_payload

ถ้า import umqtt.simple ไม่ได้ ลองใน REPL:
  import mip; mip.install("umqtt.simple")
"""

import binascii
import gc
import machine
import network
import time

try:
    import ujson as json
except ImportError:
    import json

try:
    from umqtt.simple import MQTTClient
except ImportError:
    MQTTClient = None

try:
    import sensor

    _HAS_KIDB_SENSOR = True
except ImportError:
    _HAS_KIDB_SENSOR = False

# ค่าเดียวกับที่เคยใช้ใน secrets / test_mqtt — แก้ตรงนี้ได้ทั้งหมด
_BOARD = {
    "WIFI_SSID": "skibidi",
    "WIFI_PASSWORD": "12345678",
    "MQTT_HOST": "iot.cpe.ku.ac.th",
    "MQTT_PORT": 1883,
    "MQTT_TOPIC": "b6710545709/field_monitoring",
    "MQTT_USER": "b6710545709",
    "MQTT_PASS": "paramee.sae@ku.th",
    "DEVICE_ID": "kidbright_01",
    "PUBLISH_INTERVAL_MS": 10_000,
    "SOIL_ADC_PIN": 34,
}

try:
    import secrets as _secrets_mod

    for _k in _BOARD:
        if hasattr(_secrets_mod, _k):
            _BOARD[_k] = getattr(_secrets_mod, _k)
except ImportError:
    pass

WIFI_SSID = _BOARD["WIFI_SSID"]
WIFI_PASSWORD = _BOARD["WIFI_PASSWORD"]
MQTT_HOST = _BOARD["MQTT_HOST"]
MQTT_PORT = _BOARD["MQTT_PORT"]
MQTT_TOPIC = _BOARD["MQTT_TOPIC"]
MQTT_USER = _BOARD["MQTT_USER"]
MQTT_PASS = _BOARD["MQTT_PASS"]
DEVICE_ID = _BOARD["DEVICE_ID"]
PUBLISH_INTERVAL_MS = _BOARD["PUBLISH_INTERVAL_MS"]
SOIL_ADC_PIN = _BOARD["SOIL_ADC_PIN"]


def _client_id():
    return "kb-" + binascii.hexlify(machine.unique_id()).decode()


def _wifi_connect(timeout_s=45):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return wlan
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    for _ in range(timeout_s * 10):
        if wlan.isconnected():
            break
        time.sleep_ms(100)
    return wlan


def _read_soil():
    if SOIL_ADC_PIN is None:
        return None
    try:
        adc = machine.ADC(machine.Pin(SOIL_ADC_PIN))
        try:
            adc.atten(machine.ADC.ATTN_11DB)
        except AttributeError:
            pass
        raw = adc.read()
        return int(raw // 16)
    except OSError:
        return None


def _read_temp_hum():
    temp = None
    hum = None
    if _HAS_KIDB_SENSOR:
        try:
            temp = float(sensor.temperature())
        except (OSError, ValueError, TypeError):
            pass
    return temp, hum


def _read_dust():
    return None, None, None


def build_payload():
    soil = _read_soil()
    temp, hum = _read_temp_hum()
    pm1, pm25, pm10 = _read_dust()

    doc = {
        "device_id": DEVICE_ID,
        "soil_moisture": soil,
        "temperature": temp,
        "humidity": hum,
        "dust": {"pm1_0": pm1, "pm2_5": pm25, "pm10": pm10},
    }
    return json.dumps(doc)


def _mqtt_connect():
    if MQTTClient is None:
        raise RuntimeError("ไม่พบ umqtt.simple — ติดตั้งไลบรารี MQTT ในเฟิร์มแวร์ก่อน")

    user = MQTT_USER
    pwd = MQTT_PASS
    if user:
        client = MQTTClient(
            _client_id(),
            MQTT_HOST,
            port=MQTT_PORT,
            user=user,
            password=pwd or "",
            keepalive=60,
        )
    else:
        client = MQTTClient(_client_id(), MQTT_HOST, port=MQTT_PORT, keepalive=60)
    client.connect()
    return client


def main():
    wlan = _wifi_connect()
    if not wlan.isconnected():
        machine.reset()

    mqtt = _mqtt_connect()

    while True:
        try:
            if not wlan.isconnected():
                wlan = _wifi_connect()
                if not wlan.isconnected():
                    machine.reset()

            payload = build_payload()
            mqtt.publish(MQTT_TOPIC, payload, qos=0)
        except OSError:
            time.sleep_ms(2000)
            try:
                mqtt.disconnect()
            except OSError:
                pass
            mqtt = _mqtt_connect()
        gc.collect()
        time.sleep_ms(PUBLISH_INTERVAL_MS)


if __name__ == "__main__":
    main()
