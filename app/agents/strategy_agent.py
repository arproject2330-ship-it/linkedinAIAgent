"""Strategy Agent: decide post_type, tone, cta_type, hook_structure. ReeloomStudios default."""
from app.workflow.state import WorkflowState


async def strategy_agent(state: WorkflowState) -> dict:
    """Decide strategy from context and performance insights. Defaults to ReeloomStudios founder voice."""
    performance = state.get("performance_insights") or {}
    optimized = (state.get("optimized_input") or "")[:500].lower()

    # ReeloomStudios: default founder POV and creator/studio positioning
    if "data" in optimized or "number" in optimized or "percent" in optimized:
        post_type = "data_driven"
        hook_structure = "stat"
    elif "story" in optimized or "lesson" in optimized:
        post_type = "story"
        hook_structure = "story_open"
    else:
        post_type = "founder_pov"  # ReeloomStudios default
        hook_structure = "question" if "?" in (state.get("optimized_input") or "") else "story_open"

    tone = "conversational"  # founder-style: approachable but confident
    cta_type = "question"  # drives comments; fits LinkedIn

    return {
        "strategy": {
            "post_type": post_type,
            "tone": tone,
            "cta_type": cta_type,
            "hook_structure": hook_structure,
            "brand": "ReeloomStudios",  # hint for post generator
        }
    }
