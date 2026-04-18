"""
รับข้อมูลจากบอร์ดผ่านสาย USB (Serial) แล้วบันทึกลง SQLite ในเครื่อง — ไม่ต้องใช้ MQTT/MySQL

รันหลังเสียบบอร์ด:
  python app_plug.py

กำหนดพอร์ตเอง (ถ้า auto-detect ไม่เจอ):
  SERIAL_PORT=/dev/cu.usbmodem* python app_plug.py
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

import serial
from serial.tools import list_ports

from parser_utils import parse_payload
from scoring import analyze_secondary
from secondary_data import classify_soil_condition, recommend_footwear

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "field_data_local.sqlite"


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode = WAL;
        CREATE TABLE IF NOT EXISTS field_monitoring_raw (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            soil_moisture INTEGER,
            temperature REAL,
            humidity REAL,
            pm1_0 INTEGER,
            pm2_5 INTEGER,
            pm10 INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            processed INTEGER NOT NULL DEFAULT 0,
            processed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS field_monitoring_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_id INTEGER NOT NULL UNIQUE,
            device_id TEXT NOT NULL,
            soil_condition TEXT,
            footwear_recommendation TEXT,
            field_score REAL,
            field_status TEXT,
            air_quality_status TEXT,
            temp_score REAL,
            humidity_score REAL,
            air_quality_score REAL,
            soil_score REAL,
            rain_probability_pct INTEGER,
            rain_forecast_status TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (raw_id) REFERENCES field_monitoring_raw(id)
        );
        CREATE INDEX IF NOT EXISTS idx_raw_device_time
            ON field_monitoring_raw (device_id, created_at);
        """
    )


def _pick_serial_port(explicit: str | None) -> str:
    if explicit:
        return explicit
    env_port = os.getenv("SERIAL_PORT", "").strip()
    if env_port:
        return env_port
    ports = list(list_ports.comports())
    if not ports:
        print(
            "[SERIAL] ไม่พบพอร์ต — เสียบสาย USB หรือระบุ SERIAL_PORT / --port",
            file=sys.stderr,
        )
        sys.exit(1)
    usbish = ("usb", "ch340", "cp210", "ftdi", "serial", "acm", "modem", "wch")
    for p in ports:
        blob = " ".join(
            filter(
                None,
                [p.device, p.description, p.manufacturer or "", p.hwid or ""],
            )
        ).lower()
        if any(k in blob for k in usbish):
            return p.device
    return ports[0].device


def _insert_and_analyze(conn: sqlite3.Connection, parsed: dict) -> int:
    soil_condition = classify_soil_condition(parsed.get("soil_moisture"))
    footwear = recommend_footwear(soil_condition)
    analysis = analyze_secondary(parsed)

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO field_monitoring_raw (
            device_id, soil_moisture, temperature, humidity, pm1_0, pm2_5, pm10
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            parsed["device_id"],
            parsed["soil_moisture"],
            parsed["temperature"],
            parsed["humidity"],
            parsed["pm1_0"],
            parsed["pm2_5"],
            parsed["pm10"],
        ),
    )
    raw_id = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO field_monitoring_analysis (
            raw_id, device_id, soil_condition, footwear_recommendation,
            field_score, field_status, air_quality_status,
            temp_score, humidity_score, air_quality_score, soil_score,
            rain_probability_pct, rain_forecast_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            raw_id,
            parsed["device_id"],
            soil_condition,
            footwear,
            analysis["field_score"],
            analysis["field_status"],
            analysis["air_quality_status"],
            analysis["temp_score"],
            analysis["humidity_score"],
            analysis["air_quality_score"],
            analysis["soil_score"],
            analysis["rain_probability_pct"],
            analysis["rain_forecast_status"],
        ),
    )
    cur.execute(
        """
        UPDATE field_monitoring_raw
        SET processed = 1, processed_at = datetime('now')
        WHERE id = ?
        """,
        (raw_id,),
    )
    conn.commit()
    return raw_id


def main() -> None:
    parser = argparse.ArgumentParser(description="USB Serial → SQLite (plug-and-play)")
    parser.add_argument(
        "--port",
        default=None,
        help="Serial device (default: auto or SERIAL_PORT env)",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=int(os.getenv("SERIAL_BAUD", "115200")),
        help="Baud rate (default 115200 or SERIAL_BAUD)",
    )
    parser.add_argument(
        "--db",
        default=os.getenv("LOCAL_SQLITE_PATH", str(DEFAULT_DB_PATH)),
        help=f"SQLite file path (default: {DEFAULT_DB_PATH})",
    )
    args = parser.parse_args()

    port = _pick_serial_port(args.port)
    db_path = Path(args.db)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    _ensure_schema(conn)

    print(f"[PLUG] Serial: {port} @ {args.baud} baud")
    print(f"[PLUG] Database: {db_path.resolve()}")
    print("[PLUG] Waiting for JSON lines (same format as MQTT payload)...")

    try:
        with serial.Serial(port, args.baud, timeout=1) as ser:
            while True:
                line = ser.readline()
                if not line:
                    continue
                text = line.decode("utf-8", errors="replace").strip()
                if not text or text.startswith("#"):
                    continue
                parsed = parse_payload(line)
                if not parsed:
                    continue
                rid = _insert_and_analyze(conn, parsed)
                print(f"[PLUG] Saved raw_id={rid} device={parsed['device_id']!r}")
    except serial.SerialException as err:
        print(f"[PLUG] Serial error: {err}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[PLUG] Stopped.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
