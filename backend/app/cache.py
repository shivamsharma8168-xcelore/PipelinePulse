import json

import redis
from flask import current_app


def get_redis_client():
    url = current_app.config.get("REDIS_URL")
    if not url:
        return None
    return redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1)


def cache_get(key):
    client = get_redis_client()
    if client is None:
        return None
    try:
        raw_value = client.get(key)
    except redis.RedisError:
        return None
    if not raw_value:
        return None
    return json.loads(raw_value)


def cache_set(key, value, ttl_seconds):
    client = get_redis_client()
    if client is None:
        return False
    try:
        client.setex(key, ttl_seconds, json.dumps(value))
    except redis.RedisError:
        return False
    return True
