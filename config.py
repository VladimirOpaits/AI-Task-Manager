import dotenv
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        if os.getenv("GOOGLE_CLIENT_ID"):
            self.google_client_id = str(os.getenv("GOOGLE_CLIENT_ID"))
        if os.getenv("GOOGLE_CLIENT_SECRET"):
            self.google_client_secret = str(os.getenv("GOOGLE_CLIENT_SECRET"))
        if os.getenv("GOOGLE_REDIRECT_URI"):
            self.google_redirect_uri = str(os.getenv("GOOGLE_REDIRECT_URI"))
        if os.getenv("DATABASE_URL"):
            self.database_url = str(os.getenv("DATABASE_URL"))
        if os.getenv("LLM_TOKEN"):
            self.llm_token = str(os.getenv("LLM_TOKEN"))

GOOGLE_CLIENT_ID = Settings().google_client_id
GOOGLE_CLIENT_SECRET = Settings().google_client_secret
GOOGLE_REDIRECT_URI = Settings().google_redirect_uri
DATABASE_URL = Settings().database_url
LLM_TOKEN = Settings().llm_token
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_INFO_URL = "https://openidconnect.googleapis.com/v1/userinfo" 