import asyncio
from databasemanager import DatabaseManager
from llmmanager import LLMManager
from config import DATABASE_URL

db_manager = DatabaseManager(DATABASE_URL)
llm_manager = LLMManager()

async def init_backend():
    """Инициализация backend сервиса"""
    print("Backend microservice started")
    await db_manager.init_db()
    await llm_manager.init_redis()
    print("✅ Database and Redis initialized")

async def shutdown_backend():
    """Завершение работы backend сервиса"""
    await llm_manager.redis.close()
    print("Backend microservice ended")

if __name__ == "__main__":
    asyncio.run(init_backend())