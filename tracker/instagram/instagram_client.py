"""Instagram client for fetching video/reel data using yt-dlp."""

import re
import logging
from typing import Optional
import yt_dlp

logger = logging.getLogger(__name__)


def parse_duration(seconds) -> str:
    """Convert seconds to HH:MM:SS format."""
    if not seconds:
        return "00:00:00"

    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class InstagramClient:
    """Client for fetching Instagram video/reel data using yt-dlp."""

    def __init__(self, cookies_from_browser: str = None, cookies_file: str = None):
        self.request_count = 0
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
        }
        if cookies_file:
            self.ydl_opts['cookiefile'] = cookies_file
        elif cookies_from_browser:
            self.ydl_opts['cookiesfrombrowser'] = (cookies_from_browser,)

    def extract_post_id(self, url: str) -> Optional[str]:
        """Extract post/reel ID from Instagram URL."""
        patterns = [
            r'/reel/([A-Za-z0-9_-]+)',
            r'/p/([A-Za-z0-9_-]+)',
            r'/reels/([A-Za-z0-9_-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_video_details(self, urls: list[str]) -> dict[str, dict]:
        """Fetch detailed information for multiple videos. Returns dict keyed by post ID."""
        results = {}

        for url in urls:
            post_id = self.extract_post_id(url)
            if not post_id:
                logger.warning(f"Could not extract post ID from: {url}")
                continue

            try:
                self.request_count += 1
                logger.info(f"Fetching: {url}")

                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                if info:
                    # Clean title: remove newlines, limit length
                    title = info.get("description", info.get("title", "")) or ""
                    title = " ".join(title.split())[:200]  # Collapse whitespace/newlines

                    # Instagram uses play_count for reels, view_count for videos
                    views = info.get("view_count") or info.get("play_count") or 0

                    results[post_id] = {
                        "video_id": post_id,
                        "title": title,
                        "channel": info.get("uploader", info.get("channel", "")),
                        "duration": parse_duration(info.get("duration")),
                        "views": int(views),
                        "likes": int(info.get("like_count", 0) or 0),
                        "comments": int(info.get("comment_count", 0) or 0),
                        "published": (info.get("upload_date", "") or "")[:10],
                        "thumbnail": info.get("thumbnail", ""),
                    }
                    # Format published date
                    if results[post_id]["published"] and len(results[post_id]["published"]) == 8:
                        d = results[post_id]["published"]
                        results[post_id]["published"] = f"{d[:4]}-{d[4:6]}-{d[6:8]}"

            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")

        return results

    def get_video_stats(self, urls: list[str]) -> dict[str, dict]:
        """Fetch only statistics for multiple videos. Returns dict keyed by post ID."""
        results = {}

        for url in urls:
            post_id = self.extract_post_id(url)
            if not post_id:
                continue

            try:
                self.request_count += 1
                logger.info(f"Fetching stats: {url}")

                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                if info:
                    views = info.get("view_count") or info.get("play_count") or 0
                    results[post_id] = {
                        "views": int(views),
                        "likes": int(info.get("like_count", 0) or 0),
                        "comments": int(info.get("comment_count", 0) or 0),
                    }

            except Exception as e:
                logger.error(f"Error fetching stats for {url}: {e}")

        return results
