"""FastAPI Web API + Dashboard for the DAQ project.

จุดประสงค์:
- เปิด HTTP API ที่ให้ข้อมูลแบบ "ตัดสินใจได้" (analysis + recommendation)
  ไม่ใช่แค่ raw จาก MQTT
- เสิร์ฟ dashboard HTML ที่เรียกใช้ API ตัวเองเท่านั้น (ไม่แตะ DB ตรง ๆ)

รัน:
  uvicorn api:app --reload --host 0.0.0.0 --port 8000

จากนั้นเปิด:
  http://localhost:8000/         -> dashboard
  http://localhost:8000/docs     -> OpenAPI / Swagger
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from queue import Empty, Queue
from threading import Lock
from typing import Any

import pymysql
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from api_queries import fetch_devices, fetch_history, fetch_latest, fetch_summary
from config import API_DB_POOL_SIZE, DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from db_utils import get_db_connection

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="Smart Sport Field Monitoring API",
    description=(
        "Web API for the Smart Sports Field Monitoring System.\n\n"
        "Returns **integrated / secondary** information derived from raw sensor data — "
        "field suitability score, air-quality status, footwear recommendation and rain "
        "forecast — none of which are present in the raw MQTT payload."
    ),
    version="1.0.0",
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


class MySQLConnectionPool:
    def __init__(self, size: int) -> None:
        self.size = max(1, size)
        self._queue: Queue[pymysql.connections.Connection] = Queue(maxsize=self.size)
        self._created = 0
        self._lock = Lock()

    def _new_connection(self) -> pymysql.connections.Connection:
        return get_db_connection(DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME)

    def acquire(self) -> pymysql.connections.Connection:
        try:
            conn = self._queue.get_nowait()
            conn.ping(reconnect=True)
            return conn
        except Empty:
            pass
        except pymysql.MySQLError:
            # Broken connection: drop and create a new one below.
            pass

        with self._lock:
            if self._created < self.size:
                conn = self._new_connection()
                self._created += 1
                return conn

        conn = self._queue.get()
        conn.ping(reconnect=True)
        return conn

    def release(self, conn: pymysql.connections.Connection) -> None:
        try:
            conn.ping(reconnect=True)
            self._queue.put_nowait(conn)
        except Exception:  # noqa: BLE001
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass
            with self._lock:
                self._created = max(0, self._created - 1)


pool = MySQLConnectionPool(size=API_DB_POOL_SIZE)


# ---------------------------------------------------------------------------
# DB connection pool (reuse connections, keep connection count stable)
# ---------------------------------------------------------------------------
def get_conn() -> pymysql.connections.Connection:
    if not DB_PASSWORD:
        raise HTTPException(status_code=500, detail="DB_PASSWORD is not configured.")
    try:
        conn = pool.acquire()
    except pymysql.MySQLError as err:
        raise HTTPException(
            status_code=503, detail=f"Database is busy or unavailable: {err}"
        ) from err

    try:
        yield conn
    finally:
        pool.release(conn)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _coerce(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, Decimal):
        return float(value)
    return value


def _serialize(row: dict) -> dict:
    return {k: _coerce(v) for k, v in row.items()}


def _ensure_latest(conn, device_id: str) -> dict:
    latest = fetch_latest(conn, device_id)
    if not latest:
        raise HTTPException(status_code=404, detail="No data available yet.")
    return latest


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["meta"], summary="Service and database health check")
def api_health(conn: pymysql.connections.Connection = Depends(get_conn)) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
        ok = cur.fetchone()[0] == 1
    return {"status": "ok" if ok else "down", "database": DB_NAME}


@app.get("/api/devices", tags=["meta"], summary="List devices that have reported data")
def api_devices(conn: pymysql.connections.Connection = Depends(get_conn)) -> list[dict]:
    return [_serialize(d) for d in fetch_devices(conn)]


@app.get(
    "/api/latest",
    tags=["live"],
    summary="Latest reading joined with its analysis row",
)
def api_latest(
    device_id: str = Query("", description="Filter by device_id; leave empty for the most recent of any device"),
    conn: pymysql.connections.Connection = Depends(get_conn),
) -> dict:
    return _serialize(_ensure_latest(conn, device_id))


@app.get(
    "/api/recommendation",
    tags=["live"],
    summary="Decision-ready summary derived from the latest analysis",
)
def api_recommendation(
    device_id: str = Query("", description="Filter by device_id; leave empty for any device"),
    conn: pymysql.connections.Connection = Depends(get_conn),
) -> dict:
    latest = _ensure_latest(conn, device_id)
    play_decision = (
        "Play"
        if latest.get("field_status") == "Good"
        else "Play with Caution"
        if latest.get("field_status") == "Caution"
        else "Do Not Play"
        if latest.get("field_status") == "Not Recommended"
        else "Unknown"
    )
    return _serialize(
        {
            "device_id": latest.get("device_id"),
            "as_of": latest.get("analysis_created_at") or latest.get("raw_created_at"),
            "field_status": latest.get("field_status"),
            "field_score": latest.get("field_score"),
            "play_decision": play_decision,
            "footwear_recommendation": latest.get("footwear_recommendation"),
            "soil_condition": latest.get("soil_condition"),
            "air_quality_status": latest.get("air_quality_status"),
            "rain_probability_pct": latest.get("rain_probability_pct"),
            "rain_forecast_status": latest.get("rain_forecast_status"),
        }
    )


@app.get(
    "/api/summary",
    tags=["analytics"],
    summary="Aggregated statistics over the last N hours",
)
def api_summary(
    hours: int = Query(24, ge=1, le=24 * 14, description="Look-back window in hours"),
    device_id: str = Query("", description="Filter by device_id; leave empty for all devices"),
    conn: pymysql.connections.Connection = Depends(get_conn),
) -> dict:
    summary = fetch_summary(conn, hours=hours, device_id=device_id)
    summary["aggregates"] = _serialize(summary.get("aggregates") or {})
    return summary


@app.get(
    "/api/history",
    tags=["analytics"],
    summary="Time-series history (sensors + analysis) for charting",
)
def api_history(
    hours: int = Query(24, ge=1, le=24 * 14, description="Look-back window in hours"),
    limit: int = Query(200, ge=10, le=2000, description="Maximum number of points to return"),
    device_id: str = Query("", description="Filter by device_id; leave empty for all devices"),
    conn: pymysql.connections.Connection = Depends(get_conn),
) -> list[dict]:
    rows = fetch_history(conn, hours=hours, limit=limit, device_id=device_id)
    # Return oldest -> newest so the chart can plot left-to-right.
    rows.reverse()
    return [_serialize(r) for r in rows]


# ---------------------------------------------------------------------------
# Dashboard (HTML)
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, tags=["dashboard"], include_in_schema=False)
def dashboard(request: Request) -> Any:
    return templates.TemplateResponse("dashboard.html", {"request": request})


# Convenience JSON for empty 404 case
@app.exception_handler(404)
def _not_found_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc, HTTPException) else "Not Found"
    return JSONResponse(status_code=404, content={"detail": detail})
