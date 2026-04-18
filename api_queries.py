"""Read-only SQL helpers used by the Web API.

ฟังก์ชันที่นี่ "อ่านอย่างเดียว" และคืนข้อมูลที่ผ่านการ join/aggregate แล้ว
เพื่อให้ฝั่ง API ส่งค่าที่ "ใช้งานได้จริง" — ไม่ใช่ raw ที่ทำซ้ำกับ MQTT
"""

from __future__ import annotations

from typing import Any

import pymysql

SQL_LATEST_RAW = """
SELECT
    id              AS raw_id,
    device_id,
    soil_moisture, temperature, humidity,
    pm1_0, pm2_5, pm10,
    created_at      AS raw_created_at
FROM field_monitoring_raw
WHERE (%s = '' OR device_id = %s)
ORDER BY id DESC
LIMIT 1
"""

SQL_LATEST_ANALYSIS = """
SELECT
    a.raw_id,
    a.device_id,
    a.field_score, a.field_status,
    a.soil_condition, a.footwear_recommendation,
    a.air_quality_status,
    a.temp_score, a.humidity_score, a.air_quality_score, a.soil_score,
    a.rain_probability_pct, a.rain_forecast_status,
    a.created_at      AS analysis_created_at
FROM field_monitoring_analysis a
WHERE (%s = '' OR a.device_id = %s)
ORDER BY a.id DESC
LIMIT 1
"""

SQL_HISTORY = """
SELECT
    r.id, r.device_id, r.created_at,
    NULLIF(r.soil_moisture, -1) AS soil_moisture,
    NULLIF(r.temperature, -1)   AS temperature,
    NULLIF(r.humidity, -1)      AS humidity,
    NULLIF(r.pm1_0, -1)         AS pm1_0,
    NULLIF(r.pm2_5, -1)         AS pm2_5,
    NULLIF(r.pm10, -1)          AS pm10,
    a.field_score, a.field_status, a.air_quality_status,
    a.rain_probability_pct
FROM field_monitoring_raw r
LEFT JOIN field_monitoring_analysis a ON a.raw_id = r.id
WHERE r.created_at >= (NOW() - INTERVAL %s HOUR)
  AND (%s = '' OR r.device_id = %s)
ORDER BY r.id DESC
LIMIT %s
"""

# Aggregates ignore -1 (sensor-error sentinel) by converting to NULL first.
SQL_SUMMARY_AGG = """
SELECT
    COUNT(*)                              AS row_count,
    AVG(NULLIF(r.temperature, -1))        AS avg_temp,
    MIN(NULLIF(r.temperature, -1))        AS min_temp,
    MAX(NULLIF(r.temperature, -1))        AS max_temp,
    AVG(NULLIF(r.humidity, -1))           AS avg_humidity,
    MIN(NULLIF(r.humidity, -1))           AS min_humidity,
    MAX(NULLIF(r.humidity, -1))           AS max_humidity,
    AVG(NULLIF(r.pm2_5, -1))              AS avg_pm25,
    MIN(NULLIF(r.pm2_5, -1))              AS min_pm25,
    MAX(NULLIF(r.pm2_5, -1))              AS max_pm25,
    AVG(NULLIF(r.pm10, -1))               AS avg_pm10,
    MIN(NULLIF(r.pm10, -1))               AS min_pm10,
    MAX(NULLIF(r.pm10, -1))               AS max_pm10,
    AVG(NULLIF(r.soil_moisture, -1))      AS avg_soil,
    MIN(NULLIF(r.soil_moisture, -1))      AS min_soil,
    MAX(NULLIF(r.soil_moisture, -1))      AS max_soil,
    AVG(a.field_score)                    AS avg_field_score,
    AVG(a.rain_probability_pct)           AS avg_rain_prob
FROM field_monitoring_raw r
LEFT JOIN field_monitoring_analysis a ON a.raw_id = r.id
WHERE r.created_at >= (NOW() - INTERVAL %s HOUR)
  AND (%s = '' OR r.device_id = %s)
"""

# Per-field "last known valid value" (used to fill -1 in /api/latest).
SQL_LAST_VALID_FIELD_TEMPLATE = """
SELECT {field}, created_at
FROM field_monitoring_raw
WHERE {field} IS NOT NULL
  AND {field} <> -1
  AND (%s = '' OR device_id = %s)
ORDER BY id DESC
LIMIT 1
"""

SENSOR_FIELDS = ("soil_moisture", "temperature", "humidity", "pm1_0", "pm2_5", "pm10")

SQL_STATUS_DISTRIBUTION = """
SELECT a.field_status, COUNT(*) AS n
FROM field_monitoring_raw r
JOIN field_monitoring_analysis a ON a.raw_id = r.id
WHERE r.created_at >= (NOW() - INTERVAL %s HOUR)
  AND (%s = '' OR r.device_id = %s)
GROUP BY a.field_status
"""

SQL_DEVICES = """
SELECT
    device_id,
    COUNT(*)        AS total_rows,
    MAX(created_at) AS last_seen
FROM field_monitoring_raw
GROUP BY device_id
ORDER BY last_seen DESC
"""


def _row_to_dict(cursor: pymysql.cursors.Cursor, row: tuple) -> dict:
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


def _fetch_last_valid_value(
    conn: pymysql.connections.Connection,
    field: str,
    device_id: str,
) -> tuple[Any, Any]:
    """Return (value, created_at) of the most recent row whose `field` is not -1."""
    sql = SQL_LAST_VALID_FIELD_TEMPLATE.format(field=field)
    with conn.cursor() as cur:
        cur.execute(sql, (device_id, device_id))
        row = cur.fetchone()
        if not row:
            return None, None
        return row[0], row[1]


def fetch_latest(conn: pymysql.connections.Connection, device_id: str = "") -> dict | None:
    """Return the latest raw row merged with the latest available analysis row.

    Behavior:
    - If a sensor field on the latest row is `-1` (sensor error), we substitute the
      most recent *valid* value for that field and mark it in `stale_fields`.
    - Analysis values come from the most recent analysis row, even if its raw_id is
      older than the very last raw sample (because analysis runs on a delay).
    """
    with conn.cursor() as cur:
        cur.execute(SQL_LATEST_RAW, (device_id, device_id))
        raw_row = cur.fetchone()
        if not raw_row:
            return None
        merged = _row_to_dict(cur, raw_row)

    stale_fields: list[str] = []
    for field in SENSOR_FIELDS:
        value = merged.get(field)
        if value is None or value == -1:
            replacement, replaced_at = _fetch_last_valid_value(conn, field, device_id)
            if replacement is not None:
                merged[field] = replacement
                stale_fields.append(field)
            else:
                merged[field] = None
    merged["stale_fields"] = stale_fields

    with conn.cursor() as cur:

        cur.execute(SQL_LATEST_ANALYSIS, (device_id, device_id))
        analysis_row = cur.fetchone()
        if analysis_row:
            analysis = _row_to_dict(cur, analysis_row)
            # Track whether the analysis really matches the latest raw or is older.
            merged["analysis_from_raw_id"] = analysis.get("raw_id")
            merged["analysis_is_latest"] = analysis.get("raw_id") == merged.get("raw_id")
            for key in (
                "field_score",
                "field_status",
                "soil_condition",
                "footwear_recommendation",
                "air_quality_status",
                "temp_score",
                "humidity_score",
                "air_quality_score",
                "soil_score",
                "rain_probability_pct",
                "rain_forecast_status",
                "analysis_created_at",
            ):
                merged[key] = analysis.get(key)
        else:
            merged["analysis_from_raw_id"] = None
            merged["analysis_is_latest"] = False
            for key in (
                "field_score",
                "field_status",
                "soil_condition",
                "footwear_recommendation",
                "air_quality_status",
                "temp_score",
                "humidity_score",
                "air_quality_score",
                "soil_score",
                "rain_probability_pct",
                "rain_forecast_status",
                "analysis_created_at",
            ):
                merged[key] = None
        return merged


def fetch_history(
    conn: pymysql.connections.Connection,
    hours: int = 24,
    limit: int = 200,
    device_id: str = "",
) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(SQL_HISTORY, (hours, device_id, device_id, limit))
        rows = cur.fetchall()
        result = [_row_to_dict(cur, r) for r in rows]

    # Rows are returned newest-first by SQL. Forward-fill on the time-ordered
    # series (oldest -> newest) so a single -1 reading does not create a gap.
    if not result:
        return result
    result.reverse()
    last_valid: dict[str, Any] = {}
    for row in result:
        for field in SENSOR_FIELDS:
            value = row.get(field)
            if value is None and field in last_valid:
                row[field] = last_valid[field]
            elif value is not None:
                last_valid[field] = value
    result.reverse()  # caller expects newest-first; api.py will reverse again for charts
    return result


def fetch_summary(
    conn: pymysql.connections.Connection,
    hours: int = 24,
    device_id: str = "",
) -> dict:
    with conn.cursor() as cur:
        cur.execute(SQL_SUMMARY_AGG, (hours, device_id, device_id))
        agg_row = cur.fetchone()
        agg = _row_to_dict(cur, agg_row) if agg_row else {}

        cur.execute(SQL_STATUS_DISTRIBUTION, (hours, device_id, device_id))
        dist_rows = cur.fetchall()
        distribution = {r[0] or "Unknown": int(r[1]) for r in dist_rows}

    return {
        "window_hours": hours,
        "device_id": device_id or "all",
        "aggregates": agg,
        "status_distribution": distribution,
    }


def fetch_devices(conn: pymysql.connections.Connection) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(SQL_DEVICES)
        return [_row_to_dict(cur, r) for r in cur.fetchall()]
