"""
Multi-Account YouTube Uploader
Uploads videos to 5 different YouTube accounts with staggered timing
Helps avoid spam detection by distributing uploads across accounts
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Optional, List, Dict
import pickle

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.api_client.discovery import build

logger = logging.getLogger(__name__)

# YouTube API scopes
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


class YouTubeAccountManager:
    """Manage multiple YouTube accounts and their credentials"""
    
    def __init__(self, credentials_dir: str = 'credentials'):
        """
        Initialize account manager
        
        Args:
            credentials_dir: Directory containing account credentials
        """
        self.credentials_dir = Path(credentials_dir)
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        
        self.accounts = {}
        self.current_account_index = 0
        self.load_accounts()
    
    def load_accounts(self):
        """Load all YouTube account credentials"""
        logger.info("Loading YouTube accounts...")
        
        # Look for credentials files (youtube_creds_1.json, youtube_creds_2.json, etc.)
        creds_files = sorted(self.credentials_dir.glob('youtube_creds_*.json'))
        
        if not creds_files:
            logger.warning("No YouTube credentials found. Use setup wizard to add accounts.")
            return
        
        for creds_file in creds_files:
            account_num = creds_file.stem.split('_')[-1]
            
            try:
                credentials = self._load_credentials(str(creds_file))
                if credentials:
                    self.accounts[f"account_{account_num}"] = {
                        'creds_file': str(creds_file),
                        'credentials': credentials,
                        'name': f"Account {account_num}",
                        'last_upload': None,
                        'upload_count': 0
                    }
                    logger.info(f"✅ Loaded account {account_num}")
            except Exception as e:
                logger.error(f"Failed to load account {account_num}: {e}")
        
        logger.info(f"Loaded {len(self.accounts)} YouTube accounts")
    
    def _load_credentials(self, creds_file: str) -> Optional[Credentials]:
        """Load OAuth credentials from file"""
        try:
            # First try to load token (if exists)
            token_file = creds_file.replace('.json', '_token.pickle')
            
            if os.path.exists(token_file):
                with open(token_file, 'rb') as f:
                    credentials = pickle.load(f)
                
                # Refresh if expired
                if credentials and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                
                return credentials
            else:
                # Use OAuth flow
                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_file,
                    YOUTUBE_SCOPES
                )
                credentials = flow.run_local_server(port=0)
                
                # Save token
                with open(token_file, 'wb') as f:
                    pickle.dump(credentials, f)
                
                return credentials
                
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            return None
    
    def get_next_account(self) -> Optional[tuple]:
        """
        Get next account in rotation
        
        Returns:
            Tuple of (account_name, credentials) or None
        """
        if not self.accounts:
            logger.error("No YouTube accounts configured")
            return None
        
        account_list = list(self.accounts.items())
        account_name, account_data = account_list[self.current_account_index]
        
        # Move to next account
        self.current_account_index = (self.current_account_index + 1) % len(self.accounts)
        
        return account_name, account_data['credentials']
    
    def get_account_by_name(self, account_name: str) -> Optional[Credentials]:
        """Get credentials for specific account"""
        if account_name in self.accounts:
            return self.accounts[account_name]['credentials']
        return None
    
    def list_accounts(self) -> List[str]:
        """List all configured accounts"""
        return list(self.accounts.keys())
    
    def add_account(self, account_number: int, client_secrets_file: str) -> bool:
        """Add new YouTube account"""
        try:
            creds_file = self.credentials_dir / f'youtube_creds_{account_number}.json'
            
            if not os.path.exists(client_secrets_file):
                logger.error(f"Client secrets file not found: {client_secrets_file}")
                return False
            
            # Copy client secrets
            import shutil
            shutil.copy(client_secrets_file, str(creds_file))
            
            # Load credentials
            credentials = self._load_credentials(str(creds_file))
            
            if credentials:
                logger.info(f"✅ Added YouTube account {account_number}")
                return True
            else:
                logger.error(f"Failed to authenticate account {account_number}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding account: {e}")
            return False


class MultiAccountYouTubeUploader:
    """Upload videos to multiple YouTube accounts"""
    
    def __init__(self, stagger_delay: int = 3600):
        """
        Initialize multi-account uploader
        
        Args:
            stagger_delay: Delay between uploads (seconds, default 1 hour)
        """
        self.account_manager = YouTubeAccountManager()
        self.stagger_delay = stagger_delay  # Default 1 hour between uploads
        self.upload_queue = []
    
    def upload_batch(self, video_paths: List[str], metadata: Dict, 
                    stagger: bool = True, delay: Optional[int] = None) -> Dict:
        """
        Upload same video to multiple accounts
        
        Args:
            video_paths: List of video file paths
            metadata: Dict with title, description, tags, etc.
            stagger: Whether to stagger uploads across time
            delay: Custom delay between uploads (seconds)
        
        Returns:
            Dict with upload results for each account
        """
        delay = delay or self.stagger_delay
        results = {}
        
        accounts = self.account_manager.list_accounts()
        
        if not accounts:
            logger.error("No YouTube accounts available")
            return results
        
        for idx, video_path in enumerate(video_paths):
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                continue
            
            # Select account (rotate through available accounts)
            account_name, credentials = self.account_manager.get_next_account()
            
            logger.info(f"Uploading {idx + 1}/{len(video_paths)} to {account_name}")
            
            # Upload
            video_id = self._upload_to_account(video_path, credentials, metadata, account_name)
            results[account_name] = {
                'video_path': video_path,
                'video_id': video_id,
                'status': 'success' if video_id else 'failed',
                'timestamp': time.time()
            }
            
            # Stagger uploads to avoid spam detection
            if stagger and idx < len(video_paths) - 1:
                logger.info(f"Waiting {delay}s before next upload to avoid spam detection...")
                time.sleep(delay)
        
        return results
    
    def upload_to_specific_account(self, video_path: str, account_name: str, 
                                   metadata: Dict) -> Optional[str]:
        """Upload to specific account by name"""
        credentials = self.account_manager.get_account_by_name(account_name)
        
        if not credentials:
            logger.error(f"Account not found: {account_name}")
            return None
        
        return self._upload_to_account(video_path, credentials, metadata, account_name)
    
    def _upload_to_account(self, video_path: str, credentials: Credentials, 
                          metadata: Dict, account_name: str) -> Optional[str]:
        """Actual upload logic"""
        try:
            youtube = build('youtube', 'v3', credentials=credentials)
            
            # Prepare request
            request_body = {
                'snippet': {
                    'title': metadata.get('title', 'Untitled'),
                    'description': metadata.get('description', ''),
                    'tags': metadata.get('tags', []),
                    'categoryId': '15'  # Pets category
                },
                'status': {
                    'privacyStatus': metadata.get('privacy_status', 'public'),
                    'selfDeclaredMadeForKids': False,
                    'madeForKids': False
                }
            }
            
            # Add shorts-specific settings
            request_body['snippet']['defaultLanguage'] = 'en'
            request_body['processingDetails'] = {
                'processingStatus': 'processing'
            }
            
            logger.info(f"Uploading to {account_name}: {metadata.get('title', 'Untitled')}")
            
            # Upload with resumable protocol
            from googleapiclient.http import MediaFileUpload
            
            media = MediaFileUpload(
                video_path,
                mimetype='video/mp4',
                resumable=True,
                chunksize=1024 * 1024  # 1MB chunks
            )
            
            request = youtube.videos().insert(
                part='snippet,status,processingDetails',
                body=request_body,
                media_body=media
            )
            
            # Execute with progress tracking
            response = None
            while response is None:
                try:
                    status, response = request.next_chunk()
                    
                    if status:
                        progress = int(status.progress() * 100)
                        logger.info(f"Upload progress: {progress}%")
                        
                except Exception as e:
                    logger.error(f"Upload error: {e}")
                    return None
            
            video_id = response.get('id')
            logger.info(f"✅ Successfully uploaded to {account_name}. Video ID: {video_id}")
            
            return video_id
            
        except Exception as e:
            logger.error(f"Failed to upload to {account_name}: {e}")
            return None
    
    def get_upload_stats(self) -> Dict:
        """Get upload statistics"""
        accounts = self.account_manager.accounts
        
        stats = {
            'total_accounts': len(accounts),
            'accounts': {}
        }
        
        for account_name, account_data in accounts.items():
            stats['accounts'][account_name] = {
                'upload_count': account_data.get('upload_count', 0),
                'last_upload': account_data.get('last_upload'),
                'name': account_data.get('name')
            }
        
        return stats


class BatchVideoDistributor:
    """Distribute batch videos across accounts"""
    
    def __init__(self, uploader: MultiAccountYouTubeUploader):
        self.uploader = uploader
    
    def distribute_batch(self, video_batch: List[str], metadata_template: Dict, 
                        shuffle: bool = True, stagger_delay: int = 3600) -> Dict:
        """
        Distribute a batch of videos across accounts
        
        Args:
            video_batch: List of video file paths
            metadata_template: Template for metadata (will be customized per video)
            shuffle: Whether to shuffle video order across accounts
            stagger_delay: Delay between uploads (seconds)
        
        Returns:
            Dict with results for all uploads
        """
        logger.info(f"Distributing {len(video_batch)} videos across accounts")
        
        if shuffle:
            import random
            random.shuffle(video_batch)
        
        all_results = {}
        
        for idx, video_path in enumerate(video_batch):
            # Get next account
            account_name, credentials = self.uploader.account_manager.get_next_account()
            
            # Customize metadata
            metadata = metadata_template.copy()
            metadata['title'] = f"{metadata.get('title')} - Part {idx + 1}"
            
            logger.info(f"Uploading part {idx + 1}/{len(video_batch)} to {account_name}")
            
            # Upload
            video_id = self.uploader._upload_to_account(
                video_path, 
                credentials, 
                metadata, 
                account_name
            )
            
            all_results[f"{account_name}_part{idx + 1}"] = {
                'video_path': video_path,
                'video_id': video_id,
                'account': account_name,
                'status': 'success' if video_id else 'failed'
            }
            
            # Stagger uploads
            if idx < len(video_batch) - 1:
                logger.info(f"Waiting {stagger_delay}s before next upload...")
                time.sleep(stagger_delay)
        
        return all_results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize uploader
    uploader = MultiAccountYouTubeUploader(stagger_delay=3600)
    
    # List accounts
    accounts = uploader.account_manager.list_accounts()
    print(f"Available accounts: {accounts}")
    
    # Get stats
    stats = uploader.get_upload_stats()
    print(f"Upload stats: {json.dumps(stats, indent=2)}")
