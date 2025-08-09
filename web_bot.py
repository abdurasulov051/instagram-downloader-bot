import asyncio
import logging
import os
import re
import subprocess
import tempfile
import json
import requests
import time
import random
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from telegram import Bot
from config import Config
from flask import Flask, request, jsonify

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create Flask app for web server
app = Flask(__name__)

class WebInstagramBot:
    def __init__(self, token):
        self.bot = Bot(token=token)
        self.last_update_id = 0
        self.config = Config()
        self.temp_dir = Path(self.config.TEMP_DIR)
        self.temp_dir.mkdir(exist_ok=True)
        
        # Session for persistent cookies
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Referer': 'https://www.instagram.com/',
        })
        
    async def get_updates(self):
        """Get updates from Telegram"""
        try:
            updates = await self.bot.get_updates(offset=self.last_update_id + 1, timeout=30)
            return updates
        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return []
    
    def is_instagram_url(self, text):
        """Check if text contains Instagram URL"""
        instagram_patterns = [
            r'https?://(?:www\.)?instagram\.com/p/[a-zA-Z0-9_-]+/?',
            r'https?://(?:www\.)?instagram\.com/reel/[a-zA-Z0-9_-]+/?',
            r'https?://(?:www\.)?instagram\.com/tv/[a-zA-Z0-9_-]+/?',
            r'https?://(?:www\.)?instagram\.com/stories/[^/]+/\d+/?',
            r'https?://(?:www\.)?instagram\.com/[^/]+/?'
        ]
        
        for pattern in instagram_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def extract_shortcode(self, url):
        """Extract shortcode from Instagram URL"""
        patterns = [
            r'instagram\.com/p/([a-zA-Z0-9_-]+)',
            r'instagram\.com/reel/([a-zA-Z0-9_-]+)',
            r'instagram\.com/tv/([a-zA-Z0-9_-]+)',
            r'instagram\.com/stories/[^/]+/(\d+)',
            r'instagram\.com/([^/]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def detect_content_type(self, url):
        """Detect if URL is for video, photo, or story"""
        if '/stories/' in url:
            return 'story'
        elif '/reel/' in url or '/tv/' in url:
            return 'video'
        elif '/p/' in url:
            return 'post'  # Could be photo or video
        else:
            return 'unknown'
    
    def extract_photo_urls_from_html(self, url):
        """Extract photo URLs directly from Instagram page HTML"""
        try:
            logger.info(f"Extracting photo URLs from: {url}")
            
            # Get the Instagram page
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            html_content = response.text
            logger.info(f"Got HTML content, length: {len(html_content)}")
            
            photo_urls = []
            
            # First, try to find the main JSON data structure
            shared_data_match = re.search(r'<script type="text/javascript">window\._sharedData = (.*?);</script>', html_content)
            if shared_data_match:
                try:
                    shared_data = json.loads(shared_data_match.group(1))
                    logger.info("Found _sharedData, extracting post info...")
                    
                    # Navigate through the JSON structure to find post media
                    if 'entry_data' in shared_data and 'PostPage' in shared_data['entry_data']:
                        post_data = shared_data['entry_data']['PostPage'][0]['graphql']['shortcode_media']
                        
                        # Check if it's a carousel (multiple images)
                        if 'edge_sidecar_to_children' in post_data:
                            edges = post_data['edge_sidecar_to_children']['edges']
                            for edge in edges:
                                node = edge['node']
                                if 'display_url' in node:
                                    photo_urls.append(node['display_url'])
                                    logger.info(f"Found carousel photo: {node['display_url']}")
                        else:
                            # Single image/video
                            if 'display_url' in post_data:
                                photo_urls.append(post_data['display_url'])
                                logger.info(f"Found single photo: {post_data['display_url']}")
                                
                except Exception as e:
                    logger.error(f"Error parsing _sharedData: {e}")
            
            # If no URLs found from _sharedData, try alternative methods
            if not photo_urls:
                logger.info("No URLs from _sharedData, trying alternative extraction...")
                
                # Look for specific Instagram post patterns
                patterns = [
                    r'"display_url":"([^"]+)"',
                    r'"src":"([^"]+\.jpg[^"]*)"',
                    r'"src":"([^"]+\.png[^"]*)"',
                    r'"src":"([^"]+\.webp[^"]*)"'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, html_content, re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, str) and match.startswith('http'):
                            # Clean up the URL
                            clean_url = match.split('\\u0026')[0]  # Remove escaped characters
                            clean_url = clean_url.replace('\\u0026', '&')
                            clean_url = clean_url.replace('\\/', '/')
                            
                            # Filter out Instagram's own assets and logos
                            if (clean_url not in photo_urls and 
                                any(ext in clean_url.lower() for ext in ['.jpg', '.png', '.webp']) and
                                'instagram' not in clean_url.lower() and
                                'logo' not in clean_url.lower() and
                                'icon' not in clean_url.lower() and
                                'cdninstagram' in clean_url.lower()):  # Only Instagram CDN URLs
                                
                                photo_urls.append(clean_url)
                                logger.info(f"Found photo URL: {clean_url}")
            
            # Remove duplicates and filter out any remaining Instagram assets
            unique_urls = []
            for url in list(set(photo_urls)):
                # Additional filtering to exclude Instagram's own assets
                if ('instagram' not in url.lower() or 'cdninstagram' in url.lower()) and \
                   'logo' not in url.lower() and \
                   'icon' not in url.lower() and \
                   'brand' not in url.lower():
                    unique_urls.append(url)
            
            logger.info(f"Found {len(unique_urls)} filtered photo URLs")
            return unique_urls
            
        except Exception as e:
            logger.error(f"Error extracting photo URLs: {e}")
            return []
    
    async def download_photo_from_url(self, photo_url, shortcode, index=0):
        """Download a single photo from URL"""
        try:
            logger.info(f"Downloading photo from: {photo_url}")
            
            # Download the image
            response = self.session.get(photo_url, timeout=30)
            response.raise_for_status()
            
            # Determine file extension
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            elif 'webp' in content_type:
                ext = '.webp'
            else:
                ext = '.jpg'  # Default
            
            # Save the file
            filename = f"instagram_{shortcode}_{index}{ext}"
            file_path = self.temp_dir / filename
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            file_size = file_path.stat().st_size // (1024 * 1024)  # MB
            logger.info(f"Photo downloaded: {file_path} ({file_size}MB)")
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error downloading photo: {e}")
            return None
    
    async def download_instagram_content(self, url):
        """Download Instagram content using multiple methods"""
        try:
            shortcode = self.extract_shortcode(url)
            content_type = self.detect_content_type(url)
            
            if not shortcode:
                return None, "Could not extract Instagram post ID"
            
            logger.info(f"Downloading Instagram {content_type}: {shortcode}")
            
            # For photos, try direct extraction first
            if content_type == 'post':
                photo_urls = self.extract_photo_urls_from_html(url)
                
                if photo_urls:
                    logger.info(f"Found {len(photo_urls)} photo URLs, downloading...")
                    downloaded_files = []
                    
                    for i, photo_url in enumerate(photo_urls[:5]):  # Limit to 5 photos
                        file_path = await self.download_photo_from_url(photo_url, shortcode, i)
                        if file_path:
                            downloaded_files.append(file_path)
                    
                    if downloaded_files:
                        return downloaded_files, None
                    else:
                        logger.warning("Direct photo extraction failed, trying alternative method...")
                
                # Try alternative method using Instagram's public API
                logger.info("Trying alternative photo extraction method...")
                alt_photo_urls = await self.extract_photos_from_api(shortcode)
                if alt_photo_urls:
                    logger.info(f"Found {len(alt_photo_urls)} photo URLs via API, downloading...")
                    downloaded_files = []
                    
                    for i, photo_url in enumerate(alt_photo_urls[:5]):
                        file_path = await self.download_photo_from_url(photo_url, shortcode, i)
                        if file_path:
                            downloaded_files.append(file_path)
                    
                    if downloaded_files:
                        return downloaded_files, None
            
            # Fallback to yt-dlp for videos or if direct extraction failed
            return await self.download_with_ytdlp(url, shortcode, content_type)
                
        except Exception as e:
            logger.error(f"Error downloading Instagram content: {e}")
            return None, f"Error downloading Instagram content: {str(e)}"
    
    async def extract_photos_from_api(self, shortcode):
        """Extract photos using Instagram's public API"""
        try:
            logger.info(f"Trying Instagram API for shortcode: {shortcode}")
            
            # Use Instagram's public API endpoint
            api_url = f"https://www.instagram.com/p/{shortcode}/?__a=1&__d=1"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Referer': 'https://www.instagram.com/',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            response = self.session.get(api_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info("Successfully got API response")
                    
                    photo_urls = []
                    
                    # Navigate through the API response structure
                    if 'items' in data and len(data['items']) > 0:
                        item = data['items'][0]
                        
                        # Check for carousel media
                        if 'carousel_media' in item:
                            for media in item['carousel_media']:
                                if 'image_versions2' in media and 'candidates' in media['image_versions2']:
                                    # Get the highest quality image
                                    candidates = media['image_versions2']['candidates']
                                    if candidates:
                                        photo_urls.append(candidates[0]['url'])
                                        logger.info(f"Found carousel photo: {candidates[0]['url']}")
                        else:
                            # Single media
                            if 'image_versions2' in item and 'candidates' in item['image_versions2']:
                                candidates = item['image_versions2']['candidates']
                                if candidates:
                                    photo_urls.append(candidates[0]['url'])
                                    logger.info(f"Found single photo: {candidates[0]['url']}")
                    
                    return photo_urls
                    
                except json.JSONDecodeError:
                    logger.warning("API response is not valid JSON")
                    return []
            else:
                logger.warning(f"API request failed with status: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error extracting photos from API: {e}")
            return []
    
    async def download_with_ytdlp(self, url, shortcode, content_type):
        """Download using yt-dlp as fallback"""
        try:
            output_template = str(self.temp_dir / f"instagram_ytdlp_{shortcode}.%(ext)s")
            
            cmd = [
                'yt-dlp',
                '--format', 'best[ext=mp4]/best[ext=jpg]/best[ext=png]/best',
                '--output', output_template,
                '--no-playlist',
                '--no-warnings',
                '--quiet',
                '--no-progress',
                url
            ]
            
            logger.info(f"Running yt-dlp command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                downloaded_files = []
                
                # Check for downloaded files
                for file in self.temp_dir.glob(f"instagram_ytdlp_{shortcode}.*"):
                    if file.exists() and file.stat().st_size > 0:
                        file_size = file.stat().st_size // (1024 * 1024)  # MB
                        logger.info(f"yt-dlp download successful: {file} ({file_size}MB)")
                        downloaded_files.append(file)
                
                if downloaded_files:
                    return downloaded_files, None
                else:
                    return None, "yt-dlp completed but no files found"
            else:
                error_msg = result.stderr if result.stderr else "Unknown error"
                return None, f"yt-dlp failed: {error_msg}"
                
        except Exception as e:
            logger.error(f"yt-dlp error: {e}")
            return None, f"yt-dlp error: {str(e)}"
    
    async def send_media(self, chat_id, file_path, caption=""):
        """Send media file to chat"""
        try:
            file_size = file_path.stat().st_size
            
            if file_size > self.config.MAX_FILE_SIZE:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ File too large ({file_size // (1024*1024)}MB). "
                         f"Telegram limit is {self.config.MAX_FILE_SIZE // (1024*1024)}MB."
                )
                return False
            
            logger.info(f"Sending file: {file_path} ({file_size // (1024*1024)}MB)")
            
            # Determine file type and send accordingly
            file_ext = file_path.suffix.lower()
            
            with open(file_path, 'rb') as file:
                if file_ext in ['.mp3', '.m4a', '.aac', '.wav']:
                    # Send as audio
                    await self.bot.send_audio(
                        chat_id=chat_id,
                        audio=file,
                        caption=caption
                    )
                elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    # Send as photo
                    await self.bot.send_photo(
                        chat_id=chat_id,
                        photo=file,
                        caption=caption
                    )
                elif file_ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                    # Send as video
                    await self.bot.send_video(
                        chat_id=chat_id,
                        video=file,
                        caption=caption,
                        supports_streaming=True
                    )
                else:
                    # Send as document
                    await self.bot.send_document(
                        chat_id=chat_id,
                        document=file,
                        caption=caption
                    )
            
            # Clean up
            file_path.unlink()
            logger.info("File sent successfully and cleaned up")
            return True
            
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Error sending file: {str(e)}"
            )
            return False
    
    async def process_update(self, update):
        """Process a single update"""
        if not update.message or not update.message.text:
            return
            
        text = update.message.text
        chat_id = update.message.chat_id
        
        # Handle commands
        if text == '/start':
            await self.bot.send_message(
                chat_id=chat_id,
                text="🤖 **Web Instagram Downloader Bot**\n\n"
                     "Welcome! I can download content from Instagram posts.\n\n"
                     "**Supported Content:**\n"
                     "• Videos from posts and reels ✅\n"
                     "• Photos from posts (including carousel) ✅\n"
                     "• Stories (public only) ⚠️\n"
                     "• Audio from videos ✅\n\n"
                     "**Commands:**\n"
                     "/start - Show this message\n"
                     "/help - Show help information\n"
                     "/status - Check bot status\n\n"
                     "**How to use:**\n"
                     "Send me an Instagram post URL and I'll download the content for you!"
            )
        elif text == '/help':
            await self.bot.send_message(
                chat_id=chat_id,
                text="📖 **Help Information**\n\n"
                     "This bot downloads content from Instagram posts.\n\n"
                     "**Supported URLs:**\n"
                     "• Instagram posts: https://instagram.com/p/...\n"
                     "• Instagram reels: https://instagram.com/reel/...\n"
                     "• Instagram TV: https://instagram.com/tv/...\n"
                     "• Instagram stories: https://instagram.com/stories/...\n"
                     "• User profiles: https://instagram.com/username\n\n"
                     "**Features:**\n"
                     "✅ Video downloads (reels, posts)\n"
                     "✅ Photo downloads (posts, carousel)\n"
                     "⚠️ Story downloads (public only)\n"
                     "✅ Audio extraction\n"
                     "✅ Multiple file support\n"
                     "✅ Direct photo extraction\n"
                     "✅ yt-dlp fallback\n"
                     "✅ 24/7 Online Service\n\n"
                     "**How to use:**\n"
                     "1. Find an Instagram post you want to download\n"
                     "2. Copy the URL\n"
                     "3. Send it to this bot\n"
                     "4. Wait for the content to be downloaded and sent"
            )
        elif text == '/status':
            ytdlp_status = "✅" if self.check_ytdlp() else "❌"
            await self.bot.send_message(
                chat_id=chat_id,
                text="📊 **Bot Status**\n\n"
                     "✅ Bot is running\n"
                     "✅ Web Instagram downloader enabled\n"
                     f"{ytdlp_status} yt-dlp {'installed' if ytdlp_status == '✅' else 'not installed'}\n"
                     "❌ AWS S3 not configured (using local storage)\n"
                     "✅ Direct photo extraction\n"
                     "✅ Multiple content types supported\n"
                     "✅ 24/7 Online Service\n\n"
                     "Ready to download Instagram content!"
            )
        elif self.is_instagram_url(text):
            content_type = self.detect_content_type(text)
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"🔗 **Instagram {content_type.title()} Detected**\n\n"
                     f"Processing your Instagram {content_type}...\n"
                     "⏳ This may take a few moments."
            )
            
            # Download content
            files, error = await self.download_instagram_content(text)
            
            if files and not error:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ **Download Successful!**\n\n"
                         f"Found {len(files)} file(s).\n"
                         "Sending content to you..."
                )
                
                success_count = 0
                for file_path in files:
                    success = await self.send_media(
                        chat_id=chat_id,
                        file_path=file_path,
                        caption=f"📱 Downloaded from Instagram {content_type}"
                    )
                    if success:
                        success_count += 1
                
                if success_count > 0:
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=f"🎉 **Content sent successfully!**\n\n"
                             f"Sent {success_count} out of {len(files)} files.\n"
                             "Enjoy your content! 🎬"
                    )
                else:
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text="❌ **Failed to send any files**\n\n"
                             "All files were too large or had errors."
                    )
            else:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ **Download Failed**\n\n"
                         f"Error: {error}\n\n"
                         "Please check:\n"
                         "• The URL is correct\n"
                         "• The post is public\n"
                         "• The post contains media\n"
                         "• Try a different post"
                )
        else:
            await self.bot.send_message(
                chat_id=chat_id,
                text="💬 **Message Received**\n\n"
                     "I can help you download Instagram content!\n\n"
                     "**Send me:**\n"
                     "• Instagram post URL\n"
                     "• Instagram reel URL\n"
                     "• Instagram story URL\n"
                     "• /help for instructions\n"
                     "• /status to check bot status"
            )
        
        # Update the last processed update ID
        self.last_update_id = update.update_id
    
    def check_ytdlp(self):
        """Check if yt-dlp is installed"""
        try:
            result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

# Create bot instance
config = Config()
bot = WebInstagramBot(config.TELEGRAM_TOKEN)

# Flask routes
@app.route('/')
def health_check():
    """Health check endpoint for deployment platforms"""
    return jsonify({
        "status": "healthy",
        "bot": "Instagram Downloader Bot",
        "version": "1.0.0",
        "uptime": "running"
    })

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint for Telegram updates"""
    try:
        data = request.get_json()
        # Process webhook data here if needed
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

async def bot_loop():
    """Main bot loop"""
    logger.info("🤖 Starting Web Instagram Downloader Bot...")
    logger.info("📱 Bot is running and ready to receive messages!")
    
    # Check dependencies
    if not bot.check_ytdlp():
        logger.warning("⚠️  Warning: yt-dlp is not installed. Please install it for content downloading.")
        logger.warning("   Install with: pip install yt-dlp")
    
    while True:
        try:
            updates = await bot.get_updates()
            for update in updates:
                await bot.process_update(update)
            await asyncio.sleep(1)  # Wait 1 second before checking for new updates
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            await asyncio.sleep(5)  # Wait 5 seconds before retrying

def run_bot():
    """Run the bot in a separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(bot_loop())

if __name__ == "__main__":
    import threading
    
    # Start bot in a separate thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Run Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 