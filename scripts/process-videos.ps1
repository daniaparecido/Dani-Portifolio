# ============================================
# VIDEO PROCESSING SCRIPT
# ============================================
# Downloads videos and creates 30-second preview clips
# Supports: YouTube, Instagram, TikTok
#
# Requirements: yt-dlp and ffmpeg must be in PATH
#
# Usage:
#   .\process-videos.ps1                    - Process all videos from projects.js
#   .\process-videos.ps1 -Download ID       - Download specific YouTube video
#   .\process-videos.ps1 -Process ID        - Process specific video
#   .\process-videos.ps1 -All ID            - Download, process, and get metadata
#   .\process-videos.ps1 -Metadata ID       - Just fetch metadata (no download)
#   .\process-videos.ps1 -Url "URL"         - Download from any URL (Instagram/TikTok/YouTube)

param(
    [string]$Download,
    [string]$Process,
    [string]$All,
    [string]$Metadata,
    [string]$Url,
    [switch]$NoPause
)

$ErrorActionPreference = "Continue"

$Root = Split-Path -Parent $PSScriptRoot
$SourceDir = Join-Path $Root "videos\source"
$PreviewDir = Join-Path $Root "videos\previews"
$ThumbnailDir = Join-Path $Root "images\thumbnails"
$ProjectsFile = Join-Path $Root "js\projects.js"

Write-Host ""
Write-Host "============================================"
Write-Host "VIDEO PROCESSING SCRIPT"
Write-Host "============================================"
Write-Host ""
Write-Host "Root directory: $Root"
Write-Host "Source directory: $SourceDir"
Write-Host "Preview directory: $PreviewDir"
Write-Host "Thumbnail directory: $ThumbnailDir"
Write-Host "Projects file: $ProjectsFile"
Write-Host ""

# Create directories
if (!(Test-Path $SourceDir)) { New-Item -ItemType Directory -Path $SourceDir -Force | Out-Null }
if (!(Test-Path $PreviewDir)) { New-Item -ItemType Directory -Path $PreviewDir -Force | Out-Null }
if (!(Test-Path $ThumbnailDir)) { New-Item -ItemType Directory -Path $ThumbnailDir -Force | Out-Null }

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
    param([long]$Count, [string]$Label = "views")

    if ($Count -ge 1000000) {
        return "{0:N1}M $Label" -f ($Count / 1000000)
    } elseif ($Count -ge 1000) {
        return "{0:N0}K $Label" -f ($Count / 1000)
    } else {
        return "$Count $Label"
    }
}

function Get-PlatformFromUrl {
    param([string]$Url)

    if ($Url -match "youtube\.com|youtu\.be") {
        return "youtube"
    } elseif ($Url -match "instagram\.com") {
        return "instagram"
    } elseif ($Url -match "tiktok\.com") {
        return "tiktok"
    }
    return "unknown"
}

function Get-VideoIdFromUrl {
    param([string]$Url, [string]$Platform)

    switch ($Platform) {
        "youtube" {
            if ($Url -match "(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([a-zA-Z0-9_-]{11})") {
                return $matches[1]
            }
        }
        "instagram" {
            if ($Url -match "/(?:reel|p|reels)/([A-Za-z0-9_-]+)") {
                return $matches[1]
            }
        }
        "tiktok" {
            if ($Url -match "/video/(\d+)") {
                return $matches[1]
            }
        }
    }
    return $null
}

function Download-FromUrl {
    param([string]$Url)

    $platform = Get-PlatformFromUrl -Url $Url
    $videoId = Get-VideoIdFromUrl -Url $Url -Platform $platform

    if (-not $videoId) {
        Write-Host "ERROR: Could not extract video ID from URL" -ForegroundColor Red
        return
    }

    Write-Host ""
    Write-Host "Platform: $platform"
    Write-Host "Video ID: $videoId"
    Write-Host "----------------------------------------"

    $OutputFile = Join-Path $SourceDir "$videoId.mp4"
    $ThumbnailFile = Join-Path $ThumbnailDir "$videoId.jpg"
    $cookiesFile = Join-Path $Root "cookies.txt"

    # Download video
    if (Test-Path $OutputFile) {
        Write-Host "Source file already exists, skipping download."
    } else {
        Write-Host "Downloading video..."
        & yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" -o $OutputFile --merge-output-format mp4 --cookies $cookiesFile $Url

        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Failed to download video" -ForegroundColor Red
        } else {
            Write-Host "Download complete!" -ForegroundColor Green
        }
    }

    # Download thumbnail for Instagram/TikTok
    if ($platform -ne "youtube") {
        if (Test-Path $ThumbnailFile) {
            Write-Host "Thumbnail already exists, skipping."
        } else {
            Write-Host "Downloading thumbnail..."
            & yt-dlp --write-thumbnail --skip-download --convert-thumbnails jpg -o (Join-Path $ThumbnailDir "$videoId") --cookies $cookiesFile $Url 2>$null

            # yt-dlp sometimes adds extra extension, rename if needed
            $possibleThumbs = Get-ChildItem -Path $ThumbnailDir -Filter "$videoId.*" | Where-Object { $_.Extension -match "\.(jpg|jpeg|png|webp)$" }
            if ($possibleThumbs) {
                $thumb = $possibleThumbs | Select-Object -First 1
                if ($thumb.FullName -ne $ThumbnailFile) {
                    Move-Item -Path $thumb.FullName -Destination $ThumbnailFile -Force
                }
                Write-Host "Thumbnail saved!" -ForegroundColor Green
            }
        }
    }

    # Process preview
    Process-VideoFile -VideoId $videoId -Platform $platform

    # Get metadata
    Write-Host ""
    Write-Host "Fetching metadata..."
    $metadata = & yt-dlp --cookies $cookiesFile --print "%(title)s|%(channel)s|%(view_count)s|%(like_count)s" $Url 2>$null

    if ($metadata) {
        $parts = $metadata -split '\|'
        $title = if ($parts.Count -gt 0) { $parts[0] } else { "" }
        $channel = if ($parts.Count -gt 1) { $parts[1] } else { "" }
        $views = 0; if ($parts.Count -gt 2) { [long]::TryParse($parts[2], [ref]$views) | Out-Null }
        $likes = 0; if ($parts.Count -gt 3) { [long]::TryParse($parts[3], [ref]$likes) | Out-Null }

        # For Instagram, use likes if views is 0
        $viewLabel = if ($platform -eq "instagram" -and $views -eq 0) {
            Format-ViewCount -Count $likes -Label "likes"
        } else {
            Format-ViewCount -Count $views -Label "views"
        }

        Write-Host ""
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host "METADATA FOR projects.js:" -ForegroundColor Cyan
        Write-Host "============================================" -ForegroundColor Cyan
        Write-Host "    {" -ForegroundColor White
        Write-Host "        title: `"$title`"," -ForegroundColor White
        Write-Host "        category: `"short-form`"," -ForegroundColor White
        Write-Host "        videoId: `"$videoId`"," -ForegroundColor White
        Write-Host "        platform: `"$platform`"," -ForegroundColor White
        Write-Host "        channelName: `"$channel`"," -ForegroundColor White
        Write-Host "        viewCount: `"$viewLabel`"," -ForegroundColor White
        Write-Host "        thumbnail: `"`"," -ForegroundColor White
        Write-Host "        url: `"$Url`"," -ForegroundColor White
        Write-Host "        previewVideo: `"videos/previews/$videoId.mp4`"" -ForegroundColor White
        Write-Host "    }," -ForegroundColor White
        Write-Host "============================================" -ForegroundColor Cyan
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

function Process-VideoFile {
    param(
        [string]$VideoId,
        [string]$Platform = "youtube"
    )

    Write-Host ""
    Write-Host "Processing video: $VideoId ($Platform)"
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

    # Use different scaling based on platform (vertical vs horizontal)
    if ($Platform -eq "instagram" -or $Platform -eq "tiktok") {
        Write-Host "Creating 30-second vertical preview (540x960)..."
        $scaleFilter = "scale=540:960:force_original_aspect_ratio=decrease,pad=540:960:(ow-iw)/2:(oh-ih)/2"
    } else {
        Write-Host "Creating 30-second horizontal preview (854x480)..."
        $scaleFilter = "scale=854:480:force_original_aspect_ratio=decrease,pad=854:480:(ow-iw)/2:(oh-ih)/2"
    }

    & ffmpeg -i $InputFile -ss 0 -t 30 -vf $scaleFilter -c:v libx264 -preset slow -crf 28 -profile:v main -level 3.1 -movflags +faststart -an -y $OutputFile

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to process video $VideoId" -ForegroundColor Red
    } else {
        Write-Host "Preview created: $OutputFile" -ForegroundColor Green
    }
}

function Process-Video {
    param([string]$VideoId)
    Process-VideoFile -VideoId $VideoId -Platform "youtube"
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
if ($Url) {
    Download-FromUrl -Url $Url
} elseif ($Download) {
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
if (-not $NoPause) {
    Read-Host "Press Enter to exit"
}
