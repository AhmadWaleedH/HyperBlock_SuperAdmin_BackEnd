"""
Scheduled jobs for analytics calculations
"""
import logging
import asyncio
from app.services.analytics_service import calculate_guild_analytics
from app.db.database import connect_to_mongo, close_mongo_connection

logger = logging.getLogger(__name__)

def update_guild_analytics():
    """
    Job to update analytics metrics for all guilds
    This is a synchronous wrapper for the async function
    Handles database connection within the job
    """
    logger.info("Starting scheduled guild analytics update job")
    
    try:
        # Create new event loop for each job run
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Define async function that handles DB connection
        async def run_with_connection():
            try:
                # Establish database connection
                logger.info("Connecting to MongoDB")
                await connect_to_mongo()
                
                # Run analytics calculation
                logger.info("Running guild analytics calculation")
                updated_count = await calculate_guild_analytics()
                logger.info(f"Successfully updated analytics for {updated_count} guilds")
                
                return updated_count
            finally:
                # Always close the connection
                logger.info("Closing MongoDB connection")
                await close_mongo_connection()
        
        # Run the async function
        updated_count = loop.run_until_complete(run_with_connection())
        
        # Close the loop when done
        loop.close()
        
    except Exception as e:
        logger.error(f"Error in scheduled guild analytics update job: {e}")
        # Log the full stack trace for easier debugging
        import traceback
        logger.error(traceback.format_exc())