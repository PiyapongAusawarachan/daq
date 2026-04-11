import threading
import time

import pymysql

from db_utils import fetch_unprocessed_raw_rows, insert_analysis_and_mark_processed
from scoring import analyze_secondary
from secondary_data import classify_soil_condition, recommend_footwear


def process_secondary_data_batch(
    conn: pymysql.connections.Connection,
    process_after_minutes: int,
    batch_size: int = 500,
    include_all: bool = False,
) -> int:
    rows = fetch_unprocessed_raw_rows(conn, process_after_minutes, batch_size, include_all)
    if not rows:
        return 0

    processed_count = 0
    for row in rows:
        soil_condition = classify_soil_condition(row.get("soil_moisture"))
        footwear = recommend_footwear(soil_condition)
        analysis = analyze_secondary(row)

        insert_analysis_and_mark_processed(
            conn=conn,
            raw_id=row["id"],
            device_id=row["device_id"],
            soil_condition=soil_condition,
            footwear_recommendation=footwear,
            field_score=analysis["field_score"],
            field_status=analysis["field_status"],
            air_quality_status=analysis["air_quality_status"],
            temp_score=analysis["temp_score"],
            humidity_score=analysis["humidity_score"],
            air_quality_score=analysis["air_quality_score"],
            soil_score=analysis["soil_score"],
            rain_probability_pct=analysis["rain_probability_pct"],
            rain_forecast_status=analysis["rain_forecast_status"],
        )
        processed_count += 1

    return processed_count


def backfill_all_unprocessed(conn: pymysql.connections.Connection, batch_size: int = 500) -> int:
    total = 0
    while True:
        count = process_secondary_data_batch(
            conn=conn,
            process_after_minutes=0,
            batch_size=batch_size,
            include_all=True,
        )
        if count == 0:
            break
        total += count
    return total


def start_background_processor(
    conn: pymysql.connections.Connection,
    process_after_minutes: int,
    poll_seconds: int,
) -> threading.Thread:
    def _run() -> None:
        while True:
            try:
                count = process_secondary_data_batch(conn, process_after_minutes)
                if count > 0:
                    print(f"[PROCESSOR] Processed rows={count} into field_monitoring_analysis")
            except Exception as err:  # noqa: BLE001
                print(f"[PROCESSOR] Failed: {err}")
            time.sleep(poll_seconds)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread
