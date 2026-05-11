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
import json
import mimetypes
import os
import sys
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
LIBRARY_FILE = DATA_DIR / "library.json"
SITE_CONFIG_FILE = DATA_DIR / "site-config.json"

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
        if self.path in SAFE_GET_PATHS:
            return self._send_file(SAFE_GET_PATHS[self.path])
        for prefix, base in SAFE_GET_PREFIXES:
            if self.path.startswith(prefix):
                relative = self.path[len(prefix):]
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
        if self.path != "/api/save":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
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
