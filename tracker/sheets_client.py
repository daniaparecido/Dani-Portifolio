"""Google Sheets client for reading URLs and writing video data."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

HEADERS = ["URL", "Video ID", "Title", "Channel", "Duration", "Views", "Likes", "Comments", "Published", "Thumbnail", "Last Updated"]

# Instagram headers (no Views column)
HEADERS_INSTAGRAM = ["URL", "Video ID", "Title", "Channel", "Duration", "Likes", "Comments", "Published", "Thumbnail", "Last Updated"]

# Worksheet names for different video types
WORKSHEETS = ["Long-form", "Short-form"]

GMT_MINUS_3 = timezone(timedelta(hours=-3))


def get_timestamp() -> str:
    """Get current timestamp in GMT-3."""
    return datetime.now(GMT_MINUS_3).strftime("%Y-%m-%d %H:%M")


def _text(value) -> str:
    """Prefix with apostrophe to force Google Sheets to treat as text, not number/date/time."""
    return f"'{value}" if value else ""


class SheetsClient:
    """Client for interacting with Google Sheets."""

    def __init__(self, sheet_id: str, worksheet_name: str = "Long-form",
                 credentials_file: Optional[str] = None,
                 credentials_json: Optional[str] = None,
                 headers: list[str] = None):
        """Initialize with either a credentials file path or JSON string."""
        if credentials_json:
            creds_dict = json.loads(credentials_json)
            credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        elif credentials_file:
            credentials = Credentials.from_service_account_file(credentials_file, scopes=SCOPES)
        else:
            raise ValueError("Either credentials_file or credentials_json must be provided")

        self.headers = headers if headers else HEADERS
        self.has_views = "Views" in self.headers
        self.client = gspread.authorize(credentials)
        self.spreadsheet = self.client.open_by_key(sheet_id)
        self.worksheet_name = worksheet_name
        self.worksheet = self._get_or_create_worksheet()
        logger.info(f"Connected to spreadsheet: {self.spreadsheet.title} [{worksheet_name}]")

    def _get_or_create_worksheet(self) -> gspread.Worksheet:
        """Get worksheet by name or create it with headers."""
        try:
            worksheet = self.spreadsheet.worksheet(self.worksheet_name)
            logger.info(f"Found existing {self.worksheet_name} worksheet")
        except gspread.WorksheetNotFound:
            worksheet = self.spreadsheet.add_worksheet(title=self.worksheet_name, rows=1000, cols=len(self.headers))
            worksheet.update("A1", [self.headers])
            logger.info(f"Created {self.worksheet_name} worksheet with headers")
        return worksheet

    def ensure_headers(self):
        """Ensure the worksheet has correct headers."""
        current_headers = self.worksheet.row_values(1)
        if current_headers != self.headers:
            self.worksheet.update("A1", [self.headers])
            logger.info("Updated headers")

    def get_all_rows(self) -> list[dict]:
        """Get all rows with their URLs and row numbers."""
        all_values = self.worksheet.get_all_values()

        rows = []
        for idx, row in enumerate(all_values[1:], start=2):  # Skip header, rows start at 2
            url = row[0] if row else ""
            if url.strip():
                rows.append({
                    "row_num": idx,
                    "url": url.strip(),
                    "has_data": len(row) > 1 and row[1].strip() != ""  # Check if Video ID exists
                })

        return rows

    def update_row(self, row_num: int, url: str, video_data: dict):
        """Update a single row with video data."""
        timestamp = get_timestamp()

        if self.has_views:
            row_values = [
                url,
                _text(video_data.get("video_id", "")),
                video_data.get("title", ""),
                video_data.get("channel", ""),
                _text(video_data.get("duration", "")),
                video_data.get("views", 0),
                video_data.get("likes", 0),
                video_data.get("comments", 0),
                _text(video_data.get("published", "")),
                video_data.get("thumbnail", ""),
                timestamp
            ]
            end_col = "K"
        else:
            row_values = [
                url,
                _text(video_data.get("video_id", "")),
                video_data.get("title", ""),
                video_data.get("channel", ""),
                _text(video_data.get("duration", "")),
                video_data.get("likes", 0),
                video_data.get("comments", 0),
                _text(video_data.get("published", "")),
                video_data.get("thumbnail", ""),
                timestamp
            ]
            end_col = "J"

        self.worksheet.update(f"A{row_num}:{end_col}{row_num}", [row_values], value_input_option='USER_ENTERED')

    def batch_update_rows(self, updates: list[tuple[int, str, dict]]):
        """Batch update multiple rows. Each tuple is (row_num, url, video_data)."""
        timestamp = get_timestamp()
        end_col = "K" if self.has_views else "J"

        batch_data = []
        for row_num, url, video_data in updates:
            if self.has_views:
                row_values = [
                    url,
                    _text(video_data.get("video_id", "")),
                    video_data.get("title", ""),
                    video_data.get("channel", ""),
                    _text(video_data.get("duration", "")),
                    video_data.get("views", 0),
                    video_data.get("likes", 0),
                    video_data.get("comments", 0),
                    _text(video_data.get("published", "")),
                    video_data.get("thumbnail", ""),
                    timestamp
                ]
            else:
                row_values = [
                    url,
                    _text(video_data.get("video_id", "")),
                    video_data.get("title", ""),
                    video_data.get("channel", ""),
                    _text(video_data.get("duration", "")),
                    video_data.get("likes", 0),
                    video_data.get("comments", 0),
                    _text(video_data.get("published", "")),
                    video_data.get("thumbnail", ""),
                    timestamp
                ]
            batch_data.append({
                "range": f"A{row_num}:{end_col}{row_num}",
                "values": [row_values]
            })

        if batch_data:
            self.worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')

        logger.info(f"Updated {len(updates)} rows")

    def batch_update_stats(self, updates: list[tuple[int, dict]]):
        """Update only stats and Last Updated. Each tuple is (row_num, stats)."""
        timestamp = get_timestamp()

        # Prepare batch updates
        batch_data = []
        for row_num, stats in updates:
            if self.has_views:
                # Stats columns F:H (Views, Likes, Comments), Last Updated K
                batch_data.append({
                    "range": f"F{row_num}:H{row_num}",
                    "values": [[
                        stats.get("views", 0),
                        stats.get("likes", 0),
                        stats.get("comments", 0),
                    ]]
                })
                batch_data.append({
                    "range": f"K{row_num}",
                    "values": [[timestamp]]
                })
            else:
                # Stats columns F:G (Likes, Comments), Last Updated J
                batch_data.append({
                    "range": f"F{row_num}:G{row_num}",
                    "values": [[
                        stats.get("likes", 0),
                        stats.get("comments", 0),
                    ]]
                })
                batch_data.append({
                    "range": f"J{row_num}",
                    "values": [[timestamp]]
                })

        # Execute batch update
        self.worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')
        logger.info(f"Updated stats for {len(updates)} rows")
