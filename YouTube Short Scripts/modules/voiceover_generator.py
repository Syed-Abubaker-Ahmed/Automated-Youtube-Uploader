"""
Text-to-Speech (TTS) Voiceover Module
Adds AI-generated voiceover narration to videos
Uses free Google Text-to-Speech API
"""

import os
import logging
from pathlib import Path
import subprocess
from typing import Optional

try:
    from gtts import gTTS
except ImportError:
    gTTS = None

logger = logging.getLogger(__name__)


class VoiceoverGenerator:
    """Generate AI voiceover for videos using Google TTS"""
    
    def __init__(self, language: str = 'en', accent: str = 'us'):
        """
        Initialize voiceover generator
        
        Args:
            language: Language code (en, es, fr, etc.)
            accent: Accent variant (us, gb, etc.)
        """
        self.language = language
        self.accent = accent
        self.audio_dir = Path('assets/voiceovers')
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        if not gTTS:
            logger.warning("gTTS not installed. Install with: pip install gtts")
    
    def generate_voiceover(self, text: str, voice_name: str = 'voiceover') -> str:
        """
        Generate voiceover audio from text
        
        Args:
            text: Text to convert to speech
            voice_name: Name for the audio file
        
        Returns:
            Path to audio file
        """
        try:
            if not gTTS:
                logger.error("gTTS not installed. Install: pip install gtts")
                return None
            
            # Create filename
            filename = f"{voice_name}.mp3"
            filepath = self.audio_dir / filename
            
            logger.info(f"Generating voiceover: {text[:50]}...")
            
            # Generate speech
            tts = gTTS(
                text=text,
                lang=self.language,
                slow=False,
                tld=self.accent  # 'us', 'gb', 'ca', etc
            )
            
            # Save audio
            tts.save(str(filepath))
            
            logger.info(f"✅ Voiceover saved: {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to generate voiceover: {e}")
            return None
    
    def generate_prompt_voiceover(self, prompt: str) -> str:
        """Generate voiceover for a video prompt"""
        # Create narration from prompt
        narration = f"{prompt}. Enjoy this cute moment!"
        return self.generate_voiceover(narration, voice_name="prompt_voiceover")
    
    def generate_intro_voiceover(self) -> str:
        """Generate intro voiceover"""
        intro = "Welcome to our AI pet videos. Enjoy this amazing moment."
        return self.generate_voiceover(intro, voice_name="intro")
    
    def get_voiceover_duration(self, audio_path: str) -> Optional[float]:
        """Get duration of audio file in seconds"""
        try:
            import subprocess
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 
                 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1:novalue=1',
                 audio_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"Could not get audio duration: {e}")
        return None


class MultiLanguageVoiceover:
    """Generate voiceovers in multiple languages"""
    
    LANGUAGES = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese',
        'ru': 'Russian',
        'ja': 'Japanese',
        'zh': 'Chinese',
        'hi': 'Hindi'
    }
    
    def __init__(self):
        self.generators = {}
        for lang_code in self.LANGUAGES.keys():
            self.generators[lang_code] = VoiceoverGenerator(language=lang_code)
    
    def generate_multi_language(self, text: str, languages: list = None) -> dict:
        """
        Generate voiceover in multiple languages
        
        Args:
            text: Text to convert
            languages: List of language codes (default: English only)
        
        Returns:
            Dict mapping language codes to audio paths
        """
        if languages is None:
            languages = ['en']
        
        results = {}
        for lang in languages:
            if lang in self.generators:
                audio_path = self.generators[lang].generate_voiceover(text, voice_name=f"voiceover_{lang}")
                results[lang] = audio_path
            else:
                logger.warning(f"Language {lang} not supported")
        
        return results


class VoiceoverMixer:
    """Mix voiceover with video and background music"""
    
    def __init__(self):
        self.ffmpeg_available = self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available"""
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, timeout=5)
            return True
        except:
            logger.warning("ffmpeg not found. Install with: apt-get install ffmpeg")
            return False
    
    def add_voiceover_to_video(self, video_path: str, voiceover_path: str, 
                               output_path: str, music_path: str = None) -> bool:
        """
        Add voiceover to video
        
        Args:
            video_path: Path to video file
            voiceover_path: Path to voiceover audio
            output_path: Path for output video
            music_path: Optional background music
        
        Returns:
            True if successful
        """
        if not self.ffmpeg_available:
            logger.error("ffmpeg required for voiceover mixing")
            return False
        
        try:
            if music_path and os.path.exists(music_path):
                # Mix voiceover + background music
                cmd = [
                    'ffmpeg', '-i', video_path,
                    '-i', voiceover_path,
                    '-i', music_path,
                    '-filter_complex', 
                    '[1:a]volume=1[voice]; [2:a]volume=0.3[music]; [voice][music]amerge=inputs=2[a]',
                    '-map', '0:v',
                    '-map', '[a]',
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                    '-y',
                    output_path
                ]
            else:
                # Just add voiceover
                cmd = [
                    'ffmpeg', '-i', video_path,
                    '-i', voiceover_path,
                    '-c:v', 'copy',
                    '-map', '0:v:0',
                    '-map', '1:a:0',
                    '-shortest',
                    '-y',
                    output_path
                ]
            
            logger.info("Mixing voiceover with video...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"✅ Video with voiceover saved: {output_path}")
                return True
            else:
                logger.error(f"ffmpeg error: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to mix voiceover: {e}")
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test voiceover generation
    gen = VoiceoverGenerator()
    
    test_text = "A cute golden retriever playing fetch in a sunny park"
    audio_path = gen.generate_voiceover(test_text)
    
    if audio_path:
        print(f"✅ Generated voiceover: {audio_path}")
    else:
        print("❌ Failed to generate voiceover")
