"""
YouTube HLS manifest extractor (no-SNI bypass).

Vendored from BRolling's scripts/get_hls_manifest.py. Strategy cascade:
1. No-SNI curl (PRIMARY) -- connects to YouTube's resolved IP without SNI in TLS.
   YouTube's bot-check / rate-limit middleware routes on the TLS SNI, so a
   ClientHello that omits `www.youtube.com` lands on a path that never applies
   it. Uses the IOS InnerTube client, which needs no PO token and no cookies.
   No browser. ~1-2s. Immune to 429.
2. nodriver browser (FALLBACK) -- full iPad CriOS/93 emulation via undetected
   Chrome. Only used if curl / no-SNI fails. Optional dependency; degrades
   gracefully if `nodriver` is not installed.

Based on TubeDigger's Wireshark-analyzed technique: its Delphi HTTP client
omits SNI, bypassing YouTube's bot-check middleware tied to SNI-based routing.

Usage:
    python yt_hls_manifest.py <video_id> [max_duration_seconds]

Output (JSON to stdout, logs to stderr):
    {"status": "OK"|"ERROR"|"LOGIN_REQUIRED"|"UNPLAYABLE"|"EXCEEDS_DURATION"|"NO_HLS"|"UNKNOWN",
     "hlsManifestUrl": "..." | null, "title": "...", "duration": 123,
     "description": "...", "reason": ""}
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IOS_INNERTUBE_UA = (
    "com.google.ios.youtube/20.10.4 "
    "(iPhone16,2; U; CPU iOS 18_3_2 like Mac OS X;)"
)
IOS_CLIENT_VERSION = "20.10.4"


def build_innertube_body(video_id: str) -> dict:
    """Build the IOS InnerTube /player request body."""
    return {
        "context": {
            "client": {
                "clientName": "IOS",
                "clientVersion": IOS_CLIENT_VERSION,
                "deviceMake": "Apple",
                "deviceModel": "iPhone16,2",
                "userAgent": IOS_INNERTUBE_UA,
                "osName": "iPhone",
                "osVersion": "18.3.2.22D82",
                "hl": "en",
                "timeZone": "UTC",
                "utcOffsetMinutes": 0,
            }
        },
        "videoId": video_id,
        "contentCheckOk": True,
        "racyCheckOk": True,
        "playbackContext": {
            "contentPlaybackContext": {
                "html5Preference": "HTML5_PREF_WANTS",
            }
        },
    }


# ---------------------------------------------------------------------------
# Strategy 1: No-SNI curl (PRIMARY)
# Connects to YouTube's resolved IP without SNI -- bypasses bot-check.
# ---------------------------------------------------------------------------

def innertube_no_sni_curl(video_id: str) -> "dict | None":
    """Make InnerTube /player request via curl to resolved IP (no SNI).

    Connecting to the IP address directly (not the hostname) means curl does
    not put `www.youtube.com` in the TLS ClientHello SNI extension. YouTube's
    bot-check enforcement is tied to SNI-based routing, so connections without
    SNI bypass it entirely. `-k` skips cert validation (the cert won't match
    the bare IP). Returns parsed JSON response or None on failure.
    """
    try:
        ip = socket.gethostbyname("www.youtube.com")
    except Exception as exc:
        log(f"DNS resolution failed: {exc}")
        return None

    body = json.dumps(build_innertube_body(video_id))

    try:
        result = subprocess.run(
            [
                "curl", "-s", "-k",
                "--tlsv1.2", "--tls-max", "1.2",
                "-X", "POST",
                f"https://{ip}/youtubei/v1/player?prettyPrint=false",
                "-H", "Host: www.youtube.com",
                "-H", "Content-Type: application/json",
                "-H", f"User-Agent: {IOS_INNERTUBE_UA}",
                "-H", "X-Youtube-Client-Name: 5",
                "-H", f"X-Youtube-Client-Version: {IOS_CLIENT_VERSION}",
                "-H", "Origin: https://www.youtube.com",
                "-d", body,
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )

        if result.returncode != 0:
            log(f"curl failed (code {result.returncode}): {result.stderr[:200]}")
            return None

        return json.loads(result.stdout)
    except FileNotFoundError:
        log("curl not found on PATH")
        return None
    except subprocess.TimeoutExpired:
        log("curl timed out (20s)")
        return None
    except json.JSONDecodeError as exc:
        log(f"curl response not valid JSON: {exc}")
        return None
    except Exception as exc:
        log(f"curl error: {exc}")
        return None


# ---------------------------------------------------------------------------
# Strategy 2: nodriver browser (FALLBACK)
# Only used if curl / no-SNI isn't available.
# ---------------------------------------------------------------------------

IPAD_UA = (
    "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "CriOS/93.0.4577.82 Mobile/15E148 Safari/604.1"
)

PROFILE_DIR = str(Path.home() / ".dani-portfolio-nodriver-profile")

USER_AGENT_DATA_SPOOF = """
Object.defineProperty(navigator, 'userAgentData', {
    value: {
        brands: [
            { brand: "Chromium", version: "93" },
            { brand: " Not;A Brand", version: "99" }
        ],
        mobile: true,
        platform: "iOS",
        getHighEntropyValues: function(hints) {
            return Promise.resolve({
                brands: [
                    { brand: "Chromium", version: "93" },
                    { brand: " Not;A Brand", version: "99" }
                ],
                mobile: true,
                platform: "iOS",
                platformVersion: "15.0",
                architecture: "arm",
                model: "iPad",
                uaFullVersion: "93.0.4577.82",
                fullVersionList: [
                    { brand: "Chromium", version: "93.0.4577.82" },
                    { brand: " Not;A Brand", version: "99.0.0.0" }
                ]
            });
        }
    },
    configurable: true
});
"""


async def nodriver_fallback(video_id: str) -> "dict | None":
    """Get the InnerTube /player response via nodriver browser -- fallback when
    curl / no-SNI isn't available."""
    try:
        import nodriver as uc
    except ImportError:
        log("nodriver not installed, skipping browser fallback")
        return None

    browser = None
    try:
        os.makedirs(PROFILE_DIR, exist_ok=True)
        browser = await uc.start(
            browser_args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars", "--disable-extensions",
                "--no-first-run", "--no-default-browser-check",
                "--mute-audio",
                f"--user-data-dir={PROFILE_DIR}",
            ],
            headless=True,
        )

        page = browser.main_tab

        await page.send(uc.cdp.emulation.set_device_metrics_override(
            width=1024, height=768, device_scale_factor=2.0, mobile=True,
        ))
        await page.send(uc.cdp.network.set_user_agent_override(
            user_agent=IPAD_UA, platform="iPad",
        ))
        await page.send(uc.cdp.page.add_script_to_evaluate_on_new_document(
            source=USER_AGENT_DATA_SPOOF,
        ))
        await page.send(uc.cdp.emulation.set_touch_emulation_enabled(
            enabled=True, max_touch_points=5,
        ))

        log("[nodriver] Session warmup...")
        await page.get("https://m.youtube.com/")
        await asyncio.sleep(3)

        log(f"[nodriver] Navigating to video: {video_id}")
        await page.get(f"https://m.youtube.com/watch?v={video_id}")
        await asyncio.sleep(2)

        body = build_innertube_body(video_id)
        body_json = json.dumps(json.dumps(body))

        js = f"""
        (() => {{
            try {{
                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/youtubei/v1/player?prettyPrint=false', false);
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.withCredentials = true;
                xhr.send({body_json});
                if (xhr.status === 200) return xhr.responseText;
                return JSON.stringify({{error: 'HTTP ' + xhr.status}});
            }} catch(e) {{
                return JSON.stringify({{error: e.message}});
            }}
        }})()
        """

        log("[nodriver] browser_ios XHR...")
        raw = await page.evaluate(js)
        if hasattr(raw, "value"):
            raw = raw.value
        if raw and isinstance(raw, str):
            return json.loads(raw)
        return None

    except Exception as exc:
        log(f"[nodriver] error: {exc}")
        return None
    finally:
        if browser:
            try:
                browser.stop()
            except Exception:
                pass
            await asyncio.sleep(2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(video_id: str, max_duration: int = 0) -> None:
    result = {
        "status": "ERROR",
        "hlsManifestUrl": None,
        "title": "",
        "duration": 0,
        "description": "",
        "reason": "",
    }

    log(f"Strategy 1: no-SNI curl for {video_id}")
    data = innertube_no_sni_curl(video_id)

    if not data:
        log("Strategy 2: nodriver browser fallback")
        data = await nodriver_fallback(video_id)

    if data:
        ps = data.get("playabilityStatus", {})
        status = ps.get("status", "UNKNOWN")
        reason = ps.get("reason", "")

        if status in ("LOGIN_REQUIRED", "UNPLAYABLE", "ERROR"):
            result["status"] = status
            result["reason"] = reason
            log(f"InnerTube status: {status} -- {reason}")
        else:
            streaming_data = data.get("streamingData", {})
            video_details = data.get("videoDetails", {})
            hls_url = streaming_data.get("hlsManifestUrl", "")
            title = video_details.get("title", "")
            description = video_details.get("shortDescription", "")
            dur = int(video_details.get("lengthSeconds", "0"))

            n_formats = len(streaming_data.get("formats", []))
            n_adaptive = len(streaming_data.get("adaptiveFormats", []))
            log(f"Got {n_formats} formats, {n_adaptive} adaptive, hls={bool(hls_url)}")

            result["title"] = title
            result["duration"] = dur
            result["description"] = description

            if max_duration > 0 and dur > max_duration:
                result["status"] = "EXCEEDS_DURATION"
                result["reason"] = f"Video duration ({dur}s) exceeds maximum ({max_duration}s)"
            elif hls_url:
                log("HLS manifest available!")
                result["status"] = "OK"
                result["hlsManifestUrl"] = hls_url
            elif n_adaptive > 0:
                log(f"No HLS manifest but {n_adaptive} adaptive formats available")
                result["status"] = "NO_HLS"
                result["reason"] = f"{n_adaptive} adaptive formats (no HLS)"
            else:
                result["status"] = "ERROR"
                result["reason"] = "No streaming data"
    else:
        result["reason"] = "All strategies failed"

    print(json.dumps(result))


def log(msg: str) -> None:
    """Log to stderr (stdout is reserved for JSON output)."""
    print(f"[yt-hls] {msg}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "ERROR",
            "reason": "Usage: python yt_hls_manifest.py <video_id> [max_duration]",
            "hlsManifestUrl": None,
            "title": "",
            "duration": 0,
            "description": "",
        }))
        sys.exit(1)

    vid = sys.argv[1]
    max_dur = 0
    if len(sys.argv) > 2:
        try:
            max_dur = int(sys.argv[2])
        except ValueError:
            pass

    asyncio.run(main(vid, max_dur))
