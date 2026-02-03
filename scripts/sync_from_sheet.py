#!/usr/bin/env python3
"""
Sync video projects between Google Sheets and the portfolio website.

Modes:
  --populate    Fetch all data for new URLs (rows without Video ID)
  --refresh     Update view counts for existing videos
  --generate    Only generate projects.js from sheet data (no API calls)

The script writes metadata back to the sheet and generates projects.js.
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


# ============================================
# Configuration
# ============================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/youtube.readonly",
]

# Sheet column headers
HEADERS = ["URL", "Video ID", "Title", "Channel", "Views", "Last Updated"]

# Map worksheet names to category values
WORKSHEET_CATEGORIES = {
    "Long-term": "long-form",
    "Short-term": "short-form",
    "Motion Design": "motion-design",
}

ROOT_DIR = Path(__file__).parent.parent
PROJECTS_FILE = ROOT_DIR / "js" / "projects.js"

GMT_MINUS_3 = timezone(timedelta(hours=-3))


def get_timestamp() -> str:
    """Get current timestamp in GMT-3."""
    return datetime.now(GMT_MINUS_3).strftime("%Y-%m-%d %H:%M")


# ============================================
# YouTube Client
# ============================================

class YouTubeClient:
    def __init__(self, api_key: str):
        self.youtube = build("youtube", "v3", developerKey=api_key)

    def extract_video_id(self, url: str) -> str | None:
        """Extract video ID from various YouTube URL formats."""
        patterns = [
            r"(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([a-zA-Z0-9_-]{11})",
            r"^([a-zA-Z0-9_-]{11})$",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

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
                }
        return results

    def get_video_stats(self, video_ids: list[str]) -> dict:
        """Fetch only statistics (lighter API call for refreshing)."""
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
                }
        return results


# ============================================
# Google Sheets Client
# ============================================

class SheetsClient:
    def __init__(self, sheet_id: str, worksheet_name: str,
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
        self.worksheet = self._get_or_create_worksheet()

    def _get_or_create_worksheet(self) -> gspread.Worksheet:
        """Get worksheet by name or create it with headers."""
        try:
            worksheet = self.spreadsheet.worksheet(self.worksheet_name)
        except gspread.WorksheetNotFound:
            worksheet = self.spreadsheet.add_worksheet(
                title=self.worksheet_name, rows=1000, cols=len(HEADERS)
            )
            worksheet.update("A1", [HEADERS])
            print(f"  Created worksheet '{self.worksheet_name}' with headers")
        return worksheet

    def ensure_headers(self):
        """Ensure the worksheet has correct headers."""
        current_headers = self.worksheet.row_values(1)
        if current_headers != HEADERS:
            self.worksheet.update("A1", [HEADERS])
            print(f"  Updated headers in '{self.worksheet_name}'")

    def get_all_rows(self) -> list[dict]:
        """Get all rows with data."""
        all_values = self.worksheet.get_all_values()
        rows = []

        for idx, row in enumerate(all_values[1:], start=2):  # Skip header
            url = row[0] if len(row) > 0 else ""
            if not url.strip():
                continue

            rows.append({
                "row_num": idx,
                "url": url.strip(),
                "video_id": row[1].strip() if len(row) > 1 else "",
                "title": row[2] if len(row) > 2 else "",
                "channel": row[3] if len(row) > 3 else "",
                "views": int(row[4]) if len(row) > 4 and row[4].isdigit() else 0,
                "has_data": len(row) > 1 and row[1].strip() != "",
            })
        return rows

    def batch_update_full(self, updates: list[tuple[int, dict]]):
        """Update full row data. Each tuple is (row_num, data_dict)."""
        timestamp = get_timestamp()
        batch_data = []

        for row_num, data in updates:
            row_values = [
                data.get("url", ""),
                data.get("video_id", ""),
                data.get("title", ""),
                data.get("channel", ""),
                data.get("views", 0),
                timestamp,
            ]
            batch_data.append({
                "range": f"A{row_num}:F{row_num}",
                "values": [row_values]
            })

        if batch_data:
            self.worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')
            print(f"  Updated {len(updates)} rows in '{self.worksheet_name}'")

    def batch_update_stats(self, updates: list[tuple[int, int]]):
        """Update only views and timestamp. Each tuple is (row_num, views)."""
        timestamp = get_timestamp()
        batch_data = []

        for row_num, views in updates:
            # Update Views (E) and Last Updated (F)
            batch_data.append({
                "range": f"E{row_num}:F{row_num}",
                "values": [[views, timestamp]]
            })

        if batch_data:
            self.worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')
            print(f"  Updated stats for {len(updates)} rows in '{self.worksheet_name}'")


# ============================================
# Projects.js Generator
# ============================================

def format_view_count(count: int) -> str:
    """Format view count for display."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M views"
    elif count >= 1_000:
        return f"{count / 1_000:.0f}K views"
    else:
        return f"{count} views"


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
        lines.append('    {')
        lines.append(f'        title: "{escape_js_string(project["title"])}",')
        lines.append(f'        category: "{project["category"]}",')
        lines.append(f'        youtubeId: "{project["youtubeId"]}",')
        lines.append(f'        channelName: "{escape_js_string(project["channelName"])}",')
        lines.append(f'        viewCount: "{project["viewCount"]}",')
        lines.append(f'        thumbnail: "",')
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
    }

    # Resolve relative paths
    if config["credentials_file"] and not os.path.isabs(config["credentials_file"]):
        config["credentials_file"] = str(ROOT_DIR / config["credentials_file"])

    # Validate - need either file or json for credentials
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


def populate_new_videos(config: dict, dry_run: bool = False):
    """Fetch full data for new URLs (rows without Video ID)."""
    print("\n" + "=" * 50)
    print("POPULATING NEW VIDEOS")
    print("=" * 50)

    youtube = YouTubeClient(config["youtube_api_key"])
    all_projects = []

    for ws_name, category in WORKSHEET_CATEGORIES.items():
        print(f"\nProcessing: {ws_name}")

        sheets = SheetsClient(
            sheet_id=config["google_sheet_id"],
            worksheet_name=ws_name,
            credentials_file=config["credentials_file"],
            credentials_json=config.get("credentials_json"),
        )
        sheets.ensure_headers()

        rows = sheets.get_all_rows()
        new_rows = [r for r in rows if not r["has_data"]]
        existing_rows = [r for r in rows if r["has_data"]]

        print(f"  Found {len(new_rows)} new URLs, {len(existing_rows)} existing")

        # Process new rows
        if new_rows:
            video_ids = []
            row_map = {}  # video_id -> row info

            for row in new_rows:
                video_id = youtube.extract_video_id(row["url"])
                if video_id:
                    video_ids.append(video_id)
                    row_map[video_id] = row
                else:
                    print(f"  Warning: Could not extract ID from: {row['url']}")

            if video_ids:
                print(f"  Fetching metadata for {len(video_ids)} videos...")
                details = youtube.get_video_details(video_ids)

                updates = []
                for video_id, data in details.items():
                    row = row_map[video_id]
                    updates.append((row["row_num"], {
                        "url": row["url"],
                        "video_id": video_id,
                        "title": data["title"],
                        "channel": data["channel"],
                        "views": data["views"],
                    }))

                if not dry_run:
                    sheets.batch_update_full(updates)

        # Collect all projects for this category
        all_rows = sheets.get_all_rows()  # Re-fetch after updates
        for row in all_rows:
            if row["has_data"]:
                all_projects.append({
                    "title": row["title"],
                    "category": category,
                    "youtubeId": row["video_id"],
                    "channelName": row["channel"],
                    "viewCount": format_view_count(row["views"]),
                })

    return all_projects


def refresh_stats(config: dict, dry_run: bool = False):
    """Update view counts for existing videos."""
    print("\n" + "=" * 50)
    print("REFRESHING VIDEO STATS")
    print("=" * 50)

    youtube = YouTubeClient(config["youtube_api_key"])
    all_projects = []

    for ws_name, category in WORKSHEET_CATEGORIES.items():
        print(f"\nProcessing: {ws_name}")

        sheets = SheetsClient(
            sheet_id=config["google_sheet_id"],
            worksheet_name=ws_name,
            credentials_file=config["credentials_file"],
            credentials_json=config.get("credentials_json"),
        )

        rows = sheets.get_all_rows()
        existing_rows = [r for r in rows if r["has_data"]]

        print(f"  Found {len(existing_rows)} videos to refresh")

        if existing_rows:
            video_ids = [r["video_id"] for r in existing_rows]
            row_map = {r["video_id"]: r for r in existing_rows}

            print(f"  Fetching stats...")
            stats = youtube.get_video_stats(video_ids)

            updates = []
            for video_id, data in stats.items():
                row = row_map[video_id]
                updates.append((row["row_num"], data["views"]))

                # Update row data for projects.js generation
                row["views"] = data["views"]

            if not dry_run:
                sheets.batch_update_stats(updates)

        # Collect all projects for this category
        for row in existing_rows:
            all_projects.append({
                "title": row["title"],
                "category": category,
                "youtubeId": row["video_id"],
                "channelName": row["channel"],
                "viewCount": format_view_count(row["views"]),
            })

    return all_projects


def generate_only(config: dict):
    """Generate projects.js from sheet data without API calls."""
    print("\n" + "=" * 50)
    print("GENERATING projects.js FROM SHEET")
    print("=" * 50)

    all_projects = []

    for ws_name, category in WORKSHEET_CATEGORIES.items():
        print(f"\nReading: {ws_name}")

        sheets = SheetsClient(
            sheet_id=config["google_sheet_id"],
            worksheet_name=ws_name,
            credentials_file=config["credentials_file"],
            credentials_json=config.get("credentials_json"),
        )

        rows = sheets.get_all_rows()
        existing_rows = [r for r in rows if r["has_data"]]

        print(f"  Found {len(existing_rows)} videos")

        for row in existing_rows:
            all_projects.append({
                "title": row["title"],
                "category": category,
                "youtubeId": row["video_id"],
                "channelName": row["channel"],
                "viewCount": format_view_count(row["views"]),
            })

    return all_projects


def main():
    parser = argparse.ArgumentParser(description="Sync videos from Google Sheets")
    parser.add_argument("--populate", action="store_true",
                        help="Fetch full data for new URLs")
    parser.add_argument("--refresh", action="store_true",
                        help="Update view counts for existing videos")
    parser.add_argument("--generate", action="store_true",
                        help="Only generate projects.js (no API calls)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making changes")
    parser.add_argument("--download", action="store_true",
                        help="Also download/process preview videos")

    args = parser.parse_args()

    # Default to populate if no mode specified
    if not args.populate and not args.refresh and not args.generate:
        args.populate = True

    try:
        config = load_config()
        print(f"Sheet ID: {config['google_sheet_id']}")

        # Run the appropriate mode
        if args.generate:
            projects = generate_only(config)
        elif args.refresh:
            projects = refresh_stats(config, args.dry_run)
        else:
            projects = populate_new_videos(config, args.dry_run)

        # Generate projects.js
        if projects:
            print(f"\nGenerating projects.js with {len(projects)} projects...")
            content = generate_projects_js(projects)

            if args.dry_run:
                print("\n[DRY RUN] Would write:")
                print("-" * 40)
                print(content[:500] + "..." if len(content) > 500 else content)
            else:
                PROJECTS_FILE.write_text(content, encoding="utf-8")
                print(f"Written to: {PROJECTS_FILE}")

            # Download videos if requested
            if args.download and not args.dry_run:
                print("\nDownloading preview videos...")
                import subprocess
                for project in projects:
                    video_id = project["youtubeId"]
                    preview_path = ROOT_DIR / "videos" / "previews" / f"{video_id}.mp4"
                    if not preview_path.exists():
                        print(f"  Processing: {video_id}")
                        subprocess.run([
                            "powershell", "-ExecutionPolicy", "Bypass",
                            "-File", str(ROOT_DIR / "scripts" / "process-videos.ps1"),
                            "-All", video_id
                        ], cwd=ROOT_DIR)
        else:
            print("\nNo projects found.")

        print("\n" + "=" * 50)
        print("SYNC COMPLETE")
        print("=" * 50 + "\n")

    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == "__main__":
    main()
