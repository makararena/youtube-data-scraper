# Project Structure Documentation

## Overview

YouTube Comment Explorer — unified tool for scraping YouTube data without API:
- Channel videos metadata (newest → oldest)
- Video comments (with sorting and pagination)
- Recursive channel + comments pipeline

## Directory Layout

```
youtube-comment-explorer/
├── scrape.py                        # 🎯 Main CLI entry point
├── data/                            # 📁 All exports (auto-created, gitignored)
│   ├── .gitkeep                     # Keep folder in git
│   ├── <channel-name>/
│   │   ├── videos.json              # Channel videos metadata
│   │   └── comments/                # Per-video comments
│   │       ├── 0001_<videoId>.jsonl
│   │       └── 0002_<videoId>.jsonl
│   └── <video-id>/
│       └── comments.jsonl           # Single video comments
├── shared/                          # 🔧 Common utilities
│   ├── __init__.py
│   └── youtube.py                   # Core scraping logic
├── youtube-channel-videos/          # 📺 Videos scraper module
│   ├── __init__.py
│   └── channel_videos.py
├── youtube-comment-downloader/      # 💬 Comments scraper module
│   ├── __init__.py
│   ├── __main__.py
│   └── downloader.py
├── requirements.txt                 # Python dependencies
├── LICENSE                          # MIT License
├── README.md                        # User documentation
├── STRUCTURE.md                     # This file
└── commands.txt                     # Quick reference

```

## Module Responsibilities

### `scrape.py` (Main CLI)
- Unified command-line interface
- Three subcommands: `videos`, `comments`, `channel-comments`
- Auto-generates output paths in `data/` folder
- Orchestrates calls to scrapers

### `shared/youtube.py` (Core Utilities)
- HTTP session management with consent bypass
- HTML fetching and parsing
- `ytcfg` and `ytInitialData` extraction
- InnerTube API requests
- View count parsing
- Continuation token handling

### `youtube-channel-videos/channel_videos.py`
- `YoutubeChannelVideosScraper` class
- Fetches all videos from a channel (newest → oldest)
- Handles pagination via continuation tokens
- Preserves video order from YouTube's UI
- Outputs JSON with metadata

### `youtube-comment-downloader/downloader.py`
- `YoutubeCommentDownloader` class
- Downloads comments for a video
- Supports sorting (recent/popular)
- Handles nested replies
- Outputs JSONL (line-delimited JSON)

## Data Flow

### 1. Videos Command
```
User → scrape.py videos @channel
  ↓
YoutubeChannelVideosScraper
  ↓
shared.youtube (fetch_html, extract_ytcfg, inertube_ajax_request)
  ↓
data/<channel>/videos.json
```

### 2. Comments Command
```
User → scrape.py comments VIDEO_ID
  ↓
YoutubeCommentDownloader
  ↓
shared.youtube (fetch_html, extract_ytcfg, inertube_ajax_request)
  ↓
data/<video_id>/comments.jsonl
```

### 3. Channel-Comments Command
```
User → scrape.py channel-comments @channel
  ↓
YoutubeChannelVideosScraper (get all videos)
  ↓
data/<channel>/videos.json
  ↓
For each video:
  YoutubeCommentDownloader
    ↓
  data/<channel>/comments/NNNN_<videoId>.jsonl
```

## Key Features

### Auto-Path Generation
- Default paths: `data/<export-name>/`
- Sanitizes channel/video IDs for safe folder names
- Creates directories automatically
- Optional custom paths via `-o` or `--out-dir`

### Resume Support
- `channel-comments` skips existing comment files
- Use `--no-resume` to force re-download

### Progress Tracking
- Real-time video fetch updates
- Comment count per video
- Total statistics

### Error Handling
- Consent redirect bypass
- Robust JSON extraction
- Continuation token fallback

## Output Formats

### Videos JSON
```json
{
  "channel_id": "@channelname",
  "total_videos": 123,
  "videos": [
    {
      "order": 1,
      "video_id": "abc123",
      "title": "Video Title",
      "view_count": 123456,
      "view_count_raw": "123K views",
      "length": "10:25",
      "thumbnail_url": "https://...",
      "url": "https://www.youtube.com/watch?v=abc123",
      "channel_id": "UC..."
    }
  ]
}
```

### Comments JSONL
Each line is a JSON object:
```json
{"cid": "...", "text": "Comment text", "time": "2 days ago", "author": "@user", "channel": "UC...", "votes": "5", "replies": "2", "photo": "https://...", "heart": false, "reply": false}
```

## Dependencies

- `requests` — HTTP client for web scraping
- Python 3.7+ — Type hints, f-strings

## Git Configuration

### `.gitignore`
- Ignores `data/*` (except `.gitkeep`)
- Ignores `venv/`, `__pycache__/`, `*.pyc`
- Ignores `*.json`, `*.jsonl` (except in data/)

### Tracked Files
- Source code (`.py`)
- Documentation (`.md`, `.txt`)
- Config files (`requirements.txt`, `LICENSE`)
- `data/.gitkeep` (keeps folder in repo)

## Development Notes

### Adding New Features
1. Add shared utilities to `shared/youtube.py`
2. Extend scrapers in respective modules
3. Update CLI in `scrape.py`
4. Update README.md

### Testing
```bash
# Quick test
python scrape.py videos @test --max-videos 1
python scrape.py comments VIDEO_ID --limit 1
python scrape.py channel-comments @test --max-videos 1 --per-video-limit 1

# Check data folder
find data -type f
```

### Code Style
- Type hints for function signatures
- Docstrings for public methods
- Descriptive variable names
- Early returns for error handling
- Guard clauses for validation

## Future Enhancements

- [ ] Parallel comment downloads
- [ ] Rate limiting configuration
- [ ] Export to CSV/Parquet
- [ ] Video metadata enrichment (likes, dislikes)
- [ ] Playlist support
- [ ] Search results scraping
- [ ] Live chat archiving
- [ ] Transcript extraction

---

Last updated: 2025-12-24
