# Configuration for AI Video Generator

import os
from dotenv import load_dotenv

load_dotenv()

# ============= API KEYS =============
RUNWAY_API_KEY = os.getenv('RUNWAY_API_KEY')
FAL_API_KEY = os.getenv('FAL_API_KEY')
REPLICATE_API_KEY = os.getenv('REPLICATE_API_KEY')

# ============= YOUTUBE MULTI-ACCOUNT SETUP =============
# Each account needs its own OAuth credentials file
# Supported: youtube_creds_1.json, youtube_creds_2.json, ... youtube_creds_5.json
YOUTUBE_ACCOUNTS = {
    'account_1': 'credentials/youtube_creds_1.json',
    'account_2': 'credentials/youtube_creds_2.json',
    'account_3': 'credentials/youtube_creds_3.json',
    'account_4': 'credentials/youtube_creds_4.json',
    'account_5': 'credentials/youtube_creds_5.json',
}

# Stagger delay between uploads to different accounts (seconds)
# Default: 900 (15 minutes) - cycles through 5 accounts every ~1 hour and 15 minutes
UPLOAD_STAGGER_DELAY = int(os.getenv('UPLOAD_STAGGER_DELAY', '900'))

# ============= VIDEO GENERATION =============
# Choose: 'runway', 'fal', 'replicate', or 'local'
VIDEO_GENERATOR = os.getenv('VIDEO_GENERATOR', 'fal')

# Video generation settings
VIDEO_DURATION = int(os.getenv('VIDEO_DURATION', '30'))  # seconds
VIDEO_QUALITY = os.getenv('VIDEO_QUALITY', 'high')  # low, medium, high
ASPECT_RATIO = '9:16'  # For shorts

# Dog/Cat prompts (randomly selected)
PROMPTS = [
    "A cute golden retriever playing fetch in a sunny park",
    "A black cat doing yoga stretches indoors",
    "A fluffy corgi running through autumn leaves",
    "A kitten pouncing on a red ball",
    "A dog swimming in a crystal clear pool",
    "A tabby cat climbing a tall tree",
    "A puppy learning to walk",
    "A cat watching birds from a window",
    "A husky howling in the snow",
    "A Persian cat being groomed",
    "A German Shepherd playing with a frisbee",
    "A rabbit hopping through grass",
    "A poodle at a dog spa",
    "A Siamese cat playing with yarn",
]

# ============= VIDEO PROCESSING =============
# Output directories
OUTPUT_DIR = 'outputs'
GENERATED_DIR = os.path.join(OUTPUT_DIR, 'generated')
PROCESSED_DIR = os.path.join(OUTPUT_DIR, 'processed')
LOGS_DIR = os.path.join(OUTPUT_DIR, 'logs')
DATA_DIR = 'data'  # For storing history and trends

# Video format settings (9:16 for YouTube Shorts)
YOUTUBE_SIZE = (1080, 1920)  # 9:16

# Audio & Caption settings
ADD_VOICEOVER = True  # Enable AI voiceover
ADD_CAPTIONS = True
ADD_MUSIC = True  # Background music (optional with voiceover)
ADD_TEXT_OVERLAY = True
MUSIC_VOLUME = 0.3
VOICEOVER_VOLUME = 1.0

# ============= UPLOADING =============
# YouTube-only configuration (TikTok and Instagram removed)
PLATFORMS = {
    'youtube': {
        'enabled': True,
        'title_template': '🐕 {prompt} | AI Video',
        'description_template': 'AI-generated pet video with AI voiceover narration\n\n{prompt}\n\n#Dogs #Cats #AIGenerated #Pets #Shorts #YouTubeShorts',
        'tags': ['dogs', 'cats', 'AI', 'pets', 'funny', 'cute', 'animals', 'shorts', 'AI-generated'],
        'privacy': 'PUBLIC'  # PUBLIC, UNLISTED, PRIVATE
    }
}

# ============= SCHEDULING =============
# New: Continuous mode - uploads every 15 minutes on rotation across 5 accounts
CONTINUOUS_MODE = True  # Set to True for continuous 15-min uploads, False for daily schedule
SCHEDULE_TIME = os.getenv('SCHEDULE_TIME', '09:00')  # 24-hour format (HH:MM) - used when CONTINUOUS_MODE=False
VIDEOS_PER_RUN = int(os.getenv('VIDEOS_PER_RUN', '1'))
RUN_ON_STARTUP = True  # Run immediately on startup

# Continuous mode settings
UPLOAD_INTERVAL_MINUTES = int(os.getenv('UPLOAD_INTERVAL_MINUTES', '15'))  # Upload every 15 minutes
CONTINUOUS_VIDEO_ACCUMULATION = True  # Accumulate videos until 10 minutes of content
TARGET_VIDEO_LENGTH_MINUTES = 10  # Concatenate 10 minutes worth of videos into one upload

# ============= RATE LIMITS =============
API_RATE_LIMIT = 10  # requests per minute
UPLOAD_RETRY_COUNT = 3
UPLOAD_RETRY_DELAY = 5  # seconds

# ============= LOGGING =============
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_TO_FILE = True
LOG_TO_CONSOLE = True

# Create directories if they don't exist
os.makedirs(GENERATED_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs('credentials', exist_ok=True)
os.makedirs('assets/voiceovers', exist_ok=True)

