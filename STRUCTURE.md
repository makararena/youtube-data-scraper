# Project Structure Documentation

## Overview

YouTube Data Scraper - unified tool for scraping YouTube data without API:
- Channel videos metadata (newest -> oldest)
- Video comments (with sorting and pagination)
- Recursive channel + comments pipeline
- **Batch processing for multiple channels**
- **AI comment analysis** (sentiment, translation, classification, scoring)
- Configuration management via ytce.yaml
- Multiple export formats (JSON, CSV, Parquet)
- Beautiful progress output with emojis

## Directory Layout

```
youtube-data-scraper/
|-- src/
|   `-- ytce/                        # Main python package
|       |-- __init__.py
|       |-- __main__.py              # python -m ytce
|       |-- config.py                # Configuration management
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
|       |-- storage/                 # output / fs
|       |   |-- paths.py
|       |   `-- writers.py
|       |-- models/                  # typed structures
|       |   |-- video.py
|       |   `-- comment.py
|       |-- ai/                      # AI analysis engine
|       |   |-- domain/              # Domain models (immutable)
|       |   |   |-- comment.py
|       |   |   |-- config.py
|       |   |   |-- result.py
|       |   |   `-- task.py
|       |   |-- input/               # Input parsers
|       |   |   |-- comments.py
|       |   |   |-- config.py
|       |   |   |-- job.py
|       |   |   |-- questions.py
|       |   |   `-- validators.py
|       |   |-- models/              # LLM adapters
|       |   |   |-- base.py
|       |   |   |-- errors.py
|       |   |   |-- openai.py
|       |   |   `-- tokens.py
|       |   |-- promts/              # Prompt compilation
|       |   |   |-- compiler.py
|       |   |   |-- formatter.py
|       |   |   `-- templates.py
|       |   |-- runner/              # Orchestration
|       |   |   |-- analysis.py
|       |   |   |-- batching.py
|       |   |   `-- checkpoint.py
|       |   |-- tasks/               # Task executors
|       |   |   |-- base.py
|       |   |   |-- binary_classification.py
|       |   |   |-- multi_class.py
|       |   |   |-- multi_label.py
|       |   |   |-- scoring.py
|       |   |   `-- translation.py
|       |   |-- output/              # CSV export
|       |   |   |-- csv.py
|       |   |   `-- formatter.py
|       |   |-- README.md
|       |   |-- ARCHITECTURE.md
|       |   `-- TROUBLESHOOTING.md
|       `-- utils/
|           |-- logging.py
|           |-- parsing.py
|           |-- helpers.py
|           `-- progress.py
|-- data/                            # All exports (auto-created, gitignored)
|   `-- results/                     # AI analysis results
|       `-- VIDEO_ID/
|           `-- results.csv
|-- examples/                        # Example question files
|   `-- questions/
|       |-- basic-sentiment.yaml
|       |-- comprehensive-analysis.yaml
|       |-- content-moderation.yaml
|       |-- product-feedback.yaml
|       |-- translation-multilanguage.yaml
|       `-- README.md
|-- docs/
|   |-- commands.txt                 # Legacy reference
|   |-- QUICK_REFERENCE.md           # Quick command reference
|   `-- ytce.yaml.example            # Example config file
|-- scripts/                         # Dev/debug scripts
|-- tests/
|-- requirements.txt                 # Python dependencies
|-- pyproject.toml
|-- LICENSE
|-- README.md
|-- STRUCTURE.md
`-- ytce.yaml                        # Config file (created by ytce init)
```

## Module Responsibilities

### `src/ytce/cli/main.py` (Main CLI)
- Unified command-line interface
- Seven subcommands: `init`, `channel`, `video`, `comments`, `batch`, `open`, `analyze`
- Auto-generates output paths in `data/` folder
- Loads configuration from ytce.yaml
- Orchestrates calls to pipelines
- AI analysis command (`analyze`) with dry-run support

### `src/ytce/pipelines/`
- `channel_videos.py`: exports videos metadata in JSON, CSV, or Parquet format
- `video_comments.py`: exports comments in JSONL, CSV, or Parquet format for a single video
- `channel_comments.py`: (legacy) exports channel videos + per-video comments
- `scraper.py`: **core scraping logic** - reusable `scrape_channel()` function
- `batch.py`: batch processing for multiple channels with reports

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
- `writers.py`: JSON, JSONL, CSV, and Parquet writers

### `src/ytce/ai/` (AI Analysis Engine)
Standalone AI analysis engine for text comments. Works with any comment source (YouTube, CSV, etc.).

**Domain Layer** (`domain/`):
- Pure immutable data models (no I/O, no API calls)
- `Comment`: input comment object
- `TaskConfig`, `TaskType`: describes what to compute
- `TaskResult`, `EnrichedComment`, `AnalysisResult`: normalized outputs

**Input Layer** (`input/`):
- `job.py`: loads `questions.yaml` into `JobSpec`
- `comments.py`: loads comments from file (CSV/JSONL/Parquet) with field mapping
- `validators.py`: validates task configurations

**Models Layer** (`models/`):
- `base.py`: `ModelAdapter` interface
- `openai.py`: OpenAI API adapter
- `MockAdapter`: dry-run mode (no network calls)

**Prompts Layer** (`promts/`):
- `compiler.py`: builds deterministic prompts per `TaskType`
- `templates.py`: prompt templates for each task type
- Enforces strict JSON output shape

**Tasks Layer** (`tasks/`):
- Task executors: `binary_classification`, `multi_class`, `multi_label`, `scoring`, `translation`
- Pure execution logic (no file I/O)
- Compile prompts → call model → parse/validate JSON → return `TaskResult`

**Runner Layer** (`runner/`):
- `analysis.py`: main `run_analysis()` orchestrator
- `batching.py`: batch management
- `checkpoint.py`: resume support for long-running analyses

**Output Layer** (`output/`):
- `csv.py`: flattens results into CSV columns
- `formatter.py`: result formatting helpers

## Data Flow

### 1. Init Command
```
User -> ytce init
  -> config.init_project()
  -> Creates data/ directory
  -> Creates ytce.yaml config file
  -> Creates channels.txt template
```

### 2. Channel Command (with comments)
```
User -> ytce channel @channel
  -> config.load_config()
  -> pipelines.channel_comments
  -> youtube.channel_videos + youtube.comments
  -> data/<channel>/videos.json
  -> data/<channel>/comments/NNNN_<videoId>.jsonl
```

### 3. Channel Command (videos only)
```
User -> ytce channel @channel --videos-only
  -> config.load_config()
  -> pipelines.channel_videos
  -> youtube.channel_videos + youtube.*
  -> data/<channel>/videos.json
```

### 4. Comments Command
```
User -> ytce comments VIDEO_ID
  -> config.load_config()
  -> pipelines.video_comments
  -> youtube.comments + youtube.*
  -> data/<video_id>/comments.jsonl
```

### 5. Open Command
```
User -> ytce open @channel
  -> Detects output directory
  -> Opens in system file manager
```

### 6. Batch Command
```
User -> ytce batch channels.txt
  -> config.load_config()
  -> utils.channels.parse_channels_file()
  -> For each channel:
     -> pipelines.scraper.scrape_channel()
     -> Collects ChannelStats
  -> Generates BatchReport
  -> Saves report.json + errors.log to data/_batch/
  -> data/<channel1>/, data/<channel2>/, ...
```

### 7. Analyze Command (AI Analysis)
```
User -> ytce analyze questions.yaml
  -> config.load_config()
  -> ai.input.job.load_job() -> JobSpec
  -> ai.input.comments.load_comments_from_config() -> List[Comment]
  -> ai.runner.analysis.run_analysis()
     -> For each task:
        -> Batch comments
        -> ai.tasks.execute_task() -> Dict[comment_id, TaskResult]
        -> Merge into EnrichedComment
  -> ai.output.write_csv_from_analysis_result()
  -> data/results/<VIDEO_ID>/results.csv
```

## Key Features

### Auto-Path Generation
- Default paths: `data/<export-name>/`
- Sanitizes channel/video IDs for safe folder names
- Creates directories automatically
- Optional custom paths via `-o` or `--out-dir`

### Configuration Management
- `ytce.yaml` for project-level defaults
- Smart defaults from config file
- Command-line flags override config
- Graceful degradation if PyYAML not installed

### Fresh Scraping
- Each channel scrape starts fresh, deleting any existing data
- Simple and predictable behavior
- No complex state management

### Progress Tracking
- Beautiful emoji-based progress indicators
- Real-time statistics with percentages and ETA
- Data size tracking (KB/MB/GB)
- Comment count per video
- Final statistics summary box
- Ctrl+C safe interruption with confirmation
- Error handling with clear messages

### Error Handling
- Consent redirect bypass
- Robust JSON extraction
- Continuation token fallback

## Output Formats

The tool supports three export formats: **JSON**, **CSV**, and **Parquet**. Use the `--format` flag to specify your preferred format.

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
      "title_length": 11,
      "view_count": 123456,
      "view_count_raw": "123K views",
      "length": "10:25",
      "length_minutes": 10.417,
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
{"cid": "...", "text": "Comment text", "text_length": 12, "time": "2 days ago", "author": "@user", "channel": "UC...", "votes": "5", "replies": "2", "photo": "https://...", "heart": false, "reply": false}
```

### CSV Format
Videos and comments can be exported to CSV files with headers, suitable for spreadsheet applications and data analysis tools.

### Parquet Format
Videos and comments can be exported to Apache Parquet format, a columnar storage format ideal for data analytics and processing with tools like Pandas, DuckDB, or Apache Spark. Parquet files use Snappy compression for efficient storage.

## Dependencies

**Core:**
- `requests` - HTTP client for web scraping
- `pyyaml` - YAML config file support
- `pyarrow` - Parquet file format support
- Python 3.7+ - type hints, f-strings

**AI Analysis (optional):**
- `openai` - OpenAI API client (required for `ytce analyze` without `--dry-run`)
- `pandas` - CSV/Parquet file handling (required for CSV/Parquet formats)

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
# Install in editable mode
pip install -e .

# Initialize project
ytce init

# Quick test
ytce channel @test --limit 1
ytce comments VIDEO_ID --limit 1

# Test different formats
ytce channel @test --limit 1 --format csv
ytce channel @test --limit 1 --format parquet
ytce comments VIDEO_ID --limit 1 --format parquet

# Test batch processing
# Edit channels.txt with test channels
ytce batch channels.txt --limit 1 --dry-run
ytce batch channels.txt --limit 1 --format parquet

# Check data folder
find data -type f

# Open output
ytce open @test
```

### Code Style
- Type hints for function signatures
- Docstrings for public methods
