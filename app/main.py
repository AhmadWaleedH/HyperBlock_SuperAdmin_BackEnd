from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import logging

from .config import settings, FRONTEND_URLS
from .api.routes import router as api_router
from .db.database import connect_to_mongo, close_mongo_connection
from app.scheduler import scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to MongoDB and start scheduler
    logger.info("Starting application: connecting to MongoDB and starting scheduler")
    await connect_to_mongo()
    scheduler.start()
    
    yield  # This is where FastAPI serves requests
    
    # Shutdown: Close MongoDB connection and shutdown scheduler
    logger.info("Shutting down application: closing MongoDB connection and stopping scheduler")
    await close_mongo_connection()
    scheduler.shutdown()

# Create FastAPI app with lifespan
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    debug=settings.DEBUG,
    lifespan=lifespan
)

# SessionMiddleware  
app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SECRET_KEY,
    max_age=3600,  # Session expiration in seconds (1 hour)
    same_site="none" if not settings.DEBUG else "lax",
    https_only=settings.DEBUG is False  # HTTPS in production
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_URLS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.get("/", tags=["health"])
async def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)