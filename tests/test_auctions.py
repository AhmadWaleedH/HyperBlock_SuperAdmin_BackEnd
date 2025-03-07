import pytest
from httpx import AsyncClient
from fastapi import status
from datetime import datetime, timedelta

from app.main import app
from app.api.dependencies import get_current_admin

# Sample auction data for testing
sample_auction = {
    "name": "Test Auction Item",
    "quantity": 1,
    "chain": "Ethereum",
    "duration": (datetime.now() + timedelta(days=7)).isoformat(),
    "guildId": "123456789",
    "description": "This is a test auction item",
    "minimumBid": 50.0,
    "blindAuction": False
}

# Sample bid data
sample_bid = {
    "userId": "987654321",
    "bidAmount": 100.0,
    "walletAddress": "0x123456789abcdef"
}

# Skip authentication for tests
@pytest.fixture(autouse=True)
def override_auth():
    """Override the authentication dependency for testing"""
    app.dependency_overrides[get_current_admin] = lambda: {"sub": "admin", "role": "admin"}
    yield
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_create_auction(test_client, clear_test_collections):
    """Test creating a new auction"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/auctions/", json=sample_auction)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == sample_auction["name"]
        assert data["chain"] == sample_auction["chain"]
        assert "_id" in data

@pytest.mark.asyncio
async def test_get_auction_by_id(test_client, clear_test_collections):
    """Test getting an auction by ID"""
    # First create an auction
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/auctions/", json=sample_auction)
        auction_id = create_response.json()["_id"]
        
        # Then get the auction by ID
        get_response = await ac.get(f"/api/v1/auctions/{auction_id}")
        
        assert get_response.status_code == status.HTTP_200_OK
        data = get_response.json()
        assert data["name"] == sample_auction["name"]
        assert data["_id"] == auction_id

@pytest.mark.asyncio
async def test_update_auction(test_client, clear_test_collections):
    """Test updating an auction"""
    # First create an auction
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/auctions/", json=sample_auction)
        auction_id = create_response.json()["_id"]
        
        # Then update the auction
        update_data = {
            "name": "Updated Auction Item",
            "minimumBid": 75.0
        }
        update_response = await ac.patch(f"/api/v1/auctions/{auction_id}", json=update_data)
        
        assert update_response.status_code == status.HTTP_200_OK
        data = update_response.json()
        assert data["name"] == update_data["name"]
        assert data["minimumBid"] == update_data["minimumBid"]
        # Ensure other fields weren't changed
        assert data["chain"] == sample_auction["chain"]

@pytest.mark.asyncio
async def test_place_bid(test_client, clear_test_collections):
    """Test placing a bid on an auction"""
    # First create an auction
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/auctions/", json=sample_auction)
        auction_id = create_response.json()["_id"]
        
        # Place a bid
        bid_response = await ac.post(
            f"/api/v1/auctions/{auction_id}/bid", 
            json=sample_bid
        )
        
        assert bid_response.status_code == status.HTTP_200_OK
        data = bid_response.json()
        assert data["currentBid"] == sample_bid["bidAmount"]
        assert data["currentBidder"] == sample_bid["userId"]
        assert len(data["bidders"]) == 1
        assert data["bidders"][0]["userId"] == sample_bid["userId"]

@pytest.mark.asyncio
async def test_end_auction(test_client, clear_test_collections):
    """Test ending an auction"""
    # First create an auction
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/auctions/", json=sample_auction)
        auction_id = create_response.json()["_id"]
        
        # Place a bid
        await ac.post(
            f"/api/v1/auctions/{auction_id}/bid", 
            json=sample_bid
        )
        
        # End the auction
        end_response = await ac.post(f"/api/v1/auctions/{auction_id}/end")
        
        assert end_response.status_code == status.HTTP_200_OK
        data = end_response.json()
        assert data["status"] == "ended"
        assert data["winner"]["userId"] == sample_bid["userId"]
        assert data["winner"]["winningBid"] == sample_bid["bidAmount"]

@pytest.mark.asyncio
async def test_cancel_auction(test_client, clear_test_collections):
    """Test cancelling an auction"""
    # First create an auction
    async with AsyncClient(app=app, base_url="http://test") as ac:
        create_response = await ac.post("/api/v1/auctions/", json=sample_auction)
        auction_id = create_response.json()["_id"]
        
        # Cancel the auction
        cancel_response = await ac.post(f"/api/v1/auctions/{auction_id}/cancel")
        
        assert cancel_response.status_code == status.HTTP_200_OK
        data = cancel_response.json()
        assert data["status"] == "cancelled"

@pytest.mark.asyncio
async def test_filter_auctions(test_client, clear_test_collections):
    """Test filtering auctions"""
    # Create two auctions with different chains
    async with AsyncClient(app=app, base_url="http://test") as ac:
        auction1 = sample_auction.copy()
        auction1["chain"] = "Ethereum"
        
        auction2 = sample_auction.copy()
        auction2["chain"] = "Solana"
        
        await ac.post("/api/v1/auctions/", json=auction1)
        await ac.post("/api/v1/auctions/", json=auction2)
        
        # Filter by chain
        response = await ac.get("/api/v1/auctions/?chain=Ethereum")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["auctions"]) == 1
        assert data["auctions"][0]["chain"] == "Ethereum"

@pytest.mark.asyncio
async def test_search_auctions(test_client, clear_test_collections):
    """Test searching auctions"""
    # Create two auctions with different names
    async with AsyncClient(app=app, base_url="http://test") as ac:
        auction1 = sample_auction.copy()
        auction1["name"] = "Unique Collectible NFT"
        
        auction2 = sample_auction.copy()
        auction2["name"] = "Another Item"
        
        await ac.post("/api/v1/auctions/", json=auction1)
        await ac.post("/api/v1/auctions/", json=auction2)
        
        # Search by name
        response = await ac.get("/api/v1/auctions/search/?query=Collectible")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1
        assert len(data["auctions"]) == 1
        assert data["auctions"][0]["name"] == "Unique Collectible NFT"

@pytest.mark.asyncio
async def test_auction_analytics(test_client, clear_test_collections):
    """Test auction analytics endpoint"""
    # Create auctions with different data
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Add a couple auctions with different properties
        await ac.post("/api/v1/auctions/", json=sample_auction)
        
        auction2 = sample_auction.copy()
        auction2["chain"] = "Solana"
        auction2["minimumBid"] = 100
        auction_response = await ac.post("/api/v1/auctions/", json=auction2)
        auction2_id = auction_response.json()["_id"]
        
        # Add bids to an auction
        await ac.post(
            f"/api/v1/auctions/{auction2_id}/bid", 
            json={"userId": "user1", "bidAmount": 120.0}
        )
        
        await ac.post(
            f"/api/v1/auctions/{auction2_id}/bid", 
            json={"userId": "user2", "bidAmount": 150.0}
        )
        
        # Test analytics endpoint
        response = await ac.get("/api/v1/auctions/analytics/summary")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_auctions" in data
        assert data["total_auctions"] == 2
        assert "auctions_by_chain" in data
        assert "Ethereum" in data["auctions_by_chain"]
        assert "Solana" in data["auctions_by_chain"]
        assert "total_bids" in data
        assert data["total_bids"] == 2