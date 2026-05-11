<#
.SYNOPSIS
Refresh the Instagram cookies used by the daily stats workflow.

.DESCRIPTION
Extracts cookies from a local browser via yt-dlp, filters them down to
instagram.com only (to minimize the blast radius of the GitHub secret),
writes them to cookies.txt in the repo root, and uploads them as the
INSTAGRAM_COOKIES GitHub Actions secret so the next scheduled run of
update-videos.yml can refresh Instagram view counts.

Prerequisites:
- yt-dlp installed (already in requirements.txt; run pip install -r requirements.txt once)
- gh CLI authenticated for daniaparecido/Dani-Portifolio
- The chosen browser must be CLOSED (otherwise its cookie DB is locked on Windows)
- You must be logged into Instagram in that browser

.PARAMETER Browser
Browser to pull cookies from. Defaults to chrome.

.PARAMETER NoUpload
Only write the local cookies.txt; skip pushing the GitHub secret.

.EXAMPLE
.\refresh-cookies.ps1
.\refresh-cookies.ps1 -Browser edge
.\refresh-cookies.ps1 -Browser firefox -NoUpload
#>
param(
    [ValidateSet("chrome","edge","firefox","brave","opera","vivaldi","chromium")]
    [string]$Browser = "chrome",
    [switch]$NoUpload
)

# NOTE: Do NOT use $ErrorActionPreference = "Stop" globally. In PS 5.1, native commands
# that write to stderr (yt-dlp always does on a failed extraction) get wrapped as
# NativeCommandError under Stop mode, even when they exit cleanly. We check $LASTEXITCODE
# and Test-Path manually instead.
$ErrorActionPreference = "Continue"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$CookiesPath = Join-Path $RepoRoot "cookies.txt"
$TempPath = Join-Path $env:TEMP "cookies-raw.txt"
$RepoSlug = "daniaparecido/Dani-Portifolio"
$SecretName = "INSTAGRAM_COOKIES"

if (Test-Path $TempPath) { Remove-Item $TempPath -Force }

Write-Host "Extracting cookies from $Browser..." -ForegroundColor Cyan

# yt-dlp writes the --cookies file regardless of whether the URL extracts successfully.
# We don't care about extraction; we just want the cookie jar dumped to Netscape format.
# --ignore-errors lets it continue past extraction failures; 2>$null silences stderr without
# triggering the PS 5.1 native-stderr-wrap behavior (no 2>&1).
& python -m yt_dlp `
    --cookies-from-browser $Browser `
    --cookies $TempPath `
    --skip-download `
    --ignore-errors `
    --no-warnings `
    "https://www.instagram.com/instagram/" 2>$null | Out-Null

if (-not (Test-Path $TempPath)) {
    Write-Host "ERROR: yt-dlp did not produce $TempPath." -ForegroundColor Red
    Write-Host "  - Is $Browser closed? (Chrome/Edge lock their cookie DB while running.)" -ForegroundColor Yellow
    Write-Host "  - Is yt-dlp installed? Run: pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Filter to instagram.com cookies only (don't ship your whole browser cookie jar to GitHub)
$lines = Get-Content $TempPath
$header = $lines | Where-Object { $_.StartsWith("#") -or $_.Trim() -eq "" }
$instagramOnly = $lines | Where-Object { $_ -match "^\.?instagram\.com\t" }

if (-not $instagramOnly) {
    Write-Host "ERROR: No instagram.com cookies found in the export." -ForegroundColor Red
    Write-Host "  Open $Browser, log into https://www.instagram.com, close the browser, then retry." -ForegroundColor Yellow
    exit 1
}

# Critical: a logged-OUT browser produces cookies WITHOUT sessionid. Without sessionid,
# Instagram rejects all requests. Catch this before pushing a useless secret.
$hasSessionid = $instagramOnly | Where-Object { $_ -match "^\.?instagram\.com\t[^\t]+\t[^\t]+\t[^\t]+\t[^\t]+\tsessionid\t" }
if (-not $hasSessionid) {
    Write-Host "ERROR: Instagram cookies are missing sessionid (you weren't logged in)." -ForegroundColor Red
    Write-Host "  Open $Browser, go to https://www.instagram.com, log in, confirm you see your feed," -ForegroundColor Yellow
    Write-Host "  close $Browser fully, then retry." -ForegroundColor Yellow
    exit 1
}

# Set-Content + array writes one line per element with native newlines; that's correct for Netscape format
Set-Content -Path $CookiesPath -Value (@($header) + @($instagramOnly)) -Encoding ASCII

Remove-Item $TempPath -ErrorAction SilentlyContinue

$size = (Get-Item $CookiesPath).Length
$count = @($instagramOnly).Count
Write-Host "Wrote $count instagram.com cookies ($size bytes) to $CookiesPath" -ForegroundColor Green

if ($NoUpload) {
    Write-Host "NoUpload set; skipping GitHub secret push." -ForegroundColor Yellow
    return
}

Write-Host "Uploading to GitHub secret $SecretName ($RepoSlug)..." -ForegroundColor Cyan
# PS 5.1's default $OutputEncoding (UTF-8 with BOM) prepends a BOM when piping strings to native
# commands. yt-dlp rejects a BOM in Netscape cookie files ("does not look like a Netscape format
# cookies file"). Force UTF-8 without BOM for this pipe; ASCII content is safe under UTF-8.
$prevOutputEncoding = $OutputEncoding
$OutputEncoding = New-Object System.Text.UTF8Encoding $false
try {
    Get-Content $CookiesPath -Raw | & gh secret set $SecretName --repo $RepoSlug
    if ($LASTEXITCODE -ne 0) {
        throw "gh secret set failed with exit code $LASTEXITCODE"
    }
}
finally {
    $OutputEncoding = $prevOutputEncoding
}
Write-Host "Done. Next scheduled run of update-videos.yml will use the fresh cookies." -ForegroundColor Green
