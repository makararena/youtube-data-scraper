# YouTube Data Scraper

![Python](https://img.shields.io/badge/python-3.7%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![CLI](https://img.shields.io/badge/interface-CLI-orange)
![No API](https://img.shields.io/badge/youtube-no%20api%20key-red)


Download YouTube videos metadata and comments without using the YouTube API.

## TL;DR

```bash
pip install -e .
ytce channel @realmadrid
```

That's it! Your data will be in `data/realmadrid/`

## Quick Start

### 1. Install

```bash
pip install -e .
```

### 2. Initialize (optional but recommended)

```bash
ytce init
```

This creates:
- `data/` directory for outputs
- `ytce.yaml` config file with smart defaults
- `channels.txt` template for batch scraping

### 3. Download data

**Single channel:**
```bash
# Download channel videos + all comments
ytce channel @skryp

# Download only videos metadata (no comments)
ytce channel @skryp --videos-only

# Download comments for a specific video
ytce comments dQw4w9WgXcQ

# Open the downloaded data
ytce open @skryp
```

**Multiple channels (batch):**
```bash
# Edit channels.txt with your channels
# Then run batch scraping
ytce batch channels.txt
```

## Usage

### Batch Scraping (Multiple Channels)

The most efficient way to scrape multiple channels:

```bash
# 1. Initialize project (creates channels.txt template)
ytce init

# 2. Edit channels.txt with your channel list

# 3. Run batch scraping
ytce batch channels.txt
```

This will:
1. Process each channel sequentially
2. Save results to `data/<channel>/`
3. Create batch report in `data/_batch/<timestamp>/`

**channels.txt format:**

```text
# List your channels, one per line
# Supported formats:
@skryp
@errornil
https://www.youtube.com/@realmadrid
https://www.youtube.com/channel/UC1234567890
UC1234567890

# Lines starting with # are comments
# Empty lines are ignored
```

**Batch options:**

```bash
# Export to Parquet format
ytce batch channels.txt --format parquet

# Limit videos and comments
ytce batch channels.txt --limit 10 --per-video-limit 100

# Preview without downloading
ytce batch channels.txt --dry-run

# Stop on first error
ytce batch channels.txt --fail-fast

# Add delay between channels (default: 2 seconds)
ytce batch channels.txt --sleep-between 5
```

**Batch artifacts:**

After running batch, you'll find:

```
data/
├── _batch/
│   └── 2025-01-05_12-30/
│       ├── channels.txt    # Snapshot of your channels file
│       ├── report.json     # Machine-readable results
│       └── errors.log      # Error details (if any)
├── channel1/
│   ├── videos.json
│   └── comments/
└── channel2/
    ├── videos.json
    └── comments/
```

**Batch output example:**

```
▶ Reading channels from: channels.txt
✔ Found 12 channel(s) to process

▶ [1/12] Processing: @skryp
...
✔ [1/12] @skryp — 312 videos — 45,832 comments — OK (8.7 MB, 15m 42s)

▶ [2/12] Processing: @errornil
...
✔ [2/12] @errornil — 198 videos — 12,453 comments — OK (3.2 MB, 8m 15s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Batch completed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✔ Channels OK:     12
✖ Channels failed: 0
📼 Total videos:   5,321
💬 Total comments: 1,240,331
📦 Total data:     1.34 GB
⏱ Total time:     1h 29m
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✔ Batch artifacts saved to: data/_batch/2025-01-05_12-30/
```

### Channel (videos + comments)

Download all videos and comments from a channel:

```bash
ytce channel @channelname
```

This will:
1. Fetch all videos from the channel
2. Download comments for each video
3. Save everything to `data/channelname/`

**Options:**
- `--videos-only` - Download only videos metadata, skip comments
- `--limit N` - Process only first N videos
- `--per-video-limit N` - Download max N comments per video
- `--sort {recent,popular}` - Comment sort order (default: from config)
- `--language CODE` - Language for YouTube UI (default: from config)
- `--format {json,csv,parquet}` - Output format (default: json)

**Examples:**

```bash
# Quick test with 5 videos
ytce channel @realmadrid --limit 5

# Get popular comments instead of recent
ytce channel @skryp --sort popular

# Limit comments per video
ytce channel @channelname --limit 10 --per-video-limit 100

# Export to CSV format
ytce channel @channelname --format csv

# Export to Parquet format (ideal for data analysis)
ytce channel @channelname --format parquet
```

### Comments (single video)

Download comments for one video:

```bash
ytce comments VIDEO_ID
```

**Options:**
- `--limit N` - Download max N comments
- `--sort {recent,popular}` - Sort order
- `--language CODE` - Language code
- `--format {jsonl,csv,parquet}` - Output format (default: jsonl)
- `-o PATH` - Custom output path

**Examples:**

```bash
ytce comments dQw4w9WgXcQ --limit 500

# Export to Parquet format
ytce comments dQw4w9WgXcQ --format parquet
```

### Open Output Directory

Quickly open the data folder in your file manager:

```bash
ytce open @channelname
ytce open VIDEO_ID
```

## Output Structure

After running `ytce channel @skryp`, you'll get:

```
data/
└── skryp/
    ├── videos.json              # All videos metadata (or .csv/.parquet)
    └── comments/
        ├── 0001_VIDEO_ID.jsonl  # Comments for video 1 (or .csv/.parquet)
        ├── 0002_VIDEO_ID.jsonl  # Comments for video 2
        └── ...
```

### Export Formats

ytce supports three export formats:

- **JSON/JSONL** (default) - Human-readable, ideal for web apps and general use
- **CSV** - Compatible with Excel, spreadsheets, and traditional BI tools
- **Parquet** - Columnar format with compression, ideal for data analysis with Pandas, DuckDB, or Apache Spark

### Videos JSON

Single JSON file with all videos:

```json
{
  "channel_id": "@skryp",
  "total_videos": 312,
  "scraped_at": "2025-01-05T12:34:56+00:00",
  "source": "ytce/0.2.0",
  "videos": [
    {
      "video_id": "abc123",
      "title": "Video Title",
      "title_length": 11,
      "order": 1,
      "view_count": 123456,
      "view_count_raw": "123,456 views",
      "length": "10:25",
      "length_minutes": 10.417,
      "thumbnail_url": "https://...",
      "url": "https://www.youtube.com/watch?v=abc123",
      "channel_id": "UC..."
    }
  ]
}
```

**Guaranteed fields:**
- `channel_id` (string)
- `total_videos` (integer)
- `scraped_at` (ISO 8601 timestamp)
- `source` (string, ytce version)
- `videos` (array)

**Each video object contains:**
- `video_id` (string) - YouTube video ID
- `title` (string) - Video title
- `title_length` (integer) - Character count of title
- `url` (string) - Full YouTube URL
- `order` (integer) - 1 = newest, N = oldest
- `channel_id` (string) - Channel ID (now always populated)
- `view_count` (integer or null) - Parsed view count
- `view_count_raw` (string) - Original view count text
- `length` (string) - Duration (e.g., "21:47")
- `length_minutes` (float or null) - Duration in minutes for sorting
- `thumbnail_url` (string) - Thumbnail URL

### Comments JSONL

Line-delimited JSON (one comment per line):

```jsonl
{"cid": "...", "text": "Great video!", "text_length": 13, "time": "2 days ago", "author": "@user", "channel": "UC...", "votes": "5", "replies": "2", "photo": "https://...", "heart": false, "reply": false, "scraped_at": "2025-01-05T12:34:56+00:00", "source": "ytce/0.2.0"}
{"cid": "...", "text": "Another comment", "text_length": 15, "time": "1 week ago", "author": "@another", "channel": "UC...", "votes": "12", "replies": "0", "photo": "https://...", "heart": true, "reply": false, "scraped_at": "2025-01-05T12:34:56+00:00", "source": "ytce/0.2.0"}
```

**Guaranteed fields (each comment):**
- `cid` (string) - Comment ID
- `text` (string) - Comment text
- `text_length` (integer) - Character count of comment
- `time` (string) - Relative time (e.g., "2 days ago")
- `author` (string) - Author username
- `channel` (string) - Author channel ID
- `votes` (string) - Like count
- `replies` (string) - Reply count
- `photo` (string) - Author avatar URL
- `heart` (boolean) - Has creator heart
- `reply` (boolean) - Is a reply
- `scraped_at` (string) - ISO 8601 timestamp
- `source` (string) - ytce version

### Format Guarantees

**Stability Promise:**
- ✅ All documented fields will always be present
- ✅ Field types will never change
- ✅ New fields may be added in the future (but never removed)
- ✅ One JSON file = one JSON object
- ✅ One JSONL file = one JSON object per line

This makes ytce safe for:
- Data pipelines
- BI tools
- Machine learning
- Long-term archival

## AI Comment Analysis

Analyze your scraped comments using AI to extract insights, sentiment, topics, and more. The AI analysis feature supports multiple task types including classification, scoring, and **translation**.

### Quick Start

1. **Initialize a questions file:**
   ```bash
   ytce init
   ```
   This creates `questions.yaml` in your project root.

2. **Edit `questions.yaml`** to define your analysis tasks (see examples below)

3. **Run analysis:**
   ```bash
   # Test with mock data (no API calls)
   ytce analyze questions.yaml --dry-run

   # Real analysis (requires OpenAI API key)
   export OPENAI_API_KEY="sk-..."
   ytce analyze questions.yaml --model gpt-4.1-nano
   ```

### Example: Basic Sentiment Analysis

```yaml
version: 1

input:
  path: "./data/VIDEO_ID/comments.jsonl"
  format: jsonl
  id_field: cid
  text_field: text

tasks:
  - id: sentiment
    type: multi_class
    question: "What is the sentiment of this comment?"
    labels: ["positive", "neutral", "negative"]
```

### Example: Translation

Translate comments to any language for international audience analysis:

```yaml
version: 1

input:
  path: "./data/VIDEO_ID/comments.jsonl"
  format: jsonl
  id_field: cid
  text_field: text

tasks:
  - id: translation_ru
    type: translation
    question: "Translate this comment to Russian, preserving the original meaning, tone, and any technical terms or product names."
    target_language: "Russian"
```

**Translation Use Cases:**
- **International audience analysis**: Understand feedback from non-English speaking viewers
- **Multilingual team collaboration**: Translate comments for team members who speak different languages
- **Cross-language content analysis**: Compare sentiment and topics across language barriers
- **Localization insights**: Identify region-specific concerns and preferences

### Supported Task Types

1. **Translation** (`translation`)
   - Translate comments to any target language
   - Preserves meaning, tone, and technical terms
   - Required: `target_language` field

2. **Binary Classification** (`binary_classification`)
   - Classify into one of two categories
   - Example: spam detection (yes/no)

3. **Multi-Class Classification** (`multi_class`)
   - Classify into exactly one category from multiple options
   - Example: sentiment (positive/neutral/negative)

4. **Multi-Label Classification** (`multi_label`)
   - Assign multiple labels to each comment
   - Example: topics (can have multiple topics per comment)

5. **Scoring** (`scoring`)
   - Assign numeric scores within a range
   - Example: toxicity score (0.0 to 1.0)

6. **Language Detection** (`language_detection`)
   - Detect the primary language of each comment
   - Returns ISO 639-1 or ISO 639-2 language codes (e.g., "en", "ru", "es")
   - Example: identify which comments are in different languages

### Output Structure

Results are automatically organized by video ID:

```
data/
└── results/
    └── VIDEO_ID/
        ├── results.csv          # Full analysis results
        └── results.preview.csv  # Preview results (if run interactively)
```

Each task creates two CSV columns:
- `{task_id}_value`: The analysis result
- `{task_id}_confidence`: Confidence score (0.0-1.0)

### Example Questions Files

See `examples/questions/` for ready-to-use templates:

- **`basic-sentiment.yaml`** - Simple sentiment analysis
- **`language-detection.yaml`** - Detect comment languages
- **`translation-multilanguage.yaml`** - Translate to multiple languages
- **`product-feedback.yaml`** - Comprehensive product feedback analysis
- **`content-moderation.yaml`** - Spam and toxicity detection
- **`comprehensive-analysis.yaml`** - Full-featured multi-task analysis

### Configuration

**API Key Setup:**
```bash
# Set globally
ytce key YOUR_API_KEY

# Or use environment variable
export OPENAI_API_KEY="sk-..."
```

**Analysis Options:**
```bash
# Limit to first N comments (useful for testing)
ytce analyze questions.yaml --max-comments 100

# Adjust batch size (default: 20)
ytce analyze questions.yaml --batch-size 10

# Use different model
ytce analyze questions.yaml --model gpt-4.1-mini

# Test without API calls
ytce analyze questions.yaml --dry-run
```

### Advanced: Custom Prompts

Add context to improve analysis accuracy:

```yaml
custom_prompt: |
  This video announces a new product feature. We're analyzing user comments to identify:
  - Feature requests and product improvement suggestions
  - User sentiment and concerns
  - Use cases and expectations
  - Pain points and issues users are experiencing
```

The custom prompt is included in all analysis tasks to provide context about your channel, product, or use case.

### Tips

- **Start with dry-run**: Test your questions.yaml with `--dry-run` before spending API credits
- **Use translation**: Add translation tasks to analyze international audiences
- **Combine tasks**: Mix different task types for comprehensive insights
- **Batch size**: Smaller batches (10-15) work better for longer comments
- **Preview mode**: Interactive runs show preview results first and ask to proceed

For more details, see `src/ytce/ai/README.md` and `examples/questions/README.md`.

## Configuration

Create `ytce.yaml` in your project root (or run `ytce init`):

```yaml
output_dir: data
language: en
comment_sort: recent
```

These become your defaults, so you don't need to pass flags every time.

## Progress Output

You'll see nice progress indicators with real-time statistics:

```
▶ Fetching channel: @skryp
✔ Found 312 videos

▶ Processing videos
  📊 Videos: 0/312 (0.0%) | Comments: 0 | Data: 0B | Time: 0s

[001/312] dQw4w9WgXcQ — 1,245 comments — in 3s
[002/312] xYz123      — comments disabled
[003/312] abc987      — 532 comments — in 2s
  📊 Videos: 3/312 (1.0%) | Comments: 1,777 | Data: 125.3KB | Time: 8s | ETA: 13m 24s
...

📊 FINAL STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total Videos:   312
  Total Comments: 45,832
  Total Data:     8.7MB
  Total Time:     15m 42s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✔ Done!
✔ Output: data/skryp/
```

Progress tracking includes:
- Video completion percentage
- Total comments downloaded
- Data size (KB/MB/GB)
- Time elapsed and ETA
- Final summary statistics

## Features

- **Batch Processing** - Scrape multiple channels efficiently with `ytce batch`
- **Multiple Export Formats** - JSON, CSV, and Parquet support
- **No API Key Required** - Uses YouTube's web interface
- **AI Comment Analysis** - Analyze comments with sentiment, topics, translation, and more
- **Translation Support** - Translate comments to any language for international analysis
- **Simple & Clean** - Fresh scraping each time, no complex state management
- **Rich Progress Tracking** - Real-time stats with percentages, data size, and ETA
- **Smart Data Fields** - Includes text/title length, duration in minutes for easy analysis
- **Safe Interruption** - Ctrl+C confirmation prevents accidental data loss
- **Config File** - Set defaults once, use everywhere
- **Auto-organizing** - Clean folder structure with automatic results organization
- **Batch Reports** - Machine-readable JSON reports for pipeline integration
- **Final Statistics** - Beautiful summary of downloaded data

## Requirements

**Core dependencies:**
- Python 3.7+
- `requests` - HTTP client for web scraping
- `pyyaml` - YAML config file support (optional)

**Optional dependencies:**
- `pyarrow` - Parquet format support (required for `--format parquet`)
- `openai` - AI analysis support (required for `ytce analyze` without `--dry-run`)
- `pandas` - CSV/Parquet file handling (required for CSV/Parquet formats)

## Advanced Usage

### Custom Output Directory

```bash
ytce channel @name --out-dir /path/to/custom/location
```

### Debug Mode

```bash
ytce channel @name --debug
```

### Process Specific Range

```bash
# Get first 10 videos only
ytce channel @name --limit 10

# Get 50 comments per video
ytce channel @name --per-video-limit 50
```

## Troubleshooting

### "Failed to extract ytcfg" error
YouTube may have changed their page structure. Debug HTML is saved to `/tmp/youtube_debug.html`.

### Comments not downloading
Check if comments are disabled for the video. The scraper will automatically skip these.

### Module not found
Make sure you installed the package: `pip install -e .`

## Project Structure

```
youtube-comment-explorer/
├── src/
│   └── ytce/                    # Main package
│       ├── cli/                 # CLI interface
│       ├── pipelines/           # High-level workflows
│       ├── youtube/             # YouTube scraping primitives
│       ├── storage/             # File I/O and paths
│       ├── models/              # Data structures
│       ├── utils/               # Helpers
│       └── config.py            # Configuration management
├── data/                        # Downloaded data (gitignored)
├── README.md                    # This file
├── pyproject.toml               # Package configuration
└── requirements.txt             # Dependencies
```

## License

This project incorporates code from [youtube-comment-downloader](https://github.com/egbertbouman/youtube-comment-downloader) by Egbert Bouman (MIT License).

## Notes

- **Rate Limiting**: Built-in delays between requests to respect YouTube's servers
- **No Authentication**: Works without YouTube account login
- **Order Preservation**: Videos are always ordered newest → oldest
