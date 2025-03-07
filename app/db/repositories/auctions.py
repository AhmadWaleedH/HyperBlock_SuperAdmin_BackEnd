from typing import List, Dict, Any, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection, AsyncIOMotorCursor
from datetime import datetime
from bson import ObjectId

from ...models.auction import (
    AuctionModel, AuctionCreate, AuctionUpdate, AuctionFilter, 
    PlaceBidModel, AuctionAnalytics, AuctionStatistics
)
from ...models.user import PaginationParams

class AuctionRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.collection = database.auctions

    async def create(self, auction: AuctionCreate) -> AuctionModel:
        """
        Create a new auction in the database
        """
        auction_data = auction.dict()
        auction_data["createdAt"] = datetime.now()
        auction_data["updatedAt"] = datetime.now()
        auction_data["currentBid"] = auction.minimumBid
        auction_data["bidders"] = []
        auction_data["status"] = "active"
        
        result = await self.collection.insert_one(auction_data)
        auction_data["_id"] = result.inserted_id
        
        return AuctionModel(**auction_data)

    async def get_by_id(self, auction_id: str) -> Optional[AuctionModel]:
        """
        Get an auction by MongoDB ID
        """
        if not ObjectId.is_valid(auction_id):
            return None
            
        auction = await self.collection.find_one({"_id": ObjectId(auction_id)})
        if auction:
            return AuctionModel(**auction)
        return None

    async def get_auctions_by_guild_id(self, guild_id: str, pagination: PaginationParams) -> Tuple[List[AuctionModel], int]:
        """
        Get auctions by Guild ID
        """
        query = {"guildId": guild_id}
        
        # Count total matches
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        auctions = []
        async for auction_doc in cursor:
            auctions.append(AuctionModel(**auction_doc))
        
        return auctions, total

    async def update(self, auction_id: str, auction_update: AuctionUpdate) -> Optional[AuctionModel]:
        """
        Update an auction
        """
        if not ObjectId.is_valid(auction_id):
            return None
            
        update_data = auction_update.dict(exclude_unset=True)
        if update_data:
            update_data["updatedAt"] = datetime.now()
            
            await self.collection.update_one(
                {"_id": ObjectId(auction_id)},
                {"$set": update_data}
            )
            
        return await self.get_by_id(auction_id)

    async def delete(self, auction_id: str) -> bool:
        """
        Delete an auction
        """
        if not ObjectId.is_valid(auction_id):
            return False
            
        result = await self.collection.delete_one({"_id": ObjectId(auction_id)})
        return result.deleted_count > 0

    async def place_bid(self, auction_id: str, bid: PlaceBidModel) -> Optional[AuctionModel]:
        """
        Place a bid on an auction
        """
        if not ObjectId.is_valid(auction_id):
            return None
        
        # Check if auction exists and is active
        auction = await self.get_by_id(auction_id)
        if not auction or auction.status != "active":
            return None
        
        # Add new bid to bidders list
        bidder_data = bid.dict()
        bidder_data["timestamp"] = datetime.now()
        
        await self.collection.update_one(
            {"_id": ObjectId(auction_id)},
            {
                "$push": {"bidders": bidder_data},
                "$set": {
                    "currentBid": bid.bidAmount,
                    "currentBidder": bid.userId,
                    "updatedAt": datetime.now()
                }
            }
        )
        
        return await self.get_by_id(auction_id)

    async def end_auction(self, auction_id: str) -> Optional[AuctionModel]:
        """
        End an auction and determine the winner
        """
        if not ObjectId.is_valid(auction_id):
            return None
        
        # Get the auction
        auction = await self.get_by_id(auction_id)
        if not auction or auction.status != "active":
            return None
        
        # Set winner from current highest bidder
        winner = None
        if auction.currentBidder and auction.currentBid > 0:
            winner = {
                "userId": auction.currentBidder,
                "winningBid": auction.currentBid
            }
        
        # Update auction status to ended and set winner
        await self.collection.update_one(
            {"_id": ObjectId(auction_id)},
            {
                "$set": {
                    "status": "ended",
                    "winner": winner,
                    "updatedAt": datetime.now()
                }
            }
        )
        
        return await self.get_by_id(auction_id)

    async def cancel_auction(self, auction_id: str) -> Optional[AuctionModel]:
        """
        Cancel an auction
        """
        if not ObjectId.is_valid(auction_id):
            return None
        
        # Get the auction to check if it exists
        auction = await self.get_by_id(auction_id)
        if not auction:
            return None
        
        # Update auction status to cancelled
        await self.collection.update_one(
            {"_id": ObjectId(auction_id)},
            {
                "$set": {
                    "status": "cancelled",
                    "updatedAt": datetime.now()
                }
            }
        )
        
        return await self.get_by_id(auction_id)

    async def get_all_with_filters(
        self, 
        filter_params: AuctionFilter,
        pagination: PaginationParams
    ) -> Tuple[List[AuctionModel], int]:
        """
        Get all auctions with filters and pagination
        """
        # Build the filter query
        query = {}
        
        if filter_params.guildId:
            query["guildId"] = filter_params.guildId
            
        if filter_params.status:
            query["status"] = filter_params.status
            
        if filter_params.chain:
            query["chain"] = filter_params.chain
            
        if filter_params.created_after:
            query["createdAt"] = query.get("createdAt", {})
            query["createdAt"]["$gte"] = filter_params.created_after
            
        if filter_params.created_before:
            query["createdAt"] = query.get("createdAt", {})
            query["createdAt"]["$lte"] = filter_params.created_before
            
        if filter_params.has_bids is not None:
            if filter_params.has_bids:
                query["bidders"] = {"$exists": True, "$not": {"$size": 0}}
            else:
                query["bidders"] = {"$exists": True, "$size": 0}
                
        if filter_params.min_bid is not None:
            query["currentBid"] = query.get("currentBid", {})
            query["currentBid"]["$gte"] = filter_params.min_bid
            
        if filter_params.max_bid is not None:
            query["currentBid"] = query.get("currentBid", {})
            query["currentBid"]["$lte"] = filter_params.max_bid
            
        if filter_params.bidder_id:
            query["bidders.userId"] = filter_params.bidder_id
        
        # Count total documents matching the query
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        auctions = []
        async for auction_doc in cursor:
            auctions.append(AuctionModel(**auction_doc))
        
        return auctions, total

    async def search(self, query_string: str, pagination: PaginationParams) -> Tuple[List[AuctionModel], int]:
        """
        Search auctions by a general query string
        """
        # Building a search query across multiple fields
        query = {
            "$or": [
                {"name": {"$regex": query_string, "$options": "i"}},
                {"description": {"$regex": query_string, "$options": "i"}},
                {"chain": {"$regex": query_string, "$options": "i"}},
                {"guildId": {"$regex": query_string, "$options": "i"}},
            ]
        }
        
        # Count total matches
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        auctions = []
        async for auction_doc in cursor:
            auctions.append(AuctionModel(**auction_doc))
        
        return auctions, total
    
    async def get_auction_analytics(self) -> AuctionAnalytics:
        """
        Get analytics for all auctions
        """
        # Count total auctions
        total_auctions = await self.collection.count_documents({})
        
        # Count auctions by status
        active_auctions = await self.collection.count_documents({"status": "active"})
        ended_auctions = await self.collection.count_documents({"status": "ended"})
        cancelled_auctions = await self.collection.count_documents({"status": "cancelled"})
        
        # Aggregate auctions by guild
        guild_pipeline = [
            {"$group": {"_id": "$guildId", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        guild_results = await self.collection.aggregate(guild_pipeline).to_list(length=None)
        auctions_by_guild = {item["_id"]: item["count"] for item in guild_results}
        
        # Aggregate auctions by chain
        chain_pipeline = [
            {"$group": {"_id": "$chain", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        chain_results = await self.collection.aggregate(chain_pipeline).to_list(length=None)
        auctions_by_chain = {item["_id"]: item["count"] for item in chain_results}
        
        # Calculate total bids across all auctions
        bids_pipeline = [
            {"$unwind": {"path": "$bidders", "preserveNullAndEmptyArrays": False}},
            {"$group": {"_id": None, "totalBids": {"$sum": 1}, "totalValue": {"$sum": "$bidders.bidAmount"}}}
        ]
        bids_result = await self.collection.aggregate(bids_pipeline).to_list(length=None)
        total_bids = bids_result[0]["totalBids"] if bids_result else 0
        total_bid_value = bids_result[0]["totalValue"] if bids_result else 0
        
        # Calculate average bids per auction
        avg_bids = total_bids / total_auctions if total_auctions > 0 else 0
        
        # Get top auctions by number of bids
        top_auctions_pipeline = [
            {"$addFields": {"bidCount": {"$size": {"$ifNull": ["$bidders", []]}}}},
            {"$sort": {"bidCount": -1, "currentBid": -1}},
            {"$limit": 5},
            {"$project": {
                "_id": 1,
                "name": 1,
                "bidCount": 1,
                "currentBid": 1
            }}
        ]
        top_auctions_result = await self.collection.aggregate(top_auctions_pipeline).to_list(length=None)
        
        top_auctions = []
        for auction in top_auctions_result:
            top_auctions.append(AuctionStatistics(
                auction_id=str(auction["_id"]),
                name=auction["name"],
                total_bids=auction["bidCount"],
                current_bid=auction["currentBid"]
            ))
        
        return AuctionAnalytics(
            total_auctions=total_auctions,
            active_auctions=active_auctions,
            ended_auctions=ended_auctions,
            cancelled_auctions=cancelled_auctions,
            total_bids=total_bids,
            total_bid_value=total_bid_value,
            auctions_by_guild=auctions_by_guild,
            top_auctions=top_auctions,
            auctions_by_chain=auctions_by_chain,
            avg_bids_per_auction=avg_bids
        )