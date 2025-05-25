import os
from pydantic_settings import BaseSettings
from typing import List
from dotenv import load_dotenv
from enum import Enum

load_dotenv()

class Environment(Enum):
    LOCAL = "LOCAL"
    STAGE = "STAGE"
    PROD = "PROD"
    CI = "CI"

class Settings(BaseSettings):
    # Environment
    ENVIRONMENT: Environment
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/statuspage"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Auth0 Authentication
    AUTH0_CLIENT_SECRET: str
    AUTH0_DOMAIN: str
    AUTH0_CLIENT_ID: str
    AUTH0_AUDIENCE: str
    AUTH0_CLIENT_AUDIENCE: str
    AUTH0_ALGORITHMS: str

    # Development flags
    DEBUG: bool = False
    CREATE_TABLES: bool = False

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), ".env")

settings =  Settings()
