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
    DISCORD_CLIENT_ID: str = Field(default="1234567890")
    DISCORD_CLIENT_SECRET: str = Field(default="abcdefghijklmnopqrstuvwxyz")
    DISCORD_REDIRECT_URI: str = Field(default="/api/v1/auth/discord/callback")
    DISCORD_API_ENDPOINT: str = Field(default="https://discord.com/api/v10")

    # Twitter Settings
    TWITTER_CLIENT_ID: str = Field(default="abcdedfghijklmnopqrstuvwxyz")
    TWITTER_CLIENT_SECRET: str = Field(default="abcdefghijklmnopqrstuvwxyz")
    TWITTER_REDIRECT_URI: str = Field(default="/connect/twitter/callback")
    TWITTER_AUTH_URL: str = Field(default="https://twitter.com/i/oauth2/authorize")
    TWITTER_TOKEN_URL: str = Field(default="https://api.twitter.com/2/oauth2/token")

    # Cybersource Settings
    CYBERSOURCE_MERCHANT_ID: str = os.getenv("CYBERSOURCE_MERCHANT_ID", "")
    CYBERSOURCE_API_KEY_ID: str = os.getenv("CYBERSOURCE_API_KEY_ID", "")
    CYBERSOURCE_SECRET_KEY: str = os.getenv("CYBERSOURCE_SECRET_KEY", "")
    CYBERSOURCE_PROFILE_ID: str = os.getenv("CYBERSOURCE_PROFILE_ID", "")
    CYBERSOURCE_ENVIRONMENT: str = os.getenv("CYBERSOURCE_ENVIRONMENT", "test")
    CYBERSOURCE_WEBHOOK_SECRET: str = os.getenv("CYBERSOURCE_WEBHOOK_SECRET", "")
        
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
    ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
    DISCORD_CLIENT_ID=os.getenv("DISCORD_CLIENT_ID", "1234567890"),
    DISCORD_CLIENT_SECRET=os.getenv("DISCORD_CLIENT_SECRET", "abcdefghijklmnopqrstuvwxyz"),
    DISCORD_REDIRECT_URI=os.getenv("DISCORD_REDIRECT_URI", "/api/v1/auth/discord/callback"),
    DISCORD_API_ENDPOINT=os.getenv("DISCORD_API_ENDPOINT", "https://discord.com/api/v10"),
    TWITTER_CLIENT_ID=os.getenv("TWITTER_CLIENT_ID", "abcdedfghijklmnopqrstuvwxyz"),
    TWITTER_CLIENT_SECRET=os.getenv("TWITTER_CLIENT_SECRET", "abcdefghijklmnopqrstuvwxyz"),
    TWITTER_REDIRECT_URI=os.getenv("TWITTER_REDIRECT_URI", "/connect/twitter/callback"),
    TWITTER_AUTH_URL=os.getenv("TWITTER_AUTH_URL", "https://twitter.com/i/oauth2/authorize"),
    TWITTER_TOKEN_URL=os.getenv("TWITTER_TOKEN_URL", "https://api.twitter.com/2/oauth2/token"),
)