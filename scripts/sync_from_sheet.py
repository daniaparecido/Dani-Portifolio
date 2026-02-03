#!/usr/bin/env python3
"""
Sync video projects between Google Sheets and the portfolio website.

Supports: YouTube, Instagram, TikTok

Modes:
  --populate    Fetch all data for new URLs (rows without Video ID)
  --refresh     Update stats for existing videos
  --generate    Only generate projects.js from sheet data (no API calls)
"""

import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Google API imports
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import gspread

# yt-dlp for Instagram/TikTok
try:
    import yt_dlp
    HAS_YTDLP = True
except ImportError:
    HAS_YTDLP = False


# ============================================
# Configuration
# ============================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/youtube.readonly",
]

# Sheet column headers per worksheet type
HEADERS_YOUTUBE = ["URL", "Video ID", "Title", "Channel", "Views", "Last Updated"]
HEADERS_SOCIAL = ["URL", "Video ID", "Title", "Channel", "Views", "Likes", "Last Updated"]

# Map worksheet names to category and type
WORKSHEET_CONFIG = {
    "Long-term": {"category": "long-form", "headers": HEADERS_YOUTUBE, "type": "youtube"},
    "Short-term": {"category": "short-form", "headers": HEADERS_SOCIAL, "type": "mixed"},
    "Motion Design": {"category": "motion-design", "headers": HEADERS_YOUTUBE, "type": "youtube"},
}

ROOT_DIR = Path(__file__).parent.parent
PROJECTS_FILE = ROOT_DIR / "js" / "projects.js"

GMT_MINUS_3 = timezone(timedelta(hours=-3))


def get_timestamp() -> str:
    """Get current timestamp in GMT-3."""
    return datetime.now(GMT_MINUS_3).strftime("%Y-%m-%d %H:%M")


# ============================================
# Platform Detection
# ============================================

def detect_platform(url: str) -> str:
    """Detect platform from URL."""
    url_lower = url.lower()
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "instagram.com" in url_lower:
        return "instagram"
    elif "tiktok.com" in url_lower:
        return "tiktok"
    return "unknown"


def extract_video_id(url: str, platform: str) -> str | None:
    """Extract video ID based on platform."""
    if platform == "youtube":
        patterns = [
            r"(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([a-zA-Z0-9_-]{11})",
            r"^([a-zA-Z0-9_-]{11})$",
        ]
    elif platform == "instagram":
        patterns = [
            r'/reel/([A-Za-z0-9_-]+)',
            r'/p/([A-Za-z0-9_-]+)',
            r'/reels/([A-Za-z0-9_-]+)',
        ]
    elif platform == "tiktok":
        patterns = [
            r'/video/(\d+)',
            r'/v/(\d+)',
        ]
    else:
        return None

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


# ============================================
# YouTube Client
# ============================================

class YouTubeClient:
    def __init__(self, api_key: str):
        self.youtube = build("youtube", "v3", developerKey=api_key)

    def get_video_details(self, video_ids: list[str]) -> dict:
        """Fetch full video details from YouTube API."""
        results = {}
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            request = self.youtube.videos().list(
                part="snippet,statistics",
                id=",".join(batch)
            )
            response = request.execute()

            for item in response.get("items", []):
                video_id = item["id"]
                snippet = item["snippet"]
                stats = item.get("statistics", {})

                results[video_id] = {
                    "title": snippet.get("title", ""),
                    "channel": snippet.get("channelTitle", ""),
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                }
        return results

    def get_video_stats(self, video_ids: list[str]) -> dict:
        """Fetch only statistics."""
        results = {}
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            request = self.youtube.videos().list(
                part="statistics",
                id=",".join(batch)
            )
            response = request.execute()

            for item in response.get("items", []):
                video_id = item["id"]
                stats = item.get("statistics", {})
                results[video_id] = {
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                }
        return results


# ============================================
# Social Media Client (Instagram/TikTok via yt-dlp)
# ============================================

class SocialMediaClient:
    def __init__(self, cookies_file: str = None):
        if not HAS_YTDLP:
            raise ImportError("yt-dlp is required for Instagram/TikTok. Install with: pip install yt-dlp")

        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
        }

        if cookies_file and os.path.exists(cookies_file):
            self.ydl_opts['cookiefile'] = cookies_file

    def get_video_details(self, urls: list[str]) -> dict:
        """Fetch video details using yt-dlp."""
        results = {}

        for url in urls:
            try:
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                    if not info:
                        continue

                    video_id = extract_video_id(url, detect_platform(url))
                    title = info.get("description", info.get("title", "")) or ""
                    title = " ".join(title.split())[:100]  # Clean and truncate

                    # Instagram uses play_count for reels, view_count for videos
                    views = info.get("view_count") or info.get("play_count") or 0

                    results[video_id] = {
                        "title": title if title else info.get("title", ""),
                        "channel": info.get("uploader", info.get("channel", "")),
                        "views": int(views),
                        "likes": int(info.get("like_count", 0) or 0),
                        "platform": detect_platform(url),
                        "thumbnail": info.get("thumbnail", ""),
                        "url": url,
                    }
            except Exception as e:
                print(f"  Error fetching {url}: {e}")

        return results

    def get_video_stats(self, urls: list[str]) -> dict:
        """Fetch only stats using yt-dlp."""
        results = {}

        for url in urls:
            try:
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                    if not info:
                        continue

                    video_id = extract_video_id(url, detect_platform(url))
                    views = info.get("view_count") or info.get("play_count") or 0

                    results[video_id] = {
                        "views": int(views),
                        "likes": int(info.get("like_count", 0) or 0),
                        "platform": detect_platform(url),
                    }
            except Exception as e:
                print(f"  Error fetching stats for {url}: {e}")

        return results


# ============================================
# Google Sheets Client
# ============================================

class SheetsClient:
    def __init__(self, sheet_id: str, worksheet_name: str, headers: list[str],
                 credentials_file: str = None, credentials_json: str = None):
        if credentials_json:
            creds_dict = json.loads(credentials_json)
            credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        elif credentials_file:
            credentials = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
        else:
            raise ValueError("Either credentials_file or credentials_json must be provided")

        self.client = gspread.authorize(credentials)
        self.spreadsheet = self.client.open_by_key(sheet_id)
        self.worksheet_name = worksheet_name
        self.headers = headers
        self.has_likes = "Likes" in headers
        self.worksheet = self._get_or_create_worksheet()

    def _get_or_create_worksheet(self) -> gspread.Worksheet:
        """Get worksheet by name or create it with headers."""
        try:
            worksheet = self.spreadsheet.worksheet(self.worksheet_name)
        except gspread.WorksheetNotFound:
            worksheet = self.spreadsheet.add_worksheet(
                title=self.worksheet_name, rows=1000, cols=len(self.headers)
            )
            worksheet.update("A1", [self.headers])
            print(f"  Created worksheet '{self.worksheet_name}' with headers")
        return worksheet

    def ensure_headers(self):
        """Ensure the worksheet has correct headers."""
        current_headers = self.worksheet.row_values(1)
        if current_headers != self.headers:
            self.worksheet.update("A1", [self.headers])
            print(f"  Updated headers in '{self.worksheet_name}'")

    def get_all_rows(self) -> list[dict]:
        """Get all rows with data."""
        all_values = self.worksheet.get_all_values()
        rows = []

        for idx, row in enumerate(all_values[1:], start=2):  # Skip header
            url = row[0] if len(row) > 0 else ""
            if not url.strip():
                continue

            if self.has_likes:
                # Social format: URL, Video ID, Title, Channel, Views, Likes, Last Updated
                rows.append({
                    "row_num": idx,
                    "url": url.strip(),
                    "video_id": row[1].strip() if len(row) > 1 else "",
                    "title": row[2] if len(row) > 2 else "",
                    "channel": row[3] if len(row) > 3 else "",
                    "views": int(row[4]) if len(row) > 4 and row[4].isdigit() else 0,
                    "likes": int(row[5]) if len(row) > 5 and row[5].isdigit() else 0,
                    "has_data": len(row) > 1 and row[1].strip() != "",
                    "platform": detect_platform(url),
                })
            else:
                # YouTube format: URL, Video ID, Title, Channel, Views, Last Updated
                rows.append({
                    "row_num": idx,
                    "url": url.strip(),
                    "video_id": row[1].strip() if len(row) > 1 else "",
                    "title": row[2] if len(row) > 2 else "",
                    "channel": row[3] if len(row) > 3 else "",
                    "views": int(row[4]) if len(row) > 4 and row[4].isdigit() else 0,
                    "likes": 0,
                    "has_data": len(row) > 1 and row[1].strip() != "",
                    "platform": "youtube",
                })
        return rows

    def batch_update_full(self, updates: list[tuple[int, dict]]):
        """Update full row data."""
        timestamp = get_timestamp()
        batch_data = []

        for row_num, data in updates:
            if self.has_likes:
                row_values = [
                    data.get("url", ""),
                    data.get("video_id", ""),
                    data.get("title", ""),
                    data.get("channel", ""),
                    data.get("views", 0),
                    data.get("likes", 0),
                    timestamp,
                ]
                end_col = "G"
            else:
                row_values = [
                    data.get("url", ""),
                    data.get("video_id", ""),
                    data.get("title", ""),
                    data.get("channel", ""),
                    data.get("views", 0),
                    timestamp,
                ]
                end_col = "F"

            batch_data.append({
                "range": f"A{row_num}:{end_col}{row_num}",
                "values": [row_values]
            })

        if batch_data:
            self.worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')
            print(f"  Updated {len(updates)} rows in '{self.worksheet_name}'")

    def batch_update_stats(self, updates: list[tuple[int, dict]]):
        """Update only stats and timestamp."""
        timestamp = get_timestamp()
        batch_data = []

        for row_num, data in updates:
            if self.has_likes:
                # Update Views (E), Likes (F), Last Updated (G)
                batch_data.append({
                    "range": f"E{row_num}:G{row_num}",
                    "values": [[data.get("views", 0), data.get("likes", 0), timestamp]]
                })
            else:
                # Update Views (E), Last Updated (F)
                batch_data.append({
                    "range": f"E{row_num}:F{row_num}",
                    "values": [[data.get("views", 0), timestamp]]
                })

        if batch_data:
            self.worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')
            print(f"  Updated stats for {len(updates)} rows in '{self.worksheet_name}'")


# ============================================
# Projects.js Generator
# ============================================

def format_count(count: int, label: str = "views") -> str:
    """Format count for display."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M {label}"
    elif count >= 1_000:
        return f"{count / 1_000:.0f}K {label}"
    else:
        return f"{count} {label}"


def escape_js_string(s: str) -> str:
    """Escape special characters for JavaScript strings."""
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')


def generate_projects_js(projects: list[dict]) -> str:
    """Generate the projects.js file content."""
    lines = [
        '/**',
        ' * ============================================',
        ' * PROJECT DATA - AUTO-GENERATED FROM GOOGLE SHEETS',
        ' * ============================================',
        ' *',
        ' * To update this file, run: python scripts/sync_from_sheet.py',
        ' * Or use the /sync-videos skill in Claude Code',
        f' * Last updated: {get_timestamp()}',
        ' */',
        '',
        'const projects = [',
    ]

    for project in projects:
        platform = project.get("platform", "youtube")

        # For Instagram, use likes instead of views
        if platform == "instagram" and project.get("views", 0) == 0:
            view_count = format_count(project.get("likes", 0), "likes")
        else:
            view_count = format_count(project.get("views", 0), "views")

        # Build thumbnail URL
        thumbnail = project.get("thumbnail", "")

        # Build video URL for non-YouTube platforms
        video_url = project.get("url", "")

        lines.append('    {')
        lines.append(f'        title: "{escape_js_string(project["title"])}",')
        lines.append(f'        category: "{project["category"]}",')
        lines.append(f'        videoId: "{project["youtubeId"]}",')
        lines.append(f'        platform: "{platform}",')
        lines.append(f'        channelName: "{escape_js_string(project["channelName"])}",')
        lines.append(f'        viewCount: "{view_count}",')
        lines.append(f'        thumbnail: "{thumbnail}",')
        lines.append(f'        url: "{video_url}",')
        lines.append(f'        previewVideo: "videos/previews/{project["youtubeId"]}.mp4"')
        lines.append('    },')

    lines.append('];')
    lines.append('')

    return '\n'.join(lines)


# ============================================
# Main Logic
# ============================================

def load_config() -> dict:
    """Load configuration from environment variables."""
    load_dotenv(ROOT_DIR / ".env")

    config = {
        "youtube_api_key": os.getenv("YOUTUBE_API_KEY"),
        "google_sheet_id": os.getenv("GOOGLE_SHEET_ID"),
        "credentials_file": os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"),
        "credentials_json": os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"),
        "cookies_file": os.getenv("COOKIES_FILE", str(ROOT_DIR / "cookies.txt")),
    }

    # Resolve relative paths
    if config["credentials_file"] and not os.path.isabs(config["credentials_file"]):
        config["credentials_file"] = str(ROOT_DIR / config["credentials_file"])

    # Validate
    if not config["credentials_file"] and not config["credentials_json"]:
        raise ValueError("Either GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON required")

    if config["credentials_file"] and not os.path.exists(config["credentials_file"]):
        if not config["credentials_json"]:
            raise FileNotFoundError(f"Service account file not found: {config['credentials_file']}")

    if not config["youtube_api_key"]:
        raise ValueError("YOUTUBE_API_KEY is required")

    if not config["google_sheet_id"]:
        raise ValueError("GOOGLE_SHEET_ID is required")

    return config


def process_worksheet(config: dict, ws_name: str, ws_config: dict,
                      mode: str = "populate", dry_run: bool = False,
                      fetch_thumbnails: bool = False) -> list[dict]:
    """Process a single worksheet and return projects."""
    print(f"\nProcessing: {ws_name}")

    category = ws_config["category"]
    headers = ws_config["headers"]

    sheets = SheetsClient(
        sheet_id=config["google_sheet_id"],
        worksheet_name=ws_name,
        headers=headers,
        credentials_file=config["credentials_file"],
        credentials_json=config.get("credentials_json"),
    )
    sheets.ensure_headers()

    rows = sheets.get_all_rows()
    new_rows = [r for r in rows if not r["has_data"]]
    existing_rows = [r for r in rows if r["has_data"]]

    print(f"  Found {len(new_rows)} new URLs, {len(existing_rows)} existing")

    # Initialize clients
    youtube_client = YouTubeClient(config["youtube_api_key"])
    social_client = None
    if HAS_YTDLP:
        social_client = SocialMediaClient(config.get("cookies_file"))

    # Storage for thumbnails fetched during this run
    thumbnails = {}

    # Process based on mode
    if mode == "populate" and new_rows:
        # Group by platform
        youtube_rows = [r for r in new_rows if r["platform"] == "youtube"]
        social_rows = [r for r in new_rows if r["platform"] in ("instagram", "tiktok")]

        updates = []

        # Process YouTube
        if youtube_rows:
            video_ids = []
            row_map = {}
            for row in youtube_rows:
                vid = extract_video_id(row["url"], "youtube")
                if vid:
                    video_ids.append(vid)
                    row_map[vid] = row

            if video_ids:
                print(f"  Fetching YouTube metadata for {len(video_ids)} videos...")
                details = youtube_client.get_video_details(video_ids)

                for vid, data in details.items():
                    row = row_map[vid]
                    updates.append((row["row_num"], {
                        "url": row["url"],
                        "video_id": vid,
                        "title": data["title"],
                        "channel": data["channel"],
                        "views": data["views"],
                        "likes": data.get("likes", 0),
                    }))

        # Process Instagram/TikTok
        if social_rows and social_client:
            print(f"  Fetching social media metadata for {len(social_rows)} videos...")
            urls = [r["url"] for r in social_rows]
            details = social_client.get_video_details(urls)

            for row in social_rows:
                vid = extract_video_id(row["url"], row["platform"])
                if vid and vid in details:
                    data = details[vid]
                    # Store thumbnail for later use
                    if data.get("thumbnail"):
                        thumbnails[vid] = data["thumbnail"]
                    updates.append((row["row_num"], {
                        "url": row["url"],
                        "video_id": vid,
                        "title": data["title"],
                        "channel": data["channel"],
                        "views": data["views"],
                        "likes": data.get("likes", 0),
                    }))

        if updates and not dry_run:
            sheets.batch_update_full(updates)

    elif mode == "refresh" and existing_rows:
        # Group by platform
        youtube_rows = [r for r in existing_rows if r["platform"] == "youtube"]
        social_rows = [r for r in existing_rows if r["platform"] in ("instagram", "tiktok")]

        updates = []

        # Refresh YouTube
        if youtube_rows:
            video_ids = [r["video_id"] for r in youtube_rows]
            row_map = {r["video_id"]: r for r in youtube_rows}

            print(f"  Refreshing YouTube stats for {len(video_ids)} videos...")
            stats = youtube_client.get_video_stats(video_ids)

            for vid, data in stats.items():
                row = row_map[vid]
                row["views"] = data["views"]
                row["likes"] = data.get("likes", 0)
                updates.append((row["row_num"], data))

        # Refresh social media
        if social_rows and social_client:
            print(f"  Refreshing social media stats for {len(social_rows)} videos...")
            urls = [r["url"] for r in social_rows]
            stats = social_client.get_video_stats(urls)

            for row in social_rows:
                vid = row["video_id"]
                if vid in stats:
                    data = stats[vid]
                    row["views"] = data["views"]
                    row["likes"] = data.get("likes", 0)
                    updates.append((row["row_num"], data))

        if updates and not dry_run:
            sheets.batch_update_stats(updates)

    # Fetch thumbnails for social media videos if requested
    if fetch_thumbnails and social_client:
        social_existing = [r for r in existing_rows if r["platform"] in ("instagram", "tiktok")]
        if social_existing:
            print(f"  Fetching thumbnails for {len(social_existing)} social media videos...")
            urls = [r["url"] for r in social_existing]
            details = social_client.get_video_details(urls)
            for vid, data in details.items():
                if data.get("thumbnail"):
                    thumbnails[vid] = data["thumbnail"]

    # Re-fetch rows after updates
    if mode != "generate":
        rows = sheets.get_all_rows()

    # Build projects list
    projects = []
    for row in rows:
        if row["has_data"]:
            # Use fetched thumbnail if available
            thumbnail = thumbnails.get(row["video_id"], row.get("thumbnail", ""))
            projects.append({
                "title": row["title"],
                "category": category,
                "youtubeId": row["video_id"],
                "channelName": row["channel"],
                "views": row["views"],
                "likes": row.get("likes", 0),
                "platform": row.get("platform", "youtube"),
                "thumbnail": thumbnail,
                "url": row.get("url", ""),
            })

    return projects


def main():
    parser = argparse.ArgumentParser(description="Sync videos from Google Sheets")
    parser.add_argument("--populate", action="store_true",
                        help="Fetch full data for new URLs")
    parser.add_argument("--refresh", action="store_true",
                        help="Update stats for existing videos")
    parser.add_argument("--generate", action="store_true",
                        help="Only generate projects.js (no API calls)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making changes")
    parser.add_argument("--fetch-thumbnails", action="store_true",
                        help="Fetch thumbnails for Instagram/TikTok videos")
    parser.add_argument("--download", action="store_true",
                        help="Also download/process preview videos")

    args = parser.parse_args()

    # Default to populate if no mode specified
    if not args.populate and not args.refresh and not args.generate:
        args.populate = True

    mode = "generate" if args.generate else ("refresh" if args.refresh else "populate")

    try:
        config = load_config()
        print(f"\n{'=' * 50}")
        print(f"SYNC VIDEOS - Mode: {mode.upper()}")
        print(f"{'=' * 50}")
        print(f"Sheet ID: {config['google_sheet_id']}")

        all_projects = []

        for ws_name, ws_config in WORKSHEET_CONFIG.items():
            projects = process_worksheet(config, ws_name, ws_config, mode, args.dry_run, args.fetch_thumbnails)
            all_projects.extend(projects)

        # Generate projects.js
        if all_projects:
            print(f"\nGenerating projects.js with {len(all_projects)} projects...")
            content = generate_projects_js(all_projects)

            if args.dry_run:
                print("\n[DRY RUN] Would write:")
                print("-" * 40)
                print(content[:800] + "..." if len(content) > 800 else content)
            else:
                PROJECTS_FILE.write_text(content, encoding="utf-8")
                print(f"Written to: {PROJECTS_FILE}")

            # Download videos if requested
            if args.download and not args.dry_run:
                print("\nDownloading preview videos...")
                import subprocess
                for project in all_projects:
                    video_id = project["youtubeId"]
                    platform = project.get("platform", "youtube")
                    url = project.get("url", "")
                    preview_path = ROOT_DIR / "videos" / "previews" / f"{video_id}.mp4"
                    thumb_path = ROOT_DIR / "images" / "thumbnails" / f"{video_id}.jpg"

                    # Check if we need to process this video
                    needs_preview = not preview_path.exists()
                    needs_thumb = platform in ("instagram", "tiktok") and not thumb_path.exists()

                    if needs_preview or needs_thumb:
                        print(f"  Processing: {video_id} ({platform})")
                        if platform in ("instagram", "tiktok") and url:
                            # Use -Url for Instagram/TikTok
                            subprocess.run([
                                "powershell", "-ExecutionPolicy", "Bypass",
                                "-File", str(ROOT_DIR / "scripts" / "process-videos.ps1"),
                                "-Url", url, "-NoPause"
                            ], cwd=ROOT_DIR)
                        else:
                            # Use -All for YouTube
                            subprocess.run([
                                "powershell", "-ExecutionPolicy", "Bypass",
                                "-File", str(ROOT_DIR / "scripts" / "process-videos.ps1"),
                                "-All", video_id, "-NoPause"
                            ], cwd=ROOT_DIR)
        else:
            print("\nNo projects found.")

        print(f"\n{'=' * 50}")
        print("SYNC COMPLETE")
        print(f"{'=' * 50}\n")

    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == "__main__":
    main()
