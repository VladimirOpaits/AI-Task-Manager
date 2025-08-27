import asyncio
from datetime import datetime
from typing import Optional, Dict, List, AsyncGenerator

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

async def shutdown_backend():
    """Завершение работы backend сервиса"""
    await llm_manager.redis.close()
    print("Backend microservice ended")

async def authenticate_user(google_id: str, email: str, name: Optional[str] = None, 
                          picture: Optional[str] = None, access_token: str = "", 
                          refresh_token: Optional[str] = None, expires_at: str = "") -> Dict:
    """Аутентификация/создание пользователя"""
    expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
    
    existing_user = await db_manager.get_user_by_google_id(google_id)
    
    if existing_user:
        await db_manager.update_user_tokens(
            google_id, 
            access_token, 
            refresh_token, 
            expires_datetime
        )
        return existing_user
    else:
        return await db_manager.create_user(
            google_id,
            email,
            name,
            picture,
            access_token,
            refresh_token,
            expires_datetime
        )

async def get_user_by_google_id(google_id: str) -> Optional[Dict]:
    """Получить пользователя по Google ID"""
    return await db_manager.get_user_by_google_id(google_id)

async def get_user_tasks(google_id: str) -> Dict:
    """Получить задачи пользователя"""
    user = await db_manager.get_user_by_google_id(google_id)
    if not user:
        raise ValueError("User not found")
    
    tasks = await db_manager.get_users_tasks(user["id"])
    return {"user_id": user["id"], "tasks": tasks}

async def get_task_by_id(task_id: int, google_id: str) -> Dict:
    """Получить задачу по ID"""
    user = await db_manager.get_user_by_google_id(google_id)
    if not user:
        raise ValueError("User not found")
    
    return await db_manager.get_task(task_id, user["id"])

async def create_new_task(task_name: str, task_description: str, google_id: str, private: bool = True) -> Dict:
    """Создать новую задачу"""
    user = await db_manager.get_user_by_google_id(google_id)
    if not user:
        raise ValueError("User not found")
    
    created_task = await db_manager.create_task(
        task_name, 
        task_description, 
        user["id"], 
        private
    )
    
    return {"message": "Success", "task": created_task}

async def delete_task_by_id(task_id: int, google_id: str) -> Dict:
    """Удалить задачу"""
    user = await db_manager.get_user_by_google_id(google_id)
    if not user:
        raise ValueError("User not found")
    
    deleted_task = await db_manager.delete_task(task_id, user["id"])
    return {"message": "Task deleted successfully", "task_id": deleted_task["id"]}

async def create_task_exchange(task_id: int, google_id: str, prompt: str) -> Dict:
    """Создать обмен сообщениями с AI"""
    user = await db_manager.get_user_by_google_id(google_id)
    if not user:
        raise ValueError("User not found")

    task = await db_manager.get_task(task_id, user["id"])
    
    await llm_manager.invalidate_task_cache(task_id, user["id"])
    
    task_context = await llm_manager.generate_task_context(
        task["task_name"], 
        task["task_description"], 
        task["id"], 
        user["id"], 
        task["task_context"]
    )
    await db_manager.update_task_context(task_id, user["id"], task_context)
    
    result = llm_manager.get_answer(prompt, task_context)
    await db_manager.create_exchange(task_id, user["id"], prompt, result)
    
    return {"message": "Exchange created successfully", "exchange": result}

async def get_task_exchanges(task_id: int, google_id: str) -> Dict:
    """Получить историю обменов для задачи"""
    user = await db_manager.get_user_by_google_id(google_id)
    if not user:
        raise ValueError("User not found")
    
    exchanges = await db_manager.get_task_exchanges(task_id, user["id"])
    task = await db_manager.get_task(task_id, user["id"])
    return {"task": task, "exchanges": exchanges}

async def get_task_context(task_id: int, google_id: str) -> Dict:
    """Получить контекст задачи"""
    user = await db_manager.get_user_by_google_id(google_id)
    if not user:
        raise ValueError("User not found")
    
    task = await db_manager.get_task(task_id, user["id"])
        
    task_context = await llm_manager.generate_task_context(
        task["task_name"], 
        task["task_description"], 
        task["id"], 
        user["id"], 
        task["task_context"]
    )
    
    if task_context != task["task_context"]:
        await db_manager.update_task_context(task_id, user["id"], task_context)
    
    return {"task": task, "context": task_context}

async def change_task_status(task_id: int, user_id: int, status: str) -> Dict:
    """Изменить статус задачи"""
    await db_manager.update_task_status(task_id, user_id, status)
    return {"message": "Task status changed successfully"}

async def update_task_context_by_user(task_id: int, user_id: int, context: str) -> Dict:
    """Обновить контекст задачи пользователем"""
    await db_manager.update_task_context(task_id, user_id, context)
    await llm_manager.invalidate_task_cache(task_id, user_id)
    return {"message": "Task context updated successfully"}

async def get_public_tasks() -> Dict:
    """Получить публичные задачи"""
    tasks = await db_manager.get_public_tasks()
    return {"tasks": tasks}

async def update_task_privacy(task_id: int, google_id: str, private: bool) -> Dict:
    """Обновить приватность задачи"""
    user = await db_manager.get_user_by_google_id(google_id)
    if not user:
        raise ValueError("User not found")
    
    updated_task = await db_manager.update_task_privacy(task_id, user["id"], private)
    return {"message": "Task privacy updated successfully", "task": updated_task}

async def chat_with_task_stream(task_id: int, google_id: str, prompt: str) -> AsyncGenerator[str, None]:
    """Чат с AI с потоковым ответом"""
    user = await db_manager.get_user_by_google_id(google_id)
    if not user:
        raise ValueError("User not found")

    task = await db_manager.get_task(task_id, user["id"])
    
    await llm_manager.invalidate_task_cache(task_id, user["id"])
    
    task_context = await llm_manager.generate_task_context(
        task["task_name"], 
        task["task_description"], 
        task["id"], 
        user["id"], 
        task["task_context"]
    )
    await db_manager.update_task_context(task_id, user["id"], task_context)
    
    full_response = ""
    
    try:
        stream = llm_manager.stream_answer(prompt, task_context)
        for chunk in stream:
            if chunk and chunk.strip():
                full_response += chunk
                yield chunk
                
    except Exception as e:
        error_msg = f"🚫 Ошибка AI: {str(e)}"
        full_response = error_msg
        yield error_msg
    
    await db_manager.create_exchange(task_id, user["id"], prompt, full_response)

if __name__ == "__main__":
    asyncio.run(init_backend())