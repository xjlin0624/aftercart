import hashlib
from datetime import datetime, timezone

from google import genai

from ..core.settings import get_settings
from .redis_store import allow_rate_limit, get_json, get_redis_client, set_json


def _digest(namespace: str, prompt: str, model: str) -> str:
    raw = f"{namespace}:{model}:{prompt}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def generate_cached_gemini_text(*, namespace: str, prompt: str, model: str) -> str:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    digest = _digest(namespace, prompt, model)
    cache_key = f"llm:cache:{digest}"
    dedupe_key = f"llm:dedupe:{digest}"
    cached = get_json(cache_key)
    if cached and isinstance(cached, dict) and "text" in cached:
        return cached["text"]

    if not allow_rate_limit(
        "llm:rate:global",
        limit=settings.llm_rate_limit_per_minute,
        window_seconds=settings.llm_rate_limit_window_seconds,
    ):
        raise RuntimeError("LLM rate limit exceeded.")

    redis_client = get_redis_client()
    dedupe_acquired = False
    try:
        dedupe_acquired = bool(
            redis_client.set(
                dedupe_key,
                "1",
                ex=settings.llm_dedupe_ttl_seconds,
                nx=True,
            )
        )
    except Exception:
        dedupe_acquired = True

    if not dedupe_acquired:
        cached = get_json(cache_key)
        if cached and isinstance(cached, dict) and "text" in cached:
            return cached["text"]
        raise RuntimeError("An identical Gemini request is already in progress.")

    client = genai.Client(api_key=settings.gemini_api_key)
    response = client.models.generate_content(model=model, contents=prompt)
    text = response.text.strip()
    set_json(
        cache_key,
        {
            "text": text,
            "model": model,
            "cached_at": datetime.now(timezone.utc).isoformat(),
        },
        ttl_seconds=settings.llm_cache_ttl_seconds,
    )
    try:
        redis_client.delete(dedupe_key)
    except Exception:
        pass
    return text
