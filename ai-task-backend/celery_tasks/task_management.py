from celery_config import celery_app
from databasemanager import DatabaseManager
from llmmanager import LLMManager
from config import DATABASE_URL
import asyncio

@celery_app.task(name="create_new_task", bind=True)
def create_new_task_celery(self, task_name: str, task_description: str, user_id: int, private: bool = True):
    """Создание новой задачи"""
    try:
        async def _create_task():
            db_manager = DatabaseManager(DATABASE_URL)
            llm_manager = LLMManager()
            
            # Проверяем пользователя
            user = await db_manager.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            
            # Создаем задачу
            created_task = await db_manager.create_task(task_name, task_description, user_id, private)
            return {"message": "Success", "task": created_task}
        
        return asyncio.run(_create_task())
    except Exception as exc:
        print(f"❌ Error creating task: {exc}")
        raise self.retry(exc=exc, countdown=30)

@celery_app.task(name="delete_task_by_id", bind=True)
def delete_task_by_id_celery(self, task_id: int, user_id: int):
    """Удаление задачи"""
    try:
        async def _delete_task():
            db_manager = DatabaseManager(DATABASE_URL)
            
            # Проверяем права доступа
            task = await db_manager.get_task(task_id, user_id)
            if not task:
                raise ValueError("Task not found or access denied")
            
            deleted_task = await db_manager.delete_task(task_id, user_id)
            return {"message": "Task deleted successfully", "task_id": deleted_task["id"]}
        
        return asyncio.run(_delete_task())
    except Exception as exc:
        print(f"❌ Error deleting task: {exc}")
        raise self.retry(exc=exc, countdown=30)

@celery_app.task(name="get_task_by_id", bind=True)
def get_task_by_id_celery(self, task_id: int, user_id: int):
    """Получение задачи по ID"""
    try:
        async def _get_task():
            db_manager = DatabaseManager(DATABASE_URL)
            
            task = await db_manager.get_task(task_id, user_id)
            if not task:
                raise ValueError("Task not found or access denied")
            return task
        
        return asyncio.run(_get_task())
    except Exception as exc:
        print(f"❌ Error getting task: {exc}")
        return None

@celery_app.task(name="get_user_tasks", bind=True)
def get_user_tasks_celery(self, user_id: int):
    """Получение всех задач пользователя"""
    try:
        async def _get_tasks():
            db_manager = DatabaseManager(DATABASE_URL)
            tasks = await db_manager.get_users_tasks(user_id)
            return {"user_id": user_id, "tasks": tasks}
        
        return asyncio.run(_get_tasks())
    except Exception as exc:
        print(f"❌ Error getting user tasks: {exc}")
        return None

@celery_app.task(name="get_task_exchanges", bind=True)
def get_task_exchanges_celery(self, task_id: int, user_id: int):
    """Получение обменов для задачи"""
    try:
        async def _get_exchanges():
            db_manager = DatabaseManager(DATABASE_URL)
            
            # Проверяем права доступа
            task = await db_manager.get_task(task_id, user_id)
            if not task:
                raise ValueError("Task not found or access denied")
            
            exchanges = await db_manager.get_task_exchanges(task_id, user_id)
            return {"task": task, "exchanges": exchanges}
        
        return asyncio.run(_get_exchanges())
    except Exception as exc:
        print(f"❌ Error getting task exchanges: {exc}")
        return None

@celery_app.task(name="get_task_context", bind=True)
def get_task_context_celery(self, task_id: int, user_id: int):
    """Получение контекста задачи"""
    try:
        async def _get_context():
            db_manager = DatabaseManager(DATABASE_URL)
            llm_manager = LLMManager()
            
            task = await db_manager.get_task(task_id, user_id)
            if not task:
                raise ValueError("Task not found or access denied")
            
            # Генерируем или получаем контекст
            task_context = await llm_manager.generate_task_context(
                task["task_name"], 
                task["task_description"], 
                task["id"], 
                user_id, 
                task["task_context"]
            )
            
            # Обновляем контекст если изменился
            if task_context != task["task_context"]:
                await db_manager.update_task_context(task_id, user_id, task_context)
            
            return {"task": task, "context": task_context}
        
        return asyncio.run(_get_context())
    except Exception as exc:
        print(f"❌ Error getting task context: {exc}")
        return None

@celery_app.task(name="change_task_status", bind=True)
def change_task_status_celery(self, task_id: int, user_id: int, status: str):
    """Изменение статуса задачи"""
    try:
        async def _change_status():
            db_manager = DatabaseManager(DATABASE_URL)
            
            # Проверяем права доступа
            task = await db_manager.get_task(task_id, user_id)
            if not task:
                raise ValueError("Task not found or access denied")
            
            await db_manager.update_task_status(task_id, user_id, status)
            return {"message": "Task status changed successfully"}
        
        return asyncio.run(_change_status())
    except Exception as exc:
        print(f"❌ Error changing task status: {exc}")
        raise self.retry(exc=exc, countdown=30)

@celery_app.task(name="update_task_context_by_user", bind=True)
def update_task_context_by_user_celery(self, task_id: int, user_id: int, context: str):
    """Обновление контекста задачи пользователем"""
    try:
        async def _update_context():
            db_manager = DatabaseManager(DATABASE_URL)
            llm_manager = LLMManager()
            
            # Проверяем права доступа
            task = await db_manager.get_task(task_id, user_id)
            if not task:
                raise ValueError("Task not found or access denied")
            
            await db_manager.update_task_context(task_id, user_id, context)
            # Инвалидируем кэш
            await llm_manager.invalidate_task_cache(task_id, user_id)
            
            return {"message": "Task context updated successfully"}
        
        return asyncio.run(_update_context())
    except Exception as exc:
        print(f"❌ Error updating task context: {exc}")
        raise self.retry(exc=exc, countdown=30)

@celery_app.task(name="update_task_privacy", bind=True)
def update_task_privacy_celery(self, task_id: int, user_id: int, private: bool):
    """Обновление приватности задачи"""
    try:
        async def _update_privacy():
            db_manager = DatabaseManager(DATABASE_URL)
            
            # Проверяем права доступа
            task = await db_manager.get_task(task_id, user_id)
            if not task:
                raise ValueError("Task not found or access denied")
            
            updated_task = await db_manager.update_task_privacy(task_id, user_id, private)
            return {"message": "Task privacy updated successfully", "task": updated_task}
        
        return asyncio.run(_update_privacy())
    except Exception as exc:
        print(f"❌ Error updating task privacy: {exc}")
        raise self.retry(exc=exc, countdown=30)

@celery_app.task(name="get_public_tasks")
def get_public_tasks_celery():
    """Получение публичных задач"""
    try:
        async def _get_public():
            db_manager = DatabaseManager(DATABASE_URL)
            tasks = await db_manager.get_public_tasks()
            return {"tasks": tasks}
        
        return asyncio.run(_get_public())
    except Exception as exc:
        print(f"❌ Error getting public tasks: {exc}")
        return None

@celery_app.task(name="create_task_exchange", bind=True)
def create_task_exchange_celery(self, task_id: int, user_id: int, prompt: str):
    """Создание обмена сообщениями с AI"""
    try:
        async def _create_exchange():
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
            
            return {"message": "Exchange created successfully", "exchange": result}
        
        return asyncio.run(_create_exchange())
    except Exception as exc:
        print(f"❌ Error creating task exchange: {exc}")
        raise self.retry(exc=exc, countdown=60)