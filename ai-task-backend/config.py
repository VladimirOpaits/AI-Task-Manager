import dotenv
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "")
        self.llm_token = os.getenv("LLM_TOKEN", "")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

DATABASE_URL = Settings().database_url
LLM_TOKEN = Settings().llm_token
REDIS_URL = Settings().redis_url

