"""LinkedIn OAuth and posting (UGC Posts API)."""
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.db_models import LinkedInAccount
from app.utils.logging import get_logger

logger = get_logger(__name__)

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_API_BASE = "https://api.linkedin.com"
RESTLI_VERSION = "2.0.0"


class LinkedInService:
    """LinkedIn OAuth and post creation."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def get_authorization_url(self, state: str, account_type: str = "personal") -> str:
        """Build LinkedIn OAuth authorization URL. Use state to pass account_type if needed."""
        scopes = ["openid", "profile", "email", "w_member_social", "r_member_social"]
        if account_type == "company":
            scopes.extend(["w_organization_social", "r_organization_social"])
        params = {
            "response_type": "code",
            "client_id": settings.linkedin_client_id,
            "redirect_uri": settings.linkedin_redirect_uri,
            "state": state,
            "scope": " ".join(scopes),
        }
        return f"{LINKEDIN_AUTH_URL}?{urlencode(params)}"

    async def exchange_code_for_tokens(
        self, code: str, state: str, account_type: str = "personal", display_name: str = "LinkedIn Account"
    ) -> LinkedInAccount:
        """Exchange authorization code for access token; create or update LinkedInAccount."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                LINKEDIN_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.linkedin_redirect_uri,
                    "client_id": settings.linkedin_client_id,
                    "client_secret": settings.linkedin_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        resp.raise_for_status()
        data = resp.json()
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in")
        if not access_token:
            raise ValueError("No access_token in LinkedIn response")

        token_expires_at = None
        if expires_in is not None:
            try:
                token_expires_at = datetime.now(timezone.utc).replace(microsecond=0)
                from datetime import timedelta
                token_expires_at = token_expires_at + timedelta(seconds=int(expires_in))
            except (TypeError, ValueError):
                pass

        linkedin_urn = await self._get_author_urn(access_token, account_type)
        if not linkedin_urn and data.get("scope"):
            pass
        if not linkedin_urn and "openid" in (data.get("scope") or ""):
            linkedin_urn = await self._get_urn_from_userinfo(access_token)

        r = await self.session.execute(
            select(LinkedInAccount).where(LinkedInAccount.account_type == account_type).limit(1)
        )
        existing = r.scalar_one_or_none()
        if existing:
            existing.access_token = access_token
            existing.refresh_token = refresh_token
            existing.token_expires_at = token_expires_at
            existing.linkedin_urn = linkedin_urn or existing.linkedin_urn
            existing.updated_at = datetime.now(timezone.utc)
            return existing

        account = LinkedInAccount(
            account_type=account_type,
            display_name=display_name,
            linkedin_urn=linkedin_urn,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            is_active=True,
        )
        self.session.add(account)
        await self.session.flush()
        return account

    async def _get_urn_from_userinfo(self, access_token: str) -> str | None:
        """Get person URN from OpenID Connect userinfo."""
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(
                    "https://api.linkedin.com/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            r.raise_for_status()
            data = r.json()
            sub = data.get("sub")
            if sub and sub.startswith("urn:"):
                return sub
            if sub:
                return f"urn:li:person:{sub}"
            return None
        except Exception as e:
            logger.warning("linkedin_userinfo_failed", error=str(e))
            return None

    async def _get_author_urn(self, access_token: str, account_type: str) -> str | None:
        """Resolve author URN for posting (person or organization)."""
        urn = await self._get_urn_from_userinfo(access_token)
        if urn:
            return urn
        return None

    async def create_ugc_post(self, account_id: int, text: str) -> str | None:
        """Create a UGC post on LinkedIn. Returns post id (X-RestLi-Id) or None on failure."""
        r = await self.session.execute(select(LinkedInAccount).where(LinkedInAccount.id == account_id))
        account = r.scalar_one_or_none()
        if not account or not account.access_token:
            logger.warning("create_ugc_post_no_account", account_id=account_id)
            return None
        author_urn = account.linkedin_urn
        if not author_urn:
            author_urn = await self._get_urn_from_userinfo(account.access_token)
            if author_urn:
                account.linkedin_urn = author_urn
                await self.session.flush()
        if not author_urn:
            logger.warning("create_ugc_post_no_urn", account_id=account_id)
            return None

        body = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{LINKEDIN_API_BASE}/v2/ugcPosts",
                    json=body,
                    headers={
                        "Authorization": f"Bearer {account.access_token}",
                        "Content-Type": "application/json",
                        "X-Restli-Protocol-Version": RESTLI_VERSION,
                    },
                )
            resp.raise_for_status()
            post_id = resp.headers.get("X-RestLi-Id")
            return post_id or ""
        except httpx.HTTPStatusError as e:
            logger.warning("create_ugc_post_failed", account_id=account_id, status=e.response.status_code, body=e.response.text[:500])
            return None
        except Exception as e:
            logger.warning("create_ugc_post_failed", account_id=account_id, error=str(e))
            return None
