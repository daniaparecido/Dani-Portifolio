"""
Generate the missing hover-preview clips referenced by js/projects.js.

For each YouTube video that is referenced in js/projects.js but has no
videos/previews/<id>.mp4 on disk yet (and no videos/source/<id>.mp4 either),
this:
  1. Resolves an HLS master playlist via scripts/yt_hls_manifest.py
     (no-SNI curl bypass -- immune to YouTube rate limiting; nodriver fallback).
  2. Picks an H.264 variant <= 1280px on the long edge from the master playlist.
  3. ffmpeg-encodes a 30-second, muted preview clip:
       - vertical sources (Shorts) -> 540x960
       - horizontal sources         -> 854x480
  4. Writes videos/previews/<id>.mp4.

Anything that already has a preview (or a source file) on disk is skipped, so
re-running is cheap and never re-hits YouTube. yt-dlp is only used as a last
resort if the no-SNI path can't produce an HLS manifest.

Usage:
    python scripts/process_previews.py [--dry-run] [--limit N] [--only id,id,...]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PROJECTS_JS = ROOT_DIR / "js" / "projects.js"
PREVIEWS_DIR = ROOT_DIR / "videos" / "previews"
SOURCE_DIR = ROOT_DIR / "videos" / "source"
HLS_HELPER = ROOT_DIR / "scripts" / "yt_hls_manifest.py"
COOKIES_FILE = ROOT_DIR / "cookies.txt"

IPAD_UA = (
    "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "CriOS/93.0.4577.82 Mobile/15E148 Safari/604.1"
)

PREVIEW_SECONDS = 30
DELAY_BETWEEN = 2.0  # seconds between videos, gentle burst protection


# ---------------------------------------------------------------------------
# Parse js/projects.js
# ---------------------------------------------------------------------------

def referenced_youtube_videos() -> list[dict]:
    """Return [{id, platform, url}, ...] for every video referenced in
    js/projects.js (both the flat `projects` array and the `featured` groups),
    de-duplicated, in first-seen order."""
    text = PROJECTS_JS.read_text(encoding="utf-8")
    seen: set[str] = set()
    out: list[dict] = []
    # Each object lists videoId before platform before url; non-greedy across
    # the rest of the object (no nested braces in the generated file).
    pattern = re.compile(
        r'"?videoId"?\s*:\s*"([^"]+)"'
        r'[\s\S]*?"?platform"?\s*:\s*"([^"]+)"'
        r'[\s\S]*?"?url"?\s*:\s*"([^"]*)"'
    )
    for vid, platform, url in pattern.findall(text):
        if vid in seen:
            continue
        seen.add(vid)
        out.append({"id": vid, "platform": platform, "url": url})
    return out


# ---------------------------------------------------------------------------
# HLS resolution + variant pick
# ---------------------------------------------------------------------------

def get_hls_manifest(video_id: str) -> dict:
    """Run scripts/yt_hls_manifest.py and return its parsed JSON result."""
    proc = subprocess.run(
        [sys.executable, str(HLS_HELPER), video_id, str(PREVIEW_SECONDS * 60)],
        capture_output=True, text=True, timeout=120,
    )
    if proc.stderr:
        for line in proc.stderr.splitlines():
            print(f"    {line}", file=sys.stderr)
    out = proc.stdout.strip()
    if not out:
        return {"status": "ERROR", "reason": "helper produced no output"}
    try:
        return json.loads(out.splitlines()[-1])
    except json.JSONDecodeError as exc:
        return {"status": "ERROR", "reason": f"bad helper output: {exc}"}


def _http_get(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": IPAD_UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def pick_variant(master_url: str, max_long_edge: int = 1280) -> tuple[str, bool]:
    """Fetch the HLS master playlist and pick the best H.264 variant whose long
    edge is <= max_long_edge (falling back to the smallest if all are larger).

    Returns (media_playlist_url, is_vertical).
    """
    playlist = _http_get(master_url)
    base = master_url.rsplit("/", 1)[0] + "/"
    variants: list[dict] = []
    lines = playlist.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF"):
            continue
        attrs = line.split(":", 1)[1]
        codecs_m = re.search(r'CODECS="([^"]*)"', attrs)
        res_m = re.search(r'RESOLUTION=(\d+)x(\d+)', attrs)
        bw_m = re.search(r'BANDWIDTH=(\d+)', attrs)
        # The URI is the next non-comment line.
        uri = ""
        for j in range(i + 1, len(lines)):
            if lines[j] and not lines[j].startswith("#"):
                uri = lines[j].strip()
                break
        if not uri or not res_m:
            continue
        w, h = int(res_m.group(1)), int(res_m.group(2))
        variants.append({
            "uri": uri if uri.startswith("http") else base + uri,
            "w": w, "h": h,
            "long_edge": max(w, h),
            "h264": bool(codecs_m and "avc1" in codecs_m.group(1)),
            "bw": int(bw_m.group(1)) if bw_m else 0,
        })
    if not variants:
        raise RuntimeError("no variants in HLS master playlist")

    h264 = [v for v in variants if v["h264"]] or variants
    eligible = [v for v in h264 if v["long_edge"] <= max_long_edge]
    if eligible:
        chosen = max(eligible, key=lambda v: (v["long_edge"], v["bw"]))
    else:
        chosen = min(h264, key=lambda v: v["long_edge"])
    return chosen["uri"], chosen["h"] > chosen["w"]


# ---------------------------------------------------------------------------
# ffmpeg encode
# ---------------------------------------------------------------------------

def scale_filter(is_vertical: bool) -> str:
    if is_vertical:
        w, h = 540, 960
    else:
        w, h = 854, 480
    return (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1"
    )


def encode_preview(input_url: str, out_path: Path, is_vertical: bool,
                   user_agent: str | None = None) -> bool:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp.mp4")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    if user_agent:
        cmd += ["-user_agent", user_agent]
    cmd += [
        "-i", input_url,
        "-t", str(PREVIEW_SECONDS),
        "-vf", scale_filter(is_vertical),
        "-c:v", "libx264", "-preset", "slow", "-crf", "28",
        "-profile:v", "main", "-level", "3.1",
        "-an", "-movflags", "+faststart",
        str(tmp),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0 or not tmp.exists() or tmp.stat().st_size < 10_000:
        if tmp.exists():
            tmp.unlink()
        print(f"    ffmpeg failed: {proc.stderr.strip()[:300]}", file=sys.stderr)
        return False
    tmp.replace(out_path)
    return True


# ---------------------------------------------------------------------------
# yt-dlp last-resort fallback
# ---------------------------------------------------------------------------

def ytdlp_fallback(video_id: str, url: str, out_path: Path) -> bool:
    """Download via yt-dlp to videos/source/ then encode a preview from it.
    Only called when the no-SNI HLS path can't produce a manifest."""
    src = SOURCE_DIR / f"{video_id}.mp4"
    if not src.exists():
        SOURCE_DIR.mkdir(parents=True, exist_ok=True)
        dl_url = url or f"https://www.youtube.com/watch?v={video_id}"
        cmd = [
            "yt-dlp",
            "-f", "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "-o", str(src),
        ]
        if COOKIES_FILE.exists():
            cmd += ["--cookies", str(COOKIES_FILE)]
        cmd.append(dl_url)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0 or not src.exists():
            print(f"    yt-dlp failed: {proc.stderr.strip()[:300]}", file=sys.stderr)
            return False
    # Probe orientation from the downloaded file.
    is_vertical = False
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(src)],
            capture_output=True, text=True, timeout=30,
        )
        w, h = (int(x) for x in probe.stdout.strip().split("x")[:2])
        is_vertical = h > w
    except Exception:
        pass
    return encode_preview(str(src), out_path, is_vertical)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Generate missing hover-preview clips.")
    ap.add_argument("--dry-run", action="store_true", help="list what is missing, do nothing")
    ap.add_argument("--limit", type=int, default=0, help="stop after N successful encodes")
    ap.add_argument("--only", default="", help="comma-separated video IDs to restrict to")
    args = ap.parse_args()

    only = {x.strip() for x in args.only.split(",") if x.strip()}

    videos = referenced_youtube_videos()
    missing = []
    for v in videos:
        if only and v["id"] not in only:
            continue
        preview = PREVIEWS_DIR / f"{v['id']}.mp4"
        source = SOURCE_DIR / f"{v['id']}.mp4"
        if preview.exists() or source.exists():
            continue
        if v["platform"] != "youtube":
            print(f"skip {v['id']} (platform={v['platform']}; use process-videos.ps1 -Url for IG/TikTok)")
            continue
        missing.append(v)

    if not missing:
        print("Nothing missing -- all referenced YouTube videos already have a preview or source clip.")
        return 0

    print(f"{len(missing)} preview clip(s) to generate: {', '.join(v['id'] for v in missing)}")
    if args.dry_run:
        return 0

    done = 0
    failed: list[str] = []
    for idx, v in enumerate(missing):
        vid = v["id"]
        out_path = PREVIEWS_DIR / f"{vid}.mp4"
        print(f"\n[{idx + 1}/{len(missing)}] {vid}")
        if idx > 0:
            time.sleep(DELAY_BETWEEN)

        ok = False
        result = get_hls_manifest(vid)
        status = result.get("status")
        if status == "OK" and result.get("hlsManifestUrl"):
            try:
                media_url, is_vertical = pick_variant(result["hlsManifestUrl"])
                print(f"    HLS variant: {'vertical' if is_vertical else 'horizontal'}; encoding {PREVIEW_SECONDS}s clip...")
                ok = encode_preview(media_url, out_path, is_vertical, user_agent=IPAD_UA)
            except Exception as exc:
                print(f"    HLS path error: {exc}", file=sys.stderr)
        else:
            print(f"    no-SNI HLS unavailable ({status}: {result.get('reason', '')}); trying yt-dlp...")

        if not ok:
            ok = ytdlp_fallback(vid, v.get("url", ""), out_path)

        if ok:
            size_kb = out_path.stat().st_size // 1024
            print(f"    OK -> videos/previews/{vid}.mp4 ({size_kb} KB)")
            done += 1
            if args.limit and done >= args.limit:
                print(f"\nReached --limit {args.limit}, stopping.")
                break
        else:
            print(f"    FAILED to produce a preview for {vid}")
            failed.append(vid)

    print(f"\nDone: {done} created, {len(failed)} failed" + (f" ({', '.join(failed)})" if failed else ""))
    print("Run `python scripts/sync_from_sheet.py --generate` to update js/projects.js with the new paths.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
