import asyncio
from app.database import init_db, AsyncSessionLocal
from app.models import PlantProfile
from sqlalchemy import select, func

async def check():
    await init_db()
    async with AsyncSessionLocal() as s:
        count = (await s.execute(select(func.count(PlantProfile.id)))).scalar_one()
        names = (await s.execute(select(PlantProfile.name).limit(30))).scalars().all()
        print(f"Total: {count}")
        print("Sample names:", names)

asyncio.run(check())
