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
    const grid = document.getElementById('project-grid');
    const lightbox = document.getElementById('lightbox');
    const lightboxClose = document.getElementById('lightbox-close');
    const videoContainer = document.getElementById('video-container');
    const navLinks = document.querySelectorAll('.nav-link[data-category]');


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

        // Click handler - YouTube opens lightbox, others open in new tab
        item.addEventListener('click', () => {
            if (platform === 'youtube') {
                openLightbox(videoId);
            } else if (project.url) {
                window.open(project.url, '_blank');
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
     * Render all projects to the grid
     */
    function renderGrid(projectsToShow) {
        if (!grid) return;

        grid.innerHTML = '';

        projectsToShow.forEach(project => {
            const item = createGridItem(project);
            grid.appendChild(item);
        });
    }

    /**
     * Filter projects by category
     */
    function filterProjects(category) {
        if (category === 'all') {
            return projects;
        }
        return projects.filter(project => project.category === category);
    }

    // ============================================
    // Navigation / Filtering
    // ============================================

    /**
     * Handle category filter click
     */
    function handleFilterClick(e) {
        e.preventDefault();

        const category = e.target.dataset.category;
        if (!category) return;

        // Update active state
        navLinks.forEach(link => link.classList.remove('active'));
        e.target.classList.add('active');

        // Filter and re-render
        const filteredProjects = filterProjects(category);
        renderGrid(filteredProjects);
    }

    /**
     * Set up navigation event listeners
     */
    function initNavigation() {
        navLinks.forEach(link => {
            link.addEventListener('click', handleFilterClick);
        });
    }

    // ============================================
    // Lightbox
    // ============================================

    /**
     * Open the lightbox with a YouTube video
     */
    function openLightbox(videoId) {
        if (!lightbox || !videoContainer) return;

        const embedUrl = getYouTubeEmbedUrl(videoId);

        videoContainer.innerHTML = `
            <iframe
                src="${embedUrl}"
                title="YouTube video player"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowfullscreen>
            </iframe>
        `;

        lightbox.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    /**
     * Close the lightbox
     */
    function closeLightbox() {
        if (!lightbox || !videoContainer) return;

        lightbox.classList.remove('active');
        videoContainer.innerHTML = '';
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

        renderGrid(filterProjects('long-form'));
        initNavigation();
        initLightbox();

        const hash = window.location.hash.slice(1);
        if (hash) {
            const matchingLink = document.querySelector(`.nav-link[data-category="${hash}"]`);
            if (matchingLink) {
                matchingLink.click();
            }
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
