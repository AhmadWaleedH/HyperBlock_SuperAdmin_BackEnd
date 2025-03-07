import pytest
from httpx import AsyncClient
from fastapi import status

from app.main import app
from app.api.dependencies import get_current_admin

# Sample guild data for testing
sample_guild = {
    "guildId": "123456789",
    "guildName": "Test Guild",
    "guildIconURL": "https://example.com/icon.png",
    "ownerDiscordId": "987654321",
    "twitterUrl": "https://twitter.com/testguild",
    "category": "Gaming",
    "userCategory": "Gamers",
    "subscription": {
        "tier": "Gold",
        "autoRenew": True
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
async def test_create_guild(test_client, clear_test_collections):
    """Test creating a new guild"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/guilds/", json=sample_guild)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["guildId"] == sample_guild["guildId"]
        assert data["guildName"] == sample_guild["guildName"]
        assert "_id" in data

@pytest.mark.asyncio
async def test_get_guild_by_id(test_client, clear_test_collections):
    """Test getting a guild by ID"""
    # First create a guild
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/guilds/", json=sample_guild)
        guild_id = create_response.json()["_id"]
        
        # Then get the guild by ID
        get_response = await ac.get(f"/api/v1/guilds/{guild_id}")
        
        assert get_response.status_code == status.HTTP_200_OK
        data = get_response.json()
        assert data["guildId"] == sample_guild["guildId"]
        assert data["_id"] == guild_id

@pytest.mark.asyncio
async def test_get_guild_by_discord_id(test_client, clear_test_collections):
    """Test getting a guild by Discord Guild ID"""
    # First create a guild
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post("/api/v1/guilds/", json=sample_guild)
        
        # Then get the guild by Discord ID
        get_response = await ac.get(f"/api/v1/guilds/discord/{sample_guild['guildId']}")
        
        assert get_response.status_code == status.HTTP_200_OK
        data = get_response.json()
        assert data["guildId"] == sample_guild["guildId"]

@pytest.mark.asyncio
async def test_update_guild(test_client, clear_test_collections):
    """Test updating a guild"""
    # First create a guild
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/guilds/", json=sample_guild)
        guild_id = create_response.json()["_id"]
        
        # Then update the guild
        update_data = {
            "guildName": "Updated Guild",
            "category": "NFT"
        }
        update_response = await ac.patch(f"/api/v1/guilds/{guild_id}", json=update_data)
        
        assert update_response.status_code == status.HTTP_200_OK
        data = update_response.json()
        assert data["guildName"] == update_data["guildName"]
        assert data["category"] == update_data["category"]
        # Ensure other fields weren't changed
        assert data["guildId"] == sample_guild["guildId"]

@pytest.mark.asyncio
async def test_filter_guilds(test_client, clear_test_collections):
    """Test filtering guilds"""
    # Create two guilds with different subscriptions
    async with AsyncClient(app=app, base_url="http://test") as ac:
        guild1 = sample_guild.copy()
        guild1["subscription"] = {"tier": "Gold"}
        
        guild2 = sample_guild.copy()
        guild2["guildId"] = "987654321"
        guild2["guildName"] = "Another Guild"
        guild2["subscription"] = {"tier": "Free"}
        
        await ac.post("/api/v1/guilds/", json=guild1)
        await ac.post("/api/v1/guilds/", json=guild2)
        
        # Filter by subscription tier
        response = await ac.get("/api/v1/guilds/?subscription_tier=Gold")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["guilds"]) == 1
        assert data["guilds"][0]["subscription"]["tier"] == "Gold"

@pytest.mark.asyncio
async def test_search_guilds(test_client, clear_test_collections):
    """Test searching guilds"""
    # Create two guilds with different names
    async with AsyncClient(app=app, base_url="http://test") as ac:
        guild1 = sample_guild.copy()
        guild1["guildName"] = "Unique Name Guild"
        
        guild2 = sample_guild.copy()
        guild2["guildId"] = "987654321"
        guild2["guildName"] = "Another Guild"
        
        await ac.post("/api/v1/guilds/", json=guild1)
        await ac.post("/api/v1/guilds/", json=guild2)
        
        # Search by name
        response = await ac.get("/api/v1/guilds/search/?query=Unique")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["guilds"]) == 1
        assert data["guilds"][0]["guildName"] == "Unique Name Guild"

@pytest.mark.asyncio
async def test_delete_guild(test_client, clear_test_collections):
    """Test deleting a guild"""
    # First create a guild
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/guilds/", json=sample_guild)
        guild_id = create_response.json()["_id"]
        
        # Then delete the guild
        delete_response = await ac.delete(f"/api/v1/guilds/{guild_id}")
        
        assert delete_response.status_code == status.HTTP_200_OK
        
        # Verify the guild has been deleted
        get_response = await ac.get(f"/api/v1/guilds/{guild_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.asyncio
async def test_guild_analytics(test_client, clear_test_collections):
    """Test guild analytics endpoint"""
    # Create some guilds with different data
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Add a few guilds with different properties
        guild1 = sample_guild.copy()
        guild1["subscription"] = {"tier": "Gold"}
        guild1["analytics"] = {
            "rating": "A",
            "isTop10": True,
            "metrics": {
                "activeUsers": 100,
                "messageCount": 500
            }
        }
        
        guild2 = sample_guild.copy()
        guild2["guildId"] = "987654321"
        guild2["category"] = "NFT"
        guild2["subscription"] = {"tier": "Free"}
        guild2["analytics"] = {
            "rating": "B",
            "isTop10": False,
            "metrics": {
                "activeUsers": 50,
                "messageCount": 200
            }
        }
        
        await ac.post("/api/v1/guilds/", json=guild1)
        await ac.post("/api/v1/guilds/", json=guild2)
        
        # Test analytics endpoint
        response = await ac.get("/api/v1/guilds/analytics/summary")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_guilds" in data
        assert data["total_guilds"] == 2
        assert "subscription_tiers" in data