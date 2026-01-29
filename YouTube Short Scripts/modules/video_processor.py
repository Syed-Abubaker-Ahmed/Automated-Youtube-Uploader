"""
Video Processing Module
Formats videos for different platforms and adds captions/music/voiceover
"""

import os
import logging
from pathlib import Path
import json
from datetime import datetime

try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip
    from moviepy.audio.AudioFileClip import AudioFileClip
except ImportError:
    logging.warning("MoviePy not installed. Video processing will be limited.")

import config
from voiceover_generator import VoiceoverGenerator, VoiceoverMixer

logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self):
        self.config = config
        self.voiceover_gen = VoiceoverGenerator()
        self.voiceover_mixer = VoiceoverMixer()
        
    def process(self, input_video: str, platform: str = 'youtube', prompt: str = None, add_voiceover: bool = True) -> str:
        """
        Process video for specific platform
        
        Args:
            input_video: Path to raw video
            platform: 'youtube', 'tiktok', or 'instagram'
            prompt: Video prompt for voiceover narration
            add_voiceover: Whether to add AI voiceover
        
        Returns:
            Path to processed video
        """
        try:
            logger.info(f"Processing video for {platform}: {input_video}")
            
            # Load video
            clip = VideoFileClip(input_video)
            
            # Resize to platform specifications
            clip = self._resize_for_platform(clip, platform)
            
            # Add text overlay
            if config.ADD_TEXT_OVERLAY:
                clip = self._add_captions(clip)
            
            # Add voiceover (AI narration)
            if add_voiceover and prompt:
                clip = self._add_voiceover(clip, input_video, prompt)
            
            # Add background music
            if config.ADD_MUSIC and not add_voiceover:  # Skip if voiceover was added
                clip = self._add_background_music(clip)
            
            # Export
            output_path = self._get_output_path(input_video, platform)
            self._export_video(clip, output_path)
            
            clip.close()
            logger.info(f"✅ Video processed: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            raise
    
    def _resize_for_platform(self, clip, platform: str):
        """Resize video to platform specifications"""
        if platform == 'youtube':
            target_size = config.YOUTUBE_SIZE
        elif platform == 'tiktok':
            target_size = config.TIKTOK_SIZE
        elif platform == 'instagram':
            target_size = config.INSTAGRAM_SIZE
        else:
            return clip
        
        logger.info(f"Resizing to {target_size} for {platform}")
        
        # Calculate aspect ratio
        target_width, target_height = target_size
        target_ratio = target_width / target_height
        
        clip_ratio = clip.w / clip.h
        
        if clip_ratio > target_ratio:
            # Clip is wider, crop width
            new_width = int(clip.h * target_ratio)
            offset = (clip.w - new_width) // 2
            clip = clip.crop(x1=offset, y1=0, x2=offset + new_width, y2=clip.h)
        else:
            # Clip is taller, add padding
            new_height = int(clip.w / target_ratio)
            offset = (new_height - clip.h) // 2
            # In real implementation, use CompositeVideoClip to add padding
        
        clip = clip.resize(width=target_width)
        return clip
    
    def _add_captions(self, clip):
        """Add captions/text overlay to video"""
        try:
            logger.info("Adding captions to video")
            
            # Example: Add "Made with AI" text
            txt_clip = TextClip(
                "🤖 AI Generated",
                fontsize=40,
                color='white',
                method='caption',
                size=(clip.w - 40, None),
                font='Arial'
            ).set_duration(clip.duration).set_position(('center', 'bottom'))
            
            # Composite the text on the video
            final_clip = CompositeVideoClip([clip, txt_clip.set_opacity(0.8)])
            final_clip = final_clip.set_duration(clip.duration)
            
            return final_clip
            
        except Exception as e:
            logger.warning(f"Could not add captions: {e}. Continuing without captions.")
            return clip
    
    def _add_voiceover(self, clip, video_path: str, prompt: str):
        """Add AI voiceover narration to video"""
        try:
            logger.info(f"Adding AI voiceover for prompt: {prompt[:50]}...")
            
            # Generate voiceover from prompt
            voiceover_path = self.voiceover_gen.generate_prompt_voiceover(prompt)
            
            if not voiceover_path or not os.path.exists(voiceover_path):
                logger.warning("Voiceover generation failed. Continuing without voiceover.")
                return clip
            
            # Get audio duration to match video length
            audio_duration = self.voiceover_mixer.get_voiceover_duration(voiceover_path) or clip.duration
            
            # If audio is shorter than video, add background music
            music_path = None
            if config.ADD_MUSIC:
                music_dir = Path("assets/music")
                if music_dir.exists():
                    music_files = list(music_dir.glob("*.mp3"))
                    if music_files:
                        music_path = str(music_files[0])
            
            # Create output path for temp video with voiceover
            temp_output = video_path.replace('.mp4', '_with_voiceover.mp4')
            
            # Mix voiceover with video (and optional background music)
            success = self.voiceover_mixer.add_voiceover_to_video(
                video_path=video_path,
                voiceover_path=voiceover_path,
                output_path=temp_output,
                music_path=music_path
            )
            
            if success and os.path.exists(temp_output):
                # Reload the video with voiceover
                new_clip = VideoFileClip(temp_output)
                logger.info("✅ Voiceover successfully added")
                return new_clip
            else:
                logger.warning("Voiceover mixing failed. Using original video.")
                return clip
                
        except Exception as e:
            logger.error(f"Error adding voiceover: {e}")
            return clip

    
    def _add_background_music(self, clip):
        """Add royalty-free background music"""
        try:
            logger.info("Adding background music")
            
            # For free royalty-free music, you can:
            # 1. Download from Pixabay or Pexels (requires manual download)
            # 2. Use YouTube Audio Library (requires authentication)
            # 3. Generate with free tools
            
            music_dir = Path("assets/music")
            if music_dir.exists():
                music_files = list(music_dir.glob("*.mp3"))
                if music_files:
                    music_path = str(music_files[0])
                    audio = AudioFileClip(music_path)
                    
                    # Loop music if it's shorter than video
                    if audio.duration < clip.duration:
                        loops = int(clip.duration / audio.duration) + 1
                        audio_list = [audio] * loops
                        audio = concatenate_videoclips(audio_list)
                    
                    # Trim to video length
                    audio = audio.subclipped(0, clip.duration)
                    
                    # Reduce volume
                    audio = audio.volumex(config.MUSIC_VOLUME)
                    
                    # Composite audio
                    final_clip = clip.set_audio(audio)
                    return final_clip
            
            logger.warning("No music files found in assets/music/")
            return clip
            
        except Exception as e:
            logger.warning(f"Could not add music: {e}")
            return clip
    
    def _export_video(self, clip, output_path: str):
        """Export video with optimization for platform"""
        logger.info(f"Exporting video to {output_path}")
        
        # High quality settings for social media
        clip.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            fps=30,
            verbose=False,
            logger=None
        )
    
    def _get_output_path(self, input_path: str, platform: str) -> str:
        """Generate output filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{platform}_{timestamp}.mp4"
        return os.path.join(config.PROCESSED_DIR, filename)


class MetadataGenerator:
    """Generate platform-specific metadata (titles, descriptions, hashtags)"""
    
    def __init__(self):
        self.config = config
    
    def generate_metadata(self, prompt: str, platform: str) -> dict:
        """Generate metadata for a platform"""
        platform_config = config.PLATFORMS.get(platform, {})
        
        return {
            'title': platform_config.get('title_template', '').format(prompt=prompt),
            'description': platform_config.get('description_template', '').format(prompt=prompt),
            'caption': platform_config.get('caption_template', '').format(prompt=prompt),
            'hashtags': platform_config.get('hashtags', ''),
            'tags': platform_config.get('tags', [])
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test processing
    processor = VideoProcessor()
    print("Video processor ready. Configure video files to test.")
