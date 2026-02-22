"""Serve generated draft images by draft_id."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.db_models import PostDraft

router = APIRouter(prefix="/storage", tags=["storage"])


@router.get("/{draft_id}")
async def get_draft_image(
    draft_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Return the generated image for a draft if it exists."""
    r = await session.execute(select(PostDraft).where(PostDraft.id == draft_id))
    draft = r.scalar_one_or_none()
    if not draft or not draft.image_path:
        raise HTTPException(status_code=404, detail="Image not found")
    raw = Path(draft.image_path)
    # Resolve relative to storage dir (we store filename or relative path)
    path = (settings.storage_dir / raw) if not raw.is_absolute() else raw
    path = path.resolve()
    try:
        path.relative_to(settings.storage_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid path")
    if not path.is_file() or path.stat().st_size == 0:
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(path, media_type="image/png")
