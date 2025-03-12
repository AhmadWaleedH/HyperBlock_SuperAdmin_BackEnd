from motor.motor_asyncio import AsyncIOMotorDatabase

async def init_subscription_tiers(db: AsyncIOMotorDatabase):
    """
    Initialize default subscription tiers if they don't exist
    """
    # Check if tiers already exist
    count = await db.subscription_tiers.count_documents({})
    if count > 0:
        print("Subscription tiers already exist, skipping initialization")
        return
    
    # Define default tiers
    default_tiers = [
        {
            "name": "Basic",
            "description": "Basic subscription with essential features",
            "price_monthly": 9.99,
            "price_yearly": 99.99,
            "features": [
                "Guild management",
                "Basic analytics",
                "Standard support"
            ]
        },
        {
            "name": "Premium",
            "description": "Premium subscription with advanced features",
            "price_monthly": 19.99,
            "price_yearly": 199.99,
            "features": [
                "All Basic features",
                "Advanced analytics",
                "Priority support",
                "Custom branding"
            ]
        },
        {
            "name": "Enterprise",
            "description": "Enterprise subscription with all features",
            "price_monthly": 49.99,
            "price_yearly": 499.99,
            "features": [
                "All Premium features",
                "White-label solution",
                "Dedicated account manager",
                "API access",
                "Custom integrations"
            ]
        }
    ]
    
    # Insert tiers
    await db.subscription_tiers.insert_many(default_tiers)
    print(f"Initialized {len(default_tiers)} subscription tiers")