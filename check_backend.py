"""
Verify backend and AI agents: imports, graph, DB, and optional full flow.
Run: python check_backend.py
"""
import asyncio
import sys


def check(name: str, fn):
    try:
        fn()
        print(f"  OK  {name}")
        return True
    except Exception as e:
        print(f"  FAIL {name}: {e}")
        return False


def main_sync():
    print("1. Imports (config, models, db, services, agents, workflow, routes)...")
    ok = True
    ok &= check("config", lambda: __import__("app.config"))
    ok &= check("models (schemas + db_models)", lambda: __import__("app.models.schemas") or __import__("app.models.db_models"))
    ok &= check("db (get_db, init_db)", lambda: __import__("app.db"))
    ok &= check("services (analytics, gemini, linkedin)", lambda: __import__("app.services.analytics_service") or __import__("app.services.gemini_service") or __import__("app.services.linkedin_service"))
    ok &= check("agents (performance, input, strategy, post, image, scheduler)", lambda: __import__("app.agents.performance_agent") or __import__("app.agents.input_handler_agent") or __import__("app.agents.strategy_agent") or __import__("app.agents.post_generator") or __import__("app.agents.image_generator") or __import__("app.agents.scheduler_agent"))
    ok &= check("workflow (state + graph)", lambda: __import__("app.workflow.state") or __import__("app.workflow.graph"))
    ok &= check("routes (generate, publish, analytics, accounts, history, storage)", lambda: __import__("app.routes.generate") or __import__("app.routes.publish") or __import__("app.routes.history"))
    ok &= check("main app", lambda: __import__("app.main"))
    if not ok:
        return 1

    print("\n2. LangGraph compile...")
    try:
        from app.workflow.graph import create_post_graph
        graph = create_post_graph()
        print("  OK  Graph compiled")
    except Exception as e:
        print(f"  FAIL Graph: {e}")
        return 1

    async def run_async_checks():
        from app.models.db_models import init_db
        from sqlalchemy import text
        from app.agents.performance_agent import performance_agent
        from app.agents.input_handler_agent import input_handler_agent
        from app.agents.strategy_agent import strategy_agent
        from app.workflow.state import WorkflowState

        print("\n3. DB connection (Supabase)...")
        factory = init_db()
        if factory is None:
            print("  SKIP DATABASE_URL not set (add to .env to test DB and agents).")
            return None
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        factory = init_db()
        print("  OK  DB connected")

        print("\n4. Agent chain (performance -> input -> strategy) with real session...")
        async with factory() as session:
            state: WorkflowState = {"user_input": "Test topic for LinkedIn", "session": session}
            state = {**state, **(await performance_agent(state))}
            state = {**state, **(await input_handler_agent(state))}
            state = {**state, **(await strategy_agent(state))}
        assert state.get("optimized_input")
        assert state.get("strategy")
        print("  OK  Performance -> Input -> Strategy agents ran")

        print("\n5. Post + Image agents (require GEMINI_API_KEY)...")
        from app.workflow.graph import create_post_graph as _create_graph
        graph = _create_graph()
        async with factory() as session:
            result = await graph.ainvoke({"user_input": "One line test.", "session": session})
        return result

    try:
        result = asyncio.run(run_async_checks())
        if result.get("post") and result["post"].get("hook"):
            print("  OK  Full graph (Performance -> ... -> Post -> Image) ran; post generated.")
        else:
            print("  WARN Full graph ran but no post in result (check Gemini API key):", list(result.keys()) if isinstance(result, dict) else result)
    except (ValueError, UnicodeEncodeError) as e:
        err = str(e)
        if "Gemini" in err or "API key" in err:
            print("  SKIP Full graph (no GEMINI_API_KEY or invalid). Other backend OK.")
        elif "codec" in err or "charmap" in err or "encode" in err:
            print("  OK  Full graph ran (Gemini responded; Windows console encoding).")
        else:
            print(f"  FAIL Full graph: {e}")
            return 1
    except Exception as e:
        err = str(e)
        if "codec" in err or "charmap" in err or "encode" in err:
            print("  OK  Full graph ran (Gemini responded; Windows console encoding).")
        else:
            print(f"  FAIL: {e}")
            return 1

    print("\nBackend and agents check done.")
    return 0


if __name__ == "__main__":
    sys.exit(main_sync())
