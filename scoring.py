from secondary_data import (
    HUMIDITY_THRESHOLDS_PCT,
    PM10_THRESHOLDS_UGM3,
    PM25_THRESHOLDS_UGM3,
    SCORE_WEIGHTS,
    TEMP_THRESHOLDS_C,
    classify_soil_condition,
)


def _score_temperature(temp_c: float | None) -> float:
    if temp_c is None:
        return 50.0
    good_min, good_max = TEMP_THRESHOLDS_C["good"]
    caution_min, caution_max = TEMP_THRESHOLDS_C["caution"]
    if good_min <= temp_c <= good_max:
        return 100.0
    if caution_min <= temp_c <= caution_max:
        return 65.0
    return 30.0


def _score_humidity(humidity: float | None) -> float:
    if humidity is None:
        return 50.0
    good_min, good_max = HUMIDITY_THRESHOLDS_PCT["good"]
    caution_min, caution_max = HUMIDITY_THRESHOLDS_PCT["caution"]
    if good_min <= humidity <= good_max:
        return 100.0
    if caution_min <= humidity <= caution_max:
        return 65.0
    return 35.0


def _pm_level_score(value: int | None, safe_max: int, moderate_max: int) -> float:
    if value is None:
        return 50.0
    if value <= safe_max:
        return 100.0
    if value <= moderate_max:
        return 65.0
    return 20.0


def _score_air_quality(pm2_5: int | None, pm10: int | None) -> float:
    pm25_score = _pm_level_score(
        pm2_5, PM25_THRESHOLDS_UGM3["safe_max"], PM25_THRESHOLDS_UGM3["moderate_max"]
    )
    pm10_score = _pm_level_score(
        pm10, PM10_THRESHOLDS_UGM3["safe_max"], PM10_THRESHOLDS_UGM3["moderate_max"]
    )
    return (pm25_score + pm10_score) / 2


def _air_quality_status(pm2_5: int | None, pm10: int | None) -> str:
    if pm2_5 is None and pm10 is None:
        return "Unknown"
    if (
        (pm2_5 is not None and pm2_5 > PM25_THRESHOLDS_UGM3["moderate_max"])
        or (pm10 is not None and pm10 > PM10_THRESHOLDS_UGM3["moderate_max"])
    ):
        return "Unhealthy"
    if (
        (pm2_5 is not None and pm2_5 > PM25_THRESHOLDS_UGM3["safe_max"])
        or (pm10 is not None and pm10 > PM10_THRESHOLDS_UGM3["safe_max"])
    ):
        return "Moderate"
    return "Good"


def _score_soil(soil_moisture: int | None) -> float:
    condition = classify_soil_condition(soil_moisture)
    if condition == "normal":
        return 100.0
    if condition in ("dry", "wet"):
        return 70.0
    if condition == "very_wet":
        return 30.0
    return 50.0


def _rain_probability_percent(
    temperature: float | None,
    humidity: float | None,
    soil_moisture: int | None,
) -> int:
    # Simple heuristic forecast (starter): humidity and wet ground drive rain chance.
    prob = 10
    if humidity is not None:
        if humidity >= 90:
            prob += 55
        elif humidity >= 80:
            prob += 35
        elif humidity >= 70:
            prob += 20

    soil_condition = classify_soil_condition(soil_moisture)
    if soil_condition == "very_wet":
        prob += 20
    elif soil_condition == "wet":
        prob += 10

    if temperature is not None and 24 <= temperature <= 32:
        prob += 10

    return max(0, min(100, prob))


def _rain_forecast_status(rain_prob_pct: int) -> str:
    if rain_prob_pct >= 70:
        return "High chance of rain"
    if rain_prob_pct >= 40:
        return "Possible rain"
    return "Low chance of rain"


def calculate_field_score(parsed: dict) -> tuple[float, str]:
    score_t = _score_temperature(parsed.get("temperature"))
    score_h = _score_humidity(parsed.get("humidity"))
    score_aq = _score_air_quality(parsed.get("pm2_5"), parsed.get("pm10"))
    score_s = _score_soil(parsed.get("soil_moisture"))

    total_score = (
        score_t * SCORE_WEIGHTS["temperature"]
        + score_h * SCORE_WEIGHTS["humidity"]
        + score_aq * SCORE_WEIGHTS["air_quality"]
        + score_s * SCORE_WEIGHTS["soil"]
    )

    status = "Good"
    if total_score < 80:
        status = "Caution"
    if total_score < 55:
        status = "Not Recommended"

    # Hard-stop rule for unsafe air quality.
    pm2_5 = parsed.get("pm2_5")
    pm10 = parsed.get("pm10")
    if (
        pm2_5 is not None
        and pm2_5 > PM25_THRESHOLDS_UGM3["moderate_max"]
        or pm10 is not None
        and pm10 > PM10_THRESHOLDS_UGM3["moderate_max"]
    ):
        status = "Not Recommended"

    return round(total_score, 2), status


def analyze_secondary(parsed: dict) -> dict:
    temp_score = round(_score_temperature(parsed.get("temperature")), 2)
    humidity_score = round(_score_humidity(parsed.get("humidity")), 2)
    air_quality_score = round(_score_air_quality(parsed.get("pm2_5"), parsed.get("pm10")), 2)
    soil_score = round(_score_soil(parsed.get("soil_moisture")), 2)

    field_score, field_status = calculate_field_score(parsed)
    rain_prob = _rain_probability_percent(
        parsed.get("temperature"),
        parsed.get("humidity"),
        parsed.get("soil_moisture"),
    )

    return {
        "temp_score": temp_score,
        "humidity_score": humidity_score,
        "air_quality_score": air_quality_score,
        "soil_score": soil_score,
        "air_quality_status": _air_quality_status(parsed.get("pm2_5"), parsed.get("pm10")),
        "field_score": field_score,
        "field_status": field_status,
        "rain_probability_pct": rain_prob,
        "rain_forecast_status": _rain_forecast_status(rain_prob),
    }
