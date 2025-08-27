import redis.asyncio as redis
import json
from typing import Optional
from datetime import timedelta

class RedisManager:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client = None
        
    async def init_redis(self):
        try:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            print("✅ Redis connected successfully")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            self.redis_client = None
    
    async def close(self):
        if self.redis_client:
            await self.redis_client.close()
    
    def _make_task_context_key(self, task_id: int, user_id: int) -> str:
        return f"task_context:{task_id}:{user_id}"
    
    def _make_task_exchanges_key(self, task_id: int, user_id: int) -> str:
        return f"task_exchanges:{task_id}:{user_id}"
    
    async def get_task_context(self, task_id: int, user_id: int) -> Optional[str]:
        if not self.redis_client:
            return None
        
        try:
            key = self._make_task_context_key(task_id, user_id)
            cached_context = await self.redis_client.get(key)
            return cached_context
        except Exception as e:
            print(f"Redis get error for task context: {e}")
            return None
    
    async def set_task_context(self, task_id: int, user_id: int, context: str, ttl_hours: int = 24) -> bool:
        if not self.redis_client:
            print(f"❌ Redis client not connected!")
            return False
        
        try:
            key = self._make_task_context_key(task_id, user_id)
            await self.redis_client.setex(
                key, 
                timedelta(hours=ttl_hours), 
                context
            )
            print(f"✅ Cached context for task {task_id}:{user_id} (TTL: {ttl_hours}h)")
            return True
        except Exception as e:
            print(f"❌ Redis set error for task context: {e}")
            return False
    
    async def invalidate_task_context(self, task_id: int, user_id: int) -> bool:
        if not self.redis_client:
            return False
        
        try:
            key = self._make_task_context_key(task_id, user_id)
            await self.redis_client.delete(key)
            
            exchanges_key = self._make_task_exchanges_key(task_id, user_id)
            await self.redis_client.delete(exchanges_key)
            
            return True
        except Exception as e:
            print(f"Redis delete error for task context: {e}")
            return False
    
    async def cache_task_exchanges(self, task_id: int, user_id: int, exchanges: list, ttl_hours: int = 1) -> bool:
        if not self.redis_client:
            return False
        
        try:
            key = self._make_task_exchanges_key(task_id, user_id)
            serialized_exchanges = json.dumps(exchanges, default=str)
            await self.redis_client.setex(
                key,
                timedelta(hours=ttl_hours),
                serialized_exchanges
            )
            return True
        except Exception as e:
            print(f"Redis cache exchanges error: {e}")
            return False
    
    async def get_cached_task_exchanges(self, task_id: int, user_id: int) -> Optional[list]:
        if not self.redis_client:
            return None
        
        try:
            key = self._make_task_exchanges_key(task_id, user_id)
            cached_exchanges = await self.redis_client.get(key)
            if cached_exchanges:
                return json.loads(cached_exchanges)
            return None
        except Exception as e:
            print(f"Redis get exchanges error: {e}")
            return None
