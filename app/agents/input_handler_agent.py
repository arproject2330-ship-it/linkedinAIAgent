"""Input Handler Agent: optimize user input for LinkedIn or pick topic from analytics."""
from app.workflow.state import WorkflowState


async def input_handler_agent(state: WorkflowState) -> dict:
    """Produce optimized_input: either optimized user text or a topic from performance insights."""
    user_input = (state.get("user_input") or "").strip()
    performance = state.get("performance_insights") or {}
    top_topics = performance.get("top_topics") or []
    hook_style = performance.get("hook_style_pattern") or ""

    if user_input:
        # Optimize for LinkedIn: keep it punchy, add hook potential
        optimized = (
            user_input[:1500]
            + ("\n\n[Optimize for LinkedIn: short paragraphs, clear hook, one CTA.]" if len(user_input) > 500 else "")
        )
        optimized = optimized.strip()
    else:
        # No input: suggest topic from top topics or default
        if top_topics:
            topic = top_topics[0]
        else:
            topic = "professional growth and leadership"
        optimized = f"Topic to write about: {topic}. Style hint: {hook_style or 'Strong opening, valuable insight.'}"

    return {"optimized_input": optimized}
