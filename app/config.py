"""Application configuration from environment."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root (parent of app/); .env is loaded from here so it works regardless of CWD
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini
    gemini_api_key: str = ""
    gemini_text_model: str = "gemini-3-flash-preview"
    gemini_image_model: str = "imagen-4.0-generate-001"

    # LinkedIn
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    # Must match EXACTLY the redirect URL in LinkedIn Developer Portal (Auth → Authorized redirect URLs).
    # Default 127.0.0.1 to match common portal setup; use localhost in .env if your portal has localhost.
    linkedin_redirect_uri: str = "http://127.0.0.1:8000/auth/linkedin/callback"

    # Database (Supabase: use Connection string from Supabase Dashboard → Settings → Database)
    database_url: str = ""

    # Optional: Supabase project URL (for future Supabase Auth/Storage client)
    supabase_url: str = ""
    supabase_key: str = ""

    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic (replace +asyncpg with empty string)."""
        if not self.database_url:
            return ""
        return self.database_url.replace("+asyncpg", "") if "+asyncpg" in self.database_url else self.database_url

    # App
    secret_key: str = "change-me-in-production"
    storage_path: str = "./storage"
    log_level: str = "INFO"

    @property
    def storage_dir(self) -> Path:
        p = Path(self.storage_path)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
