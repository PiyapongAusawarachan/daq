# MQTT to MySQL (Python)

รับข้อมูลจาก MQTT topic แล้วบันทึกลงตาราง `field_monitoring` ใน MySQL

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
- subscribe topic `b6710545709/field_monitoring`
- parse JSON payload
- insert ข้อมูลลง `field_monitoring (device_id, soil_status, pm1_0, pm2_5, pm10)`
