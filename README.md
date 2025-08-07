# YouTube Transcript Scraper

A Python utility for downloading transcripts in bulk from a Youtube channel or from an individual video.

This package was created as an alternative to existing youtube transcript libraries to avoid the new Youtube API per-IP limitations which rendered those libraries unusable without the use of rotating proxies.

## Installation
0. Create local python environment (Python 3.8+)
    ```bash
    python -m venv <env_name>
    ```
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. Optionally set up YouTube API key in `.env` (if not, must be passed in using `-k <YT_API_KEY>`):
   ```bash
   YT_API_KEY=your_youtube_api_key_here
   ```

## Usage

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

### Single Video Scraping
Can be called using either raw video URL or video ID 
```bash
# By video ID
python yt_scraper.py -v VIDEO_ID

# By URL
python yt_scraper.py -u "https://www.youtube.com/watch?v=VIDEO_ID"

# Copy to clipboard
python yt_scraper.py -v VIDEO_ID -c
```
**Options:**
- `-v, --vid_id`: Youtube video ID
- `-u, --vid_url`: Video URL
- `-c, --copy`: Copy output to clipboard (otherwise prints output to console)
## Output

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

Directory structure:
```
transcripts/
├── raw/
    └── CHANNEL_ID.json      # Successful transcripts
└── failed/
    └── CHANNEL_ID.json   # Failed attempts
```

## Notes

- Only processes English transcripts
- Requires YouTube Data API key ([get one here](https://developers.google.com/youtube/v3/getting-started))
- Progress saved every 10 videos
- Automatically resumes from where it left off