import json
import os
from pathlib import Path
from typing import Any, Dict

import paho.mqtt.client as mqtt
import pymysql
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
elif ENV_EXAMPLE_PATH.exists():
    # Fallback to example config when .env is missing.
    load_dotenv(dotenv_path=ENV_EXAMPLE_PATH)

MQTT_HOST = os.getenv("MQTT_HOST", "iot.cpe.ku.ac.th")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "b6710545709/field_monitoring")
MQTT_DEBUG_WILDCARD = os.getenv("MQTT_DEBUG_WILDCARD", "1") == "1"
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

DB_HOST = os.getenv("DB_HOST", "iot.cpe.ku.ac.th")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "b6710545709")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "b6710545709")

SQL_INSERT = """
INSERT INTO field_monitoring1 (
    device_id, soil_moisture, temperature, humidity, pm1_0, pm2_5, pm10
)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""


def get_db_connection() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
    )


def parse_payload(raw_payload: bytes) -> Dict[str, Any] | None:
    try:
        text = raw_payload.decode("utf-8").strip()
    except UnicodeDecodeError:
        print("[ERROR] Payload is not valid UTF-8")
        return None

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        print("[ERROR] Invalid JSON payload")
        return None

    device_id = data.get("device_id") or "kidbright_01"
    soil_moisture = to_int_or_none(data.get("soil_moisture"))
    temperature = to_float_or_none(data.get("temperature"))
    humidity = to_float_or_none(data.get("humidity"))

    dust = data.get("dust") or {}
    pm1_0 = to_int_or_none(dust.get("pm1_0"))
    pm2_5 = to_int_or_none(dust.get("pm2_5"))
    pm10 = to_int_or_none(dust.get("pm10"))

    return {
        "device_id": device_id,
        "soil_moisture": soil_moisture,
        "temperature": temperature,
        "humidity": humidity,
        "pm1_0": pm1_0,
        "pm2_5": pm2_5,
        "pm10": pm10,
    }


def to_int_or_none(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(float(value))
    except (ValueError, TypeError):
        return None


def to_float_or_none(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (ValueError, TypeError):
        return None


def on_connect(client: mqtt.Client, _userdata: Any, _flags: Dict[str, Any], rc: int) -> None:
    if rc == 0:
        print(f"[MQTT] Connected to {MQTT_HOST}:{MQTT_PORT}")
        subscribe_topic = "b6710545709/#" if MQTT_DEBUG_WILDCARD else MQTT_TOPIC
        client.subscribe(subscribe_topic)
        print(f"[MQTT] Subscribed topic: {subscribe_topic}")
        if MQTT_DEBUG_WILDCARD:
            print("[MQTT] Debug wildcard mode is ON (set MQTT_DEBUG_WILDCARD=0 to disable)")
    else:
        print(f"[MQTT] Connection failed, rc={rc}")


def on_subscribe(_client: mqtt.Client, _userdata: Any, mid: int, granted_qos: list[int]) -> None:
    print(f"[MQTT] SUBACK mid={mid}, granted_qos={granted_qos}")
    if any(qos == 128 for qos in granted_qos):
        print("[MQTT] Subscription rejected by broker (ACL/topic permission issue)")


def on_disconnect(_client: mqtt.Client, _userdata: Any, rc: int) -> None:
    print(f"[MQTT] Disconnected rc={rc}")


def on_message(_client: mqtt.Client, userdata: Dict[str, Any], msg: mqtt.MQTTMessage) -> None:
    print(f"[MQTT] Message received on topic: {msg.topic}")
    print(f"[MQTT] Raw payload: {msg.payload.decode('utf-8', errors='replace')}")

    parsed = parse_payload(msg.payload)
    if not parsed:
        print("[MQTT] Skip message due to parse error")
        return

    values = (
        parsed["device_id"],
        parsed["soil_moisture"],
        parsed["temperature"],
        parsed["humidity"],
        parsed["pm1_0"],
        parsed["pm2_5"],
        parsed["pm10"],
    )

    try:
        conn: pymysql.connections.Connection = userdata["db_conn"]
        with conn.cursor() as cursor:
            affected_rows = cursor.execute(SQL_INSERT, values)
        print(f"[DB] Inserted rows={affected_rows}, values={values}")
    except pymysql.MySQLError as err:
        print(f"[DB] Insert failed: {err}")


def main() -> None:
    if not DB_PASSWORD:
        print(f"[CONFIG] Missing DB_PASSWORD in {ENV_PATH}")
        print("[CONFIG] Please set DB_PASSWORD in .env before running.")
        return

    db_conn = get_db_connection()
    print(f"[DB] Connected to {DB_HOST}:{DB_PORT}/{DB_NAME}")

    client = mqtt.Client(client_id="daq_subscriber_python")
    if MQTT_USER:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
        print(f"[MQTT] Using username auth: {MQTT_USER}")
    else:
        print("[MQTT] Using anonymous auth (no username/password)")
    client.user_data_set({"db_conn": db_conn})
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.")
