from typing import Any

# Secondary data (reference thresholds/rules)
# -----------------------------------------------------------------------------
# These are starter values from public guidance + domain practice.
# You should calibrate with local field data.
#
# How to find secondary data:
# 1) Weather thresholds (temperature/humidity):
#    - Start from outdoor activity/heat-stress guidance.
#    - Adjust by local seasonal baseline.
# 2) Air quality thresholds (PM2.5/PM10):
#    - Use recognized AQI/health breakpoints.
# 3) Soil moisture (ADC):
#    - Field-calibrate on real ground states: dry/normal/wet/very_wet.
# 4) Footwear recommendation:
#    - Build rule matrix with coach/groundkeeper input.

TEMP_THRESHOLDS_C = {
    "good": (18.0, 30.0),
    "caution": (30.0, 34.0),
}

HUMIDITY_THRESHOLDS_PCT = {
    "good": (30.0, 75.0),
    "caution": (75.0, 85.0),
}

PM25_THRESHOLDS_UGM3 = {
    "safe_max": 25,
    "moderate_max": 50,
}

PM10_THRESHOLDS_UGM3 = {
    "safe_max": 50,
    "moderate_max": 100,
}

SOIL_ADC_LEVELS = {
    "dry_min": 3200,
    "normal_min": 2200,
    "wet_min": 1200,
}

SCORE_WEIGHTS = {
    "temperature": 0.25,
    "humidity": 0.20,
    "air_quality": 0.35,
    "soil": 0.20,
}


def classify_soil_condition(soil_adc: int | None) -> str:
    if soil_adc is None:
        return "unknown"
    if soil_adc >= SOIL_ADC_LEVELS["dry_min"]:
        return "dry"
    if soil_adc >= SOIL_ADC_LEVELS["normal_min"]:
        return "normal"
    if soil_adc >= SOIL_ADC_LEVELS["wet_min"]:
        return "wet"
    return "very_wet"


def recommend_footwear(soil_condition: str) -> str:
    if soil_condition == "dry":
        return "FG (Firm Ground)"
    if soil_condition in ("wet", "very_wet"):
        return "SG (Soft Ground Cleats)"
    return "TF (Turf Shoes)"
