"""Post Generation Agent: Gemini Pro generates hook, body, cta, hashtags, suggested_visual."""
import asyncio

import app.services.gemini_service as gemini_svc
from app.workflow.state import WorkflowState


async def post_generator_agent(state: WorkflowState) -> dict:
    """Call Gemini to generate post content. Returns post dict."""
    optimized = state.get("optimized_input") or "Share a valuable professional insight."
    performance = state.get("performance_insights") or {}
    strategy = state.get("strategy") or {}

    analytics_summary = (
        f"Best days: {performance.get('best_days', [])}. "
        f"Best times: {performance.get('best_time_ranges', performance.get('best_times', []))}. "
        f"Ideal length: {performance.get('ideal_length', '')}. "
        f"Hook style: {performance.get('hook_style_pattern', '')}."
    )

    # Gemini client is sync; run in thread to avoid blocking
    post = await asyncio.to_thread(
        gemini_svc.generate_post_text,
        optimized,
        analytics_summary,
        strategy,
    )
    return {"post": post}
