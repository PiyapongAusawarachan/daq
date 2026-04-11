import pymysql

SQL_INSERT_RAW = """
INSERT INTO field_monitoring_raw (
    device_id, soil_moisture, temperature, humidity, pm1_0, pm2_5, pm10
)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

SQL_SELECT_UNPROCESSED = """
SELECT id, device_id, soil_moisture, temperature, humidity, pm1_0, pm2_5, pm10, created_at
FROM field_monitoring_raw
WHERE processed = 0
  AND created_at <= (NOW() - INTERVAL %s MINUTE)
ORDER BY id ASC
LIMIT %s
"""

SQL_SELECT_UNPROCESSED_ALL = """
SELECT id, device_id, soil_moisture, temperature, humidity, pm1_0, pm2_5, pm10, created_at
FROM field_monitoring_raw
WHERE processed = 0
ORDER BY id ASC
LIMIT %s
"""

SQL_INSERT_ANALYSIS = """
INSERT INTO field_monitoring_analysis (
    raw_id, device_id, soil_condition, footwear_recommendation,
    field_score, field_status, air_quality_status,
    temp_score, humidity_score, air_quality_score, soil_score,
    rain_probability_pct, rain_forecast_status
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

SQL_MARK_PROCESSED = """
UPDATE field_monitoring_raw
SET processed = 1, processed_at = NOW()
WHERE id = %s
"""


def get_db_connection(
    db_host: str,
    db_port: int,
    db_user: str,
    db_password: str,
    db_name: str,
) -> pymysql.connections.Connection:
    return pymysql.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name,
        autocommit=True,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.Cursor,
    )


def ensure_field_monitoring_schema(conn: pymysql.connections.Connection, _db_name: str) -> None:
    create_raw_sql = """
    CREATE TABLE IF NOT EXISTS field_monitoring_raw (
        id INT NOT NULL AUTO_INCREMENT,
        device_id VARCHAR(50) NOT NULL,
        soil_moisture INT NULL,
        temperature FLOAT NULL,
        humidity FLOAT NULL,
        pm1_0 INT NULL,
        pm2_5 INT NULL,
        pm10 INT NULL,
        created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
        processed TINYINT(1) NOT NULL DEFAULT 0,
        processed_at TIMESTAMP NULL DEFAULT NULL,
        PRIMARY KEY (id),
        INDEX idx_device_time (device_id, created_at),
        INDEX idx_raw_process_time (processed, created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """

    create_analysis_sql = """
    CREATE TABLE IF NOT EXISTS field_monitoring_analysis (
        id INT NOT NULL AUTO_INCREMENT,
        raw_id INT NOT NULL,
        device_id VARCHAR(50) NOT NULL,
        soil_condition VARCHAR(20) NULL,
        footwear_recommendation VARCHAR(50) NULL,
        field_score FLOAT NULL,
        field_status VARCHAR(30) NULL,
        air_quality_status VARCHAR(20) NULL,
        temp_score FLOAT NULL,
        humidity_score FLOAT NULL,
        air_quality_score FLOAT NULL,
        soil_score FLOAT NULL,
        rain_probability_pct INT NULL,
        rain_forecast_status VARCHAR(30) NULL,
        created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uq_raw_id (raw_id),
        INDEX idx_analysis_device_time (device_id, created_at),
        CONSTRAINT fk_analysis_raw
            FOREIGN KEY (raw_id) REFERENCES field_monitoring_raw(id)
            ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """

    with conn.cursor() as cursor:
        cursor.execute(create_raw_sql)
        cursor.execute(create_analysis_sql)
        cursor.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='field_monitoring_analysis'
            """
        )
        existing_columns = {row[0] for row in cursor.fetchall()}
        required_columns = {
            "air_quality_status": (
                "ALTER TABLE field_monitoring_analysis ADD COLUMN air_quality_status VARCHAR(20) NULL"
            ),
            "temp_score": "ALTER TABLE field_monitoring_analysis ADD COLUMN temp_score FLOAT NULL",
            "humidity_score": "ALTER TABLE field_monitoring_analysis ADD COLUMN humidity_score FLOAT NULL",
            "air_quality_score": (
                "ALTER TABLE field_monitoring_analysis ADD COLUMN air_quality_score FLOAT NULL"
            ),
            "soil_score": "ALTER TABLE field_monitoring_analysis ADD COLUMN soil_score FLOAT NULL",
            "rain_probability_pct": (
                "ALTER TABLE field_monitoring_analysis ADD COLUMN rain_probability_pct INT NULL"
            ),
            "rain_forecast_status": (
                "ALTER TABLE field_monitoring_analysis ADD COLUMN rain_forecast_status VARCHAR(30) NULL"
            ),
        }
        for col_name, alter_sql in required_columns.items():
            if col_name not in existing_columns:
                cursor.execute(alter_sql)


def insert_field_monitoring_raw(conn: pymysql.connections.Connection, parsed: dict) -> int:
    values = (
        parsed["device_id"],
        parsed["soil_moisture"],
        parsed["temperature"],
        parsed["humidity"],
        parsed["pm1_0"],
        parsed["pm2_5"],
        parsed["pm10"],
    )
    with conn.cursor() as cursor:
        return cursor.execute(SQL_INSERT_RAW, values)


def fetch_unprocessed_raw_rows(
    conn: pymysql.connections.Connection,
    process_after_minutes: int,
    batch_size: int = 500,
    include_all: bool = False,
) -> list[dict]:
    with conn.cursor() as cursor:
        if include_all:
            cursor.execute(SQL_SELECT_UNPROCESSED_ALL, (batch_size,))
        else:
            cursor.execute(SQL_SELECT_UNPROCESSED, (process_after_minutes, batch_size))
        rows = cursor.fetchall()
    return [
        {
            "id": row[0],
            "device_id": row[1],
            "soil_moisture": row[2],
            "temperature": row[3],
            "humidity": row[4],
            "pm1_0": row[5],
            "pm2_5": row[6],
            "pm10": row[7],
            "created_at": row[8],
        }
        for row in rows
    ]


def insert_analysis_and_mark_processed(
    conn: pymysql.connections.Connection,
    raw_id: int,
    device_id: str,
    soil_condition: str,
    footwear_recommendation: str,
    field_score: float,
    field_status: str,
    air_quality_status: str,
    temp_score: float,
    humidity_score: float,
    air_quality_score: float,
    soil_score: float,
    rain_probability_pct: int,
    rain_forecast_status: str,
) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            SQL_INSERT_ANALYSIS,
            (
                raw_id,
                device_id,
                soil_condition,
                footwear_recommendation,
                field_score,
                field_status,
                air_quality_status,
                temp_score,
                humidity_score,
                air_quality_score,
                soil_score,
                rain_probability_pct,
                rain_forecast_status,
            ),
        )
        cursor.execute(SQL_MARK_PROCESSED, (raw_id,))
