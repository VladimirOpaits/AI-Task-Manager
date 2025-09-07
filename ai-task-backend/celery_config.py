from celery import Celery
from config import REDIS_URL

celery_app = Celery("ai-task-backend", 
    broker=f"{REDIS_URL}/0", 
    backend=f"{REDIS_URL}/1",
    include=[
        "celery_tasks.task_management", 
        "celery_tasks.user_management",
        "celery_tasks.llm_management"
    ]
)

celery_app.conf.task_routes = {
    # User Authentication & Management
    "authenticate_telegram_user": {"queue": "user_auth"},
    "authenticate_google_user": {"queue": "user_auth"},
    "get_user_by_google_id": {"queue": "user_auth"},
    "get_user_by_telegram_id": {"queue": "user_auth"},
    "create_telegram_user": {"queue": "user_auth"},
    "update_user_tokens": {"queue": "user_auth"},
    "init_database": {"queue": "user_auth"},

    # Task Management Operations
    "get_user_tasks": {"queue": "task_management"},
    "get_task_by_id": {"queue": "task_management"},
    "create_new_task": {"queue": "task_management"},
    "delete_task_by_id": {"queue": "task_management"},
    "create_task_exchange": {"queue": "task_management"},
    "get_task_exchanges": {"queue": "task_management"},
    "get_task_context": {"queue": "task_management"},
    "change_task_status": {"queue": "task_management"},
    "update_task_context_by_user": {"queue": "task_management"},
    "update_task_privacy": {"queue": "task_management"},
    "get_public_tasks": {"queue": "task_management"},

    # LLM & AI Operations
    "generate_task_response": {"queue": "llm_tasks"},
    "process_chat": {"queue": "llm_tasks"},
    "generate_task_context": {"queue": "llm_tasks"},
    "get_ai_answer": {"queue": "llm_tasks"},
    "stream_chat_response": {"queue": "llm_tasks"},
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1500,
    task_soft_time_limit=1200,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=2,
    worker_max_tasks_per_child=1000,
    worker_max_memory_per_child=1024 * 1024 * 1024,
)

celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5

celery_app.conf.task_annotations = {
    '*': {
        'retry_backoff': True,
        'retry_jitter': True,
        'max_retries': 3,
    }
}