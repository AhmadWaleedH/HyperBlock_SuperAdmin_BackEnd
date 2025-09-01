from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError
import certifi
import logging
import asyncio
from contextvars import ContextVar
from ..config import settings

logger = logging.getLogger(__name__)

# Context variable to store database connection per request context
db_client_context: ContextVar[AsyncIOMotorClient] = ContextVar("db_client", default=None)

class Database:
    client: AsyncIOMotorClient = None
    
    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        """
        Get client from context var if available, otherwise use the global client
        """
        client_from_context = db_client_context.get()
        return client_from_context if client_from_context else cls.client

db = Database()

async def get_database():
    """
    Return database client instance
    This is called for each request to get the database
    """
    client = db.get_client()
    if client is None:
        # Create a new client for this request if none exists
        logger.debug("Creating new MongoDB client for request")
        client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=100,  # Increase connection pool size for better concurrency
            minPoolSize=10,   # Maintain minimum connections
            maxIdleTimeMS=30000,  # Close idle connections after 30 seconds
            waitQueueTimeoutMS=5000,  # Maximum time to wait for a connection from the pool
            tls=True,
            tlsCAFile=certifi.where()
        )
        # Store in context var for this request
        db_client_context.set(client)
    
    return client[settings.MONGODB_DB_NAME]

async def connect_to_mongo():
    """
    Connect to MongoDB with proper SSL configuration for Atlas
    This is called once at application startup
    """
    try:
        # Using the certifi CA bundle for SSL certificate verification
        db.client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=100,  # Increase connection pool size for better concurrency
            minPoolSize=10,   # Maintain minimum connections
            maxIdleTimeMS=30000,  # Close idle connections after 30 seconds
            waitQueueTimeoutMS=5000,  # Maximum time to wait for a connection from the pool
            tls=True,
            tlsCAFile=certifi.where(),
            # Set explicit event loop to prevent issues
            io_loop=asyncio.get_event_loop()
        )
        
        # Check connection
        await db.client.server_info()
        logger.info(f"Connected to MongoDB at {settings.MONGODB_URI}")
    except ServerSelectionTimeoutError as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        # Log the error but don't crash the app
        logger.warning("Using the app without a working database connection may cause errors.")

async def close_mongo_connection():
    """
    Close MongoDB connection
    This is called once at application shutdown
    """
    # Only close the global client, not per-request clients
    if db.client:
        db.client.close()
        logger.info("Closed global MongoDB connection")