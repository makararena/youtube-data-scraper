from __future__ import annotations

import argparse
from typing import Optional

from ytce.pipelines.channel_comments import run as run_channel_comments
from ytce.pipelines.channel_videos import run as run_channel_videos
from ytce.pipelines.video_comments import run as run_video_comments
from ytce.storage.paths import channel_output_dir, channel_videos_path, video_comments_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ytce")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_videos = sub.add_parser("videos", help="Download channel videos metadata as JSON (newest -> oldest).")
    p_videos.add_argument("channel_id")
    p_videos.add_argument("-o", "--output", default=None, help="Output path (default: data/<channel>/videos.json)")
    p_videos.add_argument("--max-videos", type=int, default=None)
    p_videos.add_argument("--debug", action="store_true")

    p_comments = sub.add_parser("comments", help="Download comments for a single video as JSONL.")
    p_comments.add_argument("video_id")
    p_comments.add_argument("-o", "--output", default=None, help="Output path (default: data/<video_id>/comments.jsonl)")
    p_comments.add_argument("--sort", choices=["recent", "popular"], default="recent")
    p_comments.add_argument("--limit", type=int, default=None)
    p_comments.add_argument("--language", default=None)

    p_channel = sub.add_parser(
        "channel-comments",
        help="Download channel videos + recursively download comments for each video (per-video JSONL).",
    )
    p_channel.add_argument("channel_id")
    p_channel.add_argument("--out-dir", default=None, help="Output directory (default: data/<channel>)")
    p_channel.add_argument("--max-videos", type=int, default=None)
    p_channel.add_argument("--sort", choices=["recent", "popular"], default="recent")
    p_channel.add_argument("--per-video-limit", type=int, default=None)
    p_channel.add_argument("--language", default=None)
    p_channel.add_argument("--no-resume", action="store_true")
    p_channel.add_argument("--debug", action="store_true")

    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # Auto-generate output paths in data/ folder
    if args.cmd == "videos":
        output = args.output or channel_videos_path(args.channel_id)
        run_channel_videos(channel_id=args.channel_id, output=output, max_videos=args.max_videos, debug=args.debug)
        return
    if args.cmd == "comments":
        output = args.output or video_comments_path(args.video_id)
        run_video_comments(
            video_id=args.video_id,
            output=output,
            sort=args.sort,
            limit=args.limit,
            language=args.language,
        )
        return
    if args.cmd == "channel-comments":
        out_dir = args.out_dir or channel_output_dir(args.channel_id)
        run_channel_comments(
            channel_id=args.channel_id,
            out_dir=out_dir,
            max_videos=args.max_videos,
            sort=args.sort,
            per_video_limit=args.per_video_limit,
            language=args.language,
            resume=not args.no_resume,
            debug=args.debug,
        )
        return


if __name__ == "__main__":
    main()
