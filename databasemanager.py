from sqlalchemy.ext.asyncio import  create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from datetime import datetime
from typing import Optional

class DatabaseManager:
    def __init__(self, database_url: str):
        self.engine = create_async_engine(database_url, echo=True)
        self.async_session = async_sessionmaker(
            self.engine,
            class_= AsyncSession,
            expire_on_commit= False
        )

    async def init_db(self):
        async with self.engine.begin() as conn:
            print("creating db...")

            await conn.execute(text("""CREATE TABLE IF NOT EXISTS users (
                                    id SERIAL PRIMARY KEY,
                                    google_id VARCHAR(255) UNIQUE NOT NULL,
                                    email TEXT NOT NULL,
                                    name VARCHAR(255),
                                    picture TEXT,
                                    access_token TEXT NOT NULL,
                                    refresh_token TEXT,
                                    token_expires_at TIMESTAMP NOT NULL,
                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL)"""))
            
            await conn.execute(text("""CREATE TABLE IF NOT EXISTS tasks (
                                    id SERIAL PRIMARY KEY,
                                    task_name TEXT NOT NULL,
                                    task_description TEXT NOT NULL,
                                    task_context TEXT,
                                    task_status TEXT NOT NULL,
                                    user_id INTEGER NOT NULL,
                                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)"""))
                                    
            await conn.execute(text("""CREATE TABLE IF NOT EXISTS exchanges (
            id SERIAL PRIMARY KEY,
            task_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)"""))
            print("db created")

    async def get_all_tasks(self):
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT t.id, t.task_name, t.task_description, t.task_status, t.user_id, t.created_at, t.updated_at, u.name as user_name, u.email as user_email 
                FROM tasks t 
                JOIN users u ON t.user_id = u.id
                ORDER BY t.created_at DESC
            """))
            return [{
                "id": row[0],
                "task_name": row[1],
                "task_description": row[2],
                "task_status": row[3],
                "user_id": row[4],
                "created_at": row[5],
                "updated_at": row[6],
                "user_name": row[7],
                "user_email": row[8]
            } for row in result.fetchall()]

    async def create_task(self, task_name: str, task_description: str, user_id: int):
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""
                INSERT INTO tasks (task_name, task_description, task_context, task_status, user_id) 
                VALUES (:task_name, :task_description, 'no context', 'not solved', :user_id) 
                RETURNING id, created_at
            """), {"task_name": task_name, "task_description": task_description, "user_id": user_id})
            row = result.fetchone()
            if row is None:
                raise Exception("Failed to create task")
            task_id = row[0]
            created_at = row[1]
            return {"id": task_id, "task_name": task_name, "task_description": task_description, "task_context": "no context", "task_status": "not solved", "user_id": user_id, "created_at": created_at}
        
    async def delete_task(self, task_id: int, user_id: int):
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""
                DELETE FROM tasks 
                WHERE id = :task_id AND user_id = :user_id
            """), {"task_id": task_id, "user_id": user_id})
            if result.rowcount == 0:
                raise Exception("Task not found or you don't have permission to delete it")
            return {"id": task_id}
        
    async def get_task(self, task_id: int, user_id: int):
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT t.id, t.task_name, t.task_description, t.task_context, t.task_status, t.user_id, t.created_at, u.name as user_name, u.email as user_email 
                FROM tasks t 
                JOIN users u ON t.user_id = u.id 
                WHERE t.id = :task_id AND t.user_id = :user_id
            """), {"task_id": task_id, "user_id": user_id})
            row = result.fetchone()
            if row is None:
                raise Exception("Task not found or you don't have permission to access it")
            return {"id": row[0], "task_name": row[1], "task_description": row[2], "task_context": row[3], "task_status": row[4], "user_id": row[5], "created_at": row[6], "user_name": row[7], "user_email": row[8]}

    async def update_task_context(self, task_id: int, user_id: int, task_context: str):
        async with self.engine.begin() as conn:
            await conn.execute(text("""UPDATE tasks SET task_context = :task_context WHERE id = :task_id AND user_id = :user_id"""), {"task_context": task_context, "task_id": task_id, "user_id": user_id})
            return {"id": task_id, "task_context": task_context}

    async def create_user(self, google_id: str, email: str, name: Optional[str] = None, picture: Optional[str] = None, access_token: Optional[str] = None, refresh_token: Optional[str] = None, token_expires_at: Optional[datetime] = None):
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""INSERT INTO users (google_id, email, name, picture, access_token, refresh_token, token_expires_at) VALUES (:google_id, :email, :name, :picture, :access_token, :refresh_token, :token_expires_at) RETURNING id"""), {"google_id": google_id, "email": email, "name": name, "picture": picture, "access_token": access_token, "refresh_token": refresh_token, "token_expires_at": token_expires_at})
            row = result.fetchone()
            if row is None:
                raise Exception("Failed to create user")
            return {"id": row[0], "google_id": google_id, "email": email, "name": name, "picture": picture, "access_token": access_token, "refresh_token": refresh_token, "token_expires_at": token_expires_at}


    async def get_users_tasks(self, user_id: int):
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT id, task_name, task_description, task_status, user_id, created_at, updated_at
                FROM tasks 
                WHERE user_id = :user_id
                ORDER BY created_at DESC
            """), {"user_id": user_id})
            return [{
                "id": row[0],
                "task_name": row[1],
                "task_description": row[2],
                "task_status": row[3],
                "user_id": row[4],
                "created_at": row[5],
                "updated_at": row[6]
            } for row in result.fetchall()]

    async def get_user_by_email(self, email:str):
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""SELECT * FROM users WHERE email = :email"""), {"email": email})
            row = result.fetchone()
            if row is None:
                return None
            return {
                "id": row[0],
                "google_id": row[1],
                "email": row[2],
                "name": row[3],
                "picture": row[4],
                "access_token": row[5],
                "refresh_token": row[6],
                "token_expires_at": row[7],
                "created_at": row[8]
            }
    
    async def update_user_tokens(self, google_id: str, access_token: str, refresh_token: Optional[str] = None, token_expires_at: Optional[datetime] = None):
        async with self.engine.begin() as conn:
            if refresh_token:
                await conn.execute(text("""UPDATE users SET access_token = :access_token, refresh_token = :refresh_token, token_expires_at = :token_expires_at WHERE google_id = :google_id"""), {"google_id": google_id, "access_token": access_token, "refresh_token": refresh_token, "token_expires_at": token_expires_at})
            else:
                await conn.execute(text("""UPDATE users SET access_token = :access_token, token_expires_at = :token_expires_at WHERE google_id = :google_id"""), {"google_id": google_id, "access_token": access_token, "token_expires_at": token_expires_at})
            return {"google_id": google_id, "access_token": access_token, "refresh_token": refresh_token, "token_expires_at": token_expires_at}

    async def get_user_by_google_id(self, google_id:str):
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""SELECT * FROM users WHERE google_id = :google_id"""), {"google_id": google_id})
            row = result.fetchone()
            if row is None:
                return None
            return {
                "id": row[0],
                "google_id": row[1],
                "email": row[2],
                "name": row[3],
                "picture": row[4],
                "access_token": row[5],
                "refresh_token": row[6],
                "token_expires_at": row[7],
                "created_at": row[8]
            }

    async def create_exchange(self, task_id: int, user_id: int, prompt: str, response: str):
        async with self.engine.begin() as conn:
            check = await conn.execute(text("""
                SELECT 1 FROM tasks WHERE id = :task_id AND user_id = :user_id
            """), {"task_id": task_id, "user_id": user_id})
            if check.fetchone() is None:
                raise Exception("Task not found or you don't have permission to add exchanges to it")
            
            result = await conn.execute(text("""
                INSERT INTO exchanges (task_id, user_id, prompt, response) 
                VALUES (:task_id, :user_id, :prompt, :response)
                RETURNING id, created_at
            """), {"task_id": task_id, "user_id": user_id, "prompt": prompt, "response": response})
            row = result.fetchone()
            if row is None:
                raise Exception("Failed to create exchange")
            return {"id": row[0], "task_id": task_id, "user_id": user_id, "prompt": prompt, "response": response, "created_at": row[1]}

    async def get_task_exchanges(self, task_id: int, user_id: int):
        async with self.engine.begin() as conn:
            check = await conn.execute(text("""
                SELECT 1 FROM tasks WHERE id = :task_id AND user_id = :user_id
            """), {"task_id": task_id, "user_id": user_id})
            if check.fetchone() is None:
                raise Exception("Task not found or you don't have permission to view its exchanges")
            
            result = await conn.execute(text("""
                SELECT id, prompt, response, created_at 
                FROM exchanges 
                WHERE task_id = :task_id AND user_id = :user_id
                ORDER BY created_at ASC
            """), {"task_id": task_id, "user_id": user_id})
            return [{"id": row[0], "prompt": row[1], "response": row[2], "created_at": row[3]} for row in result.fetchall()]