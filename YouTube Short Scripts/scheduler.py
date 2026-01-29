"""
Scheduler for automated daily uploads
Runs the workflow at specified times
"""

import schedule
import time
import logging
from datetime import datetime
from main import VideoWorkflow
import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VideoScheduler:
    def __init__(self):
        self.workflow = VideoWorkflow()
    
    def job(self):
        """Job to run at scheduled time"""
        logger.info(f"\n🎬 Scheduled job started at {datetime.now()}")
        try:
            self.workflow.run(num_videos=config.VIDEOS_PER_RUN)
        except Exception as e:
            logger.error(f"Scheduled job failed: {e}")
    
    def start(self):
        """Start scheduler"""
        logger.info("🚀 Video Scheduler Started")
        logger.info(f"Scheduled time: {config.SCHEDULE_TIME}")
        logger.info(f"Videos per run: {config.VIDEOS_PER_RUN}")
        
        # Schedule daily job
        schedule.every().day.at(config.SCHEDULE_TIME).do(self.job)
        
        # Optional: Run immediately on startup
        if config.RUN_ON_STARTUP:
            logger.info("Running job immediately on startup...")
            self.job()
        
        # Keep scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


if __name__ == "__main__":
    try:
        scheduler = VideoScheduler()
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("\n⏹️ Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
