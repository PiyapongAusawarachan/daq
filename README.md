# MQTT to MySQL (Python)

รับข้อมูลจาก MQTT topic แล้วบันทึกลงตาราง `field_monitoring1` ใน MySQL

โครงสร้างโค้ดถูกแยกไฟล์ให้ดูง่าย:
- `app.py` main runtime (MQTT callbacks + orchestration)
- `config.py` โหลด `.env` และ validate config
- `parser_utils.py` parse payload + cast type
- `db_utils.py` SQL และฟังก์ชัน raw/analysis DB
- `secondary_data.py` secondary data thresholds/rules + comment วิธีหา
- `scoring.py` คำนวณ Field Suitability Score
- `processor.py` ประมวลผล secondary data แบบ background
- `schema.sql` โครงสร้างตารางสมบูรณ์สำหรับ phpMyAdmin/MySQL
- `api.py` Web API (FastAPI) + เสิร์ฟ dashboard
- `api_queries.py` SQL อ่านอย่างเดียวสำหรับ API
- `templates/dashboard.html` + `static/dashboard.{css,js}` หน้าจอ visualization

## Setup

1. สร้าง virtual environment และติดตั้ง dependencies
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`
2. คัดลอกไฟล์ config
   - `cp .env.example .env`
3. แก้ค่าใน `.env` ให้ถูกต้อง

## Run

- `python app.py`

เมื่อรันแล้ว โปรแกรมจะ:
- connect ไปที่ MQTT broker
- subscribe topic จาก `.env` (หรือ wildcard debug)
- parse JSON payload
- ensure schema ของ `field_monitoring_raw` และ `field_monitoring_analysis` อัตโนมัติ
- insert ข้อมูล sensor ดิบลง `field_monitoring_raw` ทันที
- background processor จะรันทุก `PROCESS_POLL_SECONDS`
- ตอนเริ่มระบบจะ backfill ข้อมูลดิบที่ยังไม่ประมวลผลทั้งหมดก่อน (ถ้า `BACKFILL_ALL_ON_START=1`)
- ประมวลผลเฉพาะข้อมูลดิบที่อายุเกิน `PROCESS_AFTER_MINUTES` (ค่าเริ่มต้น 60 นาที)
- บันทึกผล secondary data ลง `field_monitoring_analysis`

คอลัมน์ที่บันทึก:
- raw table `field_monitoring_raw`: sensor + `created_at` + `processed`
- analysis table `field_monitoring_analysis`:
  `raw_id, device_id, soil_condition, footwear_recommendation, field_score, field_status,`
  `air_quality_status, temp_score, humidity_score, air_quality_score, soil_score,`
  `rain_probability_pct, rain_forecast_status, created_at`

## Web API + Dashboard

รัน API + Dashboard:

```bash
.venv/bin/python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

จากนั้นเปิด:
- `http://localhost:8000/` — Dashboard (กราฟ + คำแนะนำ)
- `http://localhost:8000/docs` — OpenAPI / Swagger UI (auto-generated)

### Endpoints

| Method | Path | คืนค่า |
|---|---|---|
| GET | `/api/health` | สถานะ service + DB |
| GET | `/api/devices` | list devices + last seen |
| GET | `/api/latest` | sensor + analysis ของแถวล่าสุด (join 2 ตาราง) |
| GET | `/api/recommendation` | สรุปการตัดสินใจ: เล่น/รองเท้า/ฝน |
| GET | `/api/summary?hours=24` | avg/min/max + การกระจาย field_status |
| GET | `/api/history?hours=24&limit=200` | time-series สำหรับวาดกราฟ |

> Dashboard เรียกใช้แต่ `/api/*` เท่านั้น ไม่ติดต่อ DB โดยตรง

## Secondary Data Calibration (แนะนำ)

1. เก็บข้อมูลจริงจากสนามอย่างน้อย 1-2 สัปดาห์
2. เทียบค่า ADC กับสภาพดินจริง (dry/normal/wet/very_wet)
3. ปรับ threshold ใน `secondary_data.py`
4. ทดสอบคะแนนใน `scoring.py` แล้วปรับน้ำหนัก `SCORE_WEIGHTS`
