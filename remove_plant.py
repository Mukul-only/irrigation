"""
Remove plant profile with id=6 from the database.
Usage: python remove_plant.py
"""
import asyncio
from sqlalchemy import select
from app.database import init_db, AsyncSessionLocal
from app.models import PlantProfile


async def remove_plant(plant_id: int):
    """Remove a plant profile by ID."""
    await init_db()
    
    async with AsyncSessionLocal() as session:
        # Fetch the plant
        plant = (await session.execute(
            select(PlantProfile).where(PlantProfile.id == plant_id)
        )).scalar_one_or_none()
        
        if plant:
            plant_name = plant.name
            await session.delete(plant)
            await session.commit()
            print(f"✅ Removed plant profile: {plant_name} (ID: {plant_id})")
        else:
            print(f"❌ Plant with ID {plant_id} not found.")


if __name__ == "__main__":
    asyncio.run(remove_plant(6))
