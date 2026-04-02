"""
Regression-Based Moisture Prediction Module
--------------------------------------------
Uses the last N sensor readings to fit a linear regression model that
predicts future soil moisture levels at +1h, +3h, and +6h horizons.

Algorithm:
  X = time offset (minutes from first reading)
  y = moisture_percent

  sklearn LinearRegression → slope (decay rate per minute)
  Future moisture extrapolated from current timestamp.

  If fewer readings exist than MIN_READINGS_FOR_PREDICTION, uses a
  physics-based fallback: plant's avg_moisture_decay_per_hour.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import Optional

import numpy as np
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
    from sklearn.pipeline import make_pipeline
    _SKLEARN_OK = True
except ImportError:
    _SKLEARN_OK = False

from app.config import settings
from app.schemas import PredictionOut


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def _physics_predict(
    current_moisture: float,
    decay_per_hour: float,
    hours: float,
    rain_probability: float = 0.0,
    rain_now: float = 0.0,
) -> float:
    """Simple exponential decay adjusted for rain probability."""
    rain_factor = 1.0 - (rain_probability / 100.0) * 0.5 - (rain_now / 100.0) * 0.3
    effective_decay = decay_per_hour * max(0.1, rain_factor)
    return _clamp(current_moisture - effective_decay * hours)


async def predict_moisture(
    db: AsyncSession,
    plant_id: Optional[int],
    current_reading_id: int,
    current_moisture: float,
    decay_per_hour: float,
    rain_probability: float = 0.0,
    rain_now: float = 0.0,
) -> PredictionOut:
    """
    Fetch recent readings and fit a regression to predict future moisture.
    """
    from app.models import SensorReading  # lazy

    now = datetime.now(timezone.utc)

    # ---- Fetch recent readings (excluding the one just inserted) ----------
    query = (
        select(SensorReading.recorded_at, SensorReading.moisture_percent)
        .where(SensorReading.id != current_reading_id)
    )
    if plant_id is not None:
        query = query.where(SensorReading.plant_id == plant_id)

    query = query.order_by(desc(SensorReading.recorded_at)).limit(settings.LOOKBACK_READINGS)
    result = await db.execute(query)
    rows = result.all()

    model_type = "physics_decay"
    confidence = 0.0

    if _SKLEARN_OK and len(rows) >= settings.MIN_READINGS_FOR_PREDICTION:
        # Build X (minutes since oldest reading) and y (moisture)
        rows_sorted = sorted(rows, key=lambda r: r.recorded_at)
        t0 = rows_sorted[0].recorded_at
        X = np.array(
            [(r.recorded_at - t0).total_seconds() / 60.0 for r in rows_sorted]
        ).reshape(-1, 1)
        y = np.array([r.moisture_percent for r in rows_sorted])

        # Fit polynomial (degree 2) regression for non-linear decay
        try:
            model = make_pipeline(PolynomialFeatures(degree=2), LinearRegression())
            model.fit(X, y)
            model_type = "polynomial_regression_d2"

            # Minutes from t0 to now + horizon
            t_now_min = (now - t0).total_seconds() / 60.0
            preds = {
                h: float(model.predict([[t_now_min + h * 60]])[0])
                for h in (1, 3, 6)
            }

            # R² as proxy confidence (clipped to [0,1])
            from sklearn.metrics import r2_score
            y_pred_train = model.predict(X)
            r2 = r2_score(y, y_pred_train)
            confidence = _clamp(r2, 0.0, 1.0)

            m1h = _clamp(preds[1])
            m3h = _clamp(preds[3])
            m6h = _clamp(preds[6])

        except Exception:
            # Fallback if model fails
            m1h = _physics_predict(current_moisture, decay_per_hour, 1, rain_probability, rain_now)
            m3h = _physics_predict(current_moisture, decay_per_hour, 3, rain_probability, rain_now)
            m6h = _physics_predict(current_moisture, decay_per_hour, 6, rain_probability, rain_now)
            model_type = "physics_decay_fallback"

    else:
        # Not enough data — use physics model
        m1h = _physics_predict(current_moisture, decay_per_hour, 1, rain_probability, rain_now)
        m3h = _physics_predict(current_moisture, decay_per_hour, 3, rain_probability, rain_now)
        m6h = _physics_predict(current_moisture, decay_per_hour, 6, rain_probability, rain_now)

    # Estimate when soil will reach dry threshold (moisture ≈ 0 or plant_min)
    # Simple linear extrapolation from current → 6h predicted
    predicted_dry_at: Optional[datetime] = None
    if m6h < current_moisture and m6h < 5.0:
        # Already trending dry within 6h
        predicted_dry_at = now + timedelta(hours=6)
    elif current_moisture > m6h:
        decay_per_6h = current_moisture - m6h
        if decay_per_6h > 0:
            hours_to_zero = current_moisture / (decay_per_6h / 6.0)
            if hours_to_zero < 72:   # only report if within 3 days
                predicted_dry_at = now + timedelta(hours=hours_to_zero)

    return PredictionOut(
        predicted_moisture_1h=round(m1h, 2),
        predicted_moisture_3h=round(m3h, 2),
        predicted_moisture_6h=round(m6h, 2),
        predicted_dry_at=predicted_dry_at,
        confidence_score=round(confidence, 3),
        model_type=model_type,
    )
