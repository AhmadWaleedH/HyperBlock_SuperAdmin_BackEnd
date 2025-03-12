from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId

from ...models.payment import Payment

class PaymentRepository:
    def __init__(self, database: AsyncIOMotorDatabase):
        self.database = database
        self.collection = database.payments

    async def create(self, payment_data: Dict[str, Any]) -> Payment:
        """Create a new payment record"""
        payment_data["createdAt"] = datetime.now()
        payment_data["updatedAt"] = datetime.now()
        
        result = await self.collection.insert_one(payment_data)
        payment_data["_id"] = result.inserted_id
        
        return Payment(**payment_data)

    async def get_by_id(self, payment_id: str) -> Optional[Payment]:
        """Get a payment by ID"""
        if not ObjectId.is_valid(payment_id):
            return None
            
        payment = await self.collection.find_one({"_id": ObjectId(payment_id)})
        if payment:
            return Payment(**payment)
        return None

    async def get_by_session_id(self, session_id: str) -> Optional[Payment]:
        """Get a payment by Cybersource session ID"""
        payment = await self.collection.find_one({"session_id": session_id})
        if payment:
            return Payment(**payment)
        return None

    async def get_by_transaction_id(self, transaction_id: str) -> Optional[Payment]:
        """Get a payment by transaction ID"""
        payment = await self.collection.find_one({"transaction_id": transaction_id})
        if payment:
            return Payment(**payment)
        return None

    async def update_status(self, payment_id: str, status: str, metadata: Dict[str, Any] = None) -> Optional[Payment]:
        """Update a payment status"""
        if not ObjectId.is_valid(payment_id):
            return None
            
        update_data = {
            "status": status,
            "updatedAt": datetime.now()
        }
        
        if metadata:
            update_data["metadata"] = metadata
            
        await self.collection.update_one(
            {"_id": ObjectId(payment_id)},
            {"$set": update_data}
        )
            
        return await self.get_by_id(payment_id)

    async def get_by_subscription_id(self, subscription_id: str) -> List[Payment]:
        """Get all payments for a subscription"""
        if not ObjectId.is_valid(subscription_id):
            return []
            
        cursor = self.collection.find({"subscription_id": ObjectId(subscription_id)})
        payments = []
        async for doc in cursor:
            payments.append(Payment(**doc))
        return payments