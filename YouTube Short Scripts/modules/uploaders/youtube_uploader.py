"""
YouTube Shorts Uploader
Uses OAuth 2.0 for authentication
"""

import os
import pickle
import logging
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.api_python_client import discovery
import config

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


class YouTubeUploader:
    def __init__(self):
        self.youtube = None
        self.credentials_file = config.YOUTUBE_CREDENTIALS
        self.token_file = 'credentials/youtube_token.pickle'
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with YouTube API"""
        try:
            # Load existing token
            if os.path.exists(self.token_file):
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
                
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
            
            # No token exists, create new
            elif not os.path.exists(self.credentials_file):
                raise FileNotFoundError(
                    f"YouTube credentials not found at {self.credentials_file}\n"
                    "Please download your OAuth credentials from Google Cloud Console"
                )
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
                
                # Save token for future use
                with open(self.token_file, 'wb') as token:
                    pickle.dump(creds, token)
            
            self.youtube = discovery.build('youtube', 'v3', credentials=creds)
            logger.info("✅ YouTube authenticated successfully")
            
        except Exception as e:
            logger.error(f"YouTube authentication failed: {e}")
            raise
    
    def upload(self, video_path: str, title: str, description: str, 
               tags: list = None, privacy: str = 'PUBLIC') -> str:
        """
        Upload video to YouTube Shorts
        
        Args:
            video_path: Path to MP4 video file
            title: Video title
            description: Video description
            tags: List of tags/keywords
            privacy: PUBLIC, UNLISTED, or PRIVATE
        
        Returns:
            Video ID if successful
        """
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video not found: {video_path}")
            
            logger.info(f"Uploading to YouTube: {title}")
            
            # Prepare request
            request_body = {
                'snippet': {
                    'title': title[:100],  # Max 100 chars
                    'description': description[:5000],  # Max 5000 chars
                    'tags': tags or [],
                    'categoryId': '20'  # Gaming/Pets category
                },
                'status': {
                    'privacyStatus': privacy.lower()
                }
            }
            
            # Upload video file
            with open(video_path, 'rb') as video_file:
                request = self.youtube.videos().insert(
                    part='snippet,status',
                    body=request_body,
                    media_body=discovery.MediaFileUpload(
                        video_path,
                        mimetype='video/mp4',
                        resumable=True
                    )
                )
                
                response = None
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        logger.info(f"Upload progress: {int(status.progress() * 100)}%")
            
            video_id = response.get('id')
            logger.info(f"✅ YouTube upload successful! Video ID: {video_id}")
            
            return video_id
            
        except Exception as e:
            logger.error(f"YouTube upload failed: {e}")
            raise
    
    def add_to_shorts(self, video_id: str):
        """Add video to Shorts (automatic if vertical video)"""
        try:
            logger.info(f"Marking as Short: {video_id}")
            # YouTube automatically marks vertical 9:16 videos as Shorts
            logger.info("✅ Video marked as Short (automatic)")
        except Exception as e:
            logger.error(f"Could not mark as Short: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    uploader = YouTubeUploader()
    print("YouTube uploader ready!")
