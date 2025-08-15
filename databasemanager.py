from sqlalchemy.ext.asyncio import  create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

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
            await conn.execute(text("""CREATE TABLE IF NOT EXISTS tasks (
                                    id SERIAL PRIMARY KEY,
                                    title TEXT NOT NULL,
                                    content TEXT NOT NULL)"""))
            print("db created")

    async def get_all_tasks(self):
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""SELECT * FROM tasks"""))
            return [{"id": row[0], "title": row[1], "content": row[2]} for row in result.fetchall()]

    async def create_task(self, title: str, content: str):
        async with self.engine.begin() as conn:
            result = await conn.execute(text("""INSERT INTO tasks (title, content) VALUES (:title, :content) RETURNING id"""), {"title": title, "content": content})
            row = result.fetchone()
            if row is None:
                raise Exception("Failed to create task")
            task_id = row[0]
            return {"id": task_id, "title": title, "content": content}
            