/**
 * ============================================
 * PORTFOLIO MAIN JAVASCRIPT
 * ============================================
 * Handles: Grid generation, filtering, lightbox, hover previews
 * Supports: YouTube, Instagram, TikTok
 */

(function() {
    'use strict';

    // ============================================
    // DOM Elements
    // ============================================
    const longFormGrid = document.getElementById('long-form-grid');
    const shortFormGrid = document.getElementById('short-form-grid');
    const lightbox = document.getElementById('lightbox');
    const lightboxClose = document.getElementById('lightbox-close');
    const videoContainer = document.getElementById('video-container');


    // ============================================
    // Helper Functions
    // ============================================

    /**
     * Get thumbnail URL based on platform
     */
    function getThumbnailUrl(project) {
        const videoId = project.videoId || project.youtubeId;
        const platform = project.platform || 'youtube';

        // For Instagram/TikTok, use local thumbnail
        if (platform === 'instagram' || platform === 'tiktok') {
            return `images/thumbnails/${videoId}.jpg`;
        }

        // YouTube: use their CDN
        return `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`;
    }

    /**
     * Get fallback thumbnail URL (lower quality)
     */
    function getFallbackThumbnail(project) {
        const videoId = project.videoId || project.youtubeId;
        if (project.platform === 'youtube' || !project.platform) {
            return `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`;
        }
        return '';
    }

    /**
     * Get YouTube embed URL for lightbox (with sound)
     */
    function getYouTubeEmbedUrl(videoId) {
        return `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0`;
    }

    /**
     * Get YouTube embed URL for hover preview (muted, no controls)
     */
    function getYouTubePreviewUrl(videoId) {
        return `https://www.youtube.com/embed/${videoId}?autoplay=1&mute=1&controls=0&showinfo=0&rel=0&loop=1&playlist=${videoId}&modestbranding=1&playsinline=1&enablejsapi=1`;
    }

    /**
     * Check if project has a local preview video available
     */
    function hasLocalPreview(project) {
        return !!project.previewVideo;
    }

    // ============================================
    // Grid Generation
    // ============================================

    /**
     * Create a single grid item element
     */
    function createGridItem(project) {
        const item = document.createElement('div');
        const videoId = project.videoId || project.youtubeId;
        const platform = project.platform || 'youtube';
        const canPreview = hasLocalPreview(project) || platform === 'youtube';
        const isVertical = platform === 'instagram' || platform === 'tiktok';

        item.className = 'grid-item' + (canPreview ? ' has-preview' : '') + (isVertical ? ' vertical-item' : '');
        item.dataset.category = project.category;
        item.dataset.videoId = videoId;
        item.dataset.platform = platform;

        const thumbnailUrl = getThumbnailUrl(project);
        const fallbackUrl = getFallbackThumbnail(project);

        item.innerHTML = `
            <img src="${thumbnailUrl}" alt="${project.title}" loading="lazy"
                 ${fallbackUrl ? `onerror="this.src='${fallbackUrl}'"` : ''}>
            <div class="grid-item-preview"></div>
            <div class="grid-item-overlay">
                <h3 class="grid-item-title">${project.title}</h3>
                <span class="grid-item-meta">${project.channelName || ''} ${project.channelName && project.viewCount ? '·' : ''} ${project.viewCount || ''}</span>
            </div>
        `;

        // Click handler - Open appropriate lightbox based on platform
        item.addEventListener('click', () => {
            if (platform === 'youtube') {
                openYouTubeLightbox(videoId, project.url);
            } else if (platform === 'instagram') {
                openVideoLightbox(videoId, 'instagram', project.url);
            } else if (platform === 'tiktok') {
                openVideoLightbox(videoId, 'tiktok', project.url);
            }
        });

        // Hover preview handlers (desktop only)
        let hoverTimeout;
        const previewContainer = item.querySelector('.grid-item-preview');

        item.addEventListener('mouseenter', () => {
            if (!canPreview) return;

            // Delay before loading preview (like YouTube)
            hoverTimeout = setTimeout(() => {
                if (hasLocalPreview(project)) {
                    // Use local video file for preview
                    previewContainer.innerHTML = `
                        <video
                            src="${project.previewVideo}"
                            autoplay
                            muted
                            loop
                            playsinline
                            preload="none">
                        </video>
                    `;
                } else if (platform === 'youtube') {
                    // Fallback to YouTube iframe
                    const previewUrl = getYouTubePreviewUrl(videoId);
                    previewContainer.innerHTML = `
                        <iframe
                            src="${previewUrl}"
                            title="Video preview"
                            allow="autoplay; encrypted-media"
                            loading="lazy">
                        </iframe>
                    `;
                }
                item.classList.add('preview-active');
            }, 500);
        });

        item.addEventListener('mouseleave', () => {
            clearTimeout(hoverTimeout);
            item.classList.remove('preview-active');
            // Clean up video to release memory
            const video = previewContainer.querySelector('video');
            if (video) {
                video.pause();
                video.src = '';
                video.load();
            }
            previewContainer.innerHTML = '';
        });

        return item;
    }

    /**
     * Render projects to a specific grid element
     */
    function renderGrid(grid, projectsToShow) {
        if (!grid) return;

        grid.innerHTML = '';

        projectsToShow.forEach(project => {
            const item = createGridItem(project);
            grid.appendChild(item);
        });
    }

    // ============================================
    // Lightbox
    // ============================================

    /**
     * Open the lightbox with a YouTube video
     */
    function openYouTubeLightbox(videoId, url) {
        if (!lightbox || !videoContainer) return;

        const embedUrl = getYouTubeEmbedUrl(videoId);

        videoContainer.innerHTML = `
            <iframe
                src="${embedUrl}"
                title="YouTube video player"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowfullscreen>
            </iframe>
            <a href="${url}" target="_blank" rel="noopener noreferrer" class="watch-on-platform">
                Watch on YouTube
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                    <polyline points="15 3 21 3 21 9"></polyline>
                    <line x1="10" y1="14" x2="21" y2="3"></line>
                </svg>
            </a>
        `;

        lightbox.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    /**
     * Open the lightbox with a local video file (Instagram/TikTok)
     */
    function openVideoLightbox(videoId, platform, url) {
        if (!lightbox || !videoContainer) return;

        // Mark container as vertical video
        videoContainer.classList.add('vertical-video');

        const videoPath = `videos/source/${videoId}.mp4`;
        const platformName = platform.charAt(0).toUpperCase() + platform.slice(1);

        videoContainer.innerHTML = `
            <div class="vertical-video-wrapper">
                <video
                    class="lightbox-video"
                    src="${videoPath}"
                    controls
                    autoplay
                    playsinline>
                    Your browser does not support the video tag.
                </video>
                <a href="${url}" target="_blank" rel="noopener noreferrer" class="watch-on-platform">
                    Watch on ${platformName}
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                        <polyline points="15 3 21 3 21 9"></polyline>
                        <line x1="10" y1="14" x2="21" y2="3"></line>
                    </svg>
                </a>
            </div>
        `;

        lightbox.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    /**
     * Close the lightbox
     */
    function closeLightbox() {
        if (!lightbox || !videoContainer) return;

        // Pause any playing videos before closing
        const video = videoContainer.querySelector('video');
        if (video) {
            video.pause();
            video.src = ''; // Release video resources
        }

        lightbox.classList.remove('active');
        videoContainer.innerHTML = '';
        videoContainer.classList.remove('vertical-video'); // Remove vertical class
        document.body.style.overflow = '';
    }

    /**
     * Set up lightbox event listeners
     */
    function initLightbox() {
        if (!lightbox) return;

        if (lightboxClose) {
            lightboxClose.addEventListener('click', closeLightbox);
        }

        lightbox.addEventListener('click', (e) => {
            if (e.target === lightbox) {
                closeLightbox();
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && lightbox.classList.contains('active')) {
                closeLightbox();
            }
        });
    }

    // ============================================
    // Initialization
    // ============================================

    function init() {
        if (typeof projects === 'undefined' || !Array.isArray(projects)) {
            console.error('Projects data not found. Make sure projects.js is loaded before main.js');
            return;
        }

        const longFormProjects = projects.filter(p => p.category === 'long-form');
        const shortFormProjects = projects.filter(p => p.category === 'short-form');

        renderGrid(longFormGrid, longFormProjects);
        renderGrid(shortFormGrid, shortFormProjects);
        initLightbox();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
