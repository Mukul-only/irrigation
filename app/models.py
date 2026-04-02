"""
SQLAlchemy ORM models — all persisted tables live here.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey,
    Integer, String, Text, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Plant profile
# ---------------------------------------------------------------------------
class PlantProfile(Base):
    __tablename__ = "plant_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)   # e.g. succulent, herb, vegetable

    # Water requirement thresholds (moisture %)
    moisture_min: Mapped[float] = mapped_column(Float, default=20.0)    # trigger irrigation
    moisture_max: Mapped[float] = mapped_column(Float, default=80.0)    # over-saturation warning
    ideal_moisture: Mapped[float] = mapped_column(Float, default=50.0)

    # Environmental tolerances
    temp_min: Mapped[float] = mapped_column(Float, default=5.0)
    temp_max: Mapped[float] = mapped_column(Float, default=40.0)
    humidity_min: Mapped[float] = mapped_column(Float, default=30.0)
    humidity_max: Mapped[float] = mapped_column(Float, default=90.0)

    # Expected daily moisture decay rate (% per hour without irrigation)
    avg_moisture_decay_per_hour: Mapped[float] = mapped_column(Float, default=1.0)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    readings: Mapped[list["SensorReading"]] = relationship(back_populates="plant")
    predictions: Mapped[list["MoisturePrediction"]] = relationship(back_populates="plant")
    anomalies: Mapped[list["AnomalyEvent"]] = relationship(back_populates="plant")


# ---------------------------------------------------------------------------
# Raw sensor readings (one row per API call)
# ---------------------------------------------------------------------------
class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("plant_profiles.id"), nullable=True)

    # Sensor
    moisture_percent: Mapped[float] = mapped_column(Float, nullable=False)
    soil_status: Mapped[str] = mapped_column(String(100))
    rain_percent: Mapped[float] = mapped_column(Float, default=0.0)
    rain_status: Mapped[str] = mapped_column(String(50))
    temp_celsius: Mapped[float] = mapped_column(Float)
    humidity_percent: Mapped[float] = mapped_column(Float)
    tank_status: Mapped[str] = mapped_column(String(20))
    tank_fill_percent: Mapped[float] = mapped_column(Float)

    # Weather snapshot (nullable — device may not send weather)
    weather_temp_current: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_humidity_current: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_precipitation_now: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_wind_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    weather_rain_prob_6h: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_temp_next_6h: Mapped[str | None] = mapped_column(JSON, nullable=True)  # list stored as JSON

    # Context
    last_pump_command: Mapped[str | None] = mapped_column(String(10), nullable=True)
    last_pump_command_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    moisture_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    plant: Mapped["PlantProfile | None"] = relationship(back_populates="readings")


# ---------------------------------------------------------------------------
# AI-generated moisture predictions
# ---------------------------------------------------------------------------
class MoisturePrediction(Base):
    __tablename__ = "moisture_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("plant_profiles.id"), nullable=True)
    reading_id: Mapped[int] = mapped_column(ForeignKey("sensor_readings.id"), nullable=False)

    predicted_moisture_1h: Mapped[float] = mapped_column(Float)
    predicted_moisture_3h: Mapped[float] = mapped_column(Float)
    predicted_moisture_6h: Mapped[float] = mapped_column(Float)

    predicted_dry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)   # 0–1

    model_type: Mapped[str] = mapped_column(String(50), default="linear_regression")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    plant: Mapped["PlantProfile | None"] = relationship(back_populates="predictions")


# ---------------------------------------------------------------------------
# Anomaly events detected by the AI layer
# ---------------------------------------------------------------------------
class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("plant_profiles.id"), nullable=True)
    reading_id: Mapped[int] = mapped_column(ForeignKey("sensor_readings.id"), nullable=False)

    anomaly_type: Mapped[str] = mapped_column(String(80), nullable=False)
    # e.g. OVERWATER_RISK | UNDERWATER_RISK | MOISTURE_SPIKE |
    #      TEMP_STRESS_HIGH | TEMP_STRESS_LOW | TANK_EMPTY |
    #      SENSOR_FLATLINE | HUMIDITY_EXTREME

    severity: Mapped[str] = mapped_column(String(20), default="WARNING")  # INFO | WARNING | CRITICAL
    description: Mapped[str] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    plant: Mapped["PlantProfile | None"] = relationship(back_populates="anomalies")


# ---------------------------------------------------------------------------
# Irrigation decisions / pump commands log
# ---------------------------------------------------------------------------
class IrrigationDecision(Base):
    __tablename__ = "irrigation_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reading_id: Mapped[int] = mapped_column(ForeignKey("sensor_readings.id"), nullable=False)
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("plant_profiles.id"), nullable=True)

    pump_command: Mapped[str] = mapped_column(String(10))     # ON | OFF
    reason: Mapped[str] = mapped_column(Text)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
