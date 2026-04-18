"""
Thonny: เปิดไฟล์นี้แล้วกด Run (F5)
- เชื่อม WiFi → ส่ง MQTT หนึ่งครั้ง → ตัดการเชื่อม → จบ (ดีสำหรับทดสอบ)

ต้องมีบนบอร์ด: main.py (หรือ kidbright_main.py บันทึกเป็น main.py) — secrets.py ไม่บังคับ
"""

import main

print("[Thonny] WiFi...")
wlan = main._wifi_connect()
if not wlan.isconnected():
    print("[Thonny] WiFi ไม่สำเร็จ — ตรวจ secrets.py (SSID/รหัส)")
else:
    print("[Thonny] IP:", wlan.ifconfig()[0])

print("[Thonny] MQTT connect...")
client = main._mqtt_connect()
payload = main.build_payload()
topic = main.MQTT_TOPIC
client.publish(topic, payload, qos=0)
client.disconnect()
print("[Thonny] ส่งแล้ว topic=", topic)
print("[Thonny] payload=", payload)
