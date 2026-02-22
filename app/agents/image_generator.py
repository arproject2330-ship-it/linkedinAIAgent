"""Image Generation Agent: Gemini Image creates 1:1 professional image; save to storage."""
import asyncio
from pathlib import Path
import uuid

from app.config import settings
from app.services.gemini_service import generate_image
from app.workflow.state import WorkflowState


async def image_generator_agent(state: WorkflowState) -> dict:
    """Generate a relevant image from the full post (hook, body, suggested_visual); save under storage_dir."""
    post = state.get("post") or {}
    hook = post.get("hook") or ""
    body = post.get("body") or ""
    suggested_visual = post.get("suggested_visual") or ""
    if not (hook or body or suggested_visual):
        return {"image_path": None}

    storage_dir = settings.storage_dir
    name = f"linkedin_{uuid.uuid4().hex[:12]}.png"
    output_path = storage_dir / name

    path = await asyncio.to_thread(
        generate_image,
        hook,
        body,
        suggested_visual,
        output_path,
    )
    if path and path.exists() and path.stat().st_size > 0:
        # Store only filename so serving works regardless of working directory
        return {"image_path": path.name}
    return {"image_path": None}
