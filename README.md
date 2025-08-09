# Instagram Video Downloader Telegram Bot

A powerful Telegram bot that downloads and processes Instagram videos with advanced features including proxy support, AWS S3 storage, and video compression.

## 🚀 Features

- **Instagram Video Download**: Download videos from posts, reels, and IGTV
- **Proxy Support**: Rotating proxy support for better reliability
- **Video Processing**: FFmpeg integration for video compression and conversion
- **Cloud Storage**: AWS S3 integration for temporary file storage
- **Async Architecture**: Built with python-telegram-bot v20+ for high performance
- **Automatic Compression**: Videos are automatically compressed to meet Telegram's 50MB limit
- **User-Friendly Interface**: Rich messages with progress updates and inline buttons

## 📋 Requirements

- Python 3.8+
- FFmpeg (for video processing)
- AWS S3 bucket (for temporary storage)
- Telegram Bot Token
- Instagram credentials (optional, for better access)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ig-downloader
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg**
   - **Windows**: Download from [FFmpeg website](https://ffmpeg.org/download.html)
   - **macOS**: `brew install ffmpeg`
   - **Ubuntu/Debian**: `sudo apt install ffmpeg`

4. **Set up environment variables**
   ```bash
   cp env_example.txt .env
   # Edit .env with your configuration
   ```

5. **Configure AWS S3**
   - Create an S3 bucket
   - Create an IAM user with S3 access
   - Add credentials to `.env`

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Required
TELEGRAM_TOKEN=your_telegram_bot_token
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
S3_BUCKET_NAME=your_bucket_name

# Optional
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password
PROXY_LIST=proxy1:port,proxy2:port
PROXY_USERNAME=proxy_user
PROXY_PASSWORD=proxy_pass
FFMPEG_PATH=/path/to/ffmpeg
```

### Getting Telegram Bot Token

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot`
3. Follow the instructions to create your bot
4. Copy the token and add it to your `.env` file

## 🚀 Usage

### Starting the Bot

```bash
python bot.py
```

### Bot Commands

- `/start` - Show welcome message and basic help
- `/help` - Show detailed help and troubleshooting
- `/status` - Check bot status and component health

### Using the Bot

1. Send an Instagram post/reel URL to the bot
2. The bot will:
   - Fetch post information
   - Download the video
   - Process and compress if needed
   - Upload to S3 (optional)
   - Send the video back to you

### Supported URL Formats

- `https://www.instagram.com/p/SHORTCODE/` - Posts
- `https://www.instagram.com/reel/SHORTCODE/` - Reels
- `https://www.instagram.com/tv/SHORTCODE/` - IGTV

## 🏗️ Architecture

### Components

1. **Instagram Scraper** (`instagram_scraper.py`)
   - Uses instaloader for Instagram API access
   - Supports proxy rotation
   - Handles authentication

2. **Video Processor** (`video_processor.py`)
   - FFmpeg integration for video processing
   - Automatic compression
   - Format conversion

3. **S3 Storage** (`s3_storage.py`)
   - AWS S3 integration for temporary storage
   - Presigned URL generation
   - Automatic cleanup

4. **Proxy Manager** (`proxy_manager.py`)
   - Rotating proxy support
   - Proxy health checking
   - Automatic failover

5. **Telegram Bot** (`bot.py`)
   - Main bot logic
   - User interaction handling
   - Progress updates

### File Structure

```
ig-downloader/
├── bot.py                 # Main bot application
├── config.py             # Configuration management
├── instagram_scraper.py  # Instagram scraping logic
├── video_processor.py    # Video processing with FFmpeg
├── s3_storage.py         # AWS S3 integration
├── proxy_manager.py      # Proxy management
├── requirements.txt      # Python dependencies
├── env_example.txt       # Environment variables example
├── README.md            # This file
└── temp/                # Temporary files directory
```

## 🔧 Advanced Configuration

### Proxy Setup

For better reliability, especially when dealing with rate limits:

```env
PROXY_LIST=proxy1.example.com:8080,proxy2.example.com:8080
PROXY_USERNAME=your_proxy_username
PROXY_PASSWORD=your_proxy_password
```

### Instagram Authentication

For better access to Instagram content:

```env
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password
```

### Custom FFmpeg Path

If FFmpeg is not in your system PATH:

```env
FFMPEG_PATH=/usr/local/bin/ffmpeg
```

## 🐛 Troubleshooting

### Common Issues

1. **"FFmpeg not found"**
   - Install FFmpeg and ensure it's in your PATH
   - Or set `FFMPEG_PATH` in your `.env` file

2. **"S3 connection failed"**
   - Check your AWS credentials
   - Ensure the S3 bucket exists and is accessible
   - Verify IAM permissions

3. **"Instagram download failed"**
   - Try using Instagram credentials
   - Check if the post is public
   - Use proxy configuration for better reliability

4. **"Video too large"**
   - Videos are automatically compressed
   - Check FFmpeg installation
   - Ensure sufficient disk space

### Logs

The bot logs all activities. Check the console output for detailed error messages.

## 🔒 Security Considerations

- Never commit your `.env` file to version control
- Use IAM roles with minimal required permissions for AWS
- Regularly rotate your API keys and tokens
- Monitor bot usage and implement rate limiting if needed

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the logs for error details

## ⚠️ Disclaimer

This bot is for educational purposes. Please respect Instagram's Terms of Service and only download content you have permission to access. The developers are not responsible for any misuse of this tool. 