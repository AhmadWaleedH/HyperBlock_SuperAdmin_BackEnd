import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timedelta

from app.main import app
from app.api.dependencies import get_current_admin

# Sample contest data for testing
sample_contest = {
    "guildId": "123456789",
    "title": "Test Contest",
    "duration": (datetime.now() + timedelta(days=7)).isoformat(),
    "numberOfWinners": 3,
    "description": "This is a test contest",
    "pointsForParticipants": 10,
    "isActive": True,
    "channelId": "987654321",
    "pointsForWinners": [100, 50, 25]
}

# Sample vote data
sample_vote = {
    "messageId": "567890123",
    "userVote": {
        "userId": "123123123",
        "voteCount": 1
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
async def test_create_contest(test_client, clear_test_collections):
    """Test creating a new contest"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/contests/", json=sample_contest)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["guildId"] == sample_contest["guildId"]
        assert data["title"] == sample_contest["title"]
        assert "_id" in data

@pytest.mark.asyncio
async def test_get_contest_by_id(test_client, clear_test_collections):
    """Test getting a contest by ID"""
    # First create a contest
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/contests/", json=sample_contest)
        contest_id = create_response.json()["_id"]
        
        # Then get the contest by ID
        get_response = await ac.get(f"/api/v1/contests/{contest_id}")
        
        assert get_response.status_code == status.HTTP_200_OK
        data = get_response.json()
        assert data["guildId"] == sample_contest["guildId"]
        assert data["_id"] == contest_id
        
@pytest.mark.asyncio
async def test_get_contests_by_guild(test_client, clear_test_collections):
    """Test getting contests by Guild ID"""
    # First create a contest
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/contests/", json=sample_contest)
        contest_id = create_response.json()["_id"]
        
        # Then get the contest by Guild ID
        get_response = await ac.get(f"/api/v1/contests/guild/{sample_contest['guildId']}")
        
        assert get_response.status_code == status.HTTP_200_OK
        data = get_response.json()
        assert len(data["contests"]) == 1
        assert data["contests"][0]["_id"] == contest_id

@pytest.mark.asyncio
async def test_update_contest(test_client, clear_test_collections):
    """Test updating a contest"""
    # First create a contest
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/contests/", json=sample_contest)
        contest_id = create_response.json()["_id"]
        
        # Then update the contest
        update_response = await ac.patch(f"/api/v1/contests/{contest_id}", json={"title": "Updated Contest"})
        
        assert update_response.status_code == status.HTTP_200_OK
        data = update_response.json()
        assert data["title"] == "Updated Contest"

@pytest.mark.asyncio
async def test_delete_contest(test_client, clear_test_collections):
    """Test deleting a contest"""
    # First create a contest
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/contests/", json=sample_contest)
        contest_id = create_response.json()["_id"]
        
        # Then delete the contest
        delete_response = await ac.delete(f"/api/v1/contests/{contest_id}")
        
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        assert delete_response.content == b""