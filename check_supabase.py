"""Run this to verify Supabase connection: python check_supabase.py"""
import asyncio
import sys

from sqlalchemy import text


async def check():
    from app.models.db_models import init_db

    try:
        factory = init_db()
        if factory is None:
            print("DATABASE_URL is not set. Add it to .env (Supabase: Settings → Database → Connection string URI).", file=sys.stderr)
            return 1
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        print("Supabase connected successfully.")
        return 0
    except Exception as e:
        err = str(e).strip()
        if "11001" in err or "getaddrinfo" in err:
            print("Connection failed: Could not resolve database host (DNS error).", file=sys.stderr)
            print("Fix: In Supabase Dashboard -> Settings -> Database, use the 'Transaction' (pooler) connection string.", file=sys.stderr)
            print("It should look like: ...@aws-0-XX.pooler.supabase.com:6543/postgres", file=sys.stderr)
        else:
            print("Connection failed:", e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(check())
    sys.exit(exit_code)
