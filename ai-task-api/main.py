from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2AuthorizationCodeBearer
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional
import httpx
import json
import asyncio
from datetime import datetime, timedelta

from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, GOOGLE_AUTH_URL, GOOGLE_TOKEN_URL, GOOGLE_USER_INFO_URL, BACKEND_SERVICE_URL

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
    private: bool = True

class Task(CreateTask):
    id: int

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("API microservice started")
    yield
    print("API microservice ended")

app = FastAPI(title="AI Task Manager API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.options("/{path:path}")
async def options_handler(path: str):
    print(f"🔧 OPTIONS request for path: {path}")
    return {"message": "OK"}

@app.middleware("http")
async def cors_debug_middleware(request, call_next):
    print(f"📡 {request.method} {request.url} - Origin: {request.headers.get('origin', 'No Origin')}")

    if request.method == "OPTIONS":
        from fastapi.responses import Response
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "600"
        print(f"📤 Preflight response sent")
        return response
    
    response = await call_next(request)
    
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    
    print(f"📤 Response status: {response.status_code}")
    return response

@app.get("/health")
async def health_check():
    return {"status": "OK", "message": "API microservice is running"}

@app.websocket("/ws/test")
async def websocket_test(websocket: WebSocket):
    print("🔌 Test WebSocket connection attempt")
    try:
        await websocket.accept()
        print("✅ Test WebSocket accepted")
        await websocket.send_json({"type": "test", "message": "WebSocket works!"})
        
        while True:
            try:
                data = await websocket.receive_json()
                print(f"📨 Test WebSocket received: {data}")
                await websocket.send_json({"type": "echo", "message": f"Echo: {data}"})
            except WebSocketDisconnect:
                print("🔌 Test WebSocket disconnected")
                break
    except Exception as e:
        print(f"❌ Test WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass

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

    expires_at = datetime.now() + timedelta(seconds=token_data["expires_in"])
    
    async with httpx.AsyncClient() as client:
        user_response = await client.post(
            f"{BACKEND_SERVICE_URL}/users/auth",
            json={
                "google_id": user_info["sub"],
                "email": user_info["email"],
                "name": user_info["name"],
                "picture": user_info["picture"],
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "expires_at": expires_at.isoformat()
            }
        )
    
    if user_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Backend service error")
    
    user = user_response.json()

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Авторизация успешна</title>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: #f7f7f8;
            }}
            .container {{
                text-align: center;
                padding: 40px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                max-width: 500px;
            }}
            .success-icon {{
                font-size: 48px;
                margin-bottom: 16px;
            }}
            h1 {{
                color: #059669;
                margin-bottom: 8px;
            }}
            p {{
                color: #6b7280;
                margin-bottom: 16px;
            }}
            .user-info {{
                background: #f3f4f6;
                padding: 16px;
                border-radius: 8px;
                margin: 16px 0;
                text-align: left;
            }}
            .user-name {{
                font-weight: 600;
                color: #374151;
                margin-bottom: 4px;
            }}
            .user-email {{
                color: #6b7280;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success-icon">✅</div>
            <h1>Авторизация успешна!</h1>
            <p>Добро пожаловать в AI Task Manager</p>
            
            <div class="user-info">
                <div class="user-name">{user.get("name", "Пользователь")}</div>
                <div class="user-email">{user.get("email", "")}</div>
            </div>
            
            <p>Окно закроется автоматически...</p>
        </div>
        
        <script>
            if (window.opener) {{
                window.opener.postMessage({{
                    type: 'google_auth_success',
                    user: {{
                        id: {user["id"]},
                        google_id: "{user["google_id"]}",
                        name: "{user.get("name", "")}",
                        email: "{user.get("email", "")}",
                        picture: "{user.get("picture", "")}"
                    }}
                }}, '*');
                
                setTimeout(() => {{
                    window.close();
                }}, 2000);
            }} else {{
                localStorage.setItem('auth_user', JSON.stringify({{
                    id: {user["id"]},
                    google_id: "{user["google_id"]}",
                    name: "{user.get("name", "")}",
                    email: "{user.get("email", "")}"
                }}));
                
                setTimeout(() => {{
                    window.location.href = '/';
                }}, 2000);
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/tasks/my")
async def get_my_tasks(google_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BACKEND_SERVICE_URL}/tasks/user/{google_id}")
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="User not found")
        elif response.status_code != 200:
            raise HTTPException(status_code=500, detail="Backend service error")
        return response.json()

@app.get("/tasks/{task_id}")
async def get_task(task_id: int, google_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BACKEND_SERVICE_URL}/tasks/{task_id}?google_id={google_id}")
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Task or user not found")
        elif response.status_code != 200:
            raise HTTPException(status_code=500, detail="Backend service error")
        return response.json()

@app.post("/tasks/create")
async def create_task(task: CreateTask, google_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BACKEND_SERVICE_URL}/tasks/create",
            json={
                "task_name": task.task_name,
                "task_description": task.task_description,
                "private": task.private,
                "google_id": google_id
            }
        )
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="User not found")
        elif response.status_code != 200:
            raise HTTPException(status_code=500, detail="Backend service error")
        return response.json()

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: int, google_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{BACKEND_SERVICE_URL}/tasks/{task_id}?google_id={google_id}")
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Task or user not found")
        elif response.status_code != 200:
            raise HTTPException(status_code=500, detail="Backend service error")
        return response.json()

@app.post("/tasks/{task_id}/create_exchange")
async def create_exchange(task_id: int, google_id: str, prompt: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BACKEND_SERVICE_URL}/tasks/{task_id}/exchange",
            json={
                "google_id": google_id,
                "prompt": prompt
            }
        )
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Task or user not found")
        elif response.status_code != 200:
            raise HTTPException(status_code=500, detail="Backend service error")
        return response.json()

@app.get("/tasks/{task_id}/exchanges")
async def get_exchanges(task_id: int, google_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BACKEND_SERVICE_URL}/tasks/{task_id}/exchanges?google_id={google_id}")
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Task or user not found")
        elif response.status_code != 200:
            raise HTTPException(status_code=500, detail="Backend service error")
        return response.json()

@app.get("/tasks/{task_id}/context")
async def get_task_context(task_id: int, google_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BACKEND_SERVICE_URL}/tasks/{task_id}/context?google_id={google_id}")
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Task or user not found")
        elif response.status_code != 200:
            raise HTTPException(status_code=500, detail="Backend service error")
        return response.json()

@app.post("/tasks/{task_id}/change_status")
async def change_task_status(task_id: int, user_id: int, status: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BACKEND_SERVICE_URL}/tasks/{task_id}/status",
            json={
                "user_id": user_id,
                "status": status
            }
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Backend service error")
        return response.json()

@app.post("/tasks/{task_id}/context/update")
async def update_task_context(task_id: int, user_id: int, context: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BACKEND_SERVICE_URL}/tasks/{task_id}/context",
            json={
                "user_id": user_id,
                "context": context
            }
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Backend service error")
        return response.json()

@app.get("/tasks/public")
async def get_public_tasks():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BACKEND_SERVICE_URL}/tasks/public")
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Backend service error")
        return response.json()

@app.post("/tasks/{task_id}/privacy")
async def update_task_privacy(task_id: int, google_id: str, private: bool):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BACKEND_SERVICE_URL}/tasks/{task_id}/privacy",
            json={
                "google_id": google_id,
                "private": private
            }
        )
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Task or user not found")
        elif response.status_code != 200:
            raise HTTPException(status_code=500, detail="Backend service error")
        return response.json()

@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: int, google_id: str):
    print(f"🔌 WebSocket connection attempt for task {task_id}, google_id: {google_id}")
    
    try:
        await websocket.accept()
        print(f"✅ WebSocket accepted for task {task_id}")
        
        async with httpx.AsyncClient() as client:
            user_response = await client.get(f"{BACKEND_SERVICE_URL}/users/{google_id}")
            if user_response.status_code != 200:
                await websocket.send_json({"type": "error", "message": "User not found"})
                return
            
            task_response = await client.get(f"{BACKEND_SERVICE_URL}/tasks/{task_id}?google_id={google_id}")
            if task_response.status_code != 200:
                await websocket.send_json({"type": "error", "message": "Task not found"})
                return
        
        await websocket.send_json({"type": "connected", "task_id": task_id})
        print(f"📡 WebSocket connected successfully for task {task_id}")
        
        while True:
            try:
                data = await websocket.receive_json()
                print(f"📨 Received WebSocket message: {data}")
                
                if data["type"] == "chat_message":
                    prompt = data["message"]
                    
                    await websocket.send_json({
                        "type": "response_start",
                        "message": prompt
                    })
                    
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        async with client.stream(
                            'POST',
                            f"{BACKEND_SERVICE_URL}/tasks/{task_id}/chat",
                            json={
                                "google_id": google_id,
                                "prompt": prompt
                            }
                        ) as response:
                            if response.status_code != 200:
                                await websocket.send_json({
                                    "type": "error",
                                    "message": "Backend service error"
                                })
                                return
                            
                            full_response = ""
                            async for chunk in response.aiter_text():
                                if chunk and chunk.strip():
                                    full_response += chunk
                                    await websocket.send_json({
                                        "type": "response_chunk",
                                        "chunk": chunk,
                                        "full_response": full_response
                                    })
                                    await asyncio.sleep(0.03)
                            
                            await websocket.send_json({
                                "type": "response_complete",
                                "full_response": full_response
                            })
                    
            except WebSocketDisconnect:
                print(f"🔌 WebSocket disconnected for task {task_id}")
                break
                
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
