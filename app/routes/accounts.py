"""GET /accounts and LinkedIn OAuth callback."""
import secrets
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.db_models import LinkedInAccount
from app.models.schemas import AccountOut
from app.services.linkedin_service import LinkedInService
from app.utils.logging import get_logger

router = APIRouter(prefix="/accounts", tags=["accounts"])
logger = get_logger(__name__)


@router.get("/auth/redirect-uri")
async def get_redirect_uri():
    """Return the redirect URI this app uses for LinkedIn OAuth. Copy this into LinkedIn Developer Portal → Auth → Authorized redirect URLs."""
    return {
        "redirect_uri": settings.linkedin_redirect_uri,
        "hint": "Add this exact URL in LinkedIn Developer Portal → your app → Auth → Authorized redirect URLs (no trailing slash).",
    }

# State format: "account_type:random_token" so callback knows personal vs company
STATE_PREFIX_PERSONAL = "personal:"
STATE_PREFIX_COMPANY = "company:"


@router.get("", response_model=list[AccountOut])
async def list_accounts(session: AsyncSession = Depends(get_db)):
    """List connected LinkedIn accounts (personal + company)."""
    try:
        r = await session.execute(
            select(LinkedInAccount).where(LinkedInAccount.is_active == True)
        )
        accounts = list(r.scalars().all())
        out = []
        for a in accounts:
            out.append(
                AccountOut(
                    id=int(a.id),
                    account_type=str(a.account_type or "personal"),
                    display_name=str(a.display_name or "LinkedIn Account"),
                    linkedin_urn=str(a.linkedin_urn) if a.linkedin_urn else None,
                    is_active=bool(a.is_active) if a.is_active is not None else True,
                )
            )
        return out
    except Exception as e:
        logger.exception("list_accounts_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Could not load accounts: {str(e)}",
        ) from e


@router.get("/auth/linkedin")
async def linkedin_auth_start(
    account_type: str = "personal",
    session: AsyncSession = Depends(get_db),
):
    """Return LinkedIn OAuth URL. Frontend redirects user there. Query: account_type=personal|company."""
    if account_type not in ("personal", "company"):
        account_type = "personal"
    token = secrets.token_urlsafe(16)
    state = f"{account_type}:{token}"
    service = LinkedInService(session)
    url = service.get_authorization_url(state, account_type=account_type)
    return {"authorization_url": url, "state": state}


@router.get("/auth/linkedin/callback")
async def linkedin_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    session: AsyncSession = Depends(get_db),
):
    """LinkedIn OAuth callback: exchange code for tokens, create account, redirect to dashboard."""
    if error:
        msg = (error_description or error).replace(" ", "+")[:120]
        if "unauthorized_scope" in error.lower() or "access_denied" in error.lower():
            msg = "LinkedIn+scope+not+approved.+In+Developer+Portal+add+product+Sign+In+with+LinkedIn+and+request+access."
        return RedirectResponse(url=f"/?error=linkedin&message={msg}", status_code=302)
    if not code:
        return RedirectResponse(
            url="/?error=linkedin&message=No+authorization+code.+Try+Connect+account+again.",
            status_code=302,
        )
    # Parse account_type from state (format "personal:token" or "company:token")
    account_type = "personal"
    if state and ":" in state:
        account_type = state.split(":")[0].lower() or "personal"
    if account_type not in ("personal", "company"):
        account_type = "personal"

    display_name = "Personal LinkedIn" if account_type == "personal" else "Company Page"
    service = LinkedInService(session)
    try:
        account = await service.exchange_code_for_tokens(
            code=code,
            state=state,
            account_type=account_type,
            display_name=display_name,
        )
        await session.commit()
        # Redirect user back to dashboard so they see the account in the dropdown
        return RedirectResponse(url="/?connected=1", status_code=302)
    except Exception as e:
        return RedirectResponse(url=f"/?error=linkedin&message={str(e)[:100]}", status_code=302)
