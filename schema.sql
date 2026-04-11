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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
