import os
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Settings(BaseSettings):
    # API Settings
    API_V1_PREFIX: str = Field(default="/api/v1")
    DEBUG: bool = Field(default=False)
    PROJECT_NAME: str = Field(default="HyperBlock Admin API")
    
    # MongoDB Settings
    MONGODB_URI: str = Field(default="mongodb://localhost:27017")
    MONGODB_DB_NAME: str = Field(default="hyperblock")
    
    # Security Settings
    SECRET_KEY: str = Field(default="your_secret_key_here")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings(
    API_V1_PREFIX=os.getenv("API_V1_PREFIX", "/api/v1"),
    DEBUG=os.getenv("DEBUG", "False").lower() in ("true", "1", "t"),
    MONGODB_URI=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
    MONGODB_DB_NAME=os.getenv("MONGODB_DB_NAME", "hyperblock"),
    SECRET_KEY=os.getenv("SECRET_KEY", "your_secret_key_here"),
    ALGORITHM=os.getenv("ALGORITHM", "HS256"),
    ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
)