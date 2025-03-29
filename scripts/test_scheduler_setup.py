"""
Script to test scheduler setup and execution
"""
import os
import sys
import time
import logging
from datetime import datetime

from app.services.analytics_service import calculate_guild_analytics

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import scheduler modules
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

def main():
    """Run a test scheduler with simplified analytics job"""
    logger.info("Starting test scheduler")
    
    # Create scheduler
    scheduler = BackgroundScheduler()
    
    # Add job to run every 30 seconds for testing
    scheduler.add_job(
        calculate_guild_analytics,
        IntervalTrigger(seconds=30),
        id='test_simplified_analytics',
        replace_existing=True
    )
    
    # Start scheduler
    try:
        scheduler.start()
        logger.info("Scheduler started - analytics job will run every 30 seconds")
        logger.info("Press Ctrl+C to exit")
        
        # Keep script running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Stopping scheduler")
        scheduler.shutdown()
        logger.info("Scheduler stopped")
    except Exception as e:
        logger.error(f"Error in scheduler: {e}")
        import traceback
        logger.error(traceback.format_exc())
        scheduler.shutdown()

if __name__ == "__main__":
    main()