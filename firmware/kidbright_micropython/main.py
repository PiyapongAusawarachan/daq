"""
KidBright + MicroPython — เปิดไฟ / กด Run ใน Thonny แล้วทำงาน

- Payload flat ตรงตาม schema ของตาราง field_monitoring_raw:
  device_id, soil_moisture, temperature, humidity, pm1_0, pm2_5, pm10
- ค่าที่อ่านไม่ได้ส่ง -1 (int) / -1.0 (float) ไม่ใช้ null เพื่อไม่ให้ขาดฟิลด์

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

import dht

try:
    from umqtt.robust import MQTTClient
except ImportError:
    from umqtt.simple import MQTTClient

from machine import Pin, UART, ADC

# =============================================================================
# WIFI + MQTT (แก้ที่นี่)
# =============================================================================
_BOARD = {
    "WIFI_SSID": "Jira_JA_2.4G",
    "WIFI_PASSWORD": "Aey11898866",
    "MQTT_HOST": "iot.cpe.ku.ac.th",
    "MQTT_PORT": 1883,
    "MQTT_TOPIC": "b6710545709/field_monitoring",
    "MQTT_USER": "b6710545709",
    "MQTT_PASS": "paramee.sae@ku.th",
    "DEVICE_ID": "kidbright_01",
    "PUBLISH_INTERVAL_S": 180,
    "DHT_READ_RETRIES": 3,
}

# =============================================================================
# PIN CONFIG (แก้ GPIO ที่นี่)
# =============================================================================
_PINS = {
    "SOIL_ADC_PIN": 32,     # ความชื้นดิน — GPIO 32 (analog)
    "DHT11_PIN": 33,         # DHT11 data — GPIO 33
    "PMS_UART_NUM": 2,       # PMS7003 UART index
    "PMS_UART_RX_PIN": 23,  # PMS7003 sensor TX -> board RX GPIO 23
    "LED_GREEN_PIN": 12,     # active low; -1 = ไม่มี
    "LED_RED_PIN": 2,        # active low; -1 = ไม่มี
}

# ทับค่าจาก secrets.py ถ้ามีบนบอร์ด
try:
    import secrets as _sec
    for _k in _BOARD:
        if hasattr(_sec, _k):
            _BOARD[_k] = getattr(_sec, _k)
    for _k in _PINS:
        if hasattr(_sec, _k):
            _PINS[_k] = getattr(_sec, _k)
except ImportError:
    pass

WIFI_SSID           = _BOARD["WIFI_SSID"]
WIFI_PASSWORD       = _BOARD["WIFI_PASSWORD"]
MQTT_HOST           = _BOARD["MQTT_HOST"]
MQTT_PORT           = int(_BOARD["MQTT_PORT"])
MQTT_TOPIC          = _BOARD["MQTT_TOPIC"]
MQTT_USER           = _BOARD["MQTT_USER"]
MQTT_PASS           = _BOARD["MQTT_PASS"]
DEVICE_ID           = _BOARD["DEVICE_ID"]
PUBLISH_INTERVAL_S  = int(_BOARD["PUBLISH_INTERVAL_S"])
DHT_READ_RETRIES    = int(_BOARD["DHT_READ_RETRIES"])

SOIL_ADC_PIN    = int(_PINS["SOIL_ADC_PIN"])
DHT11_PIN       = int(_PINS["DHT11_PIN"])
PMS_UART_NUM    = int(_PINS["PMS_UART_NUM"])
PMS_UART_RX_PIN = int(_PINS["PMS_UART_RX_PIN"])
LED_GREEN_PIN   = int(_PINS["LED_GREEN_PIN"])
LED_RED_PIN     = int(_PINS["LED_RED_PIN"])

# =============================================================================
# HARDWARE INIT
# =============================================================================
soil = ADC(Pin(SOIL_ADC_PIN))
soil.atten(ADC.ATTN_11DB)

_dht_pin = Pin(DHT11_PIN) if DHT11_PIN in (34,35,36,37,38,39) else Pin(DHT11_PIN, Pin.IN, Pin.PULL_UP)
dht_sensor = dht.DHT11(_dht_pin)

uart = UART(PMS_UART_NUM, baudrate=9600, rx=PMS_UART_RX_PIN) if PMS_UART_RX_PIN >= 0 else None

led_green = Pin(LED_GREEN_PIN, Pin.OUT, value=1) if LED_GREEN_PIN >= 0 else None
led_red   = Pin(LED_RED_PIN,   Pin.OUT, value=1) if LED_RED_PIN   >= 0 else None


def _led_ok():
    if led_green and led_red:
        led_green.value(0); led_red.value(1)
        time.sleep_ms(300)
        led_green.value(1)


def _led_error():
    if led_green and led_red:
        led_green.value(1); led_red.value(0)
        time.sleep_ms(300)
        led_red.value(1)


def _led_working():
    if not (led_green and led_red):
        return
    for _ in range(2):
        led_green.value(0); led_red.value(0)
        time.sleep_ms(150)
        led_green.value(1); led_red.value(1)
        time.sleep_ms(150)


# =============================================================================
# WIFI
# =============================================================================
def _wifi_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    while not wlan.isconnected():
        print("WiFi connecting...")
        _led_working()
        try:
            wlan.disconnect()
        except Exception:
            pass
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        for _ in range(40):
            if wlan.isconnected():
                print("WiFi connected:", wlan.ifconfig()[0])
                return wlan
            time.sleep(0.5)
        print("Retrying...")
        time.sleep(2)
    return wlan


# =============================================================================
# MQTT
# =============================================================================
def _client_id():
    return "%s-%s" % (DEVICE_ID, binascii.hexlify(machine.unique_id()).decode()[:8])


def _mqtt_connect():
    client = MQTTClient(
        _client_id(), MQTT_HOST,
        port=MQTT_PORT, user=MQTT_USER, password=MQTT_PASS, keepalive=120,
    )
    client.connect()
    print("MQTT connected")
    return client


# =============================================================================
# SENSORS
# =============================================================================
def _read_soil() -> int:
    try:
        return int(soil.read())
    except Exception as e:
        print("Soil read error:", e)
        return -1


def _read_dht11() -> tuple:
    time.sleep_ms(500)
    for attempt in range(DHT_READ_RETRIES):
        try:
            dht_sensor.measure()
            time.sleep_ms(120)
            return float(dht_sensor.temperature()), float(dht_sensor.humidity())
        except OSError as e:
            print("DHT11 error (try %d/%d):" % (attempt + 1, DHT_READ_RETRIES), e)
            time.sleep(1.2)
        except Exception as e:
            print("DHT11 error:", e)
            break
    print("DHT11: giving up — check wiring/pull-up")
    return -1.0, -1.0


def _read_pms7003() -> tuple:
    if uart is None:
        return -1, -1, -1
    start = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), start) < 2000:
        if uart.any() >= 32:
            data = uart.read(32)
            if data and len(data) == 32 and data[0] == 0x42 and data[1] == 0x4D:
                return (
                    int(data[10] * 256 + data[11]),
                    int(data[12] * 256 + data[13]),
                    int(data[14] * 256 + data[15]),
                )
        time.sleep_ms(100)
    return -1, -1, -1


# =============================================================================
# PAYLOAD — flat ตรงตาม schema ของตาราง (ทุกฟิลด์ส่งครบเสมอ)
# =============================================================================
def build_payload() -> str:
    soil_v        = _read_soil()
    temp, hum     = _read_dht11()
    pm1, pm25, pm10 = _read_pms7003()

    print("Soil  =", soil_v)
    print("Temp  =", temp, "C  Hum =", hum, "%")
    print("PM1.0 =", pm1, " PM2.5 =", pm25, " PM10 =", pm10)

    return json.dumps({
        "device_id":    DEVICE_ID,
        "soil_moisture": soil_v,
        "temperature":  temp,
        "humidity":     hum,
        "pm1_0":        pm1,
        "pm2_5":        pm25,
        "pm10":         pm10,
    })


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("=" * 45)
    print("KidBright — Field Monitoring")
    print("Device  :", DEVICE_ID)
    print("Topic   :", MQTT_TOPIC)
    print("Interval:", PUBLISH_INTERVAL_S, "s")
    print("PIN map :")
    print("  SOIL  GPIO", SOIL_ADC_PIN)
    print("  DHT11 GPIO", DHT11_PIN)
    print("  PMS   UART%d RX GPIO%d" % (PMS_UART_NUM, PMS_UART_RX_PIN))
    print("=" * 45)

    if uart is not None:
        print("Waiting for dust sensor to stabilize...")
        time.sleep(5)

    wlan = _wifi_connect()
    mqtt = _mqtt_connect()

    reading_count = 0
    while True:
        reading_count += 1
        print("-" * 45)
        print("Reading #%d" % reading_count)

        try:
            if not wlan.isconnected():
                wlan = _wifi_connect()

            payload = build_payload()
            mqtt.publish(MQTT_TOPIC, payload, qos=0)
            print("Published:", payload)
            _led_ok()

        except OSError as e:
            print("Publish error:", e)
            _led_error()
            time.sleep(2)
            try:
                mqtt.disconnect()
            except OSError:
                pass
            mqtt = _mqtt_connect()

        gc.collect()
        print("Sleeping", PUBLISH_INTERVAL_S, "s...")
        time.sleep(PUBLISH_INTERVAL_S)


if __name__ == "__main__":
    main()
