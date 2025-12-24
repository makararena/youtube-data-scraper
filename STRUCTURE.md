# Project Structure Documentation

## Overview

YouTube Comment Explorer - unified tool for scraping YouTube data without API:
- Channel videos metadata (newest -> oldest)
- Video comments (with sorting and pagination)
- Recursive channel + comments pipeline

## Directory Layout

```
youtube-comment-explorer/
|-- src/
|   `-- ytce/                        # Main python package
|       |-- __init__.py
|       |-- __main__.py              # python -m ytce
|       |-- cli/                     # CLI interface
|       |   `-- main.py
|       |-- pipelines/               # High-level workflows
|       |   |-- channel_videos.py
|       |   |-- video_comments.py
|       |   `-- channel_comments.py
|       |-- youtube/                 # YouTube primitives
|       |   |-- session.py
|       |   |-- html.py
|       |   |-- extractors.py
|       |   |-- innertube.py
|       |   |-- pagination.py
|       |   |-- channel_videos.py
|       |   `-- comments.py
|       |-- storage/                 # output / fs / resume
|       |   |-- paths.py
|       |   |-- writers.py
|       |   `-- resume.py
|       |-- models/                  # typed structures
|       |   |-- video.py
|       |   `-- comment.py
|       `-- utils/
|           |-- logging.py
|           |-- parsing.py
|           `-- helpers.py
|-- data/                            # All exports (auto-created, gitignored)
|   `-- .gitkeep                     # Keep folder in git
|-- docs/
|   `-- commands.txt                 # Quick reference
|-- scripts/                         # Dev/debug scripts
|-- tests/
|-- requirements.txt                 # Python dependencies
|-- pyproject.toml
|-- LICENSE
|-- README.md
`-- STRUCTURE.md
```

## Module Responsibilities

### `src/ytce/cli/main.py` (Main CLI)
- Unified command-line interface
- Three subcommands: `videos`, `comments`, `channel-comments`
- Auto-generates output paths in `data/` folder
- Orchestrates calls to pipelines

### `src/ytce/pipelines/`
- `channel_videos.py`: exports videos metadata JSON
- `video_comments.py`: exports comments JSONL for a single video
- `channel_comments.py`: exports channel videos + per-video comments JSONL

### `src/ytce/youtube/`
- `session.py`: session headers and consent bypass
- `html.py`: `fetch_html()`
- `extractors.py`: `extract_ytcfg()`, `extract_ytinitialdata()`
- `innertube.py`: InnerTube API requests
- `pagination.py`: continuation helpers, `search_dict()`
- `channel_videos.py`: `YoutubeChannelVideosScraper`
- `comments.py`: `YoutubeCommentDownloader`

### `src/ytce/storage/`
- `paths.py`: default output paths
- `writers.py`: JSON and JSONL writers
- `resume.py`: skip/resume behavior

## Data Flow

### 1. Videos Command
```
User -> ytce videos @channel
  -> pipelines.channel_videos
  -> youtube.channel_videos + youtube.*
  -> data/<channel>/videos.json
```

### 2. Comments Command
```
User -> ytce comments VIDEO_ID
  -> pipelines.video_comments
  -> youtube.comments + youtube.*
  -> data/<video_id>/comments.jsonl
```

### 3. Channel-Comments Command
```
User -> ytce channel-comments @channel
  -> pipelines.channel_comments
  -> data/<channel>/videos.json
  -> data/<channel>/comments/NNNN_<videoId>.jsonl
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

- `requests` - HTTP client for web scraping
- Python 3.7+ - type hints, f-strings

## Git Configuration

### `.gitignore`
- Ignores `data/*` (except `.gitkeep`)
- Ignores `venv/`, `__pycache__/`, `*.pyc`
- Ignores `*.json`, `*.jsonl` (except in data/)

### Tracked Files
- Source code (`.py`)
- Documentation (`.md`, `.txt`)
- Config files (`requirements.txt`, `pyproject.toml`, `LICENSE`)
- `data/.gitkeep` (keeps folder in repo)

## Development Notes

### Adding New Features
1. Add shared utilities to `src/ytce/youtube/`
2. Extend pipelines in `src/ytce/pipelines/`
3. Update CLI in `src/ytce/cli/main.py`
4. Update README.md

### Testing
```bash
# Quick test
PYTHONPATH=src python -m ytce videos @test --max-videos 1
PYTHONPATH=src python -m ytce comments VIDEO_ID --limit 1
PYTHONPATH=src python -m ytce channel-comments @test --max-videos 1 --per-video-limit 1

# Check data folder
find data -type f
```

### Code Style
- Type hints for function signatures
- Docstrings for public methods
