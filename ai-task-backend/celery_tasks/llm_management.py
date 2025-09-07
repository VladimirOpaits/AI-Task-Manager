from celery_config import celery_app
from databasemanager import DatabaseManager
from llmmanager import LLMManager
from config import DATABASE_URL
import asyncio

@celery_app.task(name="process_chat", bind=True, max_retries=2)
def process_chat_celery(self, task_id: int, user_id: int, prompt: str):
    """Обработка чат сообщения через AI"""
    try:
        async def _process_chat():
            db_manager = DatabaseManager(DATABASE_URL)
            llm_manager = LLMManager()
            
            # Проверяем права доступа
            task = await db_manager.get_task(task_id, user_id)
            if not task:
                raise ValueError("Task not found or access denied")
            
            # Инвалидируем кэш
            await llm_manager.invalidate_task_cache(task_id, user_id)
            
            # Генерируем контекст
            task_context = await llm_manager.generate_task_context(
                task["task_name"], 
                task["task_description"], 
                task["id"], 
                user_id, 
                task["task_context"]
            )
            
            # Обновляем контекст в БД
            await db_manager.update_task_context(task_id, user_id, task_context)
            
            # Получаем ответ от AI
            result = llm_manager.get_answer(prompt, task_context)
            
            # Создаем обмен
            await db_manager.create_exchange(task_id, user_id, prompt, result)
            
            return {"response": result, "task_id": task_id}
        
        return asyncio.run(_process_chat())
    except Exception as exc:
        print(f"❌ Error processing chat: {exc}")
        raise self.retry(exc=exc, countdown=120)

@celery_app.task(name="generate_task_context", bind=True, max_retries=2)
def generate_task_context_celery(self, task_id: int, user_id: int):
    """Генерация контекста задачи"""
    try:
        async def _generate_context():
            db_manager = DatabaseManager(DATABASE_URL)
            llm_manager = LLMManager()
            
            # Проверяем права доступа
            task = await db_manager.get_task(task_id, user_id)
            if not task:
                raise ValueError("Task not found or access denied")
            
            # Генерируем контекст
            task_context = await llm_manager.generate_task_context(
                task["task_name"], 
                task["task_description"], 
                task["id"], 
                user_id, 
                task["task_context"]
            )
            
            # Обновляем контекст в БД
            await db_manager.update_task_context(task_id, user_id, task_context)
            
            return {"context": task_context, "task_id": task_id}
        
        return asyncio.run(_generate_context())
    except Exception as exc:
        print(f"❌ Error generating task context: {exc}")
        raise self.retry(exc=exc, countdown=60)

@celery_app.task(name="get_ai_answer")
def get_ai_answer_celery(prompt: str, context: str):
    """Получение ответа от AI"""
    try:
        async def _get_answer():
            llm_manager = LLMManager()
            result = llm_manager.get_answer(prompt, context)
            return {"response": result}
        
        return asyncio.run(_get_answer())
    except Exception as exc:
        print(f"❌ Error getting AI answer: {exc}")
        return None

@celery_app.task(name="stream_chat_response", bind=True, max_retries=2)
def stream_chat_response_celery(self, task_id: int, user_id: int, prompt: str):
    """Стриминг ответа от AI"""
    try:
        async def _stream_response():
            db_manager = DatabaseManager(DATABASE_URL)
            llm_manager = LLMManager()
            
            # Проверяем права доступа
            task = await db_manager.get_task(task_id, user_id)
            if not task:
                raise ValueError("Task not found or access denied")
            
            # Инвалидируем кэш
            await llm_manager.invalidate_task_cache(task_id, user_id)
            
            # Генерируем контекст
            task_context = await llm_manager.generate_task_context(
                task["task_name"], 
                task["task_description"], 
                task["id"], 
                user_id, 
                task["task_context"]
            )
            
            # Обновляем контекст в БД
            await db_manager.update_task_context(task_id, user_id, task_context)
            
            # Собираем все чанки ответа
            response_chunks = []
            stream = llm_manager.stream_answer(prompt, task_context)
            
            for chunk in stream:
                if chunk and chunk.strip():
                    response_chunks.append(chunk)
            
            full_response = "".join(response_chunks)
            
            # Создаем обмен
            await db_manager.create_exchange(task_id, user_id, prompt, full_response)
            
            return {"response": full_response, "task_id": task_id}
        
        return asyncio.run(_stream_response())
    except Exception as exc:
        print(f"❌ Error streaming chat response: {exc}")
        raise self.retry(exc=exc, countdown=120)

@celery_app.task(name="generate_task_response")
def generate_task_response_celery(task_id: int, user_id: int, prompt: str):
    """Генерация ответа для задачи (alias для process_chat)"""
    try:
        async def _generate_response():
            db_manager = DatabaseManager(DATABASE_URL)
            llm_manager = LLMManager()
            
            # Проверяем права доступа
            task = await db_manager.get_task(task_id, user_id)
            if not task:
                raise ValueError("Task not found or access denied")
            
            # Инвалидируем кэш
            await llm_manager.invalidate_task_cache(task_id, user_id)
            
            # Генерируем контекст
            task_context = await llm_manager.generate_task_context(
                task["task_name"], 
                task["task_description"], 
                task["id"], 
                user_id, 
                task["task_context"]
            )
            
            # Обновляем контекст в БД
            await db_manager.update_task_context(task_id, user_id, task_context)
            
            # Получаем ответ от AI
            result = llm_manager.get_answer(prompt, task_context)
            
            # Создаем обмен
            await db_manager.create_exchange(task_id, user_id, prompt, result)
            
            return {"response": result, "task_id": task_id}
        
        return asyncio.run(_generate_response())
    except Exception as exc:
        print(f"❌ Error generating task response: {exc}")
        return None
