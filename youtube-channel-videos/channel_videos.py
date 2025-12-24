from __future__ import print_function

import argparse
import json
import os
import time
from typing import Any, Dict, List, Optional

# Allow importing repo-root `shared/` when running this file directly.
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from shared.youtube import (  # type: ignore  # noqa: E402
    fetch_html,
    extract_ytcfg,
    extract_ytinitialdata,
    inertube_ajax_request,
    parse_view_count,
    pick_longest_continuation,
    search_dict,
    make_session,
)

CHANNEL_VIDEOS_URL = "https://www.youtube.com/{channel_id}/videos"


class YoutubeChannelVideosScraper:
    """
    Scraper for extracting all video links from a YouTube channel.
    Uses YouTube InnerTube API (same mechanism as comments).
    """

    def __init__(self, debug=False):
        self.session = make_session()
        self.debug = debug

    def get_videos(self, channel_id):
        """
        Entry point.
        Loads channel /videos page and extracts initial data.
        """
        url = CHANNEL_VIDEOS_URL.format(channel_id=channel_id)
        html, final_url = fetch_html(self.session, url, timeout=30)
        if self.debug:
            print("Final URL:", final_url)

        ytcfg = extract_ytcfg(html)
        data = extract_ytinitialdata(html)

        # Parse videos from the data
        videos = self._parse_videos(data)
        
        # Add order index to maintain order
        # YouTube's /videos page returns videos in reverse chronological order (newest first)
        # This order is preserved throughout pagination
        for idx, video in enumerate(videos, start=1):
            video['order'] = idx
        
        # Find continuation token for pagination
        # Look for the one with the longest token (usually the video continuation)
        continuation = pick_longest_continuation(list(search_dict(data, "continuationEndpoint")))
        
        return {
            'ytcfg': ytcfg,
            'videos': videos,
            'continuation': continuation,
            'raw_data': data  # Keep raw data for debugging
        }
    
    def get_all_videos(self, channel_id, max_videos=None, show_progress=True):
        """
        Get all videos from a channel with pagination support.
        
        Args:
            channel_id: Channel ID (e.g., '@realmadrid' or 'UC...')
            max_videos: Maximum number of videos to fetch (None for all)
            show_progress: Whether to print progress updates
        
        Returns:
            List of video dictionaries
        """
        result = self.get_videos(channel_id)
        all_videos = result['videos']
        continuation = result['continuation']
        ytcfg = result['ytcfg']
        
        # Apply limit to initial batch if needed
        if max_videos and len(all_videos) > max_videos:
            all_videos = all_videos[:max_videos]
            continuation = None  # No need to fetch more
        
        # Print initial batch
        if show_progress:
            for i, video in enumerate(all_videos, 1):
                view_info = f" - {video['view_count']}" if video['view_count'] else ""
                print(f"Video {i} fetched: {video['title']} ({video['video_id']}){view_info}")
        
        if self.debug:
            print(f"Initial batch: {len(all_videos)} videos")
        
        # Continue fetching while there are more videos
        while continuation and (max_videos is None or len(all_videos) < max_videos):
            if self.debug:
                print(f"Fetching more videos... (current: {len(all_videos)})")
            
            # Fetch next batch
            response = self._ajax_request(continuation, ytcfg)
            if not response:
                break
            
            # Parse videos from response
            batch_videos = self._parse_videos(response)
            
            # Add order index to batch videos (continuing from previous count)
            start_order = len(all_videos) + 1
            for idx, video in enumerate(batch_videos):
                video['order'] = start_order + idx
            
            # Print progress for each new video (respecting limit)
            for video in batch_videos:
                # Check if we've reached the limit before adding
                if max_videos and len(all_videos) >= max_videos:
                    break
                
                all_videos.append(video)
                
                if show_progress:
                    video_num = len(all_videos)
                    view_info = ""
                    if video.get('view_count') is not None:
                        view_info = f" - {video['view_count']:,} views"
                    elif video.get('view_count_raw'):
                        view_info = f" - {video['view_count_raw']}"
                    print(f"Video {video_num} fetched: {video['title']} ({video['video_id']}){view_info}")
            
            # Check if we've reached the limit
            if max_videos and len(all_videos) >= max_videos:
                break
            
            # Find next continuation (look for continuationItemRenderer)
            continuations = list(search_dict(response, "continuationItemRenderer"))
            if continuations:
                continuation_item = continuations[0]
                continuation = continuation_item.get('continuationEndpoint', None)
                if self.debug:
                    print(f"Found continuation: {continuation is not None}")
            else:
                continuation = None
                if self.debug:
                    print("No continuation found, stopping pagination")
            
            time.sleep(0.1)  # Be nice to YouTube's servers
        
        # Videos are already in correct order from YouTube (newest first, oldest last)
        # YouTube's /videos page returns videos in reverse chronological order by default
        # The order field maintains this sequence throughout pagination
        # No sorting needed - YouTube provides them in the correct order
        
        if show_progress:
            print(f"\n✅ Total videos fetched: {len(all_videos)}")
        elif self.debug:
            print(f"Total videos fetched: {len(all_videos)}")
        
        return all_videos
    
    def _ajax_request(self, endpoint, ytcfg, retries=5, sleep=20, timeout=60):
        return inertube_ajax_request(
            self.session, endpoint, ytcfg, retries=retries, sleep=float(sleep), timeout=timeout
        )
    
    def _parse_videos(self, data):
        """
        Parse video information from ytInitialData or API response.
        Returns a list of video dictionaries.
        """
        videos = []
        
        # Handle API response format (onResponseReceivedEndpoints)
        if 'onResponseReceivedEndpoints' in data:
            for endpoint in data['onResponseReceivedEndpoints']:
                if 'appendContinuationItemsAction' in endpoint:
                    items = endpoint['appendContinuationItemsAction'].get('continuationItems', [])
                    for item in items:
                        # Skip continuation items (they're not videos)
                        if 'continuationItemRenderer' in item:
                            continue
                        
                        rich_item = item.get('richItemRenderer', {})
                        if rich_item:
                            content = rich_item.get('content', {})
                            video_renderer = content.get('videoRenderer', {})
                            if video_renderer:
                                video = self._extract_video_info(video_renderer)
                                if video:
                                    videos.append(video)
            return videos
        
        # Handle API response format (onResponseReceivedActions) - alternative format
        if 'onResponseReceivedActions' in data:
            for action in data['onResponseReceivedActions']:
                if 'appendContinuationItemsAction' in action:
                    items = action['appendContinuationItemsAction'].get('continuationItems', [])
                    for item in items:
                        # Skip continuation items
                        if 'continuationItemRenderer' in item:
                            continue
                        
                        rich_item = item.get('richItemRenderer', {})
                        if rich_item:
                            content = rich_item.get('content', {})
                            video_renderer = content.get('videoRenderer', {})
                            if video_renderer:
                                video = self._extract_video_info(video_renderer)
                                if video:
                                    videos.append(video)
            return videos
        
        # Handle initial page format (ytInitialData for /videos page)
        # IMPORTANT: Do NOT use _search_dict here for ordering. It is a DFS stack traversal and
        # does not preserve list order, which breaks newest -> oldest ordering.
        videos = self._parse_initial_page_videos_in_order(data)
        if videos:
            return videos
        if self.debug:
            print("WARNING: Falling back to unordered richItemRenderer search. Ordering may be wrong.")
            print("WARNING: Consider updating _parse_initial_page_videos_in_order for this channel layout.")
        
        # Fallback (may be unordered)
        rich_items = list(search_dict(data, "richItemRenderer"))
        for item in rich_items:
            content = item.get('content', {})
            video_renderer = content.get('videoRenderer', {})
            if video_renderer:
                video = self._extract_video_info(video_renderer)
                if video:
                    videos.append(video)
        
        # Also check for gridVideoRenderer (alternative format)
        grid_videos = list(search_dict(data, "gridVideoRenderer"))
        for video_renderer in grid_videos:
            video = self._extract_video_info(video_renderer)
            if video:
                videos.append(video)
        
        return videos

    def _parse_initial_page_videos_in_order(self, data):
        """
        Parse videos from ytInitialData using the on-screen list order (newest -> oldest).
        This follows the richGridRenderer.contents array in order.
        """
        try:
            tabs = data.get('contents', {}).get('twoColumnBrowseResultsRenderer', {}).get('tabs', [])
            if not tabs:
                return []

            # Prefer the selected tab; otherwise pick the first tab with a richGridRenderer content.
            tab_renderer = None
            for t in tabs:
                tr = t.get('tabRenderer') or {}
                if tr.get('selected'):
                    tab_renderer = tr
                    break
            if not tab_renderer:
                for t in tabs:
                    tr = t.get('tabRenderer') or {}
                    if 'richGridRenderer' in (tr.get('content') or {}):
                        tab_renderer = tr
                        break
            if not tab_renderer:
                tab_renderer = tabs[0].get('tabRenderer') or {}

            content = tab_renderer.get('content', {}) or {}
            rich_grid = content.get('richGridRenderer', {}) or {}
            contents = rich_grid.get('contents', []) or []

            ordered_videos = []
            for item in contents:
                if 'richItemRenderer' in item:
                    vr = (
                        item['richItemRenderer']
                        .get('content', {})
                        .get('videoRenderer', {})
                    )
                    if vr and vr.get('videoId'):
                        video = self._extract_video_info(vr)
                        if video:
                            ordered_videos.append(video)
                # ignore continuationItemRenderer here; pagination handles it

            return ordered_videos
        except Exception:
            return []
    
    def _extract_video_info(self, video_renderer):
        """
        Extract video information from a videoRenderer object.
        """
        video_id = video_renderer.get('videoId')
        if not video_id:
            return None
        
        title = video_renderer.get('title', {}).get('runs', [{}])[0].get('text', '')
        if not title:
            title = video_renderer.get('title', {}).get('simpleText', '')
        
        # Channel ID is optional; keep it for future linking
        channel_id = ""
        owner_text = video_renderer.get("ownerText", {})
        runs = owner_text.get("runs", []) if owner_text else []
        if runs:
            channel_id = runs[0].get("navigationEndpoint", {}).get("browseEndpoint", {}).get("browseId", "")
        
        view_count_text = video_renderer.get("viewCountText", {})
        view_count_raw = ""
        if view_count_text:
            view_count_raw = view_count_text.get("simpleText", "") or ""
            if not view_count_raw:
                runs = view_count_text.get("runs", [])
                if runs:
                    view_count_raw = runs[0].get("text", "") or ""
        view_count = parse_view_count(view_count_raw)
        
        # Get length
        length_text = video_renderer.get('lengthText', {})
        length = ''
        if length_text:
            length = length_text.get('simpleText', '')
        
        # Get thumbnail
        thumbnails = video_renderer.get('thumbnail', {}).get('thumbnails', [])
        thumbnail_url = thumbnails[-1].get('url', '') if thumbnails else ''
        
        return {
            'video_id': video_id,
            'title': title,
            'channel_id': channel_id,
            'view_count': view_count,  # Parsed as integer, None if not parseable
            'view_count_raw': view_count_raw,  # Original string for reference
            'length': length,
            'thumbnail_url': thumbnail_url,
            'url': f'https://www.youtube.com/watch?v={video_id}'
        }
    
    # NOTE: `search_dict` is provided by shared/youtube.py; do not re-implement here.

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract videos from a YouTube channel')
    parser.add_argument('channel_id', help='YouTube channel ID (e.g., @realmadrid or UC...)')
    parser.add_argument('-o', '--output', help='Output JSON file path', default=None)
    parser.add_argument('--max-videos', type=int, help='Maximum number of videos to fetch (default: all)', default=None)
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--no-progress', action='store_true', help='Disable progress output')
    
    args = parser.parse_args()
    
    scraper = YoutubeChannelVideosScraper(debug=args.debug)
    
    print(f"Fetching videos from channel: {args.channel_id}")
    if args.max_videos:
        print(f"Limit: {args.max_videos} videos")
    else:
        print("No limit - fetching all videos")
    print()
    
    # Fetch all videos
    show_progress = not args.no_progress
    all_videos = scraper.get_all_videos(args.channel_id, max_videos=args.max_videos, show_progress=show_progress)
    
    # Determine output file
    if args.output:
        output_file = args.output
    else:
        # Generate filename from channel_id
        safe_channel_id = args.channel_id.replace('@', '').replace('/', '_')
        output_file = f"{safe_channel_id}_videos.json"
    
    # Export to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'channel_id': args.channel_id,
            'total_videos': len(all_videos),
            'videos': all_videos
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Videos exported to: {output_file}")
    
    # Show summary
    print("\nFirst 5 videos:")
    for i, video in enumerate(all_videos[:5], 1):
        print(f"\n{i}. {video['title']}")
        print(f"   Video ID: {video['video_id']}")
        print(f"   Order: {video.get('order', 'N/A')}")
        view_info = f"{video['view_count']:,}" if video.get('view_count') is not None else video.get('view_count_raw', 'N/A')
        print(f"   Views: {view_info}")
        print(f"   Length: {video['length']}")
        print(f"   URL: {video['url']}")
