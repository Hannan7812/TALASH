import asyncio
from sqlalchemy import text
from app.db.database import engine


async def clear_db():
    """Truncate all tables in the public schema and reset sequences.

    This is a safer operation than dropping the schema: it preserves
    types and extensions while removing all user data.
    """
    async with engine.begin() as conn:
        await conn.execute(text("""
DO $$
DECLARE
    r RECORD;
    tbls TEXT := '';
BEGIN
    FOR r IN SELECT schemaname, tablename FROM pg_tables
             WHERE schemaname = 'public' AND tablename NOT LIKE 'alembic_version' LOOP
        tbls := tbls || format('%I.%I,', r.schemaname, r.tablename);
    END LOOP;
    IF tbls <> '' THEN
        tbls := left(tbls, -1);
        EXECUTE format('TRUNCATE TABLE %s RESTART IDENTITY CASCADE;', tbls);
    END IF;
END
$$;
"""))
    print("Database cleared: all tables truncated and sequences reset.")


if __name__ == "__main__":
    asyncio.run(clear_db())
