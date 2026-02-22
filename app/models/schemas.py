"""Pydantic schemas for API and agent state."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ----- Performance Intelligence Agent output -----
class PerformanceInsights(BaseModel):
    """Output of Performance Intelligence Agent."""

    best_days: list[str] = Field(default_factory=list, description="e.g. ['Tuesday', 'Wednesday', 'Thursday']")
    best_time_ranges: list[str] = Field(default_factory=list, description="e.g. ['08:00-10:00', '12:00-14:00']")
    ideal_length: str = Field(default="", description="Recommended post length")
    top_topics: list[str] = Field(default_factory=list)
    hook_style_pattern: str = Field(default="", description="Pattern from best-performing hooks")


# ----- Strategy Agent output -----
class StrategyDecision(BaseModel):
    """Output of Strategy Agent."""

    post_type: str = Field(description="story | authority | data_driven | founder_pov")
    tone: str = Field(description="e.g. professional, conversational, bold")
    cta_type: str = Field(description="e.g. comment, share, link, question")
    hook_structure: str = Field(description="e.g. question, stat, story_open")


# ----- API Request/Response -----
class GenerateRequest(BaseModel):
    """Request body for POST /generate."""

    user_input: str | None = Field(default=None, description="Optional manual input to optimize for LinkedIn")
    regenerate_draft_id: int | None = Field(default=None, description="If set, regenerate from this draft")


class GenerateResponse(BaseModel):
    """Response when post is ready for review."""

    status: str = Field(default="ready", description="e.g. 'ready'")
    message: str = Field(default="Your LinkedIn post is ready for review.")
    draft_id: int = Field(description="ID of the draft for edit/publish")
    post_preview: dict[str, Any] = Field(description="Hook, body, cta, hashtags, suggested_visual")
    image_url: str | None = Field(default=None, description="Local or storage URL of generated image")
    image_path: str | None = Field(default=None, description="Path to image file if stored locally")


class PublishRequest(BaseModel):
    """Request body for POST /publish."""

    draft_id: int = Field(description="Draft to publish")
    account_id: int = Field(description="LinkedIn account (personal or company) ID")
    schedule_override: datetime | None = Field(default=None, description="Override scheduled time; null = use smart logic")


class UpdateDraftRequest(BaseModel):
    """Request body for PATCH draft (review step – edit before publish)."""

    hook: str | None = Field(default=None)
    body: str | None = Field(default=None)
    cta: str | None = Field(default=None)
    hashtags: str | None = Field(default=None)


# ----- Analytics -----
class AnalyticsSummary(BaseModel):
    """Summary for dashboard analytics."""

    total_posts: int = 0
    total_impressions: int = 0
    avg_engagement_rate: float = 0.0
    best_days: list[str] = Field(default_factory=list)
    best_times: list[str] = Field(default_factory=list)
    top_posts: list[dict[str, Any]] = Field(default_factory=list)


# ----- DB-backed DTOs -----
class AccountOut(BaseModel):
    """LinkedIn account for selector."""

    id: int
    account_type: str  # "personal" | "company"
    display_name: str
    linkedin_urn: str | None
    is_active: bool = True

    class Config:
        from_attributes = True


class PostDraftOut(BaseModel):
    """Draft ready for review/edit/publish."""

    id: int
    hook: str
    body: str
    cta: str
    hashtags: str
    suggested_visual: str | None
    image_path: str | None
    performance_insights: dict | None
    strategy: dict | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PostHistoryOut(BaseModel):
    """Published post record for history/analytics."""

    id: int
    account_id: int
    content_text: str
    linkedin_post_id: str | None
    impressions: int | None
    engagement_rate: float | None
    published_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class ScheduledPostOut(BaseModel):
    """Scheduled post in queue."""

    id: int
    draft_id: int
    account_id: int
    scheduled_at: datetime
    status: str  # pending | published | failed
    created_at: datetime

    class Config:
        from_attributes = True
