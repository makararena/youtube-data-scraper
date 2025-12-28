from __future__ import annotations

import argparse
import getpass
import os
import platform
import subprocess
import sys
from typing import Optional

from ytce.__version__ import __version__
from ytce.config import get_global_config_path, load_config, save_global_config
from ytce.errors import EXIT_SUCCESS, handle_error
from ytce.pipelines.batch import run_batch
from ytce.pipelines.batch_videos import run_batch_videos
from ytce.pipelines.channel_videos import run as run_channel_videos
from ytce.pipelines.scraper import ScrapeConfig, scrape_channel
from ytce.pipelines.video_comments import run as run_video_comments
from ytce.storage.paths import channel_output_dir, channel_videos_path, channel_videos_path_with_format, video_comments_path
from ytce.utils.progress import print_error, print_success


class GroupedHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom formatter that groups commands by category."""
    
    def _format_action(self, action):
        # Group subcommands by category
        if isinstance(action, argparse._SubParsersAction):
            # Define command groups with their help text
            groups = {
                "AI Analysis": [
                    ("init", "Generate example questions.yaml for AI analysis"),
                    ("analyze", "Run AI analysis defined in questions.yaml"),
                    ("setup", "Configure OpenAI API key and model (saved globally)"),
                    ("key", "Set or change OpenAI API key (saved globally)"),
                    ("model", "Choose default OpenAI model (saved globally)"),
                ],
                "Data Scraping": [
                    ("channel", "Download channel videos and comments"),
                    ("video", "Download single video metadata"),
                    ("comments", "Download comments for a video"),
                    ("batch", "Scrape multiple channels from a file"),
                    ("batch-videos", "Scrape multiple videos from a file"),
                ],
                "Utilities": [
                    ("open", "Open output directory in file manager"),
                ],
            }
            
            # Build formatted help text
            parts = []
            parts.append("Commands:\n")
            
            for group_name, commands in groups.items():
                parts.append(f"  {group_name}:")
                # Filter to only include commands that exist in action.choices
                available_commands = [(cmd, help_txt) for cmd, help_txt in commands if cmd in action.choices]
                if not available_commands:
                    continue
                
                # Calculate max command length for alignment
                max_cmd_len = max(len(cmd) for cmd, _ in available_commands)
                
                for cmd_name, help_text in available_commands:
                    # Format: command_name  help_text (wrapped)
                    padding = " " * (max_cmd_len - len(cmd_name) + 2)
                    # Wrap help text
                    help_lines = self._split_lines(help_text, 80 - len(cmd_name) - len(padding) - 2)
                    parts.append(f"    {cmd_name}{padding}{help_lines[0]}")
                    for line in help_lines[1:]:
                        parts.append(f"    {' ' * (max_cmd_len + 2)}{line}")
                parts.append("")  # Empty line between groups
            
            return "\n".join(parts)
        
        return super()._format_action(action)
    
    def format_help(self):
        # Get the default help text
        help_text = super().format_help()
        # Remove the "positional arguments:" line
        lines = help_text.split("\n")
        filtered_lines = []
        skip_next_empty = False
        for i, line in enumerate(lines):
            if line.strip() == "positional arguments:":
                skip_next_empty = True
                continue
            if skip_next_empty and line.strip() == "":
                skip_next_empty = False
                continue
            filtered_lines.append(line)
        return "\n".join(filtered_lines)


# Template for questions.yaml
QUESTIONS_YAML_TEMPLATE = """version: 1

# Input section: where to load comments from
input:
  path: "./comments.csv"
  format: csv
  id_field: id
  text_field: text

# Optional: Custom prompt providing background story/context about the channel
# This context will be included when analyzing comments to help the AI understand
# the channel's focus, audience, and content style
custom_prompt: ""

# Tasks section: what analysis to run on each comment
tasks:
  # Example 1: Language detection
  - id: language
    type: language_detection
    question: "What is the primary language of this comment? Return the ISO 639-1 or ISO 639-2 language code (e.g., 'en' for English, 'ru' for Russian, 'es' for Spanish)."

  # Example 2: Multi-class classification
  - id: sentiment
    type: multi_class
    question: "What is the sentiment of this comment?"
    labels: ["positive", "neutral", "negative"]

  # Example 3: Binary classification
  - id: spam
    type: binary_classification
    question: "Is this comment spam or self-promotion?"
    labels: ["yes", "no"]

  # Example 4: Multi-label classification
  - id: topics
    type: multi_label
    question: "What topics are mentioned in this comment?"
    labels:
      - price
      - quality
      - delivery
      - support
      - usability
    max_labels: 2

  # Example 5: Scoring task
  - id: toxicity
    type: scoring
    question: "How toxic or aggressive is this comment?"
    scale: [0.0, 1.0]
"""


def init_questions_yaml() -> int:
    """
    Generate an example questions.yaml file and project files (channels.txt, videos.txt) in the current working directory.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    from ytce.config import CHANNELS_FILE, CHANNELS_TEMPLATE, VIDEOS_FILE, VIDEOS_TEMPLATE
    
    target_path = os.path.join(os.getcwd(), "questions.yaml")
    
    # Check if questions.yaml already exists
    if os.path.exists(target_path):
        print_error("questions.yaml already exists in current directory")
        print_error(f"Location: {target_path}")
        print_error("Remove or rename the existing file before running ytce init")
        from ytce.errors import EXIT_USER_ERROR
        return EXIT_USER_ERROR
    
    # Write the template
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(QUESTIONS_YAML_TEMPLATE.lstrip())
        
        print_success(f"Generated: {target_path}")
        
        # Create channels.txt if it doesn't exist
        channels_path = os.path.join(os.getcwd(), CHANNELS_FILE)
        if not os.path.exists(channels_path):
            with open(channels_path, "w", encoding="utf-8") as f:
                f.write(CHANNELS_TEMPLATE)
            print_success(f"Generated: {channels_path}")
        else:
            print(f"⚠️  {CHANNELS_FILE} already exists, skipping")
        
        # Create videos.txt if it doesn't exist
        videos_path = os.path.join(os.getcwd(), VIDEOS_FILE)
        if not os.path.exists(videos_path):
            with open(videos_path, "w", encoding="utf-8") as f:
                f.write(VIDEOS_TEMPLATE)
            print_success(f"Generated: {videos_path}")
        else:
            print(f"⚠️  {VIDEOS_FILE} already exists, skipping")
        
        print()
        print("Next steps:")
        print("  1. Edit questions.yaml to define your analysis tasks")
        print("  2. Prepare your comments data (CSV, JSON, or Parquet)")
        print("  3. Update the 'input.path' field to point to your data")
        print("  4. Run: ytce analyze questions.yaml")
        
        return EXIT_SUCCESS
        
    except Exception as e:
        print_error(f"Failed to create files: {e}")
        from ytce.errors import EXIT_INTERNAL_ERROR
        return EXIT_INTERNAL_ERROR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytce",
        description="YouTube Comment Explorer - Download videos and comments without API",
        epilog="""
Quick Examples:
  # Data Scraping
  ytce channel @realmadrid                    # Download channel videos + comments
  ytce channel @skryp --limit 5               # First 5 videos only
  ytce comments dQw4w9WgXcQ                  # Download comments for one video
  ytce batch channels.txt                    # Scrape multiple channels
  ytce batch-videos videos.txt                # Scrape multiple videos
  
  # AI Analysis
  ytce init                                   # Generate questions.yaml template
  ytce analyze                                # Run AI analysis on comments
  ytce setup                                  # Configure OpenAI API key & model
  
  # Utilities
  ytce open @realmadrid                       # Open output folder

Output Formats:
  Videos: JSON (default), CSV, Parquet
  Comments: JSONL (default), CSV, Parquet
  Use --format flag to specify format (e.g., --format csv, --format parquet)

For more info: https://github.com/makararena/youtube-data-scraper
        """,
        formatter_class=GroupedHelpFormatter,
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show program version and exit",
    )
    sub = parser.add_subparsers(dest="cmd", required=True, metavar="COMMAND")

    # ytce init
    p_init = sub.add_parser(
        "init",
        help="Generate example questions.yaml for AI analysis",
        description="Generate an example questions.yaml file with input configuration and sample analysis tasks.",
        epilog="""
Examples:
  ytce init                    # Create questions.yaml in current directory

The generated file includes:
  - Input section: where to load comments from
  - Tasks section: example tasks for all supported types
    • multi_class: sentiment analysis
    • binary_classification: spam detection
    • multi_label: topic classification
    • scoring: toxicity scoring
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ytce analyze (AI)
    p_analyze = sub.add_parser(
        "analyze",
        help="Run AI analysis defined in questions.yaml",
        usage="ytce analyze [questions.yaml] [options]",
        description="Runs the AI analysis pipeline over a comments file as configured in questions.yaml, and exports results to CSV.",
        epilog="""
Examples:
  ytce analyze                         # Uses ./questions.yaml
  ytce analyze questions.yaml          # Explicit job file
  ytce analyze --dry-run               # Run without LLM calls (mock results)
  ytce analyze --model gpt-4.1-nano    # Choose model (fast & cheap)
  ytce analyze --api-key $OPENAI_API_KEY
  ytce analyze -o results.csv          # Output CSV path

Notes:
  - For real runs, provide an API key via --api-key or OPENAI_API_KEY env var.
  - The input comments file path is read from questions.yaml (input.path).
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_analyze.add_argument(
        "questions",
        nargs="?",
        default="questions.yaml",
        help="Path to questions.yaml (default: questions.yaml)",
    )
    p_analyze.add_argument(
        "-o",
        "--output",
        default="analysis_results.csv",
        help="Output CSV path (default: analysis_results.csv)",
    )
    p_analyze.add_argument(
        "--model",
        default=None,
        help="Model name (default: from config, fallback: gpt-4.1-nano)",
    )
    p_analyze.add_argument(
        "--api-key",
        default=None,
        help="LLM API key (default: from OPENAI_API_KEY env var)",
    )
    p_analyze.add_argument(
        "--no-interactive",
        action="store_true",
        help="Disable interactive prompts (fail if API key/model missing)",
    )
    p_analyze.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Comments per request (default: 5, recommended: 1-5)",
    )
    p_analyze.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Model temperature (default: 0.0)",
    )
    p_analyze.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip real LLM calls and generate mock results",
    )
    p_analyze.add_argument(
        "--preview-count",
        type=int,
        default=5,
        help="Analyze first N comments and ask to proceed (default: 5, interactive only)",
    )
    p_analyze.add_argument(
        "--skip-preview",
        action="store_true",
        help="Skip the initial preview run (interactive only)",
    )
    p_analyze.add_argument(
        "--max-comments",
        type=int,
        default=None,
        help="Limit analysis to first N comments (default: process all)",
    )
    p_analyze.add_argument(
        "--max-comment-length",
        type=int,
        default=1000,
        help="Maximum characters per comment (longer comments will be truncated, default: 1000)",
    )
    p_analyze.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)",
    )
    p_analyze.add_argument(
        "--debug",
        action="store_const",
        const="DEBUG",
        dest="log_level",
        help="Shortcut for --log-level DEBUG (shows detailed logs)",
    )
    p_analyze.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Write logs to file (default: auto-generate in results directory)",
    )
    p_analyze.add_argument(
        "--resume",
        action="store_true",
        help="Resume from previous incomplete run (if checkpoint exists)",
    )
    p_analyze.add_argument(
        "--no-checkpoint",
        action="store_true",
        help="Disable checkpoint/resume functionality",
    )

    # ytce setup (AI config wizard)
    p_setup = sub.add_parser(
        "setup",
        help="Configure OpenAI API key and model (saved globally)",
        description="Interactive setup for OpenAI credentials and default model. Saves to the global user config file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_setup.add_argument(
        "--api-key",
        default=None,
        help="Set OpenAI API key (non-interactive if provided)",
    )
    p_setup.add_argument(
        "--model",
        default=None,
        help="Set default model (non-interactive if provided)",
    )

    # ytce key (change API key)
    p_key = sub.add_parser(
        "key",
        help="Set or change OpenAI API key (saved globally)",
        description="Set or change the OpenAI API key in the global user config file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_key.add_argument("--api-key", default=None, help="Set API key (non-interactive if provided)")

    # ytce model (choose model)
    p_model = sub.add_parser(
        "model",
        help="Choose default OpenAI model (saved globally)",
        description="Choose the default OpenAI model in the global user config file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_model.add_argument("--model", default=None, help="Set model (non-interactive if provided)")

    # ytce channel
    p_channel = sub.add_parser(
        "channel",
        help="Download channel videos and comments",
        usage="ytce channel @channelname [options]",
        description="Downloads all videos from a YouTube channel and all comments for each video.",
        epilog="""
Examples:
  ytce channel @realmadrid              # Download everything
  ytce channel @skryp --limit 5         # First 5 videos only
  ytce channel @test --videos-only      # Videos metadata only, skip comments
  ytce channel @name --per-video-limit 100  # Max 100 comments per video
  ytce channel @name --sort popular     # Get popular comments instead of recent
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_channel.add_argument("channel_id", metavar="@channel", help="Channel handle (e.g., @realmadrid) or channel ID")
    p_channel.add_argument("--videos-only", action="store_true", help="Download only videos metadata, skip comments")
    p_channel.add_argument("--limit", type=int, default=None, help="Limit number of videos to process")
    p_channel.add_argument("--per-video-limit", type=int, default=None, help="Limit comments per video")
    p_channel.add_argument("--sort", choices=["recent", "popular"], default=None, help="Comment sort order (default: from config or 'recent')")
    p_channel.add_argument("--language", default=None, help="Language code (default: from config or 'en')")
    p_channel.add_argument("--out-dir", default=None, help="Custom output directory")
    p_channel.add_argument("--dry-run", action="store_true", help="Preview what will be downloaded without actually downloading")
    p_channel.add_argument("--debug", action="store_true", help="Enable debug output")
    p_channel.add_argument("--format", choices=["json", "csv", "parquet"], default="json", help="Output format for videos (default: json). Comments always use same format.")

    # ytce video
    p_video = sub.add_parser(
        "video",
        help="Download single video metadata",
        usage="ytce video VIDEO_ID [options]",
        description="Downloads metadata for a single video (without comments).",
        epilog="""
Examples:
  ytce video dQw4w9WgXcQ              # Download video metadata
  ytce video abc123 -o video.json     # Save to custom path
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_video.add_argument("video_id", metavar="VIDEO_ID", help="YouTube video ID (e.g., dQw4w9WgXcQ)")
    p_video.add_argument("-o", "--output", default=None, help="Custom output path")
    p_video.add_argument("--debug", action="store_true", help="Enable debug output")
    p_video.add_argument("--format", choices=["json", "csv", "parquet"], default="json", help="Output format (default: json)")

    # ytce comments
    p_comments = sub.add_parser(
        "comments",
        help="Download comments for a video",
        usage="ytce comments VIDEO_ID [options]",
        description="Downloads all comments from a single YouTube video.",
        epilog="""
Examples:
  ytce comments dQw4w9WgXcQ           # Download all comments
  ytce comments abc123 --limit 500    # Download first 500 comments
  ytce comments xyz789 --sort popular # Get popular comments
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_comments.add_argument("video_id", metavar="VIDEO_ID", help="YouTube video ID (e.g., dQw4w9WgXcQ)")
    p_comments.add_argument("-o", "--output", default=None, help="Custom output path")
    p_comments.add_argument("--sort", choices=["recent", "popular"], default=None, help="Sort order (default: from config or 'recent')")
    p_comments.add_argument("--limit", type=int, default=None, help="Limit number of comments")
    p_comments.add_argument("--language", default=None, help="Language code (default: from config or 'en')")
    p_comments.add_argument("--format", choices=["jsonl", "csv", "parquet"], default="jsonl", help="Output format (default: jsonl)")

    # ytce open
    p_open = sub.add_parser(
        "open",
        help="Open output directory in file manager",
        usage="ytce open @channel|VIDEO_ID",
        description="Opens the output directory for a channel or video in your system file manager.",
        epilog="""
Examples:
  ytce open @realmadrid    # Open channel output folder
  ytce open dQw4w9WgXcQ    # Open video output folder
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_open.add_argument("identifier", metavar="@channel|VIDEO_ID", help="Channel handle or video ID")

    # ytce batch
    p_batch = sub.add_parser(
        "batch",
        help="Scrape multiple channels from a file",
        usage="ytce batch <channels_file> [options]",
        description="Scrape multiple channels listed in a file. Uses same options as 'ytce channel'.",
        epilog="""
Examples:
  ytce batch channels.txt                        # Scrape all channels
  ytce batch channels.txt --format parquet       # Export to Parquet
  ytce batch channels.txt --limit 10             # First 10 videos per channel
  ytce batch channels.txt --fail-fast            # Stop on first error
  ytce batch channels.txt --dry-run              # Preview without downloading
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_batch.add_argument("channels_file", metavar="<channels_file>", help="Path to file containing channel list")
    p_batch.add_argument("--limit", type=int, default=None, help="Limit number of videos per channel")
    p_batch.add_argument("--per-video-limit", type=int, default=None, help="Limit comments per video")
    p_batch.add_argument("--sort", choices=["recent", "popular"], default=None, help="Comment sort order (default: from config or 'recent')")
    p_batch.add_argument("--language", default=None, help="Language code (default: from config or 'en')")
    p_batch.add_argument("--format", choices=["json", "csv", "parquet"], default="json", help="Output format (default: json)")
    p_batch.add_argument("--out-dir", default=None, help="Custom base output directory")
    p_batch.add_argument("--fail-fast", action="store_true", help="Stop on first error")
    p_batch.add_argument("--dry-run", action="store_true", help="Preview what will be downloaded without actually downloading")
    p_batch.add_argument("--sleep-between", type=int, default=2, help="Seconds to sleep between channels (default: 2)")
    p_batch.add_argument("--debug", action="store_true", help="Enable debug output")

    # ytce batch-videos
    p_batch_videos = sub.add_parser(
        "batch-videos",
        help="Scrape multiple videos from a file",
        usage="ytce batch-videos <videos_file> [options]",
        description="Scrape comments for multiple videos listed in a file. Uses same options as 'ytce comments'.",
        epilog="""
Examples:
  ytce batch-videos videos.txt                    # Scrape all videos
  ytce batch-videos videos.txt --format parquet   # Export to Parquet
  ytce batch-videos videos.txt --limit 500        # Max 500 comments per video
  ytce batch-videos videos.txt --fail-fast        # Stop on first error
  ytce batch-videos videos.txt --dry-run          # Preview without downloading
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_batch_videos.add_argument("videos_file", metavar="<videos_file>", help="Path to file containing video list")
    p_batch_videos.add_argument("--limit", type=int, default=None, help="Limit comments per video")
    p_batch_videos.add_argument("--sort", choices=["recent", "popular"], default=None, help="Comment sort order (default: from config or 'recent')")
    p_batch_videos.add_argument("--language", default=None, help="Language code (default: from config or 'en')")
    p_batch_videos.add_argument("--format", choices=["jsonl", "csv", "parquet"], default="jsonl", help="Output format (default: jsonl)")
    p_batch_videos.add_argument("--fail-fast", action="store_true", help="Stop on first error")
    p_batch_videos.add_argument("--dry-run", action="store_true", help="Preview what will be downloaded without actually downloading")
    p_batch_videos.add_argument("--sleep-between", type=int, default=1, help="Seconds to sleep between videos (default: 1)")
    p_batch_videos.add_argument("--debug", action="store_true", help="Enable debug output")

    return parser


OPENAI_MODEL_CHOICES = [
    "gpt-4.1-nano",
    "gpt-4.1-mini",
]

OPENAI_MODEL_DESCRIPTIONS = {
    "gpt-4.1-nano": "fast & cheap (recommended)",
    "gpt-4.1-mini": "better summaries, more expensive",
}


def _require_tty_or_error(no_interactive: bool, what: str) -> bool:
    if no_interactive or not sys.stdin.isatty():
        print_error(f"Missing {what} and interactive input is disabled.")
        return False
    return True


def _prompt_api_key() -> str:
    while True:
        key = getpass.getpass("OpenAI API key (will be saved): ").strip()
        if key:
            return key
        print_error("API key cannot be empty.")


def _prompt_model(current: Optional[str] = None) -> str:
    print("Choose OpenAI model (will be saved):")
    for i, m in enumerate(OPENAI_MODEL_CHOICES, start=1):
        desc = OPENAI_MODEL_DESCRIPTIONS.get(m, "")
        desc_part = f"  ({desc})" if desc else ""
        suffix = " (current)" if current and m == current else ""
        print(f"  {i}. {m}{desc_part}{suffix}")
    while True:
        raw = input(f"Enter number [1-{len(OPENAI_MODEL_CHOICES)}]: ").strip()
        try:
            idx = int(raw)
        except ValueError:
            print_error("Please enter a number.")
            continue
        if 1 <= idx <= len(OPENAI_MODEL_CHOICES):
            chosen = OPENAI_MODEL_CHOICES[idx - 1]
            if chosen == "gpt-4.1-mini":
                print("ℹ️  gpt-4.1-mini is more expensive than nano. Recommended mainly for summaries / deeper context.")
            return chosen
        print_error("Number out of range.")


def _ensure_ai_config(
    *,
    config: dict,
    api_key: Optional[str],
    model: Optional[str],
    dry_run: bool,
    no_interactive: bool,
) -> tuple[str, str, bool]:
    """
    Returns (api_key, model, did_persist).
    Persists missing values to global config once obtained interactively.
    """
    if dry_run:
        # No API key needed; still resolve model (for consistency/logging)
        resolved_model = model or config.get("openai_model") or "gpt-4.1-nano"
        if resolved_model not in OPENAI_MODEL_CHOICES:
            resolved_model = "gpt-4.1-nano"
        return "", resolved_model, False

    resolved_api_key = api_key or os.environ.get("OPENAI_API_KEY") or config.get("openai_api_key")
    resolved_model = model or config.get("openai_model") or "gpt-4.1-nano"
    if resolved_model not in OPENAI_MODEL_CHOICES:
        resolved_model = "gpt-4.1-nano"

    did_persist = False
    global_path = get_global_config_path()

    if not resolved_api_key:
        if not _require_tty_or_error(no_interactive, "OpenAI API key"):
            raise ValueError("missing_api_key")
        resolved_api_key = _prompt_api_key()
        # Persist to global config
        new_global_cfg = load_config(global_path) if global_path else {}
        new_global_cfg["openai_api_key"] = resolved_api_key
        save_global_config(new_global_cfg)
        did_persist = True
        print_success(f"Saved API key to: {global_path}")

    # If model was not explicitly provided and not present in config, offer choice once
    if model is None and not config.get("openai_model"):
        if not _require_tty_or_error(no_interactive, "OpenAI model"):
            raise ValueError("missing_model")
        resolved_model = _prompt_model(current=resolved_model)
        new_global_cfg = load_config(global_path) if global_path else {}
        new_global_cfg["openai_model"] = resolved_model
        save_global_config(new_global_cfg)
        did_persist = True
        print_success(f"Saved model to: {global_path}")

    return resolved_api_key, resolved_model, did_persist


def _walk_exception_chain(err: BaseException) -> list[BaseException]:
    seen = set()
    out: list[BaseException] = []
    cur: Optional[BaseException] = err
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        out.append(cur)
        cur = cur.__cause__ or cur.__context__
    return out


def _is_invalid_api_key_error(err: BaseException) -> bool:
    try:
        from ytce.ai.models.errors import ModelAuthenticationError
    except Exception:
        return False
    for e in _walk_exception_chain(err):
        if isinstance(e, ModelAuthenticationError):
            return True
        if "invalid_api_key" in str(e) or "Incorrect API key provided" in str(e):
            return True
    return False


def _extract_video_id_from_input_path(input_path: str) -> Optional[str]:
    """
    Extract video ID from input path.
    
    Expected format: ./data/{video_id}/comments.jsonl or data/{video_id}/comments.jsonl
    Returns None if video ID cannot be extracted.
    """
    import os
    from pathlib import Path
    
    # Normalize path
    path = Path(input_path).resolve()
    parts = path.parts
    
    # Look for pattern: .../data/{video_id}/comments.{ext}
    try:
        # Find 'data' in path
        if 'data' in parts:
            data_idx = parts.index('data')
            if data_idx + 1 < len(parts):
                video_id = parts[data_idx + 1]
                # Verify it's not a file extension (safety check)
                if '.' not in video_id and video_id:
                    return video_id
    except (ValueError, IndexError):
        pass
    
    return None


def _get_results_output_path(input_path: str, output_path: Optional[str] = None, is_preview: bool = False) -> str:
    """
    Generate output path for results based on input path structure.
    
    If input path is in data/{video_id}/ format, outputs to data/results/{video_id}/results.csv
    Otherwise uses the provided output_path or default.
    
    Args:
        input_path: Path to input comments file from questions.yaml
        output_path: User-provided output path (optional)
        is_preview: If True, adds .preview before .csv extension
        
    Returns:
        Output path string
    """
    import os
    from pathlib import Path
    
    video_id = _extract_video_id_from_input_path(input_path)
    
    if video_id:
        # Use structured path: data/results/{video_id}/results.csv
        base_dir = Path("data") / "results" / video_id
        base_dir.mkdir(parents=True, exist_ok=True)
        
        if is_preview:
            return str(base_dir / "results.preview.csv")
        else:
            return str(base_dir / "results.csv")
    
    # Fallback to provided output_path or default
    if output_path:
        if is_preview:
            if output_path.lower().endswith(".csv"):
                return output_path[:-4] + ".preview.csv"
            return output_path + ".preview.csv"
        return output_path
    
    # Default fallback
    default = "results.preview.csv" if is_preview else "results.csv"
    return default


def _preview_output_path(output_path: str) -> str:
    if output_path.lower().endswith(".csv"):
        return output_path[:-4] + ".preview.csv"
    return output_path + ".preview.csv"


def _confirm_proceed() -> bool:
    while True:
        raw = input("Proceed with full analysis? [y/N]: ").strip().lower()
        if raw in ("", "n", "no"):
            return False
        if raw in ("y", "yes"):
            return True
        print_error("Please enter 'y' or 'n'.")


def open_directory(path: str) -> None:
    """Open a directory in the system file manager."""
    # Use the global os import - ensure it's available
    import os
    
    if not os.path.exists(path):
        print_error(f"Directory not found: {path}")
        return
    
    if not os.path.isdir(path):
        print_error(f"Path is not a directory: {path}")
        return
    
    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.run(["open", path], check=True)
        elif system == "Windows":
            os.startfile(path)
        elif system == "Linux":
            subprocess.run(["xdg-open", path], check=True)
        else:
            print_error(f"Unsupported platform: {system}")
            return
        print_success(f"Opened: {path}")
    except Exception as e:
        print_error(f"Failed to open directory: {e}")


def main(argv: Optional[list[str]] = None) -> int:
    """
    Main entry point for ytce CLI.
    
    Returns:
        Exit code (0 for success, 1-3 for errors)
    """
    try:
        parser = build_parser()
        args = parser.parse_args(argv)

        # Determine if debug mode
        debug = getattr(args, "debug", False)

        # Load config
        config = load_config()
        base_dir = config.get("output_dir", "data")

        # ytce init
        if args.cmd == "init":
            return init_questions_yaml()

        # ytce setup / key / model
        if args.cmd in {"setup", "key", "model"}:
            global_path = get_global_config_path()
            global_cfg = load_config(global_path) if global_path else {}

            if args.cmd in {"setup", "key"}:
                new_key = getattr(args, "api_key", None)
                if not new_key:
                    if not sys.stdin.isatty():
                        print_error("Missing API key. Provide --api-key (non-interactive) or run in a TTY.")
                        from ytce.errors import EXIT_USER_ERROR
                        return EXIT_USER_ERROR
                    new_key = _prompt_api_key()
                global_cfg["openai_api_key"] = new_key

            if args.cmd in {"setup", "model"}:
                new_model = getattr(args, "model", None)
                if not new_model:
                    if not sys.stdin.isatty():
                        print_error("Missing model. Provide --model (non-interactive) or run in a TTY.")
                        from ytce.errors import EXIT_USER_ERROR
                        return EXIT_USER_ERROR
                    current = global_cfg.get("openai_model") or config.get("openai_model") or "gpt-4.1-nano"
                    new_model = _prompt_model(current=current)
                elif new_model == "gpt-4.1-mini":
                    print("ℹ️  gpt-4.1-mini is more expensive than nano. Recommended mainly for summaries / deeper context.")
                global_cfg["openai_model"] = new_model

            save_global_config(global_cfg)
            print_success(f"Saved AI config to: {global_path}")
            return EXIT_SUCCESS

        # ytce analyze (AI)
        if args.cmd == "analyze":
            from ytce.ai.domain.config import RunConfig
            from ytce.ai.input.job import load_job
            from ytce.ai.output import write_csv_from_analysis_result
            from ytce.ai.runner import run_analysis

            # Resolve and (optionally) persist AI settings
            try:
                api_key, model, _ = _ensure_ai_config(
                    config=config,
                    api_key=args.api_key,
                    model=args.model,
                    dry_run=args.dry_run,
                    no_interactive=getattr(args, "no_interactive", False),
                )
            except ValueError:
                from ytce.errors import EXIT_USER_ERROR
                return EXIT_USER_ERROR

            job = load_job(args.questions)
            interactive = (not getattr(args, "no_interactive", False)) and sys.stdin.isatty()
            
            # Determine output paths based on input path structure
            input_path = job.input.path
            output_path = _get_results_output_path(input_path, args.output, is_preview=False)
            preview_output_path = _get_results_output_path(input_path, args.output, is_preview=True)
            
            # Set up logging
            import logging
            from ytce.utils.logging import get_logger
            
            # Determine log file path
            log_file = getattr(args, "log_file", None)
            if log_file is None:
                # Auto-generate log file in results directory
                import os
                results_dir = os.path.dirname(output_path)
                os.makedirs(results_dir, exist_ok=True)
                log_file = os.path.join(results_dir, "analysis.log")
            
            # Configure root logger for ytce.ai namespace
            root_logger = logging.getLogger("ytce.ai")
            log_level = getattr(logging, getattr(args, "log_level", "INFO").upper(), logging.INFO)
            root_logger.setLevel(log_level)
            
            # Remove existing handlers to avoid duplicates
            root_logger.handlers.clear()
            
            # Add file handler
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(log_level)
            root_logger.addHandler(file_handler)
            
            # Add console handler (only for INFO and above to avoid cluttering output)
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
            console_handler.setFormatter(console_formatter)
            # Only show WARNING and ERROR on console, unless DEBUG level
            console_handler.setLevel(logging.WARNING if log_level != logging.DEBUG else log_level)
            root_logger.addHandler(console_handler)
            
            logger = get_logger("ytce.ai.cli")
            logger.info(f"Logging initialized: level={logging.getLevelName(log_level)}, file={log_file}")

            def progress_callback(processed: int, total: int, task_info: str, is_preview: bool = False):
                """Display progress updates."""
                # Format numbers with commas for readability
                processed_str = f"{processed:,}" if processed >= 1000 else str(processed)
                total_str = f"{total:,}" if total >= 1000 else str(total)
                # Add preview indicator
                preview_prefix = "[PREVIEW] " if is_preview else ""
                # Clear line and print progress (no percentage, just fraction)
                print(f"\r  ✓ {preview_prefix}{processed_str}/{total_str} comments - {task_info}", end="", flush=True)
            
            def run_once(rc: RunConfig, is_preview: bool = False):
                nonlocal api_key
                tries = 0
                # Determine checkpoint settings
                enable_checkpoint = not getattr(args, "no_checkpoint", False) and not is_preview
                checkpoint_dir = os.path.dirname(output_path) if enable_checkpoint else None
                
                while True:
                    try:
                        return run_analysis(
                            job, 
                            rc, 
                            progress_callback=progress_callback if not rc.dry_run else None, 
                            is_preview=is_preview,
                            checkpoint_dir=checkpoint_dir,
                            enable_checkpoint=enable_checkpoint,
                        )
                    except Exception as e:
                        if _is_invalid_api_key_error(e):
                            if not interactive:
                                print_error("OpenAI API key is invalid. Set a new key via ytce key or provide --api-key / OPENAI_API_KEY.")
                                from ytce.errors import EXIT_USER_ERROR
                                raise RuntimeError(EXIT_USER_ERROR) from e
                            tries += 1
                            if tries > 3:
                                print_error("Too many invalid API key attempts.")
                                from ytce.errors import EXIT_USER_ERROR
                                raise RuntimeError(EXIT_USER_ERROR) from e
                            print_error("The provided OpenAI API key is invalid. Please input another one.")
                            new_key = _prompt_api_key()
                            global_path = get_global_config_path()
                            global_cfg = load_config(global_path) if global_path else {}
                            global_cfg["openai_api_key"] = new_key
                            save_global_config(global_cfg)
                            print_success(f"Saved API key to: {global_path}")
                            api_key = new_key
                            rc = RunConfig(
                                model=rc.model,
                                api_key=new_key,
                                batch_size=rc.batch_size,
                                temperature=rc.temperature,
                                dry_run=rc.dry_run,
                                max_comments=rc.max_comments,
                                max_comment_length=rc.max_comment_length,
                                run_id=rc.run_id,
                            )
                            continue
                        raise

            # Check for existing checkpoint
            checkpoint_exists = False
            if not getattr(args, "no_checkpoint", False):
                from ytce.ai.runner.checkpoint import load_checkpoint
                checkpoint = load_checkpoint(os.path.dirname(output_path))
                if checkpoint:
                    checkpoint_exists = True
                    total_completed = sum(len(ids) for ids in checkpoint.completed.values())
                    if interactive and not getattr(args, "resume", False):
                        print()
                        print(f"📋 Found incomplete analysis checkpoint:")
                        print(f"   {total_completed} items completed")
                        print(f"   Tasks: {', '.join(checkpoint.task_ids)}")
                        resume = input("Resume from checkpoint? [Y/n]: ").strip().lower()
                        if resume and resume != 'y':
                            print("Deleting checkpoint and starting fresh...")
                            from ytce.ai.runner.checkpoint import delete_checkpoint
                            delete_checkpoint(os.path.dirname(output_path))
                            checkpoint_exists = False
                        else:
                            print("Resuming from checkpoint...")
                    elif getattr(args, "resume", False):
                        print(f"📋 Resuming from checkpoint ({total_completed} items completed)")
            
            # Optional preview run (interactive only)
            if interactive and (not args.dry_run) and (not args.skip_preview) and args.preview_count > 0 and not checkpoint_exists:
                print(f"🔍 Running preview analysis on first {args.preview_count} comments...")
                preview_cfg = RunConfig(
                    model=model,
                    api_key=api_key or "",
                    batch_size=args.batch_size,
                    temperature=args.temperature,
                    dry_run=args.dry_run,
                    max_comments=args.preview_count,
                    max_comment_length=getattr(args, "max_comment_length", 1000),
                )
                try:
                    preview_result, preview_cost = run_once(preview_cfg, is_preview=True)
                except RuntimeError as e:
                    if str(e).isdigit():
                        return int(str(e))
                    raise
                print()  # New line after progress
                write_csv_from_analysis_result(preview_result, preview_output_path)
                print_success(f"Preview complete. Wrote: {preview_output_path}")
                print_success(f"Preview comments: {preview_result.total_comments} | Tasks: {preview_result.total_tasks}")
                if preview_cost.total_cost > 0:
                    print(f"  Cost: ${preview_cost.total_cost:.4f} (Input: ${preview_cost.input_cost:.4f}, Output: ${preview_cost.output_cost:.4f})")
                    
                    # Calculate estimated cost for full analysis
                    from ytce.ai.input.comments import load_comments_from_config
                    total_comments = len(load_comments_from_config(job.input, limit=None))
                    preview_comment_count = preview_result.total_comments
                    
                    if preview_comment_count > 0:
                        cost_per_comment = preview_cost.total_cost / preview_comment_count
                        estimated_total_cost = cost_per_comment * total_comments
                        print()
                        print(f"💰 Estimated cost for full analysis ({total_comments} comments): ${estimated_total_cost:.4f}")
                        print(f"   (Based on ${cost_per_comment:.6f} per comment from preview)")
                
                print()
                print("📊 Full analysis will process all comments from the input file.")
                if not _confirm_proceed():
                    return EXIT_SUCCESS
                print()

            run_config = RunConfig(
                model=model,
                api_key=api_key or "",
                batch_size=args.batch_size,
                temperature=args.temperature,
                dry_run=args.dry_run,
                max_comments=getattr(args, "max_comments", None),
                max_comment_length=getattr(args, "max_comment_length", 1000),
            )
            # Show message if not in preview mode
            if not (interactive and (not args.dry_run) and (not args.skip_preview) and args.preview_count > 0):
                from ytce.ai.input.comments import load_comments_from_config
                total_comments = len(load_comments_from_config(job.input, limit=None))
                print(f"🚀 Starting full analysis on {total_comments} comments...")
            try:
                result, cost_summary = run_once(run_config, is_preview=False)
            except RuntimeError as e:
                if str(e).isdigit():
                    return int(str(e))
                raise

            print()  # New line after progress
            write_csv_from_analysis_result(result, output_path)

            print_success(f"AI analysis complete. Wrote: {output_path}")
            print_success(f"Comments: {result.total_comments} | Tasks: {result.total_tasks}")
            
            # Display cost summary
            if cost_summary.total_cost > 0:
                print()
                print("💰 Cost Summary:")
                print(f"  Total cost: ${cost_summary.total_cost:.4f}")
                print(f"  Input tokens: {cost_summary.total_input_tokens:,} (${cost_summary.input_cost:.4f})")
                if cost_summary.total_cached_tokens > 0:
                    print(f"  Cached tokens: {cost_summary.total_cached_tokens:,} (${cost_summary.cached_cost:.4f})")
                print(f"  Output tokens: {cost_summary.total_output_tokens:,} (${cost_summary.output_cost:.4f})")
            elif not args.dry_run:
                print("  (Cost calculation not available for this model)")
            
            return EXIT_SUCCESS

        # ytce open
        if args.cmd == "open":
            # Try to determine if it's a channel or video
            identifier = args.identifier
            # Try channel first
            try:
                channel_dir = channel_output_dir(identifier, base_dir=base_dir)
                if os.path.exists(channel_dir) and os.path.isdir(channel_dir):
                    open_directory(channel_dir)
                    return EXIT_SUCCESS
            except Exception:
                pass
            
            # Try video
            try:
                video_dir = os.path.join(base_dir, identifier)
                if os.path.exists(video_dir) and os.path.isdir(video_dir):
                    open_directory(video_dir)
                    return EXIT_SUCCESS
            except Exception:
                pass
            
            # Not found - provide helpful error message
            print_error(f"No data found for: {identifier}")
            print_error(f"Searched in: {base_dir}")
            print_error("Make sure you've downloaded data for this channel/video first.")
            print_error("Example: ytce channel @realmadrid")
            from ytce.errors import EXIT_USER_ERROR
            return EXIT_USER_ERROR

        # ytce channel
        if args.cmd == "channel":
            # Merge config with args
            sort = args.sort or config.get("comment_sort", "recent")
            language = args.language or config.get("language", "en")
            dry_run = getattr(args, "dry_run", False)
            format_arg = getattr(args, "format", "json")
            
            # For channel command, format applies to both videos and comments
            if format_arg == "csv":
                comment_format = "csv"
            elif format_arg == "parquet":
                comment_format = "parquet"
            else:
                comment_format = "jsonl"
            
            if args.videos_only:
                # Only download videos metadata (use legacy pipeline)
                out_dir = args.out_dir or channel_output_dir(args.channel_id, base_dir=base_dir)
                if format_arg == "csv":
                    output = os.path.join(out_dir, "videos.csv")
                elif format_arg == "parquet":
                    output = os.path.join(out_dir, "videos.parquet")
                else:
                    output = os.path.join(out_dir, "videos.json")
                run_channel_videos(
                    channel_id=args.channel_id,
                    output=output,
                    max_videos=args.limit,
                    debug=debug,
                    format=format_arg,
                )
            else:
                # Download videos + comments (use new refactored scraper)
                scrape_config = ScrapeConfig(
                    channel_id=args.channel_id,
                    out_dir=args.out_dir,
                    base_dir=base_dir,
                    max_videos=args.limit,
                    per_video_limit=args.per_video_limit,
                    sort=sort,
                    language=language,
                    format=comment_format,
                    debug=debug,
                    videos_only=False,
                    dry_run=dry_run,
                    quiet=False,
                )
                scrape_channel(scrape_config)
            return EXIT_SUCCESS

        # ytce video
        if args.cmd == "video":
            format_arg = getattr(args, "format", "json")
            if args.output:
                output = args.output
            else:
                if format_arg == "csv":
                    output = channel_videos_path_with_format(args.video_id, base_dir=base_dir, format="csv")
                elif format_arg == "parquet":
                    output = channel_videos_path_with_format(args.video_id, base_dir=base_dir, format="parquet")
                else:
                    output = channel_videos_path(args.video_id, base_dir=base_dir)
            # For single video, we'll just create a minimal videos.json/csv
            run_channel_videos(
                channel_id=args.video_id,
                output=output,
                max_videos=1,
                debug=debug,
                format=format_arg,
            )
            return EXIT_SUCCESS

        # ytce comments
        if args.cmd == "comments":
            sort = args.sort or config.get("comment_sort", "recent")
            language = args.language or config.get("language", "en")
            format_arg = getattr(args, "format", "jsonl")
            
            output = args.output or video_comments_path(args.video_id, base_dir=base_dir, format=format_arg)
            run_video_comments(
                video_id=args.video_id,
                output=output,
                sort=sort,
                limit=args.limit,
                language=language,
                format=format_arg,
            )
            return EXIT_SUCCESS

        # ytce batch
        if args.cmd == "batch":
            # Merge config with args
            sort = args.sort or config.get("comment_sort", "recent")
            language = args.language or config.get("language", "en")
            format_arg = getattr(args, "format", "json")
            
            # For batch command, format applies to both videos and comments
            if format_arg == "csv":
                comment_format = "csv"
            elif format_arg == "parquet":
                comment_format = "parquet"
            else:
                comment_format = "jsonl"
            
            # Determine base directory
            batch_base_dir = args.out_dir or base_dir
            
            run_batch(
                channels_file=args.channels_file,
                base_dir=batch_base_dir,
                max_videos=args.limit,
                per_video_limit=args.per_video_limit,
                sort=sort,
                language=language,
                format=comment_format,
                debug=debug,
                fail_fast=args.fail_fast,
                dry_run=args.dry_run,
                sleep_between=args.sleep_between,
            )
            return EXIT_SUCCESS

        # ytce batch-videos
        if args.cmd == "batch-videos":
            # Merge config with args
            sort = args.sort or config.get("comment_sort", "recent")
            language = args.language or config.get("language", "en")
            format_arg = getattr(args, "format", "jsonl")
            
            # Determine base directory
            batch_base_dir = base_dir
            
            run_batch_videos(
                videos_file=args.videos_file,
                base_dir=batch_base_dir,
                limit=args.limit,
                sort=sort,
                language=language,
                format=format_arg,
                debug=debug,
                fail_fast=args.fail_fast,
                dry_run=args.dry_run,
                sleep_between=args.sleep_between,
            )
            return EXIT_SUCCESS

        # Should never reach here
        return EXIT_SUCCESS

    except KeyboardInterrupt:
        # User interrupted - exit gracefully
        print()
        return EXIT_SUCCESS
    
    except Exception as e:
        debug = False
        try:
            # Try to get debug flag if args were parsed
            debug = getattr(args, "debug", False)
        except:
            pass
        exit_code = handle_error(e, debug=debug)
        return exit_code


if __name__ == "__main__":
    sys.exit(main())
