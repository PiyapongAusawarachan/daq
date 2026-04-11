from typing import Any

import paho.mqtt.client as mqtt
import pymysql

from config import (
    BACKFILL_ALL_ON_START,
    DB_HOST,
    DB_NAME,
    DB_PASSWORD,
    DB_PORT,
    DB_USER,
    MQTT_DEBUG_WILDCARD,
    MQTT_HOST,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_TOPIC,
    MQTT_USER,
    PROCESS_AFTER_MINUTES,
    PROCESS_POLL_SECONDS,
    validate_required_config,
)
from db_utils import ensure_field_monitoring_schema, get_db_connection, insert_field_monitoring_raw
from parser_utils import parse_payload
from processor import backfill_all_unprocessed, start_background_processor

def on_connect(client: mqtt.Client, _userdata: Any, _flags: dict[str, Any], rc: int) -> None:
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


def on_message(_client: mqtt.Client, userdata: dict[str, Any], msg: mqtt.MQTTMessage) -> None:
    print(f"[MQTT] Message received on topic: {msg.topic}")
    print(f"[MQTT] Raw payload: {msg.payload.decode('utf-8', errors='replace')}")

    parsed = parse_payload(msg.payload)
    if not parsed:
        print("[MQTT] Skip message due to parse error")
        return

    try:
        conn: pymysql.connections.Connection = userdata["db_conn"]
        affected_rows = insert_field_monitoring_raw(conn, parsed)
        print(f"[DB] Inserted rows={affected_rows}, values={parsed}")
    except pymysql.MySQLError as err:
        print(f"[DB] Insert failed: {err}")


def main() -> None:
    is_valid, error_message = validate_required_config()
    if not is_valid:
        print(error_message)
        print("[CONFIG] Please set DB_PASSWORD in .env before running.")
        return

    db_conn = get_db_connection(DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME)
    ensure_field_monitoring_schema(db_conn, DB_NAME)
    print("[DB] Schema ready: field_monitoring_raw + field_monitoring_analysis")
    print(f"[DB] Connected to {DB_HOST}:{DB_PORT}/{DB_NAME}")
    if BACKFILL_ALL_ON_START:
        total_backfilled = backfill_all_unprocessed(db_conn)
        print(f"[PROCESSOR] Initial backfill completed, rows={total_backfilled}")
    start_background_processor(db_conn, PROCESS_AFTER_MINUTES, PROCESS_POLL_SECONDS)
    print(
        "[PROCESSOR] Started background processor "
        f"(process_after_minutes={PROCESS_AFTER_MINUTES}, poll_seconds={PROCESS_POLL_SECONDS})"
    )

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
