"""
Video Compilation Module
Handles concatenating short videos into longer compilations (10 minutes)
and generates thumbnails and titles automatically
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import json

try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips, TextClip, CompositeVideoClip
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    logging.warning("MoviePy or PIL not installed. Compilation features will be limited.")

import config

logger = logging.getLogger(__name__)


class VideoCompiler:
    """Compile multiple short videos into one long video"""
    
    def __init__(self):
        self.pending_videos = []
        self.pending_duration = 0
        self.target_duration = config.TARGET_VIDEO_LENGTH_MINUTES * 60  # Convert to seconds
        self.compilation_dir = Path(config.PROCESSED_DIR) / 'compilations'
        self.compilation_dir.mkdir(parents=True, exist_ok=True)
    
    def add_video(self, video_path: str) -> Dict:
        """
        Add video to compilation queue
        
        Args:
            video_path: Path to video file
        
        Returns:
            Dict with status and accumulated duration
        """
        try:
            clip = VideoFileClip(video_path)
            duration = clip.duration
            clip.close()
            
            self.pending_videos.append(video_path)
            self.pending_duration += duration
            
            logger.info(f"Added video to compilation queue: {video_path} ({duration:.1f}s)")
            logger.info(f"Total accumulated duration: {self.pending_duration:.1f}s / {self.target_duration:.1f}s")
            
            return {
                'status': 'queued',
                'accumulated_duration': self.pending_duration,
                'target_duration': self.target_duration,
                'is_ready': self.pending_duration >= self.target_duration
            }
        
        except Exception as e:
            logger.error(f"Error adding video to compilation: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def is_compilation_ready(self) -> bool:
        """Check if enough content for compilation"""
        return self.pending_duration >= self.target_duration
    
    def create_compilation(self, title: str = None, prompt: str = None) -> Optional[str]:
        """
        Create compilation video from pending videos
        
        Args:
            title: Custom title for compilation
            prompt: Video prompt for metadata
        
        Returns:
            Path to compiled video or None
        """
        if not self.pending_videos:
            logger.warning("No videos to compile")
            return None
        
        if not self.is_compilation_ready():
            logger.warning(f"Not enough content yet. Have {self.pending_duration:.1f}s, need {self.target_duration:.1f}s")
            return None
        
        try:
            logger.info(f"Creating compilation from {len(self.pending_videos)} videos...")
            
            # Load video clips
            clips = []
            total_duration = 0
            
            for video_path in self.pending_videos:
                try:
                    clip = VideoFileClip(video_path)
                    clips.append(clip)
                    total_duration += clip.duration
                    logger.info(f"  - Added {video_path} ({clip.duration:.1f}s)")
                except Exception as e:
                    logger.error(f"  - Failed to load {video_path}: {e}")
                    continue
            
            if not clips:
                logger.error("No valid video clips to concatenate")
                return None
            
            # Concatenate videos
            logger.info(f"Concatenating {len(clips)} videos into {total_duration:.1f}s compilation...")
            final_clip = concatenate_videoclips(clips)
            
            # Generate output filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"compilation_{timestamp}.mp4"
            output_path = self.compilation_dir / output_name
            
            # Export compilation
            logger.info(f"Exporting compilation to {output_path}...")
            final_clip.write_videofile(str(output_path), verbose=False, logger=None)
            final_clip.close()
            
            # Clean up individual clips
            for clip in clips:
                clip.close()
            
            logger.info(f"✅ Compilation created: {output_path} ({total_duration:.1f}s)")
            
            # Save metadata
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'video_path': str(output_path),
                'duration': total_duration,
                'video_count': len(self.pending_videos),
                'source_videos': self.pending_videos,
                'title': title,
                'prompt': prompt
            }
            
            metadata_path = output_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Reset queue
            self.pending_videos = []
            self.pending_duration = 0
            
            return str(output_path)
        
        except Exception as e:
            logger.error(f"Failed to create compilation: {e}")
            return None


class ThumbnailGenerator:
    """Generate YouTube thumbnails automatically"""
    
    def __init__(self):
        self.thumbnail_dir = Path(config.OUTPUT_DIR) / 'thumbnails'
        self.thumbnail_dir.mkdir(parents=True, exist_ok=True)
        self.thumbnail_size = (1280, 720)  # YouTube recommended
    
    def generate_from_video(self, video_path: str, timestamp: float = None) -> Optional[str]:
        """
        Extract frame from video and use as thumbnail
        
        Args:
            video_path: Path to video file
            timestamp: Specific timestamp to extract (seconds)
        
        Returns:
            Path to generated thumbnail
        """
        try:
            from moviepy.editor import VideoFileClip
            
            clip = VideoFileClip(video_path)
            
            # Get frame at specified time or middle of video
            if timestamp is None:
                timestamp = clip.duration / 2
            
            timestamp = min(timestamp, clip.duration - 0.1)
            frame = clip.get_frame(timestamp)
            
            # Convert to PIL Image
            image = Image.fromarray(frame)
            
            # Resize to thumbnail size
            image = image.resize(self.thumbnail_size, Image.Resampling.LANCZOS)
            
            clip.close()
            
            # Save thumbnail
            filename = f"thumbnail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            output_path = self.thumbnail_dir / filename
            image.save(output_path, 'JPEG', quality=95)
            
            logger.info(f"✅ Thumbnail generated: {output_path}")
            return str(output_path)
        
        except Exception as e:
            logger.error(f"Error generating thumbnail from video: {e}")
            return None
    
    def generate_custom(self, title: str, background_color: tuple = (0, 0, 0), 
                       text_color: tuple = (255, 255, 255)) -> Optional[str]:
        """
        Generate custom thumbnail with text
        
        Args:
            title: Text to display on thumbnail
            background_color: RGB background color
            text_color: RGB text color
        
        Returns:
            Path to generated thumbnail
        """
        try:
            # Create new image
            image = Image.new('RGB', self.thumbnail_size, background_color)
            draw = ImageDraw.Draw(image)
            
            # Try to use a nice font, fall back to default if not available
            try:
                font_size = 60
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            # Wrap text to fit
            max_width = self.thumbnail_size[0] - 40
            wrapped_text = self._wrap_text(title, max_width, draw, font)
            
            # Calculate text position (centered)
            bbox = draw.textbbox((0, 0), wrapped_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (self.thumbnail_size[0] - text_width) // 2
            y = (self.thumbnail_size[1] - text_height) // 2
            
            # Add semi-transparent background for text
            padding = 20
            draw.rectangle(
                [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
                fill=(0, 0, 0, 128),
                outline=text_color
            )
            
            # Draw text
            draw.text((x, y), wrapped_text, font=font, fill=text_color)
            
            # Save thumbnail
            filename = f"thumbnail_custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            output_path = self.thumbnail_dir / filename
            image.save(output_path, 'JPEG', quality=95)
            
            logger.info(f"✅ Custom thumbnail generated: {output_path}")
            return str(output_path)
        
        except Exception as e:
            logger.error(f"Error generating custom thumbnail: {e}")
            return None
    
    def _wrap_text(self, text: str, max_width: int, draw, font, char_limit: int = 50) -> str:
        """Wrap text to fit within max width"""
        if len(text) <= char_limit:
            return text
        
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if len(test_line) > char_limit:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
            else:
                current_line.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines[:3])  # Max 3 lines


class VideoTitleGenerator:
    """Generate catchy titles for compiled videos"""
    
    TITLE_TEMPLATES = [
        "🐕 {topic} Compilation | Best Pet Videos",
        "🐱 Cute {topic} - Funny Animals 😹",
        "{topic} Moments | Cutest Pet Videos 🥰",
        "🐶 {topic} Challenge | Hilarious Pets",
        "Adorable {topic} | Best of the Week 🎬",
        "🐾 {topic} Spectacular | Pet Compilation",
        "{topic} Extravaganza | Funniest Animals 😂",
        "🐕 {topic} Overload | Amazing Pet Videos",
    ]
    
    TOPIC_KEYWORDS = [
        "Dogs", "Cats", "Puppies", "Kittens", "Pets",
        "Animals", "Funny Moments", "Cute Scenes", "Playing",
        "Adventure", "Training", "Tricks", "Fails"
    ]
    
    def __init__(self):
        self.templates = self.TITLE_TEMPLATES
        self.topics = self.TOPIC_KEYWORDS
    
    def generate(self, prompt: str = None, use_template: int = 0) -> str:
        """
        Generate a title for a video compilation
        
        Args:
            prompt: Original video prompt (optional)
            use_template: Which template to use (0-based index)
        
        Returns:
            Generated title
        """
        import random
        
        template = self.templates[use_template % len(self.templates)]
        topic = self.topics[random.randint(0, len(self.topics) - 1)]
        
        title = template.format(topic=topic)
        
        logger.info(f"Generated title: {title}")
        return title
    
    def generate_from_prompt(self, prompt: str) -> str:
        """
        Generate title based on original prompt
        
        Args:
            prompt: Original video prompt
        
        Returns:
            Generated title
        """
        import random
        
        template = random.choice(self.templates)
        
        # Extract main subject from prompt
        words = prompt.split()
        topic = ' '.join(words[:2]) if len(words) > 1 else words[0]
        
        title = template.format(topic=topic)
        
        # Ensure it's not too long
        if len(title) > 100:
            title = title[:97] + "..."
        
        logger.info(f"Generated title from prompt: {title}")
        return title
