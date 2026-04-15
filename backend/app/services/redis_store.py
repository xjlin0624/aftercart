import json
import logging
from functools import lru_cache
from typing import Any

from redis import Redis
from redis.exceptions import RedisError

from ..core.settings import get_settings


logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


def ping_redis(client: Redis | None = None) -> bool:
    client = client or get_redis_client()
    try:
        return bool(client.ping())
    except RedisError:
        return False


def get_json(key: str, *, client: Redis | None = None) -> Any | None:
    client = client or get_redis_client()
    try:
        raw = client.get(key)
    except RedisError:
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON payload stored at Redis key %s.", key)
        return None


def set_json(key: str, value: Any, *, ttl_seconds: int | None = None, client: Redis | None = None) -> bool:
    client = client or get_redis_client()
    try:
        client.set(key, json.dumps(value), ex=ttl_seconds)
        return True
    except (RedisError, TypeError):
        return False


def allow_rate_limit(key: str, *, limit: int, window_seconds: int, client: Redis | None = None) -> bool:
    client = client or get_redis_client()
    try:
        with client.pipeline() as pipe:
            pipe.incr(key)
            pipe.expire(key, window_seconds, nx=True)
            count, _ = pipe.execute()
    except RedisError:
        return True
    return int(count) <= limit


def is_circuit_open(scope: str, *, client: Redis | None = None) -> bool:
    client = client or get_redis_client()
    try:
        return client.exists(f"circuit:{scope}") == 1
    except RedisError:
        return False


def record_circuit_failure(
    scope: str,
    *,
    threshold: int,
    cooldown_seconds: int,
    client: Redis | None = None,
) -> dict[str, int | bool]:
    client = client or get_redis_client()
    failure_key = f"circuit:failures:{scope}"
    open_key = f"circuit:{scope}"
    try:
        with client.pipeline() as pipe:
            pipe.incr(failure_key)
            pipe.expire(failure_key, cooldown_seconds)
            failures, _ = pipe.execute()
        is_open = int(failures) >= threshold
        if is_open:
            client.set(open_key, "1", ex=cooldown_seconds)
        return {"failures": int(failures), "open": is_open}
    except RedisError:
        return {"failures": 0, "open": False}


def reset_circuit(scope: str, *, client: Redis | None = None) -> None:
    client = client or get_redis_client()
    try:
        client.delete(f"circuit:{scope}", f"circuit:failures:{scope}")
    except RedisError:
        return
