import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"


def _load_env() -> None:
    # override=True: ให้ค่าใน .env มีผลแม้ใน shell จะมี DB_PASSWORD ว่างค้างไว้
    # (ค่าเริ่มต้นของ load_dotenv คือไม่ทับ env ที่ตั้งแล้ว — ทำให้ดูเหมือน .env "ไม่ทำงาน")
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH, override=True)
    elif ENV_EXAMPLE_PATH.exists():
        load_dotenv(dotenv_path=ENV_EXAMPLE_PATH, override=True)


_load_env()

# บัญชีโปรเจกต์ (MQTT + MySQL ที่ iot.cpe.ku.ac.th) — ตั้งใน .env ทับได้
_DEFAULT_USER = "b6710545709"
_DEFAULT_PASSWORD = "paramee.sae@ku.th"

MQTT_HOST = os.getenv("MQTT_HOST", "iot.cpe.ku.ac.th")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "b6710545709/field_monitoring")
MQTT_DEBUG_WILDCARD = os.getenv("MQTT_DEBUG_WILDCARD", "1") == "1"
MQTT_USER = os.getenv("MQTT_USER", _DEFAULT_USER)
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", _DEFAULT_PASSWORD)

DB_HOST = os.getenv("DB_HOST", "iot.cpe.ku.ac.th")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = (os.getenv("DB_USER", _DEFAULT_USER) or "").strip() or _DEFAULT_USER
DB_PASSWORD = (os.getenv("DB_PASSWORD", _DEFAULT_PASSWORD) or "").strip()
DB_NAME = (os.getenv("DB_NAME", "b6710545709") or "").strip() or "b6710545709"

PROCESS_AFTER_MINUTES = int(os.getenv("PROCESS_AFTER_MINUTES", "60"))
PROCESS_POLL_SECONDS = int(os.getenv("PROCESS_POLL_SECONDS", "30"))
BACKFILL_ALL_ON_START = os.getenv("BACKFILL_ALL_ON_START", "1") == "1"


def validate_required_config() -> tuple[bool, str]:
    if not DB_PASSWORD:
        return False, f"[CONFIG] Missing DB_PASSWORD in {ENV_PATH}"
    return True, ""
