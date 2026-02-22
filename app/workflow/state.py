"""LangGraph state schema for the post generation workflow."""
from typing import Any, TypedDict


class WorkflowState(TypedDict, total=False):
    """State passed between nodes. All keys optional for partial updates."""

    # Injected by API (do not persist in DB)
    user_input: str | None
    session: Any  # AsyncSession
    regenerate_draft_id: int | None

    # Performance Intelligence Agent
    performance_insights: dict[str, Any]

    # Input Handler Agent
    optimized_input: str

    # Strategy Agent
    strategy: dict[str, str]

    # Post Generation Agent
    post: dict[str, str]  # hook, body, cta, hashtags, suggested_visual

    # Image Generation Agent
    image_path: str | None

    # After save
    draft_id: int | None

    # Error
    error: str | None
