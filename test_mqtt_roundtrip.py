import json
import threading
import time

import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish

from config import MQTT_HOST, MQTT_PASSWORD, MQTT_PORT, MQTT_TOPIC, MQTT_USER

received_event = threading.Event()


def on_connect(client: mqtt.Client, _userdata, _flags, rc: int):
    if rc == 0:
        print(f"[TEST] Connected subscriber to {MQTT_HOST}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC, qos=0)
        print(f"[TEST] Subscribed: {MQTT_TOPIC}")
    else:
        print(f"[TEST] Subscriber connect failed rc={rc}")


def on_message(_client: mqtt.Client, _userdata, msg: mqtt.MQTTMessage):
    print(f"[TEST] Received topic={msg.topic}")
    print(f"[TEST] Payload={msg.payload.decode('utf-8', errors='replace')}")
    received_event.set()


def main():
    sub = mqtt.Client(client_id="daq_test_subscriber")
    if MQTT_USER:
        sub.username_pw_set(MQTT_USER, MQTT_PASSWORD or "")
        print(f"[TEST] MQTT auth user={MQTT_USER!r}")
    sub.on_connect = on_connect
    sub.on_message = on_message
    sub.connect(MQTT_HOST, MQTT_PORT, 60)
    sub.loop_start()

    time.sleep(1.5)
    # โครงเดียวกับ test เดิมใน repo + ตรง parse_payload
    payload = {
        "soil_moisture": 4095,
        "device_id": "kidbright_01",
        "temperature": 27,
        "humidity": 83,
        "dust": {"pm10": 35, "pm1_0": 16, "pm2_5": 35},
    }
    auth = {"username": MQTT_USER, "password": MQTT_PASSWORD or ""} if MQTT_USER else None
    publish.single(
        MQTT_TOPIC,
        json.dumps(payload),
        hostname=MQTT_HOST,
        port=MQTT_PORT,
        qos=0,
        auth=auth,
    )
    print("[TEST] Published one test payload")

    print("[TEST] Waiting up to 3 seconds for incoming message...")
    if received_event.wait(timeout=3):
        print("[TEST] MQTT roundtrip OK")
    else:
        print("[TEST] No message received within timeout")

    sub.loop_stop()
    sub.disconnect()


if __name__ == "__main__":
    main()
