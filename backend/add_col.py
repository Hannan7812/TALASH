import asyncio
from sqlalchemy import text
from app.db.database import AsyncSessionLocal

async def f():
    async with AsyncSessionLocal() as s:
        await s.execute(text("ALTER TABLE candidates ADD COLUMN universities TEXT;"))
        await s.commit()
        print("added column")

if __name__ == "__main__":
    asyncio.run(f())
