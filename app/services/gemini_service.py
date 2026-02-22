"""Gemini API: text generation (Gemini Pro) and image generation (Gemini Image)."""
import json
import re
from pathlib import Path
from typing import Any, Optional

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Lazy client to avoid import errors when API key is missing
_gemini_client: Any = None


def _get_client():
    """Return Google GenAI client. Uses google-genai SDK."""
    global _gemini_client
    if _gemini_client is None:
        try:
            from google import genai

            _gemini_client = genai.Client(api_key=settings.gemini_api_key)
        except Exception as e:
            logger.warning("gemini_client_init_failed", error=str(e))
            raise ValueError("Gemini API key not configured or invalid") from e
    return _gemini_client


def generate_post_text(
    user_context: str,
    analytics_summary: str,
    strategy: dict[str, str],
) -> dict[str, str]:
    """
    Generate LinkedIn post (hook, body, cta, hashtags, suggested_visual) using Gemini Pro.
    Returns dict with keys: hook, body, cta, hashtags, suggested_visual.
    """
    client = _get_client()
    strategy_str = ", ".join(f"{k}: {v}" for k, v in strategy.items())

    prompt = f"""You are a LinkedIn growth strategist writing for ReeloomStudios.

Brand: ReeloomStudios — creative video and content studio. Founder-led, authentic voice. Positioning: quality storytelling, modern production, startup energy. Tone: confident but approachable, expert without being preachy. Write as the founder or the studio voice.

Generate a high-performing LinkedIn post that fits this brand.

Context:
{user_context}

Performance Insights:
{analytics_summary}

Strategy:
{strategy_str}

Rules:
- Strong 2-line hook (founder-style: bold take, question, or story open)
- Short readable paragraphs
- Natural human tone; ReeloomStudios = creative, driven, clear
- Marketing positioning clarity (studio/founder value, not generic)
- Subtle CTA (comment, follow, or link — never pushy)
- Max 5 hashtags (mix of niche + broad, e.g. #ContentCreation #FounderLife #ReeloomStudios)
- Optimized for dwell time
- Avoid robotic or corporate jargon

Return ONLY valid JSON with exactly these keys (no markdown, no code block):
- "hook": string (first 2 lines that grab attention)
- "body": string (main content, short paragraphs)
- "cta": string (call to action)
- "hashtags": string (comma or space separated, max 5)
- "suggested_visual": string (1-2 sentences describing a concrete image that matches this post: scene, mood, key visual element; on-brand, minimal, professional. E.g. "Clean desk with laptop and notebook, soft daylight, text overlay area left empty" or "Abstract gradient background with bold headline space, modern and minimal.")
"""

    try:
        response = client.models.generate_content(
            model=settings.gemini_text_model,
            contents=[prompt],
        )
        text = (response.text or "").strip()
        # Strip markdown code block if present
        if "```" in text:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
            if match:
                text = match.group(1).strip()
        data = json.loads(text)
        return {
            "hook": data.get("hook", ""),
            "body": data.get("body", ""),
            "cta": data.get("cta", ""),
            "hashtags": data.get("hashtags", ""),
            "suggested_visual": data.get("suggested_visual", ""),
        }
    except Exception as e:
        logger.exception("gemini_post_generation_failed", error=str(e))
        raise


def _image_error_message(err: Exception) -> str:
    """Turn API errors into a short user-facing message."""
    s = str(err).strip()
    if "billed users" in s or "only accessible to billed" in s:
        return "Imagen requires a billed Google Cloud / Gemini account. Enable billing in Google Cloud Console, or use a Gemini image model (free tier has limited quota)."
    if "429" in s or "RESOURCE_EXHAUSTED" in s or "quota" in s.lower() or "exceeded" in s.lower():
        return "Image generation quota exceeded (free tier). Try again in a few minutes or see https://ai.google.dev/gemini-api/docs/rate-limits."
    if "400" in s or "INVALID_ARGUMENT" in s:
        return s[:200] if len(s) > 200 else s
    return s[:200] if len(s) > 200 else (s or "Image generation failed.")


def generate_image(hook: str, body: str, suggested_visual: str, output_path: Path) -> tuple[Path, Optional[str]]:
    """
    Generate a relevant LinkedIn image from the post content. Saves as PNG.
    Returns (output_path, error_message). error_message is set when no file was produced.
    Uses Imagen (generate_images) when model is imagen-* else Gemini (generate_content).
    """
    client = _get_client()
    body_snippet = (body or "")[:400].strip()
    visual_brief = (suggested_visual or "").strip() or "professional, minimal, on-brand"
    prompt = f"""Create a single professional image that will accompany this LinkedIn post. The image must visually support the post message.

POST HOOK (opening lines):
{hook[:300] if hook else "—"}

POST MAIN MESSAGE:
{body_snippet or "—"}

VISUAL BRIEF FROM AUTHOR:
{visual_brief}

Requirements:
- ReeloomStudios brand: creative video/content studio, modern, clean, bold.
- Image must feel relevant to the post topic and tone (no generic stock look).
- 1:1 square format, suitable for LinkedIn. No watermark, no clip art.
- Style: minimal, professional, high contrast. High quality photo or illustration.
"""
    out = Path(output_path)
    if out.suffix.lower() != ".png":
        out = out.with_suffix(".png")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    last_error: Optional[str] = None

    # Imagen models: use generate_images (imagen-4-preview, imagen-4.0-generate-001, etc.)
    imagen_models = ("imagen-4", "imagen-3")
    model_id = (settings.gemini_image_model or "").strip().lower()
    # Map preview alias to GA model id
    imagen_model = settings.gemini_image_model or "imagen-4.0-generate-001"
    if model_id == "imagen-4-preview":
        imagen_model = "imagen-4.0-generate-001"
    if any(model_id.startswith(p) for p in imagen_models):
        try:
            from google.genai import types
            import base64
            resp = client.models.generate_images(
                model=imagen_model,
                prompt=prompt[:2000],
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="1:1",
                ),
            )
            if getattr(resp, "generated_images", None) and len(resp.generated_images) > 0:
                gen = resp.generated_images[0]
                img_obj = getattr(gen, "image", None)
                if img_obj is not None:
                    raw = getattr(img_obj, "image_bytes", None)
                    if raw:
                        if isinstance(raw, bytes):
                            out.write_bytes(raw)
                        else:
                            out.write_bytes(base64.b64decode(raw))
                        if out.stat().st_size > 0:
                            return (out, None)
                    if hasattr(img_obj, "save"):
                        img_obj.save(str(out))
                        return (out, None)
        except Exception as e:
            logger.warning("imagen_generate_failed", model=imagen_model, error=str(e))
            last_error = _image_error_message(e)

    # Gemini image models: use generate_content with response_modalities IMAGE
    try:
        from google.genai import types
        gen_config = types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"])
    except Exception:
        gen_config = None

    models_to_try = [settings.gemini_image_model, "gemini-2.5-flash-image", "gemini-3-pro-image-preview"]
    for model in models_to_try:
        if not model or any(model.strip().lower().startswith(p) for p in imagen_models):
            continue
        try:
            kwargs = {"model": model, "contents": [prompt]}
            if gen_config is not None:
                kwargs["config"] = gen_config
            response = client.models.generate_content(**kwargs)
            parts = getattr(response, "parts", None)
            if parts is None and response.candidates and response.candidates[0].content.parts:
                parts = response.candidates[0].content.parts
            if not parts:
                continue
            for part in parts:
                if hasattr(part, "as_image") and callable(getattr(part, "as_image", None)):
                    try:
                        img = part.as_image()
                        if img is not None:
                            img.save(str(out))
                            return (out, None)
                    except Exception:
                        pass
                if getattr(part, "inline_data", None) and getattr(part.inline_data, "data", None):
                    data = part.inline_data.data
                    if isinstance(data, bytes):
                        out.write_bytes(data)
                    else:
                        import base64
                        out.write_bytes(base64.b64decode(data))
                    if out.stat().st_size > 0:
                        return (out, None)
        except Exception as e:
            logger.warning("gemini_image_try_failed", model=model, error=str(e))
            last_error = _image_error_message(e)
            continue

    out.touch()
    return (out, last_error or "Image generation did not produce a file.")
