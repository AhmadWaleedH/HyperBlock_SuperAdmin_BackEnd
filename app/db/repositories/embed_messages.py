from typing import List, Dict, Any, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from datetime import datetime
from bson import ObjectId

from ...models.embed_message import (
    EmbedMessageModel, EmbedMessageCreate, EmbedMessageUpdate, 
    EmbedMessageFilter, EmbedMessageAnalytics
)
from ...models.user import PaginationParams

class EmbedMessageRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.collection = database.embedmessages

    async def create(self, embed_message: EmbedMessageCreate) -> EmbedMessageModel:
        """
        Create a new embed message in the database
        """
        embed_data = embed_message.dict()
        embed_data["createdAt"] = datetime.now()
        embed_data["updatedAt"] = datetime.now()
        
        result = await self.collection.insert_one(embed_data)
        embed_data["_id"] = result.inserted_id
        
        return EmbedMessageModel(**embed_data)

    async def get_by_id(self, embed_id: str) -> Optional[EmbedMessageModel]:
        """
        Get an embed message by MongoDB ID
        """
        if not ObjectId.is_valid(embed_id):
            return None
            
        embed = await self.collection.find_one({"_id": ObjectId(embed_id)})
        if embed:
            return EmbedMessageModel(**embed)
        return None
    # async def get_by_id(self, embed_id: str) -> Optional[EmbedMessageModel]:
    #     """
    #     Get an embed message by MongoDB ID with related item and guild names
    #     """
    #     if not ObjectId.is_valid(embed_id):
    #         return None
            
    #     # Use aggregation pipeline to join with items and guilds collections
    #     pipeline = [
    #         # Match the specific embed
    #         {"$match": {"_id": ObjectId(embed_id)}},
            
    #         # Lookup item details
    #         {"$lookup": {
    #             "from": "shop_items",  # Name of the items collection
    #             "let": {"item_id": {"$toObjectId": "$itemId"}},
    #             "pipeline": [
    #                 {"$match": {"$expr": {"$eq": ["$_id", "$$item_id"]}}},
    #                 {"$project": {"name": 1}}
    #             ],
    #             "as": "item_details"
    #         }},
            
    #         # Lookup guild details
    #         {"$lookup": {
    #             "from": "guilds",  # Name of the guilds collection
    #             "let": {"guild_discord_id": "$guildId"},
    #             "pipeline": [
    #                 {"$match": {"$expr": {"$eq": ["$guildId", "$$guild_discord_id"]}}},
    #                 {"$project": {"guildName": 1}}
    #             ],
    #             "as": "guild_details"
    #         }},
            
    #         # Add fields for item name and guild name
    #         {"$addFields": {
    #             "itemName": {"$arrayElemAt": ["$item_details.name", 0]},
    #             "guildName": {"$arrayElemAt": ["$guild_details.guildName", 0]}
    #         }},
            
    #         # Remove the lookup arrays from final result
    #         {"$project": {
    #             "item_details": 0,
    #             "guild_details": 0
    #         }}
    #     ]
    
    #     # Execute the aggregation pipeline
    #     results = await self.collection.aggregate(pipeline).to_list(length=1)
        
    #     if not results:
    #         return None
            
    #     # Return the first (and should be only) result
    #     return EmbedMessageModel(**results[0])

    async def get_by_message_id(self, message_id: str) -> Optional[EmbedMessageModel]:
        """
        Get an embed message by Discord message ID
        """
        embed = await self.collection.find_one({"messageId": message_id})
        if embed:
            return EmbedMessageModel(**embed)
        return None

    async def get_by_item_id(self, item_id: str, pagination: PaginationParams) -> Tuple[List[EmbedMessageModel], int]:
        """
        Get embed messages by item ID
        """
        query = {"itemId": item_id}
        
        # Count total matches
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        embeds = []
        async for embed_doc in cursor:
            embeds.append(EmbedMessageModel(**embed_doc))
        
        return embeds, total

    async def get_by_guild_id(self, guild_id: str, pagination: PaginationParams) -> Tuple[List[EmbedMessageModel], int]:
        """
        Get embed messages by guild ID
        """
        query = {"guildId": guild_id}
        
        # Count total matches
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        embeds = []
        async for embed_doc in cursor:
            embeds.append(EmbedMessageModel(**embed_doc))
        
        return embeds, total

    async def update(self, embed_id: str, embed_update: EmbedMessageUpdate) -> Optional[EmbedMessageModel]:
        """
        Update an embed message
        """
        if not ObjectId.is_valid(embed_id):
            return None
            
        update_data = embed_update.dict(exclude_unset=True)
        if update_data:
            update_data["updatedAt"] = datetime.now()
            
            await self.collection.update_one(
                {"_id": ObjectId(embed_id)},
                {"$set": update_data}
            )
            
        return await self.get_by_id(embed_id)

    async def delete(self, embed_id: str) -> bool:
        """
        Delete an embed message
        """
        if not ObjectId.is_valid(embed_id):
            return False
            
        result = await self.collection.delete_one({"_id": ObjectId(embed_id)})
        return result.deleted_count > 0

    async def delete_by_message_id(self, message_id: str) -> bool:
        """
        Delete an embed message by Discord message ID
        """
        result = await self.collection.delete_one({"messageId": message_id})
        return result.deleted_count > 0

    async def get_all_with_filters(
        self, 
        filter_params: EmbedMessageFilter,
        pagination: PaginationParams
    ) -> Tuple[List[EmbedMessageModel], int]:
        """
        Get all embed messages with filters and pagination
        """
        # Build the filter query
        query = {}
        
        if filter_params.guildId:
            query["guildId"] = filter_params.guildId
            
        if filter_params.channelId:
            query["channelId"] = filter_params.channelId
            
        if filter_params.itemId:
            query["itemId"] = filter_params.itemId
        
        # Count total documents matching the query
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        cursor = self.collection.find(query).skip(pagination.skip).limit(pagination.limit)
        
        # Process results
        embeds = []
        async for embed_doc in cursor:
            embeds.append(EmbedMessageModel(**embed_doc))
        
        return embeds, total

    async def get_analytics(self) -> EmbedMessageAnalytics:
        """
        Get analytics for embed messages
        """
        # Count total embeds
        total_embeds = await self.collection.count_documents({})
        
        # Group embeds by guild
        guild_pipeline = [
            {"$group": {"_id": "$guildId", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        guild_results = await self.collection.aggregate(guild_pipeline).to_list(length=None)
        embeds_by_guild = {item["_id"]: item["count"] for item in guild_results}
        
        # Group embeds by channel
        channel_pipeline = [
            {"$group": {"_id": "$channelId", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        channel_results = await self.collection.aggregate(channel_pipeline).to_list(length=None)
        embeds_by_channel = {item["_id"]: item["count"] for item in channel_results}
        
        return EmbedMessageAnalytics(
            total_embeds=total_embeds,
            embeds_by_guild=embeds_by_guild,
            embeds_by_channel=embeds_by_channel
        )