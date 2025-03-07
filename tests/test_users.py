import pytest
from httpx import AsyncClient
from fastapi import status

from app.main import app
from app.models.user import UserCreate
from app.api.dependencies import get_current_admin

# Sample user data for testing
sample_user = {
    "discordId": "123456789",
    "discordUsername": "testuser",
    "discordUserAvatarURL": "https://example.com/avatar.png",
    "walletAddress": "0x1234567890abcdef",
    "hyperBlockPoints": 100,
    "status": "active",
    "socials": {
        "x": "testuser",
        "tg": "testuser"
    }
}

# Skip authentication for tests
@pytest.fixture(autouse=True)
def override_auth():
    """Override the authentication dependency for testing"""
    app.dependency_overrides[get_current_admin] = lambda: {"sub": "admin", "role": "admin"}
    yield
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_create_user(test_client, clear_test_collections):
    """Test creating a new user"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/users/", json=sample_user)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["discordId"] == sample_user["discordId"]
        assert data["discordUsername"] == sample_user["discordUsername"]
        assert "_id" in data

@pytest.mark.asyncio
async def test_get_user_by_id(test_client, clear_test_collections):
    """Test getting a user by ID"""
    # First create a user
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/users/", json=sample_user)
        user_id = create_response.json()["_id"]
        
        # Then get the user by ID
        get_response = await ac.get(f"/api/v1/users/{user_id}")
        
        assert get_response.status_code == status.HTTP_200_OK
        data = get_response.json()
        assert data["discordId"] == sample_user["discordId"]
        assert data["_id"] == user_id

@pytest.mark.asyncio
async def test_get_user_by_discord_id(test_client, clear_test_collections):
    """Test getting a user by Discord ID"""
    # First create a user
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post("/api/v1/users/", json=sample_user)
        
        # Then get the user by Discord ID
        get_response = await ac.get(f"/api/v1/users/discord/{sample_user['discordId']}")
        
        assert get_response.status_code == status.HTTP_200_OK
        data = get_response.json()
        assert data["discordId"] == sample_user["discordId"]

@pytest.mark.asyncio
async def test_update_user(test_client, clear_test_collections):
    """Test updating a user"""
    # First create a user
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/users/", json=sample_user)
        user_id = create_response.json()["_id"]
        
        # Then update the user
        update_data = {
            "discordUsername": "updateduser",
            "hyperBlockPoints": 200
        }
        update_response = await ac.patch(f"/api/v1/users/{user_id}", json=update_data)
        
        assert update_response.status_code == status.HTTP_200_OK
        data = update_response.json()
        assert data["discordUsername"] == update_data["discordUsername"]
        assert data["hyperBlockPoints"] == update_data["hyperBlockPoints"]
        # Ensure other fields weren't changed
        assert data["discordId"] == sample_user["discordId"]

@pytest.mark.asyncio
async def test_filter_users(test_client, clear_test_collections):
    """Test filtering users"""
    # Create two users with different subscriptions
    async with AsyncClient(app=app, base_url="http://test") as ac:
        user1 = sample_user.copy()
        user1["subscription"] = {"tier": "premium"}
        
        user2 = sample_user.copy()
        user2["discordId"] = "987654321"
        user2["discordUsername"] = "anotheruser"
        user2["subscription"] = {"tier": "free"}
        
        await ac.post("/api/v1/users/", json=user1)
        await ac.post("/api/v1/users/", json=user2)
        
        # Filter by subscription tier
        response = await ac.get("/api/v1/users/?subscription_tier=premium")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["users"]) == 1
        assert data["users"][0]["subscription"]["tier"] == "premium"

@pytest.mark.asyncio
async def test_search_users(test_client, clear_test_collections):
    """Test searching users"""
    # Create two users with different usernames
    async with AsyncClient(app=app, base_url="http://test") as ac:
        user1 = sample_user.copy()
        user1["discordUsername"] = "uniquename123"
        
        user2 = sample_user.copy()
        user2["discordId"] = "987654321"
        user2["discordUsername"] = "anotheruser"
        
        await ac.post("/api/v1/users/", json=user1)
        await ac.post("/api/v1/users/", json=user2)
        
        # Search by username
        response = await ac.get("/api/v1/users/search/?query=unique")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["users"]) == 1
        assert data["users"][0]["discordUsername"] == "uniquename123"

@pytest.mark.asyncio
async def test_delete_user(test_client, clear_test_collections):
    """Test deleting a user"""
    # First create a user
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/users/", json=sample_user)
        user_id = create_response.json()["_id"]
        
        # Then delete the user
        delete_response = await ac.delete(f"/api/v1/users/{user_id}")
        
        assert delete_response.status_code == status.HTTP_200_OK
        
        # Verify the user has been deleted
        get_response = await ac.get(f"/api/v1/users/{user_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND