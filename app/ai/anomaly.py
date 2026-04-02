"""
Anomaly Detection Module
-------------------------
Rule-based + statistical checks that run on every sensor reading.
Returns a list of AnomalyOut events (can be empty).

Anomaly types:
  TANK_EMPTY          — tank dry, pump cannot run
  OVERWATER_RISK      — soil saturated for extended period / rain+high moisture
  UNDERWATER_RISK     — moisture critically below plant minimum
  MOISTURE_SPIKE      — sudden large moisture drop (sensor issue or extreme evaporation)
  SENSOR_FLATLINE     — moisture unchanged over last N readings (sensor stuck)
  TEMP_STRESS_HIGH    — temperature above plant tolerance
  TEMP_STRESS_LOW     — temperature below plant tolerance
  HUMIDITY_EXTREME    — humidity outside plant comfort zone
  RAIN_OVERWATER      — raining heavily while soil already wet
  PREDICTIVE_DRY      — ML predicts soil will be dry within 3 hours
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas import AnomalyOut, ClassificationOut, PredictionOut, SensorPayload, WeatherPayload, ContextPayload


def _anomaly(atype: str, severity: str, desc: str) -> AnomalyOut:
    return AnomalyOut(anomaly_type=atype, severity=severity, description=desc)


async def detect_anomalies(
    db: AsyncSession,
    sensor: SensorPayload,
    weather: Optional[WeatherPayload],
    context: ContextPayload,
    classification: ClassificationOut,
    prediction: PredictionOut,
    plant_id: Optional[int],
    current_reading_id: int,
) -> list[AnomalyOut]:

    from app.models import SensorReading  # lazy

    anomalies: list[AnomalyOut] = []
    m = sensor.moisture_percent

    # ------------------------------------------------------------------
    # 1. Tank empty
    # ------------------------------------------------------------------
    if sensor.tank_status == "EMPTY":
        anomalies.append(_anomaly(
            "TANK_EMPTY", "CRITICAL",
            f"Water tank is empty ({sensor.tank_fill_percent:.0f}%). "
            "Irrigation is impossible until refilled."
        ))

    # ------------------------------------------------------------------
    # 2. Overwatering risk — soil already wet + raining
    # ------------------------------------------------------------------
    if m >= classification.moisture_max and sensor.rain_percent > 30:
        anomalies.append(_anomaly(
            "RAIN_OVERWATER", "WARNING",
            f"Soil is saturated ({m:.1f}%) while it is raining "
            f"({sensor.rain_percent:.0f}%). Root rot risk elevated."
        ))
    elif m >= classification.moisture_max:
        anomalies.append(_anomaly(
            "OVERWATER_RISK", "WARNING",
            f"Soil moisture ({m:.1f}%) exceeds the safe maximum "
            f"({classification.moisture_max:.0f}%) for this plant category. "
            "Reduce irrigation frequency."
        ))

    # ------------------------------------------------------------------
    # 3. Underwatering risk
    # ------------------------------------------------------------------
    if m < classification.moisture_min:
        severity = "CRITICAL" if m < classification.moisture_min * 0.5 else "WARNING"
        anomalies.append(_anomaly(
            "UNDERWATER_RISK", severity,
            f"Soil moisture ({m:.1f}%) is below the minimum threshold "
            f"({classification.moisture_min:.0f}%) for {classification.category}. "
            "Immediate irrigation recommended."
        ))

    # ------------------------------------------------------------------
    # 4. Moisture spike — sudden drop compared to last reading
    # ------------------------------------------------------------------
    query = (
        select(SensorReading.moisture_percent)
        .where(SensorReading.id != current_reading_id)
        .order_by(desc(SensorReading.recorded_at))
        .limit(1)
    )
    if plant_id:
        query = query.where(SensorReading.plant_id == plant_id)

    result = await db.execute(query)
    prev_row = result.scalar_one_or_none()
    if prev_row is not None:
        drop = prev_row - m
        if drop > settings.MOISTURE_SPIKE_THRESHOLD:
            anomalies.append(_anomaly(
                "MOISTURE_SPIKE", "WARNING",
                f"Soil moisture dropped sharply by {drop:.1f}% since the last reading "
                f"(from {prev_row:.1f}% → {m:.1f}%). Check for sensor faults or extreme evaporation."
            ))

    # ------------------------------------------------------------------
    # 5. Sensor flatline — last N readings all identical
    # ------------------------------------------------------------------
    flatline_query = (
        select(SensorReading.moisture_percent)
        .where(SensorReading.id != current_reading_id)
        .order_by(desc(SensorReading.recorded_at))
        .limit(6)
    )
    fl_result = await db.execute(flatline_query)
    fl_rows = [r for r, in fl_result.all()]
    if len(fl_rows) >= 5 and len(set(round(r, 1) for r in fl_rows)) == 1:
        anomalies.append(_anomaly(
            "SENSOR_FLATLINE", "WARNING",
            f"Soil moisture has been exactly {fl_rows[0]:.1f}% for the last "
            f"{len(fl_rows)} readings. The sensor may be stuck or disconnected."
        ))

    # ------------------------------------------------------------------
    # 6. Temperature stress
    # ------------------------------------------------------------------
    t = sensor.temp_celsius
    if t > classification.temp_max or t > settings.TEMP_STRESS_HIGH:
        anomalies.append(_anomaly(
            "TEMP_STRESS_HIGH", "WARNING",
            f"Temperature ({t:.1f}°C) exceeds the safe upper limit for "
            f"{classification.category} plants ({classification.temp_max:.0f}°C). "
            "Consider shade or misting."
        ))
    elif t < classification.temp_min or t < settings.TEMP_STRESS_LOW:
        anomalies.append(_anomaly(
            "TEMP_STRESS_LOW", "WARNING",
            f"Temperature ({t:.1f}°C) is below the minimum tolerance "
            f"({classification.temp_min:.0f}°C). Frost protection may be needed."
        ))

    # ------------------------------------------------------------------
    # 7. Humidity extreme
    # ------------------------------------------------------------------
    h = sensor.humidity_percent
    if not (20 <= h <= 95):
        anomalies.append(_anomaly(
            "HUMIDITY_EXTREME", "INFO",
            f"Ambient humidity ({h:.1f}%) is outside the typical safe range (20–95%). "
            "Sensor check advised."
        ))

    # ------------------------------------------------------------------
    # 8. Predictive dry warning from ML
    # ------------------------------------------------------------------
    if prediction.predicted_moisture_3h < classification.moisture_min:
        anomalies.append(_anomaly(
            "PREDICTIVE_DRY", "WARNING",
            f"ML model predicts moisture will drop to "
            f"{prediction.predicted_moisture_3h:.1f}% within 3 hours, "
            f"below the {classification.moisture_min:.0f}% minimum. "
            "Pre-emptive irrigation advised."
        ))

    # ------------------------------------------------------------------
    # 9. Incoming rain — skip irrigation
    # ------------------------------------------------------------------
    if weather and weather.rain_probability_next_6h >= 70 and m >= classification.moisture_min:
        anomalies.append(_anomaly(
            "RAIN_FORECAST", "INFO",
            f"High rain probability in next 6h ({weather.rain_probability_next_6h:.0f}%). "
            "Irrigation can be deferred."
        ))

    return anomalies
