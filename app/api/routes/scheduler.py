"""
Endpoints for testing the scheduler
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
import logging
from app.services.analytics_service import calculate_guild_analytics
from app.scheduler.jobs.analytics_jobs import update_guild_analytics
from app.scheduler import scheduler as app_scheduler

router = APIRouter()

logger = logging.getLogger(__name__)

@router.get("/status")
async def get_scheduler_status():
    """Get current scheduler status"""
    # Get scheduler jobs
    try:
        return app_scheduler.get_status()  # Use the get_status method we implemented
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting scheduler status: {str(e)}")

@router.post("/run-analytics")
async def run_analytics_job():
    """Run full analytics calculation immediately"""
    try:
        # Run the calculation synchronously via the job
        update_guild_analytics()
        return {"status": "success", "message": "Guild analytics calculation triggered"}
    except Exception as e:
        logger.error(f"Error running analytics job: {e}")
        raise HTTPException(status_code=500, detail=f"Error running analytics: {str(e)}")

@router.post("/run-async-analytics")
async def run_async_analytics():
    """Run analytics calculation asynchronously"""
    try:
        # Run the calculation asynchronously
        updated_count = await calculate_guild_analytics()
        return {
            "status": "success", 
            "message": f"Guild analytics calculation completed. Updated {updated_count} guilds."
        }
    except Exception as e:
        logger.error(f"Error running analytics asynchronously: {e}")
        raise HTTPException(status_code=500, detail=f"Error running analytics: {str(e)}")

@router.post("/trigger-job/{job_id}")
async def trigger_scheduled_job(job_id: str, background_tasks: BackgroundTasks):
    """
    Trigger a specific scheduled job by its ID
    """
    try:
        # Find the job with the specified ID
        job = next((job for job in app_scheduler.scheduler.get_jobs() if job.id == job_id), None)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job with ID '{job_id}' not found")
        
        # Run the job in the background
        background_tasks.add_task(job.func)
        
        return {
            "status": "success",
            "message": f"Job '{job_id}' ({job.func.__name__}) triggered"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error triggering job: {str(e)}")