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

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$CookiesPath = Join-Path $RepoRoot "cookies.txt"
$TempPath = Join-Path $env:TEMP "cookies-raw.txt"
$RepoSlug = "daniaparecido/Dani-Portifolio"
$SecretName = "INSTAGRAM_COOKIES"

Write-Host "Extracting cookies from $Browser..." -ForegroundColor Cyan

# yt-dlp loads cookies from the browser, then writes them to --cookies after the run.
# We point it at instagram.com so the relevant cookies are touched and saved.
& python -m yt_dlp `
    --cookies-from-browser $Browser `
    --cookies $TempPath `
    --skip-download `
    --no-warnings `
    --quiet `
    "https://www.instagram.com/instagram/" 2>&1 | Out-Null

if (-not (Test-Path $TempPath)) {
    throw "yt-dlp did not produce $TempPath. Make sure $Browser is closed and you're logged into Instagram."
}

# Filter to instagram.com cookies only (don't ship your whole browser cookie jar to GitHub)
$lines = Get-Content $TempPath
$header = $lines | Where-Object { $_.StartsWith("#") -or $_.Trim() -eq "" }
$instagramOnly = $lines | Where-Object { $_ -match "^\.?instagram\.com\t" }

if (-not $instagramOnly) {
    throw "No instagram.com cookies found. Open $Browser, log into https://www.instagram.com, close the browser, then retry."
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
Get-Content $CookiesPath -Raw | & gh secret set $SecretName --repo $RepoSlug
if ($LASTEXITCODE -ne 0) {
    throw "gh secret set failed with exit code $LASTEXITCODE"
}
Write-Host "Done. Next scheduled run of update-videos.yml will use the fresh cookies." -ForegroundColor Green
