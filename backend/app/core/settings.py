from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(
        default="postgresql+psycopg://aftercart:aftercart@postgres:5432/aftercart",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    celery_broker_url: str | None = Field(default=None, alias="CELERY_BROKER_URL")
    celery_result_backend: str | None = Field(default=None, alias="CELERY_RESULT_BACKEND")
    price_check_batch_size: int = Field(default=100, alias="PRICE_CHECK_BATCH_SIZE")
    price_check_interval_minutes: int = Field(default=15, alias="PRICE_CHECK_INTERVAL_MINUTES")
    delivery_check_interval_minutes: int = Field(
        default=60,
        alias="DELIVERY_CHECK_INTERVAL_MINUTES",
    )
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    allowed_origins: str = Field(default="", alias="ALLOWED_ORIGINS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    jwt_secret: str = Field(default="change-me-in-production", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")
    sentry_environment: str = Field(default="development", alias="SENTRY_ENVIRONMENT")
    sentry_release: str = Field(default="", alias="SENTRY_RELEASE")
    sentry_traces_sample_rate: float = Field(default=0.0, alias="SENTRY_TRACES_SAMPLE_RATE")
    sentry_profiles_sample_rate: float = Field(default=0.0, alias="SENTRY_PROFILES_SAMPLE_RATE")
    sentry_enable_celery: bool = Field(default=True, alias="SENTRY_ENABLE_CELERY")

    playwright_headless: bool = Field(default=True, alias="PLAYWRIGHT_HEADLESS")
    playwright_browser: str = Field(default="chromium", alias="PLAYWRIGHT_BROWSER")
    playwright_timeout_ms: int = Field(default=15000, alias="PLAYWRIGHT_TIMEOUT_MS")
    playwright_navigation_timeout_ms: int = Field(
        default=20000,
        alias="PLAYWRIGHT_NAVIGATION_TIMEOUT_MS",
    )
    playwright_storage_state_dir: str = Field(
        default="backend/.playwright/state",
        alias="PLAYWRIGHT_STORAGE_STATE_DIR",
    )
    scraper_user_agent: str = Field(
        default="AfterCartBot/1.0 (+https://aftercart.app)",
        alias="SCRAPER_USER_AGENT",
    )
    scraper_retry_attempts: int = Field(default=3, alias="SCRAPER_RETRY_ATTEMPTS")
    scraper_backoff_base_seconds: int = Field(default=2, alias="SCRAPER_BACKOFF_BASE_SECONDS")
    scraper_backoff_max_seconds: int = Field(default=30, alias="SCRAPER_BACKOFF_MAX_SECONDS")
    scraper_rate_limit_per_minute: int = Field(default=20, alias="SCRAPER_RATE_LIMIT_PER_MINUTE")
    scraper_circuit_failure_threshold: int = Field(
        default=5,
        alias="SCRAPER_CIRCUIT_FAILURE_THRESHOLD",
    )
    scraper_circuit_cooldown_seconds: int = Field(
        default=300,
        alias="SCRAPER_CIRCUIT_COOLDOWN_SECONDS",
    )

    llm_cache_ttl_seconds: int = Field(default=900, alias="LLM_CACHE_TTL_SECONDS")
    llm_rate_limit_per_minute: int = Field(default=10, alias="LLM_RATE_LIMIT_PER_MINUTE")
    llm_rate_limit_window_seconds: int = Field(default=60, alias="LLM_RATE_LIMIT_WINDOW_SECONDS")
    llm_dedupe_ttl_seconds: int = Field(default=300, alias="LLM_DEDUPE_TTL_SECONDS")

    fcm_enabled: bool = Field(default=False, alias="FCM_ENABLED")
    fcm_service_account_json: str = Field(default="", alias="FCM_SERVICE_ACCOUNT_JSON")
    fcm_service_account_file: str = Field(default="", alias="FCM_SERVICE_ACCOUNT_FILE")
    fcm_default_ttl_seconds: int = Field(default=3600, alias="FCM_DEFAULT_TTL_SECONDS")

    render_external_url: str = Field(default="http://localhost:8000", alias="RENDER_EXTERNAL_URL")

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_db_driver(cls, v: str) -> str:
        # Render (and some other hosts) provide postgresql:// but psycopg3 requires postgresql+psycopg://
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
