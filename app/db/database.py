from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError
import certifi
from ..config import settings

class Database:
    client: AsyncIOMotorClient = None

db = Database()

async def get_database() -> AsyncIOMotorClient:
    """
    Return database client instance
    """
    return db.client[settings.MONGODB_DB_NAME]

async def connect_to_mongo():
    """
    Connect to MongoDB with proper SSL configuration for Atlas
    """
    try:
        """
        TODO: Setup proper SSL configuration for MongoDB Atlas
        """
        # Using the certifi CA bundle for SSL certificate verification
        db.client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=100,  # Increase connection pool size for better concurrency
            minPoolSize=10,   # Maintain minimum connections
            maxIdleTimeMS=30000,  # Close idle connections after 30 seconds
            waitQueueTimeoutMS=5000,  # Maximum time to wait for a connection from the pool
            tls=True,
            tlsCAFile=certifi.where()
        )
        
        # Check connection
        await db.client.server_info()
        print(f"Connected to MongoDB at {settings.MONGODB_URI}")
    except ServerSelectionTimeoutError as e:
        print(f"Failed to connect to MongoDB: {e}")
        # print the error but not crash the app
        print("Using the app without a working database connection may cause errors.")

async def close_mongo_connection():
    """
    Close MongoDB connection
    """
    if db.client:
        db.client.close()
        print("Closed connection to MongoDB")