"""
Plant Classification Module
----------------------------
Matches incoming sensor + context data against stored plant profiles.
Falls back to a built-in rule-based catalogue when no plant_id is supplied.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas import ClassificationOut


# ---------------------------------------------------------------------------
# Built-in plant catalogue (used when no DB profile is linked)
# ---------------------------------------------------------------------------

@dataclass
class PlantTemplate:
    name: str
    category: str
    moisture_min: float
    moisture_max: float
    ideal_moisture: float
    temp_min: float
    temp_max: float
    humidity_min: float
    humidity_max: float
    avg_moisture_decay_per_hour: float = 1.0
    keywords: list[str] = field(default_factory=list)


PLANT_CATALOGUE: list[PlantTemplate] = [
    PlantTemplate(
        name="Succulent / Cactus",
        category="succulent",
        moisture_min=10, moisture_max=40, ideal_moisture=25,
        temp_min=10, temp_max=45,
        humidity_min=10, humidity_max=50,
        avg_moisture_decay_per_hour=0.4,
        keywords=["succulent", "cactus", "aloe", "echeveria"],
    ),
    PlantTemplate(
        name="Herb (Basil / Mint / Coriander)",
        category="herb",
        moisture_min=35, moisture_max=75, ideal_moisture=55,
        temp_min=10, temp_max=35,
        humidity_min=40, humidity_max=80,
        avg_moisture_decay_per_hour=1.2,
        keywords=["herb", "basil", "mint", "coriander", "parsley", "thyme"],
    ),
    PlantTemplate(
        name="Flowering Plant (Rose / Marigold)",
        category="flowering",
        moisture_min=30, moisture_max=70, ideal_moisture=50,
        temp_min=8, temp_max=38,
        humidity_min=35, humidity_max=75,
        avg_moisture_decay_per_hour=1.0,
        keywords=["flower", "rose", "marigold", "tulip", "lily", "bloom"],
    ),
    PlantTemplate(
        name="Vegetable (Tomato / Pepper)",
        category="vegetable",
        moisture_min=40, moisture_max=80, ideal_moisture=60,
        temp_min=12, temp_max=35,
        humidity_min=45, humidity_max=85,
        avg_moisture_decay_per_hour=1.5,
        keywords=["vegetable", "tomato", "pepper", "lettuce", "spinach", "bean"],
    ),
    PlantTemplate(
        name="Tropical / Fern",
        category="tropical",
        moisture_min=50, moisture_max=90, ideal_moisture=70,
        temp_min=15, temp_max=32,
        humidity_min=60, humidity_max=95,
        avg_moisture_decay_per_hour=0.8,
        keywords=["tropical", "fern", "palm", "monstera", "peace lily"],
    ),
    PlantTemplate(
        name="Generic / Unknown",
        category="generic",
        moisture_min=25, moisture_max=75, ideal_moisture=50,
        temp_min=5, temp_max=40,
        humidity_min=30, humidity_max=90,
        avg_moisture_decay_per_hour=1.0,
        keywords=[],
    ),
]

_DEFAULT_TEMPLATE = PLANT_CATALOGUE[-1]   # Generic fallback


def classify_by_name(plant_name: str) -> PlantTemplate:
    """Keyword-based fuzzy match against the built-in catalogue."""
    name_lower = plant_name.lower()
    for template in PLANT_CATALOGUE[:-1]:   # skip Generic sentinel
        if any(kw in name_lower for kw in template.keywords):
            return template
    return _DEFAULT_TEMPLATE


def classify_by_environment(
    moisture: float,
    temp: float,
    humidity: float,
) -> PlantTemplate:
    """
    Score each template by how well the current env fits its ranges.
    Used as a last-resort heuristic when no name is available.
    """
    best: PlantTemplate = _DEFAULT_TEMPLATE
    best_score: float = -1e9

    for t in PLANT_CATALOGUE[:-1]:
        score = 0.0
        # Penalise distance from ideal moisture
        score -= abs(moisture - t.ideal_moisture)
        # Reward if temp sits comfortably inside tolerance
        if t.temp_min <= temp <= t.temp_max:
            score += 10
        if t.humidity_min <= humidity <= t.humidity_max:
            score += 5
        if score > best_score:
            best_score = score
            best = t

    return best


async def get_classification(
    db: AsyncSession,
    plant_id: Optional[int],
    moisture: float,
    temp: float,
    humidity: float,
) -> tuple[ClassificationOut, float]:
    """
    Returns (ClassificationOut, avg_moisture_decay_per_hour).

    Priority:
      1. DB profile (if plant_id given)
      2. Env-heuristic catalogue match
    """
    from app.models import PlantProfile  # lazy import to avoid circular

    if plant_id is not None:
        result = await db.execute(
            select(PlantProfile).where(PlantProfile.id == plant_id)
        )
        profile = result.scalar_one_or_none()
        if profile:
            out = ClassificationOut(
                plant_name=profile.name,
                category=profile.category,
                moisture_min=profile.moisture_min,
                moisture_max=profile.moisture_max,
                ideal_moisture=profile.ideal_moisture,
                temp_min=profile.temp_min,
                temp_max=profile.temp_max,
            )
            return out, profile.avg_moisture_decay_per_hour

    # Fall back to heuristic catalogue
    template = classify_by_environment(moisture, temp, humidity)
    out = ClassificationOut(
        plant_name=template.name,
        category=template.category,
        moisture_min=template.moisture_min,
        moisture_max=template.moisture_max,
        ideal_moisture=template.ideal_moisture,
        temp_min=template.temp_min,
        temp_max=template.temp_max,
    )
    return out, template.avg_moisture_decay_per_hour
