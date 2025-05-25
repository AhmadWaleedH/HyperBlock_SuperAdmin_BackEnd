"""
Script to manually run guild analytics calculation
"""
import os
import sys
import asyncio
import logging
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import necessary modules
from app.services.analytics_service import calculate_guild_analytics
from app.db.database import connect_to_mongo, close_mongo_connection, get_database

async def run_analytics():
    """Run the full analytics calculation"""
    logger.info("Starting guild analytics calculation")
    
    # Connect to database
    logger.info("Connecting to MongoDB")
    await connect_to_mongo()
    
    try:
        # Run analytics calculation
        logger.info("Running analytics calculation")
        updated_count = await calculate_guild_analytics()
        logger.info(f"Analytics calculation completed. Updated {updated_count} guilds.")
        
        # Query and print updated guild to verify
        db = await get_database()
        guild = await db.guilds.find_one({"guildName": "HyperBot_Staging"})
        
        if guild and 'analytics' in guild:
            logger.info("Guild analytics after update:")
            logger.info(f"CAS: {guild['analytics'].get('CAS')}")
            logger.info(f"CHS: {guild['analytics'].get('CHS')}")
            logger.info(f"EAS: {guild['analytics'].get('EAS')}")
            logger.info(f"CCS: {guild['analytics'].get('CCS')}")
            logger.info(f"ERC: {guild['analytics'].get('ERC')}")
            logger.info(f"vault: {guild['analytics'].get('vault')}")
            logger.info(f"reservedPoints: {guild['analytics'].get('reservedPoints')}")
        else:
            logger.warning("Could not find guild analytics after update")
        
    except Exception as e:
        logger.error(f"Error running analytics: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Close database connection
        logger.info("Closing MongoDB connection")
        await close_mongo_connection()

if __name__ == "__main__":
    # Create a new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Run the analytics calculation
        loop.run_until_complete(run_analytics())
    finally:
        # Close the loop
        loop.close()