# YouTube Comment Explorer

Unified tool for scraping YouTube channel videos metadata and comments without using the YouTube API.

## Features

- **Channel Videos Scraper**: Download all videos metadata from a YouTube channel (newest to oldest)
- **Comment Downloader**: Download all comments for any video (with sorting options)
- **Recursive Pipeline**: Download all videos from a channel + comments for each video automatically
- **Shared Core**: Optimized common code for both scrapers (session management, consent handling, InnerTube API)

## Installation

1. Clone this repository:
```bash
git clone <repo-url>
cd youtube-comment-explorer
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

The main interface is through `scrape.py` which provides three commands.

**All data is automatically saved to `data/<export-name>/` folder structure.**

### 1. Download Channel Videos Metadata

Download all videos from a channel as JSON (ordered newest → oldest):

```bash
# Auto-saves to data/<channel>/videos.json
python scrape.py videos @channelname

# Or specify custom output path
python scrape.py videos @channelname -o custom/path/videos.json
```

Options:
- `-o, --output PATH`: Custom output path (default: `data/<channel>/videos.json`)
- `--max-videos N`: Limit number of videos to fetch
- `--debug`: Enable debug output

Example output structure:
```json
{
  "channel_id": "@channelname",
  "total_videos": 165,
  "videos": [
    {
      "video_id": "abc123",
      "title": "Video Title",
      "order": 1,
      "view_count": 123456,
      "view_count_raw": "123,456 views",
      "length": "10:25",
      "thumbnail_url": "https://...",
      "url": "https://www.youtube.com/watch?v=abc123",
      "channel_id": "UC..."
    }
  ]
}
```

### 2. Download Comments for a Single Video

Download all comments from one video as JSONL (line-delimited JSON):

```bash
# Auto-saves to data/<video_id>/comments.jsonl
python scrape.py comments VIDEO_ID

# Or specify custom output path
python scrape.py comments VIDEO_ID -o custom/path/comments.jsonl
```

Options:
- `-o, --output PATH`: Custom output path (default: `data/<video_id>/comments.jsonl`)
- `--limit N`: Limit number of comments
- `--sort {recent,popular}`: Sort by recent (default) or popular
- `--language LANG`: Language for YouTube generated text (e.g., 'en')

Example output (each line is a JSON object):
```json
{"cid": "...", "text": "Great video!", "time": "2 days ago", "author": "@username", "channel": "UC...", "votes": "5", "replies": "2", "photo": "https://...", "heart": false, "reply": false}
```

### 3. Download Channel Videos + All Comments (Recursive)

Download all videos from a channel and comments for each video:

```bash
# Auto-saves to data/<channel>/
python scrape.py channel-comments @channelname

# Or specify custom output directory
python scrape.py channel-comments @channelname --out-dir custom/output
```

This creates:
- `data/<channel>/videos.json` — all videos metadata
- `data/<channel>/comments/0001_<videoId>.jsonl` — comments for video 1
- `data/<channel>/comments/0002_<videoId>.jsonl` — comments for video 2
- etc.

Options:
- `--out-dir PATH`: Custom output directory (default: `data/<channel>/`)
- `--max-videos N`: Limit number of videos to process
- `--per-video-limit N`: Limit comments per video
- `--no-resume`: Ignore existing files and re-download everything
- `--sort {recent,popular}`: Sort comments by recent (default) or popular
- `--language LANG`: Language for YouTube generated text
- `--debug`: Enable debug output

The scraper will **resume automatically** if interrupted — it skips videos that already have comment files.

## Examples

### Example 1: Quick test with limited videos
```bash
# Auto-saves to data/realmadrid/videos.json
python scrape.py videos @realmadrid --max-videos 10
```

### Example 2: Download comments for a specific video
```bash
# Auto-saves to data/dQw4w9WgXcQ/comments.jsonl
python scrape.py comments dQw4w9WgXcQ --limit 100
```

### Example 3: Full channel backup
```bash
# Auto-saves to data/skryp/
python scrape.py channel-comments @skryp
```

### Example 4: Channel with limits (for testing)
```bash
# Auto-saves to data/channelname/
python scrape.py channel-comments @channelname \
    --max-videos 5 \
    --per-video-limit 50
```

## Project Structure

```
youtube-comment-explorer/
├── scrape.py                        # Main CLI interface
├── data/                            # All exports go here (auto-created)
│   ├── <channel-name>/
│   │   ├── videos.json              # Channel videos metadata
│   │   └── comments/                # Per-video comments
│   │       ├── 0001_<videoId>.jsonl
│   │       └── 0002_<videoId>.jsonl
│   └── <video-id>/
│       └── comments.jsonl           # Single video comments
├── shared/                          # Shared utilities for both scrapers
│   ├── __init__.py
│   └── youtube.py                   # Core YouTube scraping utilities
├── youtube-channel-videos/          # Channel videos scraper module
│   ├── __init__.py
│   └── channel_videos.py
├── youtube-comment-downloader/      # Comment downloader module
│   ├── __init__.py
│   ├── __main__.py
│   └── downloader.py
├── requirements.txt                 # Python dependencies (requests)
├── LICENSE                          # MIT License
└── README.md                        # This file
```

## Technical Details

### Shared Module (`shared/youtube.py`)

Common utilities used by both scrapers:
- **Session Management**: HTTP session with proper headers and consent bypass
- **HTML Fetching**: `fetch_html()` with consent redirect handling
- **Data Extraction**: 
  - `extract_ytcfg()` — extracts YouTube config (API keys, context)
  - `extract_ytinitialdata()` — extracts initial page data
- **InnerTube API**: `inertube_ajax_request()` for pagination
- **Helpers**: 
  - `search_dict()` — recursively search nested dicts (⚠️ doesn't preserve list order)
  - `parse_view_count()` — parse "123K views" → 123000
  - `pick_longest_continuation()` — find video pagination token

### Order Preservation

**Important**: Videos are returned in YouTube's default order (newest → oldest).
- `order` field: 1 = newest video, N = oldest video
- Order is preserved throughout pagination
- The scraper uses explicit list traversal (not `search_dict`) to maintain order

### Consent Handling

The scrapers automatically handle YouTube's GDPR consent redirects without requiring user interaction.

## Output Formats

### Videos JSON
Single JSON file with all videos and metadata. Videos ordered newest to oldest.

### Comments JSONL
Line-delimited JSON (one comment per line). Easy to process with streaming parsers.

Each comment contains:
- `cid`: Comment ID
- `text`: Comment text content
- `time`: Relative time (e.g., "2 days ago")
- `author`: Author username
- `channel`: Author channel ID
- `votes`: Like count
- `replies`: Reply count
- `photo`: Author avatar URL
- `heart`: Has creator heart
- `reply`: Is a reply to another comment

## Requirements

- Python 3.7+
- `requests` library

## License

This project incorporates code from:
- [youtube-comment-downloader](https://github.com/egbertbouman/youtube-comment-downloader) by Egbert Bouman (MIT License)

See individual module directories for original licenses.

## Notes

- **No API key required** — uses YouTube's web interface
- **Rate limiting**: Built-in delays between requests to be respectful to YouTube's servers
- **Resume capability**: The recursive channel-comments command can resume interrupted downloads
- **No authentication**: Works without YouTube account login

## Troubleshooting

### "Failed to extract ytcfg" error
YouTube may have changed their page structure. The HTML is saved to `/tmp/youtube_debug.html` for inspection.

### Consent redirect issues
The scraper should handle consent automatically. If issues persist, try accessing the channel/video in a browser first.

### Comments not downloading
Check if comments are disabled for the video. The scraper will skip videos with disabled comments.
