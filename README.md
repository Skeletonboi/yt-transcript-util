# YouTube Transcript Scraper

Python utility that scrapes Youtube transcripts from Youtube channels and videos*, with optional authentication and no IP rate-limiting.

We use Playwright to perform network request interception and replay on "get_transcript" and "timedtext" requests to scrape the transcripts. Authentication for age-restricted and members-only videos require Playwright session cookies from a one-time manual login session (initiated by the tool), which is saved and reused until the cookie expires (typically > 1 year, unless you logout of all devices on your Google/Youtube account).

This library was created as an alternative to existing youtube transcript libraries (such as [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) in light of the new Youtube API per-IP rate-limits which rendered those libraries unusable for high frequency/quantity scraping without needing to use rotating proxies.

*= with the exception of Youtube Shorts

## Installation
1. Create local python environment (Python 3.8+) and install dependencies:
    ```bash
    python -m venv <env_name>
    source <env_name>/bin/activate

    pip install -r requirements.txt
    playwright install chromium
    ```

2. For bulk scraping of all videos from a Youtube channel, set up your [YouTube Data API v3 key](https://console.cloud.google.com/) in `.env` (or pass as an arguement in the CLI using `-k <YT_API_KEY>`):
   ```bash
   YT_API_KEY=your_youtube_api_key_here
   ```

## CLI Usage
### Single Video Scraping
Can be called using either raw video URL or video ID 
```bash
# By video ID
python yt_scraper.py -id VIDEO_ID

# By URL
python yt_scraper.py -url "https://www.youtube.com/watch?v=VIDEO_ID"

# Copy to clipboard
python yt_scraper.py -id VIDEO_ID -c
```
**Options:**
- `-id, --vid_id`: Youtube video ID
- `-url, --vid_url`: Video URL
- `-c, --copy`: Flag to copy output to clipboard (otherwise prints output to console)
- `-cookies, --cookies_path`: Path to optional cookies.json file (for authentication for age-restricted/members-only videos)
- `-auth, --auth`: Flag to generate a one-time authentication session for cookies.json generation (must also provide -cookies arguement)

### Output

Transcripts are saved as JSON files:
```json
{
  "<VIDEO_ID>": {
    "transcript": "Full transcript text...",
    "title": "Video Title",
    "publishedAt": "2023-01-01T00:00:00Z"
  }
}
```
### Bulk Channel Scraping
```bash
# Basic usage
python yt_transcript.py CHANNEL_ID

# With options
python yt_transcript.py CHANNEL_ID -k API_KEY -s ./transcripts -r
```

**Options:**
- `-k, --yt_api_key`: YouTube API key (optional if in .env)
- `-s, --transcript_dir`: Save directory (default: `./transcripts`)
- `-r, --retry_failed`: Retry previously failed videos

Directory structure:
```
transcripts/
├── raw/
    └── CHANNEL_ID.json      # Successful transcripts
└── failed/
    └── CHANNEL_ID.json   # Failed attempts
```

## Example Python Library Usage
### Basic Video Transcript Scraping
```python
import asyncio
from yt_transcript_util.yt_scraper import YoutubeScraper

# Scrape YouTube video transcript (ideally you wrap this as an async function)
YT_VIDEO_ID = "v9c00Ty5Z7U"
scraper = YoutubeScraper.create()
transcript, url, is_english = asyncio.run(await scraper.get_transcript(YT_VIDEO_ID))
await scraper.close()
```
### Authenticated Video Transcript Scraping
```python
import asyncio
import json
from yt_transcript_util.yt_scraper import YoutubeScraper

# Generate and save cookies.json
COOKIES_PATH = "./cookies.json
YoutubeScraper.generate_cookies(COOKIES_PATH)

# Add cookies savepath to scraper 
YT_VIDEO_ID = "v9c00Ty5Z7U"
scraper = YoutubeScraper.create(COOKIES_PATH)
transcript, url, is_english = asyncio.run(await scraper.get_transcript(YT_VIDEO_ID))
await scraper.close()
```
### Bulk Channel Transcript Scraping
```python
import asyncio
 from yt_transcript_util.yt_transcript import YoutubeTranscriptRetriever

YT_CHANNEL_ID = "UClHVl2N3jPEbkNJVx-ItQIQ"
YT_API_KEY = "YOUR_YT_DATA_API_V3_KEY"
TRANSCRIPT_SAVE_DIR = "./transcripts"
RETRY_FAILED = True

# Scrape all video transcripts from YouTube channel
retriever = YoutubeTranscriptRetriever(YT_CHANNEL_ID, YT_API_KEY, TRANSCRIPT_SAVE_DIR, RETRY_FAILED)
scraped_video_dic, failed_video_dic = asyncio.run(retriever.scrape_transcripts())
```

## Notes
- Only processes English transcripts
- Progress saved every 10 videos
- Automatically resumes from where it left off
