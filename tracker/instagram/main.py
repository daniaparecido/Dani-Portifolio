"""Main script to fetch Instagram video/reel data and update Google Sheets."""

import os
import sys
import logging
import argparse

# Add parent directory to path for shared modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from instagram_client import InstagramClient
from sheets_client import SheetsClient, HEADERS_INSTAGRAM

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

WORKSHEET_NAME = "Instagram"


def load_config() -> dict:
    """Load configuration from environment variables."""
    load_dotenv()

    config = {
        "google_sheet_id": os.getenv("SOCIAL_SHEET_ID"),
        "credentials_file": os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE"),
        "credentials_json": os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"),
    }

    if not config["google_sheet_id"]:
        logger.error("SOCIAL_SHEET_ID environment variable is required")
        sys.exit(1)

    if not config["credentials_file"] and not config["credentials_json"]:
        logger.error("Either GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON is required")
        sys.exit(1)

    return config


def populate_new_videos(client: InstagramClient, sheets: SheetsClient):
    """Populate ALL data for new videos only (rows without Video ID)."""
    logger.info("Mode: POPULATE NEW VIDEOS")
    logger.info("-" * 50)

    rows = sheets.get_all_rows()
    logger.info(f"Found {len(rows)} URLs in sheet")

    if not rows:
        logger.info("No URLs to process. Add Instagram reel/video URLs to column A.")
        return

    # Filter to only new rows (no Video ID yet)
    new_rows = [r for r in rows if not r["has_data"]]
    logger.info(f"Found {len(new_rows)} new URLs to populate (skipping {len(rows) - len(new_rows)} existing)")

    if not new_rows:
        logger.info("All videos already have data. Nothing to populate.")
        return

    # Build URL to row mapping
    url_to_row = {}
    for row in new_rows:
        post_id = client.extract_post_id(row["url"])
        if post_id:
            url_to_row[row["url"]] = (row["row_num"], post_id)
        else:
            logger.warning(f"Row {row['row_num']}: Could not extract post ID from URL")

    if not url_to_row:
        logger.warning("No valid Instagram URLs found")
        return

    # Fetch video details
    urls = list(url_to_row.keys())
    logger.info(f"Fetching data for {len(urls)} videos...")
    video_data = client.get_video_details(urls)

    # Update sheet rows
    updates = []
    for url, (row_num, post_id) in url_to_row.items():
        if post_id in video_data:
            updates.append((row_num, url, video_data[post_id]))

    if updates:
        sheets.batch_update_rows(updates)

    logger.info(f"Populated {len(updates)} new videos")


def refresh_stats(client: InstagramClient, sheets: SheetsClient):
    """Refresh only Views, Likes, Comments for existing videos."""
    logger.info("Mode: REFRESH STATS")
    logger.info("-" * 50)

    rows = sheets.get_all_rows()
    logger.info(f"Found {len(rows)} URLs in sheet")

    # Filter to only existing rows (have Video ID)
    existing_rows = [r for r in rows if r["has_data"]]
    logger.info(f"Found {len(existing_rows)} existing videos to refresh")

    if not existing_rows:
        logger.info("No existing videos to refresh.")
        return

    # Build URL to row mapping
    url_to_row = {}
    for row in existing_rows:
        post_id = client.extract_post_id(row["url"])
        if post_id:
            url_to_row[row["url"]] = (row["row_num"], post_id)

    if not url_to_row:
        return

    # Fetch video stats
    urls = list(url_to_row.keys())
    logger.info(f"Fetching stats for {len(urls)} videos...")
    video_data = client.get_video_stats(urls)

    # Update only stats columns
    updates = []
    for url, (row_num, post_id) in url_to_row.items():
        if post_id in video_data:
            updates.append((row_num, video_data[post_id]))

    if updates:
        sheets.batch_update_stats(updates)

    logger.info(f"Refreshed stats for {len(updates)} videos")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Instagram Video Tracker")
    parser.add_argument("--refresh-stats", action="store_true",
                        help="Only refresh Views, Likes, Comments for existing videos")
    parser.add_argument("--browser", type=str, default=None,
                        help="Browser to get cookies from (firefox recommended)")
    parser.add_argument("--cookies", type=str, default=None,
                        help="Path to cookies.txt file (Netscape format)")
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("Instagram Video Tracker")
    logger.info("=" * 50)

    config = load_config()

    client = InstagramClient(cookies_from_browser=args.browser, cookies_file=args.cookies)

    sheets = SheetsClient(
        sheet_id=config["google_sheet_id"],
        worksheet_name=WORKSHEET_NAME,
        credentials_file=config["credentials_file"],
        credentials_json=config["credentials_json"],
        headers=HEADERS_INSTAGRAM
    )

    sheets.ensure_headers()

    if args.refresh_stats:
        refresh_stats(client, sheets)
    else:
        populate_new_videos(client, sheets)

    # Summary
    logger.info("")
    logger.info("=" * 50)
    logger.info("COMPLETE")
    logger.info(f"  Requests: {client.request_count}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
