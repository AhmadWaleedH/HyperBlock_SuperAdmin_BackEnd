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
    SECRET_KEY: str = Field(default="secret_key")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)

    # Discord Settings
    DISCORD_CLIENT_ID: str = "1298459256772624504"
    DISCORD_CLIENT_SECRET: str = "8eDm0dE5Y5qosFQph7IqHJQKEwqNuTLu"
    DISCORD_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/discord/callback"
    DISCORD_API_ENDPOINT: str = "https://discord.com/api/v10"

    # Twitter Settings
    TWITTER_CLIENT_ID: str = "UGs5Q3M4MHVCR29nbjBiZXp5S0o6MTpjaQ"
    TWITTER_CLIENT_SECRET: str = "LMifdmAhutugQGn6caxxGklSiu9Y6mWYJ09FD9iQZf5vBFBEcx"
    TWITTER_REDIRECT_URI: str = "http://localhost:3000/connect/twitter/callback"
    TWITTER_AUTH_URL: str = "https://twitter.com/i/oauth2/authorize"
    TWITTER_TOKEN_URL: str = "https://api.twitter.com/2/oauth2/token"
        
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings(
    API_V1_PREFIX=os.getenv("API_V1_PREFIX", "/api/v1"),
    DEBUG=os.getenv("DEBUG", "False").lower() in ("true", "1", "t"),
    MONGODB_URI=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
    MONGODB_DB_NAME=os.getenv("MONGODB_DB_NAME", "hyperblock"),
    SECRET_KEY=os.getenv("SECRET_KEY", "ecret_key"),
    ALGORITHM=os.getenv("ALGORITHM", "HS256"),
    ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
)