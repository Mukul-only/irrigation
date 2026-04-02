"""
Irrigation Decision Engine
---------------------------
Computes the final PUMP ON / OFF command and irrigation duration
based on classification + anomaly + prediction outputs.
"""
from __future__ import annotations

from typing import Optional

from app.schemas import (
    AnomalyOut, ClassificationOut, ContextPayload,
    IrrigationDecisionOut, PredictionOut, SensorPayload, WeatherPayload,
)


def make_decision(
    sensor: SensorPayload,
    weather: Optional[WeatherPayload],
    context: ContextPayload,
    classification: ClassificationOut,
    prediction: PredictionOut,
    anomalies: list[AnomalyOut],
) -> tuple[IrrigationDecisionOut, list[str]]:
    """
    Returns (IrrigationDecisionOut, insights: list[str]).
    """
    insights: list[str] = []
    pump = "OFF"
    reason_parts: list[str] = []
    duration_seconds: Optional[int] = None

    m = sensor.moisture_percent
    threshold = context.moisture_threshold

    # ── Hard blockers (never irrigate) ──────────────────────────────────
    anomaly_types = {a.anomaly_type for a in anomalies}

    if "TANK_EMPTY" in anomaly_types:
        reason_parts.append("Tank is empty — cannot irrigate.")
        insights.append("⚠️ Fill the water tank before any irrigation can occur.")
        return (
            IrrigationDecisionOut(pump_command="OFF", reason=" ".join(reason_parts), duration_seconds=None),
            insights,
        )

    if m >= classification.moisture_max or "OVERWATER_RISK" in anomaly_types or "RAIN_OVERWATER" in anomaly_types:
        reason_parts.append(f"Soil is already saturated ({m:.1f}%).")
        insights.append(f"💧 Soil moisture ({m:.1f}%) is above the safe max ({classification.moisture_max:.0f}%) — skipping irrigation.")
        return (
            IrrigationDecisionOut(pump_command="OFF", reason=" ".join(reason_parts), duration_seconds=None),
            insights,
        )

    # ── Rain probability deferral ────────────────────────────────────────
    if (
        weather
        and weather.rain_probability_next_6h >= 70
        and m >= classification.moisture_min
        and "RAIN_FORECAST" in anomaly_types
    ):
        reason_parts.append(
            f"Rain expected in next 6h ({weather.rain_probability_next_6h:.0f}% probability). "
            "Deferring irrigation."
        )
        insights.append("🌧️ Rain is forecast — irrigation deferred to conserve water.")
        return (
            IrrigationDecisionOut(pump_command="OFF", reason=" ".join(reason_parts), duration_seconds=None),
            insights,
        )

    # ── Trigger irrigation ───────────────────────────────────────────────
    needs_water = (
        m < threshold
        or "UNDERWATER_RISK" in anomaly_types
        or "PREDICTIVE_DRY" in anomaly_types
    )

    if needs_water:
        pump = "ON"
        moisture_deficit = classification.ideal_moisture - m
        # Base: 30s per 1% moisture deficit (plant-category agnostic simple rule)
        base_duration = max(30, int(moisture_deficit * 30))

        # Adjust for temperature (high temp → more water needed, shorter cycles ok)
        if sensor.temp_celsius > 30:
            base_duration = int(base_duration * 1.2)
            insights.append(f"🌡️ High temperature ({sensor.temp_celsius:.1f}°C) — increased irrigation duration.")

        # Adjust for humidity (low humidity → soil dries faster)
        if sensor.humidity_percent < 40:
            base_duration = int(base_duration * 1.1)
            insights.append(f"💨 Low humidity ({sensor.humidity_percent:.0f}%) — soil evaporates faster.")

        duration_seconds = min(base_duration, 600)   # cap at 10 min

        reason_parts.append(
            f"Soil moisture ({m:.1f}%) is below threshold ({threshold:.0f}%). "
            f"Irrigating for {duration_seconds}s to reach ideal ({classification.ideal_moisture:.0f}%)."
        )

        if "PREDICTIVE_DRY" in anomaly_types:
            insights.append(
                f"🤖 AI predicted moisture will drop to {prediction.predicted_moisture_3h:.1f}% "
                "within 3h — pre-emptive irrigation triggered."
            )

    else:
        reason_parts.append(
            f"Soil moisture ({m:.1f}%) is adequate (threshold: {threshold:.0f}%). No action needed."
        )

    # ── General insights ─────────────────────────────────────────────────
    insights.append(
        f"📊 Predicted moisture in 6h: {prediction.predicted_moisture_6h:.1f}% "
        f"(model: {prediction.model_type}, confidence: {prediction.confidence_score:.0%})."
    )

    if prediction.predicted_dry_at:
        insights.append(
            f"⏰ Soil projected to reach dry level around "
            f"{prediction.predicted_dry_at.strftime('%Y-%m-%d %H:%M UTC')}."
        )

    if sensor.tank_fill_percent < 20:
        insights.append(f"🪣 Tank is only {sensor.tank_fill_percent:.0f}% full — plan a refill soon.")

    for anomaly in anomalies:
        if anomaly.severity == "CRITICAL":
            insights.append(f"🚨 {anomaly.description}")

    return (
        IrrigationDecisionOut(
            pump_command=pump,
            reason=" ".join(reason_parts),
            duration_seconds=duration_seconds,
        ),
        insights,
    )
