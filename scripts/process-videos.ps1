# ============================================
# VIDEO PROCESSING SCRIPT
# ============================================
# Downloads YouTube videos and creates 30-second preview clips
# Also fetches metadata (title, channel, view count) for projects.js
#
# Requirements: yt-dlp and ffmpeg must be in PATH
#
# Usage:
#   .\process-videos.ps1                 - Process all videos from projects.js
#   .\process-videos.ps1 -Download ID    - Download specific video
#   .\process-videos.ps1 -Process ID     - Process specific video
#   .\process-videos.ps1 -All ID         - Download, process, and get metadata
#   .\process-videos.ps1 -Metadata ID    - Just fetch metadata (no download)

param(
    [string]$Download,
    [string]$Process,
    [string]$All,
    [string]$Metadata
)

$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $PSScriptRoot
$SourceDir = Join-Path $Root "videos\source"
$PreviewDir = Join-Path $Root "videos\previews"
$ProjectsFile = Join-Path $Root "js\projects.js"

Write-Host ""
Write-Host "============================================"
Write-Host "VIDEO PROCESSING SCRIPT"
Write-Host "============================================"
Write-Host ""
Write-Host "Root directory: $Root"
Write-Host "Source directory: $SourceDir"
Write-Host "Preview directory: $PreviewDir"
Write-Host "Projects file: $ProjectsFile"
Write-Host ""

# Create directories
if (!(Test-Path $SourceDir)) { New-Item -ItemType Directory -Path $SourceDir -Force | Out-Null }
if (!(Test-Path $PreviewDir)) { New-Item -ItemType Directory -Path $PreviewDir -Force | Out-Null }

# Check for required tools
Write-Host "Checking for yt-dlp..."
if (!(Get-Command yt-dlp -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: yt-dlp is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Install with: pip install yt-dlp"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "yt-dlp found."

Write-Host "Checking for ffmpeg..."
if (!(Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: ffmpeg is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Download from: https://ffmpeg.org/download.html"
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "ffmpeg found."
Write-Host ""

function Format-ViewCount {
    param([long]$Count)

    if ($Count -ge 1000000) {
        return "{0:N1}M views" -f ($Count / 1000000)
    } elseif ($Count -ge 1000) {
        return "{0:N0}K views" -f ($Count / 1000)
    } else {
        return "$Count views"
    }
}

function Get-VideoMetadata {
    param([string]$VideoId)

    Write-Host ""
    Write-Host "Fetching metadata for: $VideoId"
    Write-Host "----------------------------------------"

    $url = "https://www.youtube.com/watch?v=$VideoId"
    $cookiesFile = Join-Path $Root "cookies.txt"

    # Fetch metadata using yt-dlp
    $metadata = & yt-dlp --cookies $cookiesFile --print "%(title)s|%(channel)s|%(view_count)s" $url 2>$null

    if ($LASTEXITCODE -ne 0 -or -not $metadata) {
        Write-Host "WARNING: Could not fetch metadata for $VideoId" -ForegroundColor Yellow
        return $null
    }

    $parts = $metadata -split '\|'
    if ($parts.Count -ge 3) {
        $viewCount = 0
        [long]::TryParse($parts[2], [ref]$viewCount) | Out-Null

        return @{
            Title = $parts[0]
            Channel = $parts[1]
            ViewCount = $viewCount
            ViewCountFormatted = Format-ViewCount -Count $viewCount
        }
    }

    return $null
}

function Download-Video {
    param([string]$VideoId)

    Write-Host ""
    Write-Host "Downloading video: $VideoId"
    Write-Host "----------------------------------------"

    $OutputFile = Join-Path $SourceDir "$VideoId.mp4"

    if (Test-Path $OutputFile) {
        Write-Host "Source file already exists, skipping download."
        return
    }

    $url = "https://www.youtube.com/watch?v=$VideoId"
    $output = Join-Path $SourceDir "$VideoId.%(ext)s"

    # Use cookies file to avoid 403 errors
    $cookiesFile = Join-Path $Root "cookies.txt"
    & yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" -o $output --merge-output-format mp4 --cookies $cookiesFile $url

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to download video $VideoId" -ForegroundColor Red
    } else {
        Write-Host "Download complete: $VideoId" -ForegroundColor Green
    }
}

function Process-Video {
    param([string]$VideoId)

    Write-Host ""
    Write-Host "Processing video: $VideoId"
    Write-Host "----------------------------------------"

    $InputFile = Join-Path $SourceDir "$VideoId.mp4"
    $OutputFile = Join-Path $PreviewDir "$VideoId.mp4"

    if (!(Test-Path $InputFile)) {
        Write-Host "ERROR: Source file not found: $InputFile" -ForegroundColor Red
        Write-Host "Run '.\process-videos.ps1 -Download $VideoId' first."
        return
    }

    if (Test-Path $OutputFile) {
        Write-Host "Preview already exists, skipping processing."
        return
    }

    Write-Host "Creating 30-second preview at 480p..."

    & ffmpeg -i $InputFile -ss 0 -t 30 -vf "scale=854:480:force_original_aspect_ratio=decrease,pad=854:480:(ow-iw)/2:(oh-ih)/2" -c:v libx264 -preset slow -crf 28 -profile:v main -level 3.1 -movflags +faststart -an -y $OutputFile

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to process video $VideoId" -ForegroundColor Red
    } else {
        Write-Host "Preview created: $OutputFile" -ForegroundColor Green
    }
}

function Process-All {
    Write-Host "============================================"
    Write-Host "Processing all videos from projects.js"
    Write-Host "============================================"
    Write-Host ""

    # Read file line by line and only match non-commented lines
    $lines = Get-Content $ProjectsFile
    $videoIds = @()

    foreach ($line in $lines) {
        # Skip commented lines
        if ($line -match '^\s*//' -or $line -match '^\s*\*') {
            continue
        }
        # Match youtubeId on non-commented lines
        if ($line -match 'youtubeId:\s*"([^"]+)"') {
            $videoIds += $matches[1]
        }
    }

    if ($videoIds.Count -eq 0) {
        Write-Host "No video IDs found in projects.js" -ForegroundColor Yellow
        return
    }

    $allMetadata = @()

    foreach ($videoId in $videoIds) {
        Write-Host ""
        Write-Host "Found video ID: $videoId"
        Download-Video -VideoId $videoId
        Process-Video -VideoId $videoId

        $meta = Get-VideoMetadata -VideoId $videoId
        if ($meta) {
            $allMetadata += @{ Id = $videoId; Meta = $meta }
        }
    }

    Write-Host ""
    Write-Host "============================================"
    Write-Host "All videos processed!"
    Write-Host "============================================"

    if ($allMetadata.Count -gt 0) {
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host "METADATA FOR projects.js:" -ForegroundColor Cyan
        Write-Host "============================================" -ForegroundColor Cyan
        foreach ($item in $allMetadata) {
            Write-Host "    {" -ForegroundColor White
            Write-Host "        title: `"$($item.Meta.Title)`"," -ForegroundColor White
            Write-Host "        category: `"long-form`"," -ForegroundColor White
            Write-Host "        youtubeId: `"$($item.Id)`"," -ForegroundColor White
            Write-Host "        channelName: `"$($item.Meta.Channel)`"," -ForegroundColor White
            Write-Host "        viewCount: `"$($item.Meta.ViewCountFormatted)`"," -ForegroundColor White
            Write-Host "        thumbnail: `"`"," -ForegroundColor White
            Write-Host "        previewVideo: `"videos/previews/$($item.Id).mp4`"" -ForegroundColor White
            Write-Host "    }," -ForegroundColor White
        }
        Write-Host "============================================" -ForegroundColor Cyan
    }
}

# Main logic
if ($Download) {
    Download-Video -VideoId $Download
} elseif ($Process) {
    Process-Video -VideoId $Process
} elseif ($All) {
    Download-Video -VideoId $All
    Process-Video -VideoId $All
    $meta = Get-VideoMetadata -VideoId $All
    if ($meta) {
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host "METADATA FOR projects.js:" -ForegroundColor Cyan
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host "    {" -ForegroundColor White
        Write-Host "        title: `"$($meta.Title)`"," -ForegroundColor White
        Write-Host "        category: `"long-form`"," -ForegroundColor White
        Write-Host "        youtubeId: `"$All`"," -ForegroundColor White
        Write-Host "        channelName: `"$($meta.Channel)`"," -ForegroundColor White
        Write-Host "        viewCount: `"$($meta.ViewCountFormatted)`"," -ForegroundColor White
        Write-Host "        thumbnail: `"`"," -ForegroundColor White
        Write-Host "        previewVideo: `"videos/previews/$All.mp4`"" -ForegroundColor White
        Write-Host "    }," -ForegroundColor White
        Write-Host "============================================" -ForegroundColor Cyan
    }
} elseif ($Metadata) {
    $meta = Get-VideoMetadata -VideoId $Metadata
    if ($meta) {
        Write-Host ""
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host "METADATA FOR projects.js:" -ForegroundColor Cyan
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host "    {" -ForegroundColor White
        Write-Host "        title: `"$($meta.Title)`"," -ForegroundColor White
        Write-Host "        category: `"long-form`"," -ForegroundColor White
        Write-Host "        youtubeId: `"$Metadata`"," -ForegroundColor White
        Write-Host "        channelName: `"$($meta.Channel)`"," -ForegroundColor White
        Write-Host "        viewCount: `"$($meta.ViewCountFormatted)`"," -ForegroundColor White
        Write-Host "        thumbnail: `"`"," -ForegroundColor White
        Write-Host "        previewVideo: `"videos/previews/$Metadata.mp4`"" -ForegroundColor White
        Write-Host "    }," -ForegroundColor White
        Write-Host "============================================" -ForegroundColor Cyan
    }
} else {
    Process-All
}

Write-Host ""
Read-Host "Press Enter to exit"
