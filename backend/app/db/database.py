# =============================================================================
# TALASH - Database Connection
# app/db/database.py
# =============================================================================

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
import os
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# =============================================================================
# DATABASE URL
# Reads from .env file — never hardcode credentials
# =============================================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:yourpassword@localhost:5432/talash"
)

# =============================================================================
# ENGINE
# pool_size     — number of persistent connections
# max_overflow  — extra connections allowed under heavy load
# echo          — set True during development to see SQL logs
# =============================================================================

engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    echo=True           # set to False in production
)

# =============================================================================
# SESSION FACTORY
# Each request gets its own session via get_db()
# =============================================================================

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# =============================================================================
# BASE
# All SQLAlchemy models inherit from this
# =============================================================================

Base = declarative_base()


# =============================================================================
# DEPENDENCY
# Use this in every FastAPI route that needs DB access:
#
#   async def my_route(db: AsyncSession = Depends(get_db)):
#       ...
# =============================================================================

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# =============================================================================
# CREATE ALL TABLES
# Called once on startup from main.py
# =============================================================================

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # lightweight schema evolution for analysis columns on existing databases
        await conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS education_json TEXT"))
        await conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS experience_json TEXT"))
        await conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS research_json TEXT"))
        await conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS missing_info_json TEXT"))
        await conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS missing_info_email TEXT"))
        await conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS publication_analysis_json TEXT"))