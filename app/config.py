import os
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
load_dotenv()

FRONTEND_URLS = [
    "https://hyperblockstudio.com",
    "https://www.hyperblockstudio.com",  # Alternative domain
    "https://api.hyperblockstudio.com",
]

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

    # Stripe settings
    STRIPE_API_KEY: str = Field(default="STRIPE_API_KEY")
    STRIPE_PUBLIC_KEY: str = Field(default="STRIPE_WEBHOOK_SECRET")
    STRIPE_WEBHOOK_SECRET: str = Field(default="STRIPE_PUBLIC_KEY")

    # AWS S3 Settings
    AWS_ACCESS_KEY_ID: str = Field(default="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = Field(default="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = Field(default="AWS_REGION")
    S3_BUCKET_NAME: str = Field(default="S3_BUCKET_NAME")
    S3_BASE_URL: str = Field(default="https://s3.amazonaws.com/")
        
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

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
    STRIPE_API_KEY=os.getenv("STRIPE_API_KEY", "abcdedfghijklmnopqrstuvwxyz"),
    STRIPE_WEBHOOK_SECRET=os.getenv("STRIPE_WEBHOOK_SECRET", "abcdefghijklmnopqrstuvwxyz"),
    STRIPE_PUBLIC_KEY=os.getenv("STRIPE_PUBLIC_KEY", "abcdefghijklmnopqrstuvwxyz"),
    AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID"),
    AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY"),
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1"),
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "hyperblock-user-cards"),
    S3_BASE_URL=os.getenv("S3_BASE_URL", "https://s3.amazonaws.com/")
)