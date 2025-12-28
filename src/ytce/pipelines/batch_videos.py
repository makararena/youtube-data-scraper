"""Batch scraping pipeline for multiple videos."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import List, Optional

from ytce.pipelines.video_comments import run as run_video_comments
from ytce.storage.paths import video_comments_path
from ytce.utils.progress import format_bytes, format_duration, format_number, print_error, print_step, print_success, print_warning
from ytce.utils.videos import parse_videos_file


class VideoStats:
    """Statistics for a single video."""
    def __init__(
        self,
        video_id: str,
        status: str,
        comments: int = 0,
        bytes_mb: float = 0.0,
        duration_sec: float = 0.0,
        error: Optional[str] = None,
    ):
        self.video_id = video_id
        self.status = status
        self.comments = comments
        self.bytes_mb = bytes_mb
        self.duration_sec = duration_sec
        self.error = error


class VideoBatchReport:
    """Report for batch video scraping."""
    def __init__(
        self,
        started_at: str,
        finished_at: str,
        videos_total: int,
        videos_ok: int,
        videos_failed: int,
        total_comments: int,
        total_bytes_mb: float,
        total_duration_sec: float,
        stats: List[dict],
    ):
        self.started_at = started_at
        self.finished_at = finished_at
        self.videos_total = videos_total
        self.videos_ok = videos_ok
        self.videos_failed = videos_failed
        self.total_comments = total_comments
        self.total_bytes_mb = total_bytes_mb
        self.total_duration_sec = total_duration_sec
        self.stats = stats
    
    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "videos_total": self.videos_total,
            "videos_ok": self.videos_ok,
            "videos_failed": self.videos_failed,
            "total_comments": self.total_comments,
            "total_bytes_mb": round(self.total_bytes_mb, 2),
            "total_duration_sec": round(self.total_duration_sec, 1),
            "stats": self.stats,
        }


def run_batch_videos(
    *,
    videos_file: str,
    base_dir: str = "data",
    limit: Optional[int] = None,
    sort: str = "recent",
    language: str = "en",
    format: str = "jsonl",
    debug: bool = False,
    fail_fast: bool = False,
    dry_run: bool = False,
    sleep_between: int = 1,
) -> Optional[VideoBatchReport]:
    """
    Run batch scraping for multiple videos.
    
    Args:
        videos_file: Path to file containing video list
        base_dir: Base directory for outputs
        limit: Limit comments per video
        sort: Comment sort order
        language: Language code
        format: Output format (jsonl/csv/parquet)
        debug: Enable debug output
        fail_fast: Stop on first error
        dry_run: Preview only, don't download
        sleep_between: Seconds to sleep between videos
    
    Returns:
        VideoBatchReport with results, or None if interrupted by user
    """
    started_at = datetime.now(timezone.utc)
    
    # Parse videos file
    print_step(f"Reading videos from: {videos_file}")
    try:
        videos = parse_videos_file(videos_file)
    except FileNotFoundError:
        print_error(f"File not found: {videos_file}")
        raise
    
    if not videos:
        print_error("No valid videos found in file")
        raise ValueError("No videos to process")
    
    print_success(f"Found {len(videos)} video(s) to process")
    print()
    
    # Create batch output directory
    batch_dir = os.path.join(base_dir, "_batch_videos", started_at.strftime("%Y-%m-%d_%H-%M-%S"))
    os.makedirs(batch_dir, exist_ok=True)
    
    # Copy videos file as snapshot
    import shutil
    shutil.copy(videos_file, os.path.join(batch_dir, "videos.txt"))
    
    # Open errors log
    errors_log = os.path.join(batch_dir, "errors.log")
    
    # Process each video
    stats_list: List[VideoStats] = []
    
    for idx, video_id in enumerate(videos, 1):
        print_step(f"[{idx}/{len(videos)}] Processing: {video_id}")
        
        if dry_run:
            print_success(f"[{idx}/{len(videos)}] {video_id} — DRY RUN (skipped)")
            stats_list.append(VideoStats(video_id=video_id, status="skipped"))
            continue
        
        try:
            # Determine output path
            output = video_comments_path(video_id, base_dir=base_dir, format=format)
            
            # Track start time for this video
            video_start = time.time()
            
            # Run video comments scraping
            run_video_comments(
                video_id=video_id,
                output=output,
                sort=sort,
                limit=limit,
                language=language,
                format=format,
            )
            
            # Calculate stats
            video_duration = time.time() - video_start
            
            # Get file size if output exists
            bytes_mb = 0.0
            comments = 0
            if os.path.exists(output):
                bytes_mb = os.path.getsize(output) / (1024 * 1024)
                # Try to count comments (approximate for JSONL)
                if format == "jsonl":
                    try:
                        with open(output, 'r', encoding='utf-8') as f:
                            comments = sum(1 for _ in f)
                    except Exception:
                        pass
                elif format == "csv":
                    try:
                        with open(output, 'r', encoding='utf-8') as f:
                            # Subtract 1 for header
                            comments = max(0, sum(1 for _ in f) - 1)
                    except Exception:
                        pass
            
            stats = VideoStats(
                video_id=video_id,
                status="ok",
                comments=comments,
                bytes_mb=bytes_mb,
                duration_sec=video_duration,
            )
            stats_list.append(stats)
            
            # Print summary
            print_success(
                f"[{idx}/{len(videos)}] {video_id} — "
                f"{format_number(comments)} comments — "
                f"OK ({format_bytes(bytes_mb * 1024 * 1024)}, {format_duration(video_duration)})"
            )
            
            # Sleep between videos (except last one)
            if idx < len(videos) and sleep_between > 0:
                time.sleep(sleep_between)
        
        except KeyboardInterrupt:
            print()
            print_warning("Batch interrupted by user")
            # Save partial results and exit gracefully
            if stats_list:
                finished_at = datetime.now(timezone.utc)
                report = _create_batch_report(started_at, finished_at, stats_list, videos)
                _write_batch_report(batch_dir, started_at, stats_list, videos)
                _print_final_summary(report)
                print_success(f"Partial results saved to: {batch_dir}/")
            return None  # Signal interruption
        
        except Exception as e:
            error_msg = str(e)
            print_error(f"[{idx}/{len(videos)}] {video_id} — ERROR: {error_msg}")
            
            # Log error to file
            with open(errors_log, "a", encoding="utf-8") as f:
                f.write(f"{datetime.now(timezone.utc).isoformat()} | {video_id} | {error_msg}\n")
            
            # Record failed stats
            stats_list.append(
                VideoStats(
                    video_id=video_id,
                    status="failed",
                    error=error_msg,
                )
            )
            
            if fail_fast:
                print_error("Stopping batch due to --fail-fast")
                break
        
        print()
    
    # Generate report
    finished_at = datetime.now(timezone.utc)
    report = _create_batch_report(started_at, finished_at, stats_list, videos)
    
    # Write report
    _write_batch_report(batch_dir, started_at, stats_list, videos)
    
    # Print final summary
    _print_final_summary(report)
    
    print_success(f"Batch artifacts saved to: {batch_dir}/")
    
    return report


def _create_batch_report(
    started_at: datetime,
    finished_at: datetime,
    stats_list: List[VideoStats],
    all_videos: List[str],
) -> VideoBatchReport:
    """Create batch report from stats."""
    videos_ok = sum(1 for s in stats_list if s.status == "ok")
    videos_failed = len(stats_list) - videos_ok
    
    total_comments = sum(s.comments for s in stats_list if s.status == "ok")
    total_bytes_mb = sum(s.bytes_mb for s in stats_list if s.status == "ok")
    total_duration = (finished_at - started_at).total_seconds()
    
    stats_dicts = []
    for s in stats_list:
        if s.status == "ok":
            stats_dicts.append({
                "video_id": s.video_id,
                "comments": s.comments,
                "bytes_mb": round(s.bytes_mb, 2),
                "duration_sec": round(s.duration_sec, 1),
                "status": "ok",
            })
        else:
            stats_dicts.append({
                "video_id": s.video_id,
                "status": s.status,
                "error": s.error if s.error else None,
            })
    
    return VideoBatchReport(
        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        videos_total=len(all_videos),
        videos_ok=videos_ok,
        videos_failed=videos_failed,
        total_comments=total_comments,
        total_bytes_mb=total_bytes_mb,
        total_duration_sec=total_duration,
        stats=stats_dicts,
    )


def _write_batch_report(
    batch_dir: str,
    started_at: datetime,
    stats_list: List[VideoStats],
    all_videos: List[str],
) -> None:
    """Write batch report to JSON file."""
    finished_at = datetime.now(timezone.utc)
    report = _create_batch_report(started_at, finished_at, stats_list, all_videos)
    
    report_path = os.path.join(batch_dir, "report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)


def _print_final_summary(report: VideoBatchReport) -> None:
    """Print beautiful final summary."""
    print()
    print("━" * 60)
    print("Batch completed")
    print("━" * 60)
    print(f"✔ Videos OK:      {report.videos_ok}")
    if report.videos_failed > 0:
        print(f"✖ Videos failed:   {report.videos_failed}")
    print(f"💬 Total comments: {format_number(report.total_comments)}")
    print(f"📦 Total data:     {format_bytes(report.total_bytes_mb * 1024 * 1024)}")
    print(f"⏱ Total time:     {format_duration(report.total_duration_sec)}")
    print("━" * 60)
    print()

