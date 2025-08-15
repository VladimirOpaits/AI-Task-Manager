from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from typing import List
from pydantic import BaseModel
from databasemanager import DatabaseManager

DATABASE_URL = "postgresql+asyncpg://neondb_owner:npg_se8BY0vocPgn@ep-summer-river-aby0v3y7-pooler.eu-west-2.aws.neon.tech/neondb?ssl=require"
db_manager = DatabaseManager(DATABASE_URL)

class CreateTask(BaseModel):
    title: str
    content: str

class Task(CreateTask):
    id: int

@asynccontextmanager
async def  lifespan(app: FastAPI):
    print("FastAPI server started")
    await db_manager.init_db()
    yield
    print("FastAPI server ended")

app = FastAPI(title= "AI Task Manager", lifespan= lifespan)

@app.get("/tasks/all")
async def get_tasks():
    """"Get all the tasks"""
    tasks = await db_manager.get_all_tasks()
    return tasks

@app.post("/tasks/create")
async def create_task(task: CreateTask):
    created_task = await db_manager.create_task(task.title, task.content)
    return {"message": "Success", "task": created_task}
