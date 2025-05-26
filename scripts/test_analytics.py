"""
Script to test the analytics calculations directly
"""
import os
import sys
import asyncio
import logging
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging to see detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import necessary modules
from app.services.analytics_service import calculate_guild_analytics
from app.db.database import connect_to_mongo, close_mongo_connection

async def run_test():
    """Run the analytics calculation directly"""
    logger.info("Starting analytics test")
    
    # Connect to database
    logger.info("Connecting to MongoDB")
    await connect_to_mongo()
    
    try:
        # Run analytics calculation
        logger.info("Running analytics calculation")
        updated_count = await calculate_guild_analytics()
        logger.info(f"Analytics calculation completed. Updated {updated_count} guilds.")
        
        # You can add code here to query and print the updated guild data
        
    except Exception as e:
        logger.error(f"Error running analytics: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        # Close database connection
        logger.info("Closing MongoDB connection")
        await close_mongo_connection()

if __name__ == "__main__":
    # Run the test
    asyncio.run(run_test())