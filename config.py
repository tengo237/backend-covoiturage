import os
from dotenv import load_dotenv

load_dotenv()

# DATABASE CONFIG
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./test.db"
)

# JWT CONFIG
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# APP CONFIG
APP_NAME = "RIDE+ API"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "True") == "True"

# CORS CONFIG
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
]