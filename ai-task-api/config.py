import dotenv
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.google_client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        self.google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
        self.google_redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "")
        self.backend_service_url = os.getenv("BACKEND_SERVICE_URL", "http://localhost:8001")

GOOGLE_CLIENT_ID = Settings().google_client_id
GOOGLE_CLIENT_SECRET = Settings().google_client_secret
GOOGLE_REDIRECT_URI = Settings().google_redirect_uri
BACKEND_SERVICE_URL = Settings().backend_service_url
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_INFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
