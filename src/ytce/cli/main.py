from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from typing import Optional

from ytce.__version__ import __version__
from ytce.config import load_config
from ytce.errors import EXIT_SUCCESS, handle_error
from ytce.pipelines.batch import run_batch
from ytce.pipelines.channel_videos import run as run_channel_videos
from ytce.pipelines.scraper import ScrapeConfig, scrape_channel
from ytce.pipelines.video_comments import run as run_video_comments
from ytce.storage.paths import channel_output_dir, channel_videos_path, channel_videos_path_with_format, video_comments_path
from ytce.utils.progress import print_error, print_success


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
  # Example 1: Multi-class classification
  - id: sentiment
    type: multi_class
    question: "What is the sentiment of this comment?"
    labels: ["positive", "neutral", "negative"]

  # Example 2: Binary classification
  - id: spam
    type: binary_classification
    question: "Is this comment spam or self-promotion?"
    labels: ["yes", "no"]

  # Example 3: Multi-label classification
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

  # Example 4: Scoring task
  - id: toxicity
    type: scoring
    question: "How toxic or aggressive is this comment?"
    scale: [0.0, 1.0]
"""


def init_questions_yaml() -> int:
    """
    Generate an example questions.yaml file in the current working directory.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    target_path = os.path.join(os.getcwd(), "questions.yaml")
    
    # Check if file already exists
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
        print()
        print("Next steps:")
        print("  1. Edit questions.yaml to define your analysis tasks")
        print("  2. Prepare your comments data (CSV, JSON, or Parquet)")
        print("  3. Update the 'input.path' field to point to your data")
        print("  4. Run: ytce analyze questions.yaml")
        
        return EXIT_SUCCESS
        
    except Exception as e:
        print_error(f"Failed to create questions.yaml: {e}")
        from ytce.errors import EXIT_INTERNAL_ERROR
        return EXIT_INTERNAL_ERROR


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytce",
        description="YouTube Comment Explorer - Download videos and comments without API",
        epilog="""
Examples:
  ytce init                          # Generate questions.yaml for AI analysis
  ytce channel @realmadrid           # Download channel videos + comments
  ytce channel @skryp --limit 5      # Download first 5 videos only
  ytce comments dQw4w9WgXcQ          # Download comments for one video
  ytce open @realmadrid              # Open output folder

For more info: https://github.com/makararena/youtube-data-scraper
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
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

    return parser


def open_directory(path: str) -> None:
    """Open a directory in the system file manager."""
    if not os.path.exists(path):
        print_error(f"Directory not found: {path}")
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

        # ytce open
        if args.cmd == "open":
            # Try to determine if it's a channel or video
            identifier = args.identifier
            # Try channel first
            channel_dir = channel_output_dir(identifier, base_dir=base_dir)
            if os.path.exists(channel_dir):
                open_directory(channel_dir)
                return EXIT_SUCCESS
            # Try video
            video_dir = os.path.join(base_dir, identifier)
            if os.path.exists(video_dir):
                open_directory(video_dir)
                return EXIT_SUCCESS
            # Not found
            print_error(f"No data found for: {identifier}")
            print_error(f"Searched in: {base_dir}")
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
