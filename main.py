from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from huggingface_hub import InferenceClient
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional
import httpx
from datetime import datetime, timedelta

from databasemanager import DatabaseManager
from llmmanager import LLMManager

from config import DATABASE_URL, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, GOOGLE_AUTH_URL, GOOGLE_TOKEN_URL, GOOGLE_USER_INFO_URL

db_manager = DatabaseManager(DATABASE_URL)
llm_manager = LLMManager()


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
    task_name: str
    task_description: str

class Task(CreateTask):
    id: int

@asynccontextmanager
async def  lifespan(app: FastAPI):
    print("FastAPI server started")
    await db_manager.init_db()
    yield
    print("FastAPI server ended")

app = FastAPI(title= "AI Task Manager", lifespan= lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/login/google")
async def login_google():
    google_auth_url = f"{GOOGLE_AUTH_URL}?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20email%20profile&access_type=offline"
    return {"auth_url": google_auth_url, "message": "Google OAuth URL generated successfully"}

@app.get("/login/google/redirect")
async def login_google_redirect():
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

    existing_user = await db_manager.get_user_by_google_id(user_info["sub"])

    expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])

    if existing_user:
        await db_manager.update_user_tokens(user_info["sub"], token_data["access_token"], token_data.get("refresh_token"), expires_at)
    else:
        await db_manager.create_user(user_info["sub"], user_info["email"], user_info["name"], user_info["picture"], token_data["access_token"], token_data.get("refresh_token"), expires_at)

    return {"message": "User authenticated successfully"}



@app.get("/tasks/my")
async def get_my_tasks(google_id: str):
    user = await db_manager.get_user_by_google_id(google_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    tasks = await db_manager.get_users_tasks(user["id"])
    return {"user_id": user["id"], "tasks": tasks}

@app.get("/tasks/{task_id}")
async def get_task(task_id: int, google_id: str):
    user = await db_manager.get_user_by_google_id(google_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    task = await db_manager.get_task(task_id, user["id"])
    return task

@app.post("/tasks/create")
async def create_task(task: CreateTask, google_id: str):
    user = await db_manager.get_user_by_google_id(google_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    created_task = await db_manager.create_task(task.task_name, task.task_description, user["id"])

    return {"message": "Success", "task": created_task}

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int, google_id: str):
    user = await db_manager.get_user_by_google_id(google_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    deleted_task = await db_manager.delete_task(task_id, user["id"])
    return {"message": "Task deleted successfully", "task_id": deleted_task["id"]}

@app.post("/tasks/{task_id}/create_exchange")
async def create_exchange(task_id: int, google_id: str, prompt: str):
    user = await db_manager.get_user_by_google_id(google_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    task = await db_manager.get_task(task_id, user["id"])
    task_context = await llm_manager.generate_task_context(task["task_name"], task["task_description"], task["id"], user["id"])
    await db_manager.update_task_context(task_id, user["id"], task_context)
    
    result = llm_manager.get_answer(prompt, task_context)
    await db_manager.create_exchange(task_id, user["id"], prompt, result)
    return {"message": "Exchange created successfully", "exchange": result}

@app.get("/tasks/{task_id}/exchanges")
async def get_exchanges(task_id: int, google_id: str):
    user = await db_manager.get_user_by_google_id(google_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    exchanges = await db_manager.get_task_exchanges(task_id, user["id"])
    task = await db_manager.get_task(task_id, user["id"])
    return {"task": task, "exchanges": exchanges}

@app.get("/tasks/{task_id}/context")
async def get_task_context(task_id: int, google_id: str):
    user = await db_manager.get_user_by_google_id(google_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    task = await db_manager.get_task(task_id, user["id"])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task_context = await llm_manager.generate_task_context(task["task_name"], task["task_description"], task["id"], user["id"])
    return {"task": task, "context": task_context}