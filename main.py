from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.responses import RedirectResponse

from jose import jwt, JWTError
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional
import httpx


from databasemanager import DatabaseManager

from config import DATABASE_URL, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, GOOGLE_AUTH_URL, GOOGLE_TOKEN_URL, GOOGLE_USER_INFO_URL

db_manager = DatabaseManager(DATABASE_URL)


oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=GOOGLE_AUTH_URL,
    tokenUrl=GOOGLE_TOKEN_URL)

class User(BaseModel):
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    id_token: str 

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


@app.get("/login/google")
async def login_google():
    return RedirectResponse(
        f"{GOOGLE_AUTH_URL}?response_type=code&client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20email%20profile"
        f"&access_type=offline"
    )

@app.get("/auth/google/callback")
async def auth_google_callback(code: str):
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    
    token_data = token_response.json()
    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid token response")
    
    async with httpx.AsyncClient() as client:
        userinfo_response = await client.get(
            GOOGLE_USER_INFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
    
    user_info = userinfo_response.json()
    return {
        "token": token_data,
        "user": user_info
    }


@app.get("/tasks/all")
async def get_tasks():
    """"Get all the tasks"""
    tasks = await db_manager.get_all_tasks()
    return tasks

@app.get("/tasks/{task_id}")
async def get_task(task_id: int):
    task = await db_manager.get_task(task_id)
    return task

@app.post("/tasks/create")
async def create_task(task: CreateTask):
    created_task = await db_manager.create_task(task.title, task.content)
    return {"message": "Success", "task": created_task}
