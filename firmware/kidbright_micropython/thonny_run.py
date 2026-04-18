"""
Thonny: เปิดไฟล์นี้แล้วกด Run (F5)
- รันวนส่ง MQTT ตาม PUBLISH_INTERVAL_MS เหมือน main.py
- หยุด: ปุ่ม Stop ใน Thonny หรือ Interrupt

ต้องมีบนบอร์ด: main.py — secrets.py ไม่บังคับ (มีแค่ main ก็รันได้)
(ถ้าต้องการให้เปิดไฟวิ่งเองโดยไม่เปิด Thonny — บันทึก main.py บนบอร์ดแล้วรีเซ็ต)
"""

import main

print("[Thonny] เริ่มลูปส่งข้อมูล (กด Stop เพื่อหยุด)")
main.main()
