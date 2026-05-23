import redis

from app.core.settings import global_settings

redis_client = redis.Redis(
    host = global_settings.redis.host,
    port = global_settings.redis.port,
    db = global_settings.redis.db,
    password=global_settings.redis.password,
    decode_responses=True
)