"""
Scheduler setup and configuration
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from app.scheduler.jobs.analytics_jobs import update_guild_analytics

logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self):
        # Configure the scheduler with SQLAlchemy job store for persistence
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
        }
        executors = {
            'default': ThreadPoolExecutor(20)
        }
        job_defaults = {
            'coalesce': True,
            'max_instances': 1
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults
        )
        
    def start(self):
        """Start the scheduler and add jobs"""
        try:
            # Update guild analytics every 6 hours
            # self.scheduler.add_job(
            #     update_guild_analytics,
            #     'interval',
            #     hours=6,
            #     id='update_guild_analytics',
            #     replace_existing=True
            # )
            
            # # Also run analytics update daily at midnight
            self.scheduler.add_job(
                update_guild_analytics,
                'cron',
                hour=0,
                minute=0,
                id='daily_guild_analytics',
                replace_existing=True
            )

            # self.scheduler.add_job(
            #     update_guild_analytics,
            #     'interval',
            #     minutes=2,
            #     id='update_guild_analytics',
            #     replace_existing=True
            # )
            
            # Start the scheduler
            self.scheduler.start()
            logger.info("Scheduler started successfully")
            
            # Log the next run times
            for job in self.scheduler.get_jobs():
                logger.info(f"Job {job.id} next run at: {job.next_run_time}")
                
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
    def shutdown(self):
        """Shutdown the scheduler"""
        if hasattr(self, 'scheduler') and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shut down")
            
    def get_status(self):
        """Get scheduler status and list of all scheduled jobs"""
        if not hasattr(self, 'scheduler') or not self.scheduler:
            return {'status': 'not_initialized', 'jobs': []}
            
        running = self.scheduler.running
        jobs = []
        
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.func.__name__,
                'next_run': str(job.next_run_time),
                'trigger': str(job.trigger)
            })
            
        return {
            'status': 'running' if running else 'stopped',
            'jobs': jobs
        }