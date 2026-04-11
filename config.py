import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"


def _load_env() -> None:
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH)
    elif ENV_EXAMPLE_PATH.exists():
        # Fallback for first-time setup.
        load_dotenv(dotenv_path=ENV_EXAMPLE_PATH)


_load_env()

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

PROCESS_AFTER_MINUTES = int(os.getenv("PROCESS_AFTER_MINUTES", "60"))
PROCESS_POLL_SECONDS = int(os.getenv("PROCESS_POLL_SECONDS", "30"))
BACKFILL_ALL_ON_START = os.getenv("BACKFILL_ALL_ON_START", "1") == "1"


def validate_required_config() -> tuple[bool, str]:
    if not DB_PASSWORD:
        return False, f"[CONFIG] Missing DB_PASSWORD in {ENV_PATH}"
    return True, ""
