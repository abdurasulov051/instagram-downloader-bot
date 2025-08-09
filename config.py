import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot Configuration
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '8112287877:AAFmCdwBRWYDYkeUw-uFc4a4LA4-j-yI9Ak')
    
    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
    
    # Instagram Configuration
    INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
    INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
    INSTAGRAM_SESSION_ID = os.getenv('INSTAGRAM_SESSION_ID')
    
    # Proxy Configuration
    PROXY_LIST = os.getenv('PROXY_LIST', '').split(',') if os.getenv('PROXY_LIST') else []
    PROXY_USERNAME = os.getenv('PROXY_USERNAME')
    PROXY_PASSWORD = os.getenv('PROXY_PASSWORD')
    
    # Bot Settings
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB Telegram limit
    DOWNLOAD_TIMEOUT = 300  # 5 minutes
    MAX_CONCURRENT_DOWNLOADS = 3
    
    # File paths
    TEMP_DIR = 'temp'
    FFMPEG_PATH = os.getenv('FFMPEG_PATH', 'ffmpeg')  # Path to FFmpeg executable 