"""POST /publish: smart schedule or post immediately; enqueue job for scheduled."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.db_models import PostDraft, PostHistory, ScheduledPost
from app.models.schemas import PublishRequest
from app.services.linkedin_service import LinkedInService
from app.agents.scheduler_agent import scheduler_agent
from app.workflow.state import WorkflowState
from app.utils.helpers import safe_json_loads
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/publish", tags=["publish"])

# APScheduler will be set from main on startup
_scheduler = None


def set_scheduler(sched):
    global _scheduler
    _scheduler = sched


def get_scheduler():
    return _scheduler


@router.post("")
async def publish(
    body: PublishRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Publish a draft: if current time is optimal, post now; else schedule for next best slot.
    Pass schedule_override to force a specific time.
    """
    # Load draft
    r = await session.execute(select(PostDraft).where(PostDraft.id == body.draft_id))
    draft = r.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    full_text = f"{draft.hook}\n\n{draft.body}\n\n{draft.cta}\n\n{draft.hashtags}".strip()
    insights = safe_json_loads(draft.performance_insights) if isinstance(draft.performance_insights, str) else draft.performance_insights
    state: WorkflowState = {"performance_insights": insights or {}}
    schedule_hint = scheduler_agent(state)
    suggested_immediate = schedule_hint.get("suggested_immediate", False)
    suggested_at = schedule_hint.get("suggested_scheduled_at")

    if body.schedule_override is not None:
        scheduled_at = body.schedule_override
        post_now = scheduled_at <= datetime.now(timezone.utc)
    else:
        post_now = suggested_immediate
        scheduled_at = None
        if suggested_at:
            try:
                scheduled_at = datetime.fromisoformat(suggested_at.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                scheduled_at = None

    if post_now or (scheduled_at and scheduled_at <= datetime.now(timezone.utc)):
        # Publish immediately
        linkedin = LinkedInService(session)
        post_id = await linkedin.create_ugc_post(body.account_id, full_text)
        await session.flush()
        history = PostHistory(
            account_id=body.account_id,
            content_text=full_text,
            linkedin_post_id=post_id,
            published_at=datetime.now(timezone.utc),
        )
        session.add(history)
        await session.commit()
        return {"status": "published", "linkedin_post_id": post_id, "scheduled_at": None}
    else:
        # Schedule for later
        if not scheduled_at:
            from datetime import timedelta
            scheduled_at = datetime.now(timezone.utc) + timedelta(days=1)
        scheduled = ScheduledPost(
            draft_id=body.draft_id,
            account_id=body.account_id,
            scheduled_at=scheduled_at,
            status="pending",
        )
        session.add(scheduled)
        await session.commit()
        await session.refresh(scheduled)
        # Enqueue APScheduler job
        sched = get_scheduler()
        if sched:
            sched.add_job(
                run_scheduled_publish,
                "date",
                run_date=scheduled_at,
                id=f"scheduled_{scheduled.id}",
                args=[scheduled.id],
                replace_existing=True,
            )
        return {"status": "scheduled", "scheduled_at": scheduled_at.isoformat(), "scheduled_post_id": scheduled.id}


def run_scheduled_publish(scheduled_post_id: int):
    """Background job (sync): load scheduled post, publish via LinkedIn, update status and history."""
    import asyncio
    asyncio.run(_run_scheduled_publish(scheduled_post_id))


async def _run_scheduled_publish(scheduled_post_id: int):
    from app.models.db_models import init_db
    factory = init_db()
    if factory is None:
        logger.warning("scheduled_publish_skipped_no_db", scheduled_post_id=scheduled_post_id)
        return
    async with factory() as session:
        r = await session.execute(
            select(ScheduledPost).where(ScheduledPost.id == scheduled_post_id)
        )
        row = r.scalar_one_or_none()
        if not row or row.status != "pending":
            return
        r2 = await session.execute(select(PostDraft).where(PostDraft.id == row.draft_id))
        draft = r2.scalar_one_or_none()
        if not draft:
            return
        full_text = f"{draft.hook}\n\n{draft.body}\n\n{draft.cta}\n\n{draft.hashtags}".strip()
        linkedin = LinkedInService(session)
        post_id = await linkedin.create_ugc_post(row.account_id, full_text)
        row.status = "published" if post_id else "failed"
        history = PostHistory(
            account_id=row.account_id,
            content_text=full_text,
            linkedin_post_id=post_id,
            published_at=datetime.now(timezone.utc),
        )
        session.add(history)
        await session.commit()
    logger.info("scheduled_publish_done", scheduled_post_id=scheduled_post_id, linkedin_post_id=post_id)
