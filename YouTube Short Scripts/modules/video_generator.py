"""
AI Video Generator Module
Generates videos using free APIs: FAL.ai, Runway, or Replicate
"""

import requests
import json
import time
import logging
import random
from datetime import datetime
from pathlib import Path
import config

logger = logging.getLogger(__name__)

class VideoGenerator:
    def __init__(self):
        self.generator_type = config.VIDEO_GENERATOR
        self.api_keys = {
            'fal': config.FAL_API_KEY,
            'runway': config.RUNWAY_API_KEY,
            'replicate': config.REPLICATE_API_KEY
        }
        
    def generate(self, prompt: str) -> str:
        """
        Generate video using configured API
        Returns: path to generated video file
        """
        logger.info(f"Generating video with prompt: {prompt}")
        
        if self.generator_type == 'fal':
            return self._generate_fal(prompt)
        elif self.generator_type == 'runway':
            return self._generate_runway(prompt)
        elif self.generator_type == 'replicate':
            return self._generate_replicate(prompt)
        elif self.generator_type == 'local':
            return self._generate_local(prompt)
        else:
            raise ValueError(f"Unknown generator type: {self.generator_type}")
    
    def _generate_fal(self, prompt: str) -> str:
        """Generate video using FAL.ai API (RECOMMENDED - Free tier)"""
        try:
            # FAL.ai endpoint for text-to-video
            url = "https://api.fal.ai/v1/text-to-video"
            
            headers = {
                "Authorization": f"Key {self.api_keys['fal']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "prompt": prompt,
                "duration": config.VIDEO_DURATION,
                "aspect_ratio": config.ASPECT_RATIO,
            }
            
            logger.info("Sending request to FAL.ai...")
            response = requests.post(url, json=payload, headers=headers, timeout=300)
            response.raise_for_status()
            
            result = response.json()
            video_url = result.get('url')
            
            if not video_url:
                raise Exception("No video URL returned from FAL.ai")
            
            # Download video
            return self._download_video(video_url, f"fal_{int(time.time())}.mp4")
            
        except Exception as e:
            logger.error(f"FAL.ai generation failed: {e}")
            raise
    
    def _generate_runway(self, prompt: str) -> str:
        """Generate video using Runway API"""
        try:
            # Runway Gen-3 endpoint
            url = "https://api.runwayml.com/v1/generate"
            
            headers = {
                "Authorization": f"Bearer {self.api_keys['runway']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "prompt": prompt,
                "model": "gen3",
                "duration": config.VIDEO_DURATION,
                "aspect_ratio": config.ASPECT_RATIO
            }
            
            logger.info("Sending request to Runway ML...")
            response = requests.post(url, json=payload, headers=headers, timeout=300)
            response.raise_for_status()
            
            # Poll for completion (Runway is async)
            task_id = response.json().get('taskId')
            return self._poll_runway_task(task_id)
            
        except Exception as e:
            logger.error(f"Runway generation failed: {e}")
            raise
    
    def _generate_replicate(self, prompt: str) -> str:
        """Generate video using Replicate API"""
        try:
            url = "https://api.replicate.com/v1/predictions"
            
            headers = {
                "Authorization": f"Token {self.api_keys['replicate']}",
                "Content-Type": "application/json"
            }
            
            # Using Replicate's text-to-video model
            payload = {
                "version": "text-to-video-model-id",  # Replace with actual model ID
                "input": {
                    "prompt": prompt,
                    "duration": config.VIDEO_DURATION
                }
            }
            
            logger.info("Sending request to Replicate...")
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            # Poll for completion
            prediction_url = response.json().get('urls', {}).get('get')
            return self._poll_replicate_task(prediction_url)
            
        except Exception as e:
            logger.error(f"Replicate generation failed: {e}")
            raise
    
    def _generate_local(self, prompt: str) -> str:
        """
        Generate video using local ComfyUI/AnimateDiff (requires local setup)
        This is for advanced users with GPU
        """
        logger.warning("Local generation requires ComfyUI setup. Not implemented.")
        raise NotImplementedError("Local generation requires manual ComfyUI installation")
    
    def _download_video(self, url: str, filename: str) -> str:
        """Download video from URL"""
        filepath = Path(config.GENERATED_DIR) / filename
        
        logger.info(f"Downloading video from {url}")
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Video saved to {filepath}")
        return str(filepath)
    
    def _poll_runway_task(self, task_id: str, max_wait: int = 600) -> str:
        """Poll Runway API until video is ready"""
        url = f"https://api.runwayml.com/v1/tasks/{task_id}"
        
        headers = {
            "Authorization": f"Bearer {self.api_keys['runway']}"
        }
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            response = requests.get(url, headers=headers)
            task = response.json()
            
            if task.get('status') == 'SUCCEEDED':
                video_url = task.get('output', {}).get('video')
                return self._download_video(video_url, f"runway_{task_id}.mp4")
            
            elif task.get('status') == 'FAILED':
                raise Exception(f"Runway task failed: {task.get('error')}")
            
            logger.info(f"Task {task_id} status: {task.get('status')}. Waiting...")
            time.sleep(10)
        
        raise Exception(f"Task {task_id} timed out after {max_wait}s")
    
    def _poll_replicate_task(self, url: str, max_wait: int = 600) -> str:
        """Poll Replicate API until video is ready"""
        start_time = time.time()
        while time.time() - start_time < max_wait:
            response = requests.get(url)
            prediction = response.json()
            
            if prediction.get('status') == 'succeeded':
                video_output = prediction.get('output')
                if video_output:
                    return self._download_video(video_output[0], f"replicate_{prediction['id']}.mp4")
            
            elif prediction.get('status') == 'failed':
                raise Exception(f"Replicate prediction failed: {prediction.get('error')}")
            
            logger.info(f"Prediction {prediction['id']} status: {prediction.get('status')}")
            time.sleep(10)
        
        raise Exception(f"Prediction timed out after {max_wait}s")


def get_random_prompt() -> str:
    """Get random prompt from config"""
    return random.choice(config.PROMPTS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    gen = VideoGenerator()
    prompt = get_random_prompt()
    
    print(f"Generating video with prompt: {prompt}")
    video_path = gen.generate(prompt)
    print(f"✅ Video saved to: {video_path}")
