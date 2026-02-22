"""GET /post-history, GET/PATCH drafts, GET scheduled, POST generate-image."""
import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.db_models import PostDraft, PostHistory, ScheduledPost
from app.models.schemas import PostDraftOut, PostHistoryOut, ScheduledPostOut, UpdateDraftRequest
from app.services.gemini_service import generate_image
from app.utils.helpers import safe_json_loads

router = APIRouter(prefix="/post-history", tags=["history"])


@router.get("", response_model=list[PostHistoryOut])
async def list_post_history(
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
):
    """List published posts for analytics/history."""
    r = await session.execute(
        select(PostHistory).order_by(PostHistory.published_at.desc()).limit(limit)
    )
    posts = list(r.scalars().all())
    return [PostHistoryOut.model_validate(p) for p in posts]


@router.get("/drafts", response_model=list[PostDraftOut])
async def list_drafts(
    limit: int = 20,
    session: AsyncSession = Depends(get_db),
):
    """List draft posts (for review/publish)."""
    r = await session.execute(
        select(PostDraft).order_by(PostDraft.updated_at.desc()).limit(limit)
    )
    drafts = list(r.scalars().all())
    out = []
    for d in drafts:
        data = {
            "id": d.id,
            "hook": d.hook,
            "body": d.body,
            "cta": d.cta,
            "hashtags": d.hashtags,
            "suggested_visual": d.suggested_visual,
            "image_path": d.image_path,
            "performance_insights": safe_json_loads(d.performance_insights) if isinstance(d.performance_insights, str) else d.performance_insights,
            "strategy": safe_json_loads(d.strategy) if isinstance(d.strategy, str) else d.strategy,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
        }
        out.append(PostDraftOut(**data))
    return out


@router.get("/drafts/{draft_id}", response_model=PostDraftOut)
async def get_draft(
    draft_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Get a single draft by id."""
    r = await session.execute(select(PostDraft).where(PostDraft.id == draft_id))
    d = r.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Draft not found")
    return PostDraftOut(
        id=d.id,
        hook=d.hook,
        body=d.body,
        cta=d.cta,
        hashtags=d.hashtags,
        suggested_visual=d.suggested_visual,
        image_path=d.image_path,
        performance_insights=safe_json_loads(d.performance_insights) if isinstance(d.performance_insights, str) else d.performance_insights,
        strategy=safe_json_loads(d.strategy) if isinstance(d.strategy, str) else d.strategy,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


@router.patch("/drafts/{draft_id}", response_model=PostDraftOut)
async def update_draft(
    draft_id: int,
    body: UpdateDraftRequest,
    session: AsyncSession = Depends(get_db),
):
    """Update a draft (review step – edit hook, body, cta, hashtags before publish)."""
    r = await session.execute(select(PostDraft).where(PostDraft.id == draft_id))
    d = r.scalar_one_or_none()
    if not d:
        raise HTTPException(status_code=404, detail="Draft not found")
    if body.hook is not None:
        d.hook = body.hook
    if body.body is not None:
        d.body = body.body
    if body.cta is not None:
        d.cta = body.cta
    if body.hashtags is not None:
        d.hashtags = body.hashtags
    await session.commit()
    await session.refresh(d)
    return PostDraftOut(
        id=d.id,
        hook=d.hook,
        body=d.body,
        cta=d.cta,
        hashtags=d.hashtags,
        suggested_visual=d.suggested_visual,
        image_path=d.image_path,
        performance_insights=safe_json_loads(d.performance_insights) if isinstance(d.performance_insights, str) else d.performance_insights,
        strategy=safe_json_loads(d.strategy) if isinstance(d.strategy, str) else d.strategy,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


@router.post("/drafts/{draft_id}/generate-image")
async def generate_draft_image(
    draft_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Generate an image for this draft (relevant to post content). Optional; call when user clicks Generate image."""
    r = await session.execute(select(PostDraft).where(PostDraft.id == draft_id))
    draft = r.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    hook = draft.hook or ""
    body = draft.body or ""
    suggested_visual = draft.suggested_visual or ""
    if not (hook or body or suggested_visual):
        raise HTTPException(status_code=400, detail="Draft has no content to generate image from")
    storage_dir = settings.storage_dir
    name = f"linkedin_{uuid.uuid4().hex[:12]}.png"
    output_path = storage_dir / name
    path, error_message = await asyncio.to_thread(generate_image, hook, body, suggested_visual, output_path)
    if path and path.exists() and path.stat().st_size > 0:
        draft.image_path = path.name
        await session.commit()
        await session.refresh(draft)
        return {"image_url": f"/storage/{draft_id}", "image_path": draft.image_path}
    return {"image_url": None, "image_path": None, "message": error_message or "Image generation did not produce a file."}


@router.get("/scheduled", response_model=list[ScheduledPostOut])
async def list_scheduled(
    session: AsyncSession = Depends(get_db),
):
    """List scheduled posts."""
    r = await session.execute(
        select(ScheduledPost).where(ScheduledPost.status == "pending").order_by(ScheduledPost.scheduled_at)
    )
    return [ScheduledPostOut.model_validate(s) for s in r.scalars().all()]
