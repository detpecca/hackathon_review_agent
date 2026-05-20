"""
Redis 缓存客户端封装
- 连接管理
- 常用缓存操作
- 任务队列统计
"""
import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

from src.config.settings import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()

_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """获取 Redis 客户端单例"""
    global _client
    if _client is None:
        _client = redis.from_url(
            _settings.redis_url,
            decode_responses=True,
        )
    return _client


class RedisCache:
    """Redis 缓存操作封装"""

    def __init__(self, client: Optional[redis.Redis] = None):
        self.client = client or get_redis_client()

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        value = await self.client.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def set(
        self,
        key: str,
        value: Any,
        expire: int = 3600,
    ) -> None:
        """设置缓存值，默认1小时过期"""
        if not isinstance(value, str):
            value = json.dumps(value, default=str)
        await self.client.setex(key, expire, value)

    async def delete(self, key: str) -> None:
        """删除缓存键"""
        await self.client.delete(key)

    async def ping(self) -> bool:
        """检查 Redis 连接"""
        try:
            return await self.client.ping()
        except Exception as e:
            logger.warning(f"Redis ping failed: {e}")
            return False

    async def get_queue_stats(self) -> dict:
        """获取 Celery 队列统计"""
        try:
            queues = ["review", "sandbox", "report", "celery"]
            stats = {}
            for queue in queues:
                length = await self.client.llen(queue)
                stats[queue] = length
            return stats
        except Exception as e:
            logger.warning(f"Failed to get queue stats: {e}")
            return {}
