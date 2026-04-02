"""
Seed script — populates default plant profiles.
Run once after the server has been started:
    python seed.py

Data sourced from: RHS (rhs.org.uk), USDA Plant Database,
University Extension Services (UC Davis, Purdue, Penn State).
"""
import asyncio
from sqlalchemy import select
from app.database import init_db, AsyncSessionLocal
from app.models import PlantProfile


SEEDS = [
    # ── Flowering ────────────────────────────────────────────────────────────
    dict(name="Rose", category="flowering", moisture_min=30, moisture_max=70, ideal_moisture=50,
         temp_min=8, temp_max=38, humidity_min=35, humidity_max=75, avg_moisture_decay_per_hour=1.0,
         description="Classic flowering shrub. Prefers deep, infrequent watering; allow top 2 cm to dry between sessions."),
    dict(name="Lavender", category="flowering", moisture_min=15, moisture_max=45, ideal_moisture=30,
         temp_min=5, temp_max=38, humidity_min=20, humidity_max=60, avg_moisture_decay_per_hour=0.6,
         description="Mediterranean shrub. Extremely drought-tolerant once established; overwatering causes root rot."),
    dict(name="Sunflower", category="flowering", moisture_min=30, moisture_max=65, ideal_moisture=48,
         temp_min=10, temp_max=40, humidity_min=30, humidity_max=70, avg_moisture_decay_per_hour=1.3,
         description="Annual with deep taproot. Water deeply 1-2x per week; reduce after head formation."),
    dict(name="Geranium", category="flowering", moisture_min=25, moisture_max=60, ideal_moisture=42,
         temp_min=7, temp_max=32, humidity_min=30, humidity_max=65, avg_moisture_decay_per_hour=0.9,
         description="Popular bedding plant. Allow soil to partially dry between waterings to prevent stem rot."),

    # ── Herbs ────────────────────────────────────────────────────────────────
    dict(name="Basil", category="herb", moisture_min=35, moisture_max=75, ideal_moisture=55,
         temp_min=15, temp_max=35, humidity_min=40, humidity_max=80, avg_moisture_decay_per_hour=1.2,
         description="Warm-season culinary herb. Keep evenly moist; wilts quickly in heat."),
    dict(name="Mint", category="herb", moisture_min=40, moisture_max=80, ideal_moisture=60,
         temp_min=5, temp_max=32, humidity_min=45, humidity_max=85, avg_moisture_decay_per_hour=1.1,
         description="Vigorous spreading herb. Prefers consistently moist soil; tolerates partial shade."),
    dict(name="Rosemary", category="herb", moisture_min=15, moisture_max=45, ideal_moisture=28,
         temp_min=5, temp_max=38, humidity_min=20, humidity_max=55, avg_moisture_decay_per_hour=0.5,
         description="Woody Mediterranean herb. Drought-tolerant; well-drained soil essential."),
    dict(name="Cilantro", category="herb", moisture_min=35, moisture_max=70, ideal_moisture=52,
         temp_min=7, temp_max=28, humidity_min=35, humidity_max=75, avg_moisture_decay_per_hour=1.0,
         description="Cool-season herb. Bolts in heat; keep soil moist and grow in partial shade in summer."),
    dict(name="Thyme", category="herb", moisture_min=20, moisture_max=50, ideal_moisture=35,
         temp_min=5, temp_max=35, humidity_min=25, humidity_max=60, avg_moisture_decay_per_hour=0.6,
         description="Low-growing herb. Drought-tolerant; excellent drainage required to prevent root rot."),

    # ── Vegetables ───────────────────────────────────────────────────────────
    dict(name="Tomato", category="vegetable", moisture_min=40, moisture_max=80, ideal_moisture=60,
         temp_min=12, temp_max=35, humidity_min=45, humidity_max=85, avg_moisture_decay_per_hour=1.5,
         description="Warm-season crop. Consistent moisture prevents blossom-end rot and fruit cracking."),
    dict(name="Lettuce", category="vegetable", moisture_min=45, moisture_max=85, ideal_moisture=65,
         temp_min=4, temp_max=24, humidity_min=50, humidity_max=90, avg_moisture_decay_per_hour=1.4,
         description="Cool-season leafy green. Shallow roots dry out fast; frequent light watering needed."),
    dict(name="Pepper", category="vegetable", moisture_min=35, moisture_max=75, ideal_moisture=55,
         temp_min=15, temp_max=38, humidity_min=40, humidity_max=80, avg_moisture_decay_per_hour=1.2,
         description="Warm-season crop. Consistent moisture improves fruit set; avoid waterlogging."),
    dict(name="Cucumber", category="vegetable", moisture_min=50, moisture_max=85, ideal_moisture=68,
         temp_min=15, temp_max=35, humidity_min=50, humidity_max=90, avg_moisture_decay_per_hour=1.6,
         description="High-water vine crop. 95% water content; requires frequent irrigation in warm weather."),
    dict(name="Spinach", category="vegetable", moisture_min=40, moisture_max=80, ideal_moisture=60,
         temp_min=2, temp_max=24, humidity_min=45, humidity_max=85, avg_moisture_decay_per_hour=1.1,
         description="Cool-season green. Bolts in heat and drought; keep soil consistently moist."),
    dict(name="Carrot", category="vegetable", moisture_min=30, moisture_max=65, ideal_moisture=48,
         temp_min=5, temp_max=28, humidity_min=35, humidity_max=75, avg_moisture_decay_per_hour=0.8,
         description="Root vegetable. Even moisture prevents forked/cracked roots; avoid overwatering."),

    # ── Fruits ───────────────────────────────────────────────────────────────
    dict(name="Strawberry", category="fruit", moisture_min=40, moisture_max=75, ideal_moisture=58,
         temp_min=5, temp_max=30, humidity_min=45, humidity_max=80, avg_moisture_decay_per_hour=1.2,
         description="Shallow-rooted fruit. Consistent moisture during fruiting; avoid wetting foliage."),
    dict(name="Blueberry", category="fruit", moisture_min=45, moisture_max=80, ideal_moisture=62,
         temp_min=3, temp_max=30, humidity_min=50, humidity_max=85, avg_moisture_decay_per_hour=1.0,
         description="Acid-loving shrub. Requires consistently moist, well-drained acidic soil (pH 4.5-5.5)."),

    # ── Succulents & Cacti ───────────────────────────────────────────────────
    dict(name="Aloe Vera", category="succulent", moisture_min=10, moisture_max=40, ideal_moisture=25,
         temp_min=10, temp_max=45, humidity_min=10, humidity_max=50, avg_moisture_decay_per_hour=0.4,
         description="Medicinal succulent. Water every 2-3 weeks; allow soil to dry completely between waterings."),
    dict(name="Jade Plant", category="succulent", moisture_min=15, moisture_max=45, ideal_moisture=28,
         temp_min=10, temp_max=35, humidity_min=15, humidity_max=50, avg_moisture_decay_per_hour=0.35,
         description="Long-lived succulent shrub. Water sparingly; overwatering is the primary cause of death."),
    dict(name="Echeveria", category="succulent", moisture_min=10, moisture_max=35, ideal_moisture=20,
         temp_min=8, temp_max=40, humidity_min=10, humidity_max=45, avg_moisture_decay_per_hour=0.3,
         description="Rosette-forming succulent. Soak-and-dry method; never let water sit in the rosette."),

    # ── Tropicals / Houseplants ──────────────────────────────────────────────
    dict(name="Monstera", category="tropical", moisture_min=50, moisture_max=90, ideal_moisture=70,
         temp_min=16, temp_max=30, humidity_min=60, humidity_max=95, avg_moisture_decay_per_hour=0.8,
         description="Iconic tropical aroid. Loves high humidity; water when top 3-5 cm of soil is dry."),
    dict(name="Peace Lily", category="tropical", moisture_min=45, moisture_max=85, ideal_moisture=65,
         temp_min=15, temp_max=30, humidity_min=55, humidity_max=90, avg_moisture_decay_per_hour=0.9,
         description="Shade-tolerant tropical. Droops visibly when thirsty; keep evenly moist."),
    dict(name="Snake Plant", category="tropical", moisture_min=15, moisture_max=50, ideal_moisture=30,
         temp_min=10, temp_max=35, humidity_min=20, humidity_max=60, avg_moisture_decay_per_hour=0.3,
         description="Extremely tolerant houseplant. Water every 2-6 weeks; one of the hardest plants to overwater."),
    dict(name="Pothos", category="tropical", moisture_min=30, moisture_max=70, ideal_moisture=50,
         temp_min=12, temp_max=32, humidity_min=40, humidity_max=80, avg_moisture_decay_per_hour=0.7,
         description="Fast-growing trailing vine. Tolerates irregular watering; allow top soil to dry between waterings."),
    dict(name="Bird of Paradise", category="tropical", moisture_min=35, moisture_max=70, ideal_moisture=52,
         temp_min=13, temp_max=35, humidity_min=50, humidity_max=85, avg_moisture_decay_per_hour=0.8,
         description="Large tropical perennial. Water thoroughly then allow soil to partially dry; reduce in winter."),
]


async def seed():
    await init_db()
    added = 0
    async with AsyncSessionLocal() as session:
        for data in SEEDS:
            existing = (await session.execute(
                select(PlantProfile).where(PlantProfile.name == data["name"])
            )).scalar_one_or_none()
            if existing is None:
                session.add(PlantProfile(**data))
                added += 1
        await session.commit()
    print(f"Seeded {added} new plant profiles ({len(SEEDS) - added} already existed).")


if __name__ == "__main__":
    asyncio.run(seed())
