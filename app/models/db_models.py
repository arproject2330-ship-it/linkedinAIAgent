"""SQLAlchemy models for PostgreSQL. Run migrations to create tables."""
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.config import settings


class Base(DeclarativeBase):
    pass


class LinkedInAccount(Base):
    """LinkedIn account (personal or company page) with OAuth tokens."""

    __tablename__ = "linkedin_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)  # personal | company
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    linkedin_urn: Mapped[str | None] = mapped_column(String(128), nullable=True)  # urn:li:person:xxx or urn:li:organization:xxx
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    post_histories: Mapped[list["PostHistory"]] = relationship("PostHistory", back_populates="account")
    scheduled_posts: Mapped[list["ScheduledPost"]] = relationship("ScheduledPost", back_populates="account")


class PostDraft(Base):
    """Draft post ready for review/edit/publish."""

    __tablename__ = "post_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hook: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    cta: Mapped[str] = mapped_column(Text, nullable=False)
    hashtags: Mapped[str] = mapped_column(String(500), nullable=False)
    suggested_visual: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    performance_insights: Mapped[dict | None] = mapped_column(Text, nullable=True)  # JSON string
    strategy: Mapped[dict | None] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    scheduled_posts: Mapped[list["ScheduledPost"]] = relationship("ScheduledPost", back_populates="draft")


class PostHistory(Base):
    """Published post for analytics and performance learning."""

    __tablename__ = "post_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("linkedin_accounts.id"), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    linkedin_post_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    impressions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engagement_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    account: Mapped["LinkedInAccount"] = relationship("LinkedInAccount", back_populates="post_histories")


class ScheduledPost(Base):
    """Post scheduled for future publish via APScheduler."""

    __tablename__ = "scheduled_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    draft_id: Mapped[int] = mapped_column(Integer, ForeignKey("post_drafts.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("linkedin_accounts.id"), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | published | failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    draft: Mapped["PostDraft"] = relationship("PostDraft", back_populates="scheduled_posts")
    account: Mapped["LinkedInAccount"] = relationship("LinkedInAccount", back_populates="scheduled_posts")


# Async engine and session factory
_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db() -> async_sessionmaker[AsyncSession]:
    """Create async engine and session factory. Call once at app startup."""
    global _engine, _session_factory
    if _session_factory is not None:
        return _session_factory
    if not (settings.database_url or "").strip():
        raise ValueError(
            "DATABASE_URL is not set. Add your Supabase connection string to .env. "
            "Supabase Dashboard → Settings → Database → Connection string (URI); use postgresql+asyncpg://..."
        )
    _engine = create_async_engine(
        settings.database_url,
        echo=settings.log_level.upper() == "DEBUG",
    )
    _session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency: yield a DB session for FastAPI. Caller commits/rollbacks."""
    factory = init_db()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables() -> None:
    """Create all tables. Use for dev; prefer Alembic for production."""
    init_db()
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
