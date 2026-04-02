"""
Seed plant_profiles from Perenual API with genuine plant data.
Usage: python seed_perenual.py
"""
import asyncio
import httpx
from sqlalchemy import select
from app.database import init_db, AsyncSessionLocal
from app.models import PlantProfile

API_KEY = "sk-JhEY69ce596dc585e16059"
BASE_URL = "https://perenual.com/api"

# Mapping Perenual watering levels to moisture thresholds
WATERING_MAP = {
    "Minimum": {"min": 10, "max": 40, "ideal": 25, "decay": 0.4},
    "Average": {"min": 30, "max": 70, "ideal": 50, "decay": 1.0},
    "Frequent": {"min": 45, "max": 85, "ideal": 65, "decay": 1.3},
}

# Mapping sunlight requirements to temperature ranges
SUNLIGHT_TEMP_MAP = {
    "full_shade": {"min": 5, "max": 25},
    "part_shade": {"min": 8, "max": 30},
    "sun-part_shade": {"min": 10, "max": 32},
    "full_sun": {"min": 15, "max": 40},
}

# Category mapping based on plant type
CATEGORY_MAP = {
    "herb": "herb",
    "vegetable": "vegetable",
    "fruit": "fruit",
    "cactus": "succulent",
    "succulent": "succulent",
    "vine": "tropical",
    "tree": "flowering",
    "shrub": "flowering",
    "flower": "flowering",
    "grass": "tropical",
}


def map_plant_data(plant: dict) -> dict | None:
    """Transform Perenual plant data to PlantProfile schema."""
    watering = plant.get("watering", "Average")
    sunlight = plant.get("sunlight", [])
    sunlight_key = sunlight[0] if sunlight else "sun-part_shade"
    
    water_config = WATERING_MAP.get(watering, WATERING_MAP["Average"])
    temp_config = SUNLIGHT_TEMP_MAP.get(sunlight_key, SUNLIGHT_TEMP_MAP["sun-part_shade"])
    
    # Determine category
    plant_type = plant.get("type", "").lower()
    category = CATEGORY_MAP.get(plant_type, "flowering")
    
    # Build description
    common_name = plant.get("common_name", "Unknown")
    scientific_name = plant.get("scientific_name", [""])[0] if plant.get("scientific_name") else ""
    cycle = plant.get("cycle", "")
    description = f"{common_name}"
    if scientific_name:
        description += f" ({scientific_name})"
    if cycle:
        description += f". {cycle.capitalize()} plant"
    description += f". Watering: {watering}. Sunlight: {', '.join(sunlight) if sunlight else 'moderate'}."
    
    return {
        "name": common_name[:100],  # Limit to 100 chars
        "category": category,
        "moisture_min": water_config["min"],
        "moisture_max": water_config["max"],
        "ideal_moisture": water_config["ideal"],
        "temp_min": temp_config["min"],
        "temp_max": temp_config["max"],
        "humidity_min": 30.0,
        "humidity_max": 80.0,
        "avg_moisture_decay_per_hour": water_config["decay"],
        "description": description[:500],  # Limit description length
    }


async def fetch_plants(page: int = 1, per_page: int = 30) -> list[dict]:
    """Fetch plants from Perenual API."""
    url = f"{BASE_URL}/species-list"
    params = {"key": API_KEY, "page": page, "per_page": per_page}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            return []


async def seed_from_perenual(max_pages: int = 5):
    """Seed database with plants from Perenual API."""
    await init_db()
    
    total_added = 0
    total_skipped = 0
    
    async with AsyncSessionLocal() as session:
        for page in range(1, max_pages + 1):
            print(f"Fetching page {page}...")
            plants = await fetch_plants(page=page)
            
            if not plants:
                print(f"No plants found on page {page}. Stopping.")
                break
            
            for plant in plants:
                plant_data = map_plant_data(plant)
                if not plant_data:
                    continue
                
                # Check if plant already exists
                existing = (await session.execute(
                    select(PlantProfile).where(PlantProfile.name == plant_data["name"])
                )).scalar_one_or_none()
                
                if existing is None:
                    session.add(PlantProfile(**plant_data))
                    total_added += 1
                else:
                    total_skipped += 1
            
            await session.commit()
            print(f"Page {page}: Added {total_added}, Skipped {total_skipped}")
            
            # Small delay to respect API rate limits
            await asyncio.sleep(0.5)
    
    print(f"\n✅ Seeding complete!")
    print(f"   Total added: {total_added}")
    print(f"   Total skipped (duplicates): {total_skipped}")


if __name__ == "__main__":
    asyncio.run(seed_from_perenual(max_pages=5))
