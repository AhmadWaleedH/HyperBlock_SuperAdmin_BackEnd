import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.testclient import TestClient
from typing import AsyncGenerator, Generator

from app.main import app
from app.config import settings
from app.db.database import db, get_database

# Test database name - to avoid affecting production data
TEST_DB_NAME = "hyperblock_test"

@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for each test case.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_client() -> Generator:
    """
    Create a test client for the FastAPI app
    """
    with TestClient(app) as client:
        yield client

@pytest.fixture(scope="session")
async def test_db() -> AsyncGenerator:
    """
    Create a test database connection
    """
    # Connect to MongoDB and use a test database
    db.client = AsyncIOMotorClient(settings.MONGODB_URI)
    
    # Override the default database name with test database name
    async def override_get_database():
        return db.client[TEST_DB_NAME]
    
    # Override the get_database dependency
    app.dependency_overrides[get_database] = override_get_database
    
    yield db.client[TEST_DB_NAME]
    
    # Clean up after tests
    await db.client.drop_database(TEST_DB_NAME)
    await db.client.close()

@pytest.fixture(scope="function")
async def clear_test_collections(test_db):
    """
    Clear all collections in the test database before each test
    """
    collections = await test_db.list_collection_names()
    for collection in collections:
        await test_db[collection].delete_many({})