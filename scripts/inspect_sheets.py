#!/usr/bin/env python3
"""
Diagnostic: dump structure of the three sheets the redesigned pipeline will touch.

Reads service-account creds from .env (GOOGLE_SERVICE_ACCOUNT_FILE or
GOOGLE_SERVICE_ACCOUNT_JSON), then for each sheet lists every worksheet tab,
its headers, row count, and a couple of sample rows.

Run from repo root:
    python scripts/inspect_sheets.py
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
import gspread


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

SHEETS = [
    ("CURRENT_PORTFOLIO", "1iT9v85SzRG4TZmyrbsdgNaU7AeN-7tY0vQOxp6zV0B4"),
    ("IG_TIKTOK_LIBRARY", "1jVd2XMhOI1MVqV9YtaBMVtXWU7IzkdZNuLYdkI5ZKdQ"),
    ("YOUTUBE_LIBRARY",   "157LkGyuY_jMWwTWKu2w4Sh9lw0qHCURXKUufFfgOgqg"),
]


def authorize():
    load_dotenv(Path(__file__).parent.parent / ".env")
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    creds_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    if creds_json:
        credentials = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    elif creds_file:
        credentials = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    else:
        sys.exit("Set GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON in .env")
    return gspread.authorize(credentials)


def inspect(client, label, sheet_id):
    print(f"\n{'=' * 70}")
    print(f"{label}  ({sheet_id})")
    print("=" * 70)
    try:
        ss = client.open_by_key(sheet_id)
    except Exception as e:
        print(f"  ERROR opening: {e}")
        return
    print(f"  Title: {ss.title}")
    for ws in ss.worksheets():
        print(f"\n  Tab: {ws.title!r}  rows={ws.row_count}  cols={ws.col_count}")
        try:
            rows = ws.get_all_values()
        except Exception as e:
            print(f"    ERROR reading: {e}")
            continue
        non_empty = [r for r in rows if any(c.strip() for c in r)]
        print(f"    non-empty rows: {len(non_empty)}")
        if not non_empty:
            continue
        headers = non_empty[0]
        print(f"    headers ({len(headers)}): {headers}")
        for i, row in enumerate(non_empty[1:4], start=2):
            trimmed = [c[:80] for c in row]
            print(f"    sample row {i}: {trimmed}")


def main():
    client = authorize()
    for label, sheet_id in SHEETS:
        inspect(client, label, sheet_id)


if __name__ == "__main__":
    main()
