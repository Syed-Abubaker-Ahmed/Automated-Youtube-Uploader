"""
Continuous Video Scheduler
Runs in continuous mode - generates and uploads videos every 15 minutes
across 5 accounts in rotation, accumulating 10-minute compilations
"""

import schedule
import time
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path

from main import VideoWorkflow
from modules.video_compilation import VideoCompiler, ThumbnailGenerator, VideoTitleGenerator
import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(config.LOGS_DIR) / 'continuous_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ContinuousVideoScheduler:
    """
    Continuous mode scheduler
    - Generates a video immediately
    - Every 15 minutes, uploads to the next account in rotation
    - Accumulates videos until 10 minutes of content
    - When 10 minutes accumulated, creates compilation and uploads
    """
    
    def __init__(self):
        self.workflow = VideoWorkflow()
        self.compiler = VideoCompiler()
        self.thumbnail_gen = ThumbnailGenerator()
        self.title_gen = VideoTitleGenerator()
        
        self.current_account_index = 0
        self.num_accounts = 5
        self.upload_count = 0
        self.generation_count = 0
        self.last_upload_time = datetime.now()
        self.next_upload_time = datetime.now() + timedelta(minutes=config.UPLOAD_INTERVAL_MINUTES)
    
    def generate_and_queue(self):
        """Generate a single video and add to compilation queue"""
        logger.info(f"\n{'='*70}")
        logger.info(f"📹 Video Generation #{self.generation_count + 1}")
        logger.info(f"{'='*70}")
        
        try:
            video_path = self.workflow._generate_single_video()
            
            if video_path:
                self.generation_count += 1
                
                # Add to compilation queue
                result = self.compiler.add_video(video_path)
                
                if result.get('status') == 'queued':
                    logger.info(f"✅ Video queued for compilation")
                    logger.info(f"   Accumulated: {result['accumulated_duration']:.0f}s / {result['target_duration']:.0f}s")
                    
                    if result.get('is_ready'):
                        logger.info(f"🎥 Compilation ready! Creating 10-minute video...")
                        self._create_and_upload_compilation()
        
        except Exception as e:
            logger.error(f"❌ Video generation failed: {e}")
    
    def _create_and_upload_compilation(self):
        """Create compilation and upload to next account"""
        try:
            # Generate title
            title = self.title_gen.generate()
            
            # Create compilation
            compilation_path = self.compiler.create_compilation(title=title)
            
            if compilation_path:
                logger.info(f"🎬 Compilation created: {compilation_path}")
                
                # Generate thumbnail
                thumbnail_path = self.thumbnail_gen.generate_from_video(compilation_path, timestamp=5)
                if not thumbnail_path:
                    # Fallback to generated thumbnail
                    thumbnail_path = self.thumbnail_gen.generate_custom(title)
                
                # Upload to all 5 accounts with stagger
                logger.info(f"\n📤 Uploading to all 5 accounts (15 min intervals)...")
                
                metadata = {
                    'title': title,
                    'description': f"🐕 Cutest pets compilation! Watch amazing pet moments!\n\n#Pets #Dogs #Cats #Shorts #YouTubeShorts #Funny #Cute",
                    'tags': config.PLATFORMS['youtube']['tags'],
                    'privacy_status': 'PUBLIC',
                    'thumbnail_path': thumbnail_path
                }
                
                results = self.workflow.youtube_uploader.upload_batch(
                    [compilation_path],
                    metadata,
                    stagger=True,
                    delay=config.UPLOAD_STAGGER_DELAY
                )
                
                # Log results
                for account_name, result in results.items():
                    if result['status'] == 'success':
                        logger.info(f"✅ {account_name}: Video ID {result['video_id']}")
                        self.upload_count += 1
                    else:
                        logger.error(f"❌ {account_name}: Upload failed")
        
        except Exception as e:
            logger.error(f"Failed to create/upload compilation: {e}")
    
    def schedule_next_upload(self):
        """Schedule next upload in 15 minutes"""
        self.next_upload_time = datetime.now() + timedelta(minutes=config.UPLOAD_INTERVAL_MINUTES)
        logger.info(f"⏰ Next upload scheduled for: {self.next_upload_time.strftime('%H:%M:%S')}")
    
    def print_status(self):
        """Print current scheduler status"""
        logger.info(f"\n{'='*70}")
        logger.info("📊 SCHEDULER STATUS")
        logger.info(f"{'='*70}")
        logger.info(f"Total videos generated: {self.generation_count}")
        logger.info(f"Total compilations uploaded: {self.upload_count}")
        logger.info(f"Current accumulation: {self.compiler.pending_duration:.0f}s / {self.compiler.target_duration:.0f}s")
        logger.info(f"Videos in queue: {len(self.compiler.pending_videos)}")
        logger.info(f"Next upload: {self.next_upload_time.strftime('%H:%M:%S')}")
        logger.info(f"Upload interval: {config.UPLOAD_INTERVAL_MINUTES} minutes")
        logger.info(f"Account rotation: 5 accounts")
        logger.info(f"{'='*70}\n")
    
    def run(self):
        """Start continuous scheduler"""
        logger.info("🚀 Continuous Video Scheduler Started")
        logger.info(f"Mode: Continuous Upload (Every {config.UPLOAD_INTERVAL_MINUTES} minutes)")
        logger.info(f"Accumulation target: {config.TARGET_VIDEO_LENGTH_MINUTES} minutes")
        logger.info(f"Stagger delay: {config.UPLOAD_STAGGER_DELAY} seconds (15 minutes)")
        logger.info(f"Accounts: {self.num_accounts}")
        logger.info(f"Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Generate first video immediately
        if config.RUN_ON_STARTUP:
            logger.info("🎬 Running initial video generation...")
            self.generate_and_queue()
            self.schedule_next_upload()
        
        # Schedule generation every minute (check if it's time to upload)
        schedule.every(1).minutes.do(self.job)
        
        # Print status every 30 minutes
        schedule.every(30).minutes.do(self.print_status)
        
        # Keep scheduler running
        try:
            while True:
                schedule.run_pending()
                time.sleep(10)  # Check every 10 seconds
        
        except KeyboardInterrupt:
            logger.info("\n⏹️ Continuous scheduler stopped by user")
            self.print_status()
    
    def job(self):
        """Job that runs every minute to check if upload is due"""
        now = datetime.now()
        
        # Check if it's time to upload
        if now >= self.next_upload_time:
            logger.info(f"\n⏰ Time for next upload!")
            self.generate_and_queue()
            self.schedule_next_upload()
        
        # Also continuously generate to build up content
        else:
            # Optionally generate more videos in parallel (less frequently)
            if self.generation_count < (self.upload_count * 5) + 1:  # Generate ahead
                pass  # Uncomment to generate continuously without upload timing


if __name__ == "__main__":
    try:
        scheduler = ContinuousVideoScheduler()
        scheduler.run()
    except KeyboardInterrupt:
        logger.info("\n⏹️ Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
