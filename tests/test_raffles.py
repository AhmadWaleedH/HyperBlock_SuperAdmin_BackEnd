import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timedelta

from app.main import app
from app.api.dependencies import get_current_admin

# Sample raffle data for testing
sample_raffle = {
    "guildId": "123456789",
    "raffleTitle": "Test Raffle",
    "numWinners": 3,
    "entryCost": 50,
    "startTime": (datetime.now()).isoformat(),
    "endTime": (datetime.now() + timedelta(days=7)).isoformat(),
    "chain": "Ethereum",
    "description": "This is a test raffle",
    "partnerTwitter": "@testpartner",
    "winnerRole": "123456",
    "entriesLimited": 100
}

# Sample participant data
sample_participant = {
    "userId": "987654321"
}

# Sample draw winners data
sample_draw = {
    "count": 1
}

# Skip authentication for tests
@pytest.fixture(autouse=True)
def override_auth():
    """Override the authentication dependency for testing"""
    app.dependency_overrides[get_current_admin] = lambda: {"sub": "admin", "role": "admin"}
    yield
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_create_raffle(test_client, clear_test_collections):
    """Test creating a new raffle"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/raffles/", json=sample_raffle)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["guildId"] == sample_raffle["guildId"]
        assert data["raffleTitle"] == sample_raffle["raffleTitle"]
        assert "_id" in data

@pytest.mark.asyncio
async def test_get_raffle_by_id(test_client, clear_test_collections):
    """Test getting a raffle by ID"""
    # First create a raffle
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/raffles/", json=sample_raffle)
        raffle_id = create_response.json()["_id"]
        
        # Then get the raffle by ID
        get_response = await ac.get(f"/api/v1/raffles/{raffle_id}")
        
        assert get_response.status_code == status.HTTP_200_OK
        data = get_response.json()
        assert data["raffleTitle"] == sample_raffle["raffleTitle"]
        assert data["_id"] == raffle_id

@pytest.mark.asyncio
async def test_update_raffle(test_client, clear_test_collections):
    """Test updating a raffle"""
    # First create a raffle
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/raffles/", json=sample_raffle)
        raffle_id = create_response.json()["_id"]
        
        # Then update the raffle
        update_data = {
            "raffleTitle": "Updated Raffle",
            "entryCost": 75
        }
        update_response = await ac.patch(f"/api/v1/raffles/{raffle_id}", json=update_data)
        
        assert update_response.status_code == status.HTTP_200_OK
        data = update_response.json()
        assert data["raffleTitle"] == update_data["raffleTitle"]
        assert data["entryCost"] == update_data["entryCost"]
        # Ensure other fields weren't changed
        assert data["guildId"] == sample_raffle["guildId"]

@pytest.mark.asyncio
async def test_add_participant(test_client, clear_test_collections):
    """Test adding a participant to a raffle"""
    # First create a raffle
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/raffles/", json=sample_raffle)
        raffle_id = create_response.json()["_id"]
        
        # Add participant
        add_response = await ac.post(
            f"/api/v1/raffles/{raffle_id}/participants", 
            json=sample_participant
        )
        
        assert add_response.status_code == status.HTTP_200_OK
        data = add_response.json()
        assert data["totalParticipants"] == 1
        assert len(data["participants"]) == 1
        assert data["participants"][0]["userId"] == sample_participant["userId"]

@pytest.mark.asyncio
async def test_draw_winners(test_client, clear_test_collections):
    """Test drawing winners for a raffle"""
    # First create a raffle
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/raffles/", json=sample_raffle)
        raffle_id = create_response.json()["_id"]
        
        # Add participant
        await ac.post(
            f"/api/v1/raffles/{raffle_id}/participants", 
            json=sample_participant
        )
        
        # Draw winner
        draw_response = await ac.post(
            f"/api/v1/raffles/{raffle_id}/draw", 
            json=sample_draw
        )
        
        assert draw_response.status_code == status.HTTP_200_OK
        data = draw_response.json()
        assert len(data["winners"]) == 1
        assert data["winners"][0]["userId"] == sample_participant["userId"]

@pytest.mark.asyncio
async def test_expire_raffle(test_client, clear_test_collections):
    """Test expiring a raffle"""
    # First create a raffle
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/raffles/", json=sample_raffle)
        raffle_id = create_response.json()["_id"]
        
        # Expire raffle
        expire_response = await ac.post(f"/api/v1/raffles/{raffle_id}/expire")
        
        assert expire_response.status_code == status.HTTP_200_OK
        data = expire_response.json()
        assert data["isExpired"] == True

@pytest.mark.asyncio
async def test_filter_raffles(test_client, clear_test_collections):
    """Test filtering raffles"""
    # Create two raffles with different chains
    async with AsyncClient(app=app, base_url="http://test") as ac:
        raffle1 = sample_raffle.copy()
        raffle1["chain"] = "Ethereum"
        
        raffle2 = sample_raffle.copy()
        raffle2["chain"] = "Solana"
        
        await ac.post("/api/v1/raffles/", json=raffle1)
        await ac.post("/api/v1/raffles/", json=raffle2)
        
        # Filter by chain
        response = await ac.get("/api/v1/raffles/?chain=Ethereum")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["raffles"]) == 1
        assert data["raffles"][0]["chain"] == "Ethereum"

@pytest.mark.asyncio
async def test_search_raffles(test_client, clear_test_collections):
    """Test searching raffles"""
    # Create two raffles with different titles
    async with AsyncClient(app=app, base_url="http://test") as ac:
        raffle1 = sample_raffle.copy()
        raffle1["raffleTitle"] = "Unique Galaxy Raffle"
        
        raffle2 = sample_raffle.copy()
        raffle2["raffleTitle"] = "Another Raffle"
        
        await ac.post("/api/v1/raffles/", json=raffle1)
        await ac.post("/api/v1/raffles/", json=raffle2)
        
        # Search by title
        response = await ac.get("/api/v1/raffles/search/?query=Galaxy")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["raffles"]) == 1
        assert data["raffles"][0]["raffleTitle"] == "Unique Galaxy Raffle"

@pytest.mark.asyncio
async def test_raffle_analytics(test_client, clear_test_collections):
    """Test raffle analytics endpoint"""
    # Create raffles with different data
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Add a couple raffles with different properties
        await ac.post("/api/v1/raffles/", json=sample_raffle)
        
        raffle2 = sample_raffle.copy()
        raffle2["chain"] = "Solana"
        raffle2["entryCost"] = 100
        raffle_response = await ac.post("/api/v1/raffles/", json=raffle2)
        raffle2_id = raffle_response.json()["_id"]
        
        # Add participants to a raffle
        await ac.post(
            f"/api/v1/raffles/{raffle2_id}/participants", 
            json={"userId": "user1"}
        )
        
        await ac.post(
            f"/api/v1/raffles/{raffle2_id}/participants", 
            json={"userId": "user2"}
        )
        
        # Test analytics endpoint
        response = await ac.get("/api/v1/raffles/analytics/summary")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_raffles" in data
        assert data["total_raffles"] == 2
        assert "raffles_by_chain" in data
        assert "Ethereum" in data["raffles_by_chain"]
        assert "Solana" in data["raffles_by_chain"]