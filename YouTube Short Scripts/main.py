"""
Main orchestration script
Generates, processes, and uploads videos to 5 YouTube accounts
"""

import logging
import sys
import json
from datetime import datetime
from pathlib import Path

# Import custom modules
from modules.video_generator import VideoGenerator
from modules.video_processor import VideoProcessor, MetadataGenerator
from modules.prompt_manager import SmartPromptManager
from modules.uploaders.youtube_multi_account import MultiAccountYouTubeUploader
import config

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(config.LOGS_DIR) / 'main.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class VideoWorkflow:
    def __init__(self):
        self.generator = VideoGenerator()
        self.processor = VideoProcessor()
        self.metadata_gen = MetadataGenerator()
        self.prompt_manager = SmartPromptManager()
        self.youtube_uploader = MultiAccountYouTubeUploader(
            stagger_delay=config.UPLOAD_STAGGER_DELAY
        )
        self.upload_log = []
    
    def run(self, num_videos: int = 1):
        """
        Run complete workflow
        
        Args:
            num_videos: Number of videos to generate and upload
        """
        logger.info(f"Starting workflow: generating {num_videos} video(s) for 5 YouTube accounts")
        logger.info(f"Stagger delay between uploads: {config.UPLOAD_STAGGER_DELAY} seconds")
        
        generated_videos = []
        
        for i in range(num_videos):
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"Video {i+1}/{num_videos}")
                logger.info(f"{'='*60}")
                
                video_path = self._generate_single_video()
                if video_path:
                    generated_videos.append(video_path)
                
            except Exception as e:
                logger.error(f"Error generating video {i+1}: {e}")
                continue
        
        # Upload all generated videos to 5 accounts with staggered timing
        if generated_videos:
            logger.info(f"\n{'='*60}")
            logger.info(f"Uploading {len(generated_videos)} video(s) to 5 YouTube accounts")
            logger.info(f"{'='*60}")
            self._upload_to_all_accounts(generated_videos)
        
        # Print summary
        self._print_summary()
    
    def _generate_single_video(self) -> str:
        """Generate a single video with voiceover"""
        
        # 1. Get unique prompt
        logger.info("\n[1/3] Generating unique prompt...")
        prompt = self.prompt_manager.get_next_prompt(refresh_trends=False)
        logger.info(f"Prompt: {prompt}")
        
        try:
            # 2. Generate video with AI
            logger.info("\n[2/3] Creating AI video...")
            generated_video = self.generator.generate(prompt)
            self.prompt_manager.save_generated_prompt(prompt, platform="youtube")
            logger.info(f"✅ Video generated: {generated_video}")
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            logger.info("💡 Make sure your API key is valid in .env file")
            logger.info("💡 Check your FAL_API_KEY, RUNWAY_API_KEY, or REPLICATE_API_KEY")
            raise
        
        # 3. Process video (add voiceover, captions, etc.)
        logger.info("\n[3/3] Processing video with AI voiceover...")
        try:
            processed_video = self.processor.process(
                generated_video,
                platform='youtube',
                prompt=prompt,
                add_voiceover=config.ADD_VOICEOVER
            )
            logger.info(f"✅ Video processed: {processed_video}")
            return processed_video
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return None
    
    def _upload_to_all_accounts(self, video_paths: list):
        """Upload videos to 5 YouTube accounts with staggered timing"""
        
        if not video_paths:
            logger.warning("No videos to upload")
            return
        
        try:
            # Prepare metadata
            prompt = self.prompt_manager.get_status()['last_generated'] if hasattr(self.prompt_manager, 'get_status') else "AI Generated Pet Video"
            
            metadata = {
                'title': config.PLATFORMS['youtube']['title_template'].format(prompt=prompt or "Cute Pet Video"),
                'description': config.PLATFORMS['youtube']['description_template'].format(prompt=prompt or "AI-generated pet video"),
                'tags': config.PLATFORMS['youtube']['tags'],
                'privacy_status': 'PUBLIC'
            }
            
            # Upload videos to accounts with stagger
            results = self.youtube_uploader.upload_batch(
                video_paths,
                metadata,
                stagger=True,
                delay=config.UPLOAD_STAGGER_DELAY
            )
            
            # Log results
            for account_name, result in results.items():
                if result['status'] == 'success':
                    logger.info(f"✅ {account_name}: {result['video_id']}")
                    self.upload_log.append({
                        'account': account_name,
                        'video_id': result['video_id'],
                        'video_path': result['video_path'],
                        'timestamp': datetime.now().isoformat(),
                        'status': 'success'
                    })
                else:
                    logger.error(f"❌ {account_name}: Upload failed")
                    self.upload_log.append({
                        'account': account_name,
                        'video_path': result['video_path'],
                        'timestamp': datetime.now().isoformat(),
                        'status': 'failed'
                    })
        
        except Exception as e:
            logger.error(f"Failed to upload to accounts: {e}")
            raise
    
    def _log_result(self, prompt: str, videos: dict):
        """Log result to file"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'prompt': prompt,
            'videos': list(videos.keys()),
            'uploads': self.upload_log[-len(videos):]
        }
        
        log_file = Path(config.LOGS_DIR) / 'uploads.json'
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Could not log result: {e}")
    
    def _print_summary(self):
        """Print workflow summary"""
        logger.info(f"\n{'='*60}")
        logger.info("WORKFLOW SUMMARY")
        logger.info(f"{'='*60}")
        
        successful_uploads = len([log for log in self.upload_log if log.get('status') == 'success'])
        failed_uploads = len([log for log in self.upload_log if log.get('status') == 'failed'])
        
        logger.info(f"Total uploads: {len(self.upload_log)}")
        logger.info(f"✅ Successful: {successful_uploads}")
        logger.info(f"❌ Failed: {failed_uploads}")
        
        if self.upload_log:
            accounts = set(log['account'] for log in self.upload_log if 'account' in log)
            logger.info(f"YouTube Accounts Used: {', '.join(accounts)}")
        
        # Print prompt manager statistics
        status = self.prompt_manager.get_status()
        logger.info(f"\nPrompt History:")
        logger.info(f"  Total generated: {status['statistics']['total_generated']}")
        logger.info(f"  Unique prompts: {status['statistics']['unique_prompts']}")
        
        logger.info(f"\n📊 Multi-Account Distribution:")
        logger.info(f"  Stagger delay: {config.UPLOAD_STAGGER_DELAY} seconds")
        logger.info(f"  Accounts: 5 YouTube accounts")
        
        logger.info(f"\nLogs saved to: {config.LOGS_DIR}")
        logger.info("✅ Workflow completed!")


def main():
    """Entry point"""
    try:
        logger.info("🚀 AI Pet Video Generator & Uploader")
        logger.info(f"Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        workflow = VideoWorkflow()
        workflow.run(num_videos=config.VIDEOS_PER_RUN)
        
        logger.info("\n✅ All tasks completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        logger.error("\n⚠️ Troubleshooting tips:")
        logger.error("1. Check that all API keys are set in .env file")
        logger.error("2. Ensure you have internet connection")
        logger.error("3. Check platform API rate limits")
        logger.error("4. Review full logs in outputs/logs/main.log")
        return 1


if __name__ == "__main__":
    sys.exit(main())
