from celery_config import celery_app
from databasemanager import DatabaseManager
from config import DATABASE_URL
from datetime import datetime
import asyncio

@celery_app.task(name="authenticate_telegram_user", bind=True, max_retries=3)
def authenticate_telegram_user_celery(self, telegram_id: int, telegram_username: str, email: str, name: str, picture: str, access_token: str, refresh_token: str, expires_at: str):
    """Аутентификация Telegram пользователя"""
    try:
        async def _auth_telegram():
            db_manager = DatabaseManager(DATABASE_URL)
            
            existing_user = await db_manager.get_user_by_telegram_id(telegram_id)
            if existing_user:
                return existing_user
            else:
                return await db_manager.create_telegram_user(
                    telegram_id, 
                    telegram_username, 
                    email if email else None, 
                    name if name else None, 
                    picture if picture else None,
                    access_token if access_token else None, 
                    refresh_token if refresh_token else None, 
                    expires_at if expires_at else None
                )
        
        return asyncio.run(_auth_telegram())
    except Exception as exc:
        print(f"❌ Error authenticating telegram user: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@celery_app.task(name="authenticate_google_user", bind=True, max_retries=3)
def authenticate_google_user_celery(self, google_id: str, email: str, name: str, picture: str, access_token: str, refresh_token: str, expires_at: str):
    """Аутентификация Google пользователя"""
    try:
        async def _auth_google():
            db_manager = DatabaseManager(DATABASE_URL)
            
            if expires_at:
                expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            else:
                expires_datetime = None
            
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
                return await db_manager.create_google_user(
                    google_id,
                    email,
                    name if name else None,
                    picture if picture else None,
                    access_token,
                    refresh_token,
                    expires_datetime
                )
        
        return asyncio.run(_auth_google())
    except Exception as exc:
        print(f"❌ Error authenticating google user: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

@celery_app.task(name="get_user_by_google_id")
def get_user_by_google_id_celery(google_id: str):
    """Получение пользователя по Google ID"""
    try:
        async def _get_user():
            db_manager = DatabaseManager(DATABASE_URL)
            return await db_manager.get_user_by_google_id(google_id)
        
        return asyncio.run(_get_user())
    except Exception as exc:
        print(f"❌ Error getting user by google_id: {exc}")
        return None

@celery_app.task(name="get_user_by_telegram_id")
def get_user_by_telegram_id_celery(telegram_id: int):
    """Получение пользователя по Telegram ID"""
    try:
        async def _get_user():
            db_manager = DatabaseManager(DATABASE_URL)
            return await db_manager.get_user_by_telegram_id(telegram_id)
        
        return asyncio.run(_get_user())
    except Exception as exc:
        print(f"❌ Error getting user by telegram_id: {exc}")
        return None

@celery_app.task(name="update_user_tokens", bind=True, max_retries=2)
def update_user_tokens_celery(self, google_id: str, access_token: str, 
                             refresh_token: str = "", expires_at: str = ""):
    """Обновление токенов пользователя"""
    try:
        async def _update_tokens():
            db_manager = DatabaseManager(DATABASE_URL)
            
            expires_datetime = None
            if expires_at:
                expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            
            return await db_manager.update_user_tokens(
                google_id, 
                access_token, 
                refresh_token if refresh_token else None, 
                expires_datetime
            )
        
        return asyncio.run(_update_tokens())
    except Exception as exc:
        print(f"❌ Error updating user tokens: {exc}")
        raise self.retry(exc=exc, countdown=30) 

@celery_app.task(name="init_database")
def init_database_celery():
    """Инициализация базы данных"""
    try:
        async def _init_db():
            db_manager = DatabaseManager(DATABASE_URL)
            await db_manager.init_db()
            return {"status": "success", "message": "Database initialized"}
        
        return asyncio.run(_init_db())
    except Exception as exc:
        print(f"❌ Error initializing database: {exc}")
        return {"status": "error", "message": str(exc)} 