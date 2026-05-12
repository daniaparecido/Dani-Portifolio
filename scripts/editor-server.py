#!/usr/bin/env python3
"""
Local HTTP server backing editor.html.

Serves the editor page and the static data files (library.json, site-config.json,
thumbnails), and accepts POST /api/save to overwrite data/site-config.json.

Bound to 127.0.0.1 and refuses connections from any other address. The save
endpoint is the only write surface; it validates the incoming JSON against the
schema's hard requirements (version, featured, sections) and rejects any
referenced video id that isn't in data/library.json.

Usage:
    python scripts/editor-server.py             # serve on http://127.0.0.1:8765
    python scripts/editor-server.py --port 9000
"""

import argparse
import datetime as _dt
import json
import mimetypes
import os
import subprocess
import sys
import urllib.parse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
LIBRARY_FILE = DATA_DIR / "library.json"
SITE_CONFIG_FILE = DATA_DIR / "site-config.json"
SYNC_SCRIPT = ROOT_DIR / "scripts" / "sync_from_sheet.py"
FETCH_THUMBS_SCRIPT = ROOT_DIR / "scripts" / "fetch_thumbnails.py"
PROCESS_PREVIEWS_SCRIPT = ROOT_DIR / "scripts" / "process_previews.py"
TRACKER_WORKFLOW = "update-tracker-stats.yml"

# Explicit allowlist of paths we will serve. Keeps the surface tiny.
SAFE_GET_PATHS = {
    "/": ROOT_DIR / "editor.html",
    "/editor.html": ROOT_DIR / "editor.html",
    "/data/library.json": LIBRARY_FILE,
    "/data/site-config.json": SITE_CONFIG_FILE,
    "/data/site-config.schema.json": DATA_DIR / "site-config.schema.json",
}

# Directories under which we serve any file. Keep these narrow.
SAFE_GET_PREFIXES = [
    ("/images/thumbnails/", ROOT_DIR / "images" / "thumbnails"),
    ("/videos/previews/", ROOT_DIR / "videos" / "previews"),
]


class EditorHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Quieter than the default; keep only errors.
        if args and isinstance(args[1], str) and args[1].startswith(("4", "5")):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path):
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, f"{path.name} not found")
            return
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        # Disable caching so a fresh sync is picked up on reload.
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/api/update-stats/status":
            return self._handle_stats_status()
        if parsed.path in SAFE_GET_PATHS:
            return self._send_file(SAFE_GET_PATHS[parsed.path])
        for prefix, base in SAFE_GET_PREFIXES:
            if parsed.path.startswith(prefix):
                relative = parsed.path[len(prefix):]
                candidate = (base / relative).resolve()
                # Refuse path traversal that escapes the base.
                try:
                    candidate.relative_to(base.resolve())
                except ValueError:
                    self.send_error(HTTPStatus.FORBIDDEN)
                    return
                return self._send_file(candidate)
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        if self.path == "/api/save":
            return self._handle_save()
        if self.path == "/api/update-stats":
            return self._handle_update_stats()
        if self.path == "/api/sync-local":
            return self._handle_sync_local()
        if self.path in ("/api/refresh-assets", "/api/fetch-thumbnails"):
            # /api/fetch-thumbnails kept as a backwards-compatible alias.
            return self._handle_refresh_assets()
        self.send_error(HTTPStatus.NOT_FOUND)

    def _handle_save(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0 or length > 1_000_000:
            return self._send_json(HTTPStatus.BAD_REQUEST, {"error": "missing or oversized body"})
        try:
            raw = self.rfile.read(length)
            config = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            return self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"invalid JSON: {e}"})

        err = validate_site_config(config)
        if err:
            return self._send_json(HTTPStatus.BAD_REQUEST, {"error": err})

        try:
            write_site_config(config)
        except Exception as e:
            return self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(e)})

        return self._send_json(HTTPStatus.OK, {
            "saved": True,
            "featured": len(config.get("featured", [])),
            "sections": len(config.get("sections", [])),
            "total_video_ids": sum(len(s.get("video_ids", [])) for s in config.get("sections", [])),
        })

    def _handle_update_stats(self):
        """Trigger the upstream update-tracker-stats.yml workflow via gh CLI.

        Optional JSON body {"mode": "populate"|"refresh"} (default "refresh"):
        - populate: fill in brand-new rows that have only a URL.
        - refresh:  update view/like/comment counts on rows older than the
          workflow's staleness window (so it touches ~a handful of rows, not all).
        """
        mode = "refresh"
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length > 0:
            if length > 10_000:
                return self._send_json(HTTPStatus.BAD_REQUEST, {"error": "oversized body"})
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                return self._send_json(HTTPStatus.BAD_REQUEST, {"error": f"invalid JSON: {e}"})
            if isinstance(body, dict) and body.get("mode"):
                mode = str(body["mode"])
        if mode not in ("populate", "refresh"):
            return self._send_json(HTTPStatus.BAD_REQUEST, {
                "error": f"mode must be 'populate' or 'refresh', got {mode!r}",
            })

        triggered_at = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        proc = _run_gh(["workflow", "run", TRACKER_WORKFLOW, "-f", f"mode={mode}"], timeout=30)
        if proc.returncode != 0:
            return self._send_json(HTTPStatus.BAD_GATEWAY, {
                "error": "gh workflow run failed",
                "stderr": proc.stderr.strip(),
            })
        return self._send_json(HTTPStatus.OK, {
            "triggered": True,
            "triggered_at": triggered_at,
            "workflow": TRACKER_WORKFLOW,
            "mode": mode,
        })

    def _handle_stats_status(self):
        """Return the most recent run for the tracker workflow."""
        proc = _run_gh([
            "run", "list",
            "--workflow", TRACKER_WORKFLOW,
            "--limit", "1",
            "--json", "databaseId,status,conclusion,createdAt,url,event",
        ], timeout=20)
        if proc.returncode != 0:
            return self._send_json(HTTPStatus.BAD_GATEWAY, {
                "error": "gh run list failed",
                "stderr": proc.stderr.strip(),
            })
        try:
            runs = json.loads(proc.stdout or "[]")
        except json.JSONDecodeError:
            runs = []
        return self._send_json(HTTPStatus.OK, {"runs": runs})

    def _handle_sync_local(self):
        """Run sync_from_sheet.py to mirror latest sheet state into library.json."""
        proc = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT)],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=180,
        )
        if proc.returncode != 0:
            return self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "error": "sync_from_sheet.py failed",
                "stderr": proc.stderr.strip()[-2000:],
                "stdout": proc.stdout.strip()[-2000:],
            })
        # Count items so the client can confirm freshness without re-fetching the file.
        item_count = 0
        try:
            payload = json.loads(LIBRARY_FILE.read_text(encoding="utf-8"))
            item_count = len(payload.get("items", []))
        except Exception:
            pass
        return self._send_json(HTTPStatus.OK, {
            "synced": True,
            "items": item_count,
            "stdout": proc.stdout.strip()[-2000:],
        })

    def _handle_refresh_assets(self):
        """Download only the *missing* local assets, then re-mirror library.json.

        Two passes, both missing-only (re-downloading what is already on disk risks
        a rate-limit, so neither pass touches existing files):
          1. fetch_thumbnails.py -- re-resolves IG/TikTok posts whose local
             images/thumbnails/{id}.jpg is missing (their signed CDN URLs in the
             source sheets expire after a few weeks, so cards go black). Uses yt-dlp
             with the local cookies jars when present; Instagram needs a logged-in
             jar, and missing/expired cookies surface in the stderr below.
          2. process_previews.py -- generates videos/previews/{id}.mp4 for every
             YouTube video referenced in js/projects.js that has no preview (or
             source) clip yet, via the no-SNI HLS bypass (immune to 429) with a
             yt-dlp fallback.
        Then sync_from_sheet.py re-mirrors so library.json / projects.js point at the
        now-local files. Exposed as POST /api/refresh-assets (and the legacy alias
        POST /api/fetch-thumbnails).
        """
        thumbs = subprocess.run(
            [sys.executable, str(FETCH_THUMBS_SCRIPT), "--delay", "1.2"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=1800,
        )
        if thumbs.returncode != 0:
            return self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "error": "fetch_thumbnails.py failed",
                "stderr": thumbs.stderr.strip()[-2000:],
                "stdout": thumbs.stdout.strip()[-3000:],
            })

        # process_previews.py exits 1 when *some* clip failed (the rest still
        # succeeded), so a non-zero return code here is not fatal -- surface its
        # output and keep going. Only a crash (no usable output) is a hard error.
        previews = subprocess.run(
            [sys.executable, str(PROCESS_PREVIEWS_SCRIPT)],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=2400,
        )
        previews_failed = previews.returncode != 0

        mirror = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT)],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=180,
        )
        combined_stdout = (
            "[thumbnails]\n" + thumbs.stdout.strip()[-2500:]
            + "\n\n[previews]\n" + previews.stdout.strip()[-2500:]
            + "\n\n[mirror]\n" + mirror.stdout.strip()[-800:]
        )
        if mirror.returncode != 0:
            return self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {
                "error": "sync_from_sheet.py failed after refreshing assets",
                "stderr": mirror.stderr.strip()[-2000:],
                "stdout": combined_stdout,
            })
        item_count = 0
        try:
            payload = json.loads(LIBRARY_FILE.read_text(encoding="utf-8"))
            item_count = len(payload.get("items", []))
        except Exception:
            pass
        return self._send_json(HTTPStatus.OK, {
            "done": True,
            "items": item_count,
            "previews_partial_failure": previews_failed,
            "stdout": combined_stdout,
        })


def _run_gh(args, timeout=30):
    """Run gh CLI with given args. Returns CompletedProcess. Never raises."""
    try:
        return subprocess.run(
            ["gh", *args],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(args=args, returncode=127, stdout="", stderr="gh CLI not found on PATH")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args=args, returncode=124, stdout="", stderr=f"gh timed out after {timeout}s")


def validate_site_config(config):
    """Return None if the config is well-formed enough to save, else an error string.

    Light validation; the JSON Schema in data/site-config.schema.json is the
    full source of truth (used for IDE IntelliSense). The editor itself
    should never produce malformed payloads, but the server is the security
    boundary so it must still check.
    """
    if not isinstance(config, dict):
        return "config must be an object"
    if config.get("version") != 1:
        return "version must be 1"
    featured = config.get("featured")
    sections = config.get("sections")
    if not isinstance(featured, list) or not isinstance(sections, list):
        return "featured and sections must be arrays"

    # Build the set of known video ids so we can reject typos / stale refs.
    if not LIBRARY_FILE.exists():
        return "data/library.json missing; run scripts/sync_from_sheet.py first"
    library = json.loads(LIBRARY_FILE.read_text(encoding="utf-8"))
    known_ids = {item["id"] for item in library.get("items", [])}

    for i, group in enumerate(featured):
        if not isinstance(group, dict):
            return f"featured[{i}] must be an object"
        long_id = group.get("long_form_id")
        shorts = group.get("short_form_ids", [])
        if not isinstance(long_id, str) or not long_id:
            return f"featured[{i}].long_form_id must be a non-empty string"
        if long_id not in known_ids:
            return f"featured[{i}].long_form_id {long_id!r} not in library"
        if not isinstance(shorts, list):
            return f"featured[{i}].short_form_ids must be an array"
        for j, sid in enumerate(shorts):
            if not isinstance(sid, str) or sid not in known_ids:
                return f"featured[{i}].short_form_ids[{j}] {sid!r} not in library"

    seen_section_ids = set()
    for i, section in enumerate(sections):
        if not isinstance(section, dict):
            return f"sections[{i}] must be an object"
        sid = section.get("id")
        title = section.get("title")
        vids = section.get("video_ids", [])
        if not isinstance(sid, str) or not sid:
            return f"sections[{i}].id must be a non-empty string"
        if sid in seen_section_ids:
            return f"sections[{i}].id {sid!r} duplicated"
        seen_section_ids.add(sid)
        if not isinstance(title, str):
            return f"sections[{i}].title must be a string"
        if not isinstance(vids, list):
            return f"sections[{i}].video_ids must be an array"
        for j, vid in enumerate(vids):
            if not isinstance(vid, str) or vid not in known_ids:
                return f"sections[{i}].video_ids[{j}] {vid!r} not in library"
    return None


def write_site_config(config):
    """Atomic write: temp file in the same dir, then rename."""
    config.setdefault("$schema", "./site-config.schema.json")
    config["version"] = 1
    tmp = SITE_CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, SITE_CONFIG_FILE)


def main():
    parser = argparse.ArgumentParser(description="Local editor server for Dani Portfolio")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open the browser")
    args = parser.parse_args()

    if not LIBRARY_FILE.exists():
        print(f"WARNING: {LIBRARY_FILE} missing. Run scripts/sync_from_sheet.py first.")

    server = HTTPServer(("127.0.0.1", args.port), EditorHandler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"Editor server running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
