"""POST /generate and POST /regenerate."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.db_models import PostDraft
from app.models.schemas import GenerateRequest, GenerateResponse
from app.workflow.graph import create_post_graph
from app.utils.helpers import safe_json_dumps
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/generate", tags=["generate"])
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = create_post_graph()
    return _graph


@router.post("", response_model=GenerateResponse)
async def generate_post(
    body: GenerateRequest,
    session: AsyncSession = Depends(get_db),
):
    """Run the full pipeline and return a draft ready for review."""
    if body.regenerate_draft_id:
        return await _regenerate(session, body.regenerate_draft_id)

    initial: dict = {
        "user_input": body.user_input or None,
        "session": session,
    }
    graph = get_graph()
    try:
        result = await graph.ainvoke(initial)
    except OSError as e:
        if getattr(e, "errno", None) == 101 or "network is unreachable" in str(e).lower():
            logger.warning("generate_network_unreachable", error=str(e))
            raise HTTPException(
                status_code=503,
                detail="Network unreachable (AI service). On Render free tier the service may have just woken up—please try again in 10–20 seconds. If it persists, check that GEMINI_API_KEY is set in Render Environment.",
            ) from e
        logger.exception("generate_flow_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        logger.exception("generate_flow_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e

    post = result.get("post") or {}
    hook = post.get("hook", "")
    body_text = post.get("body", "")  # body content of the post
    cta = post.get("cta", "")
    hashtags = post.get("hashtags", "")
    suggested_visual = post.get("suggested_visual")
    image_path = result.get("image_path")
    performance_insights = result.get("performance_insights")
    strategy = result.get("strategy")

    draft = PostDraft(
        hook=hook,
        body=body_text,
        cta=cta,
        hashtags=hashtags,
        suggested_visual=suggested_visual,
        image_path=image_path,
        performance_insights=safe_json_dumps(performance_insights),
        strategy=safe_json_dumps(strategy),
    )
    session.add(draft)
    await session.commit()
    await session.refresh(draft)

    post_preview = {
        "hook": hook,
        "body": body_text,
        "cta": cta,
        "hashtags": hashtags,
        "suggested_visual": suggested_visual,
    }
    return GenerateResponse(
        status="ready",
        message="Your LinkedIn post is ready for review.",
        draft_id=draft.id,
        post_preview=post_preview,
        image_url=f"/storage/{draft.id}" if draft.image_path else None,
        image_path=draft.image_path,
    )


async def _regenerate(session: AsyncSession, draft_id: int) -> GenerateResponse:
    """Regenerate from an existing draft (use its content as user_input)."""
    r = await session.execute(select(PostDraft).where(PostDraft.id == draft_id))
    existing = r.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Draft not found")
    user_input = f"{existing.hook}\n\n{existing.body}\n\n{existing.cta}"
    initial = {"user_input": user_input, "session": session}
    graph = get_graph()
    try:
        result = await graph.ainvoke(initial)
    except OSError as e:
        if getattr(e, "errno", None) == 101 or "network is unreachable" in str(e).lower():
            logger.warning("regenerate_network_unreachable", error=str(e))
            raise HTTPException(
                status_code=503,
                detail="Network unreachable (AI service). Try again in 10–20 seconds; on Render free tier the service may have just woken up.",
            ) from e
        raise HTTPException(status_code=500, detail=str(e)) from e
    post = result.get("post") or {}
    draft = PostDraft(
        hook=post.get("hook", ""),
        body=post.get("body", ""),
        cta=post.get("cta", ""),
        hashtags=post.get("hashtags", ""),
        suggested_visual=post.get("suggested_visual"),
        image_path=result.get("image_path"),
        performance_insights=safe_json_dumps(result.get("performance_insights")),
        strategy=safe_json_dumps(result.get("strategy")),
    )
    session.add(draft)
    await session.commit()
    await session.refresh(draft)
    return GenerateResponse(
        status="ready",
        message="Your LinkedIn post is ready for review.",
        draft_id=draft.id,
        post_preview={
            "hook": draft.hook,
            "body": draft.body,
            "cta": draft.cta,
            "hashtags": draft.hashtags,
            "suggested_visual": draft.suggested_visual,
        },
        image_url=f"/storage/{draft.id}" if draft.image_path else None,
        image_path=draft.image_path,
    )


@router.post("/regenerate", response_model=GenerateResponse)
async def regenerate_post(
    body: GenerateRequest,
    session: AsyncSession = Depends(get_db),
):
    """Regenerate a new draft from an existing one (pass regenerate_draft_id in body)."""
    if not body.regenerate_draft_id:
        raise HTTPException(status_code=400, detail="regenerate_draft_id required")
    return await _regenerate(session, body.regenerate_draft_id)


# Standalone POST /regenerate (same as above, for API surface in FLOW.md)
regenerate_router = APIRouter(tags=["generate"])


@regenerate_router.post("/regenerate", response_model=GenerateResponse)
async def regenerate_standalone(
    body: GenerateRequest,
    session: AsyncSession = Depends(get_db),
):
    """Regenerate from existing draft. Body: { \"regenerate_draft_id\": <id> }."""
    if not body.regenerate_draft_id:
        raise HTTPException(status_code=400, detail="regenerate_draft_id required")
    return await _regenerate(session, body.regenerate_draft_id)
