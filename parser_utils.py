import json
from typing import Any


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


def parse_payload(raw_payload: bytes) -> dict[str, Any] | None:
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
