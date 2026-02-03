/**
 * ============================================
 * PORTFOLIO MAIN JAVASCRIPT
 * ============================================
 * Handles: Grid generation, filtering, lightbox, hover previews
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
     * Get YouTube thumbnail URL from video ID
     */
    function getYouTubeThumbnail(youtubeId) {
        return `https://img.youtube.com/vi/${youtubeId}/maxresdefault.jpg`;
    }

    /**
     * Get YouTube embed URL for lightbox (with sound)
     */
    function getYouTubeEmbedUrl(youtubeId) {
        return `https://www.youtube.com/embed/${youtubeId}?autoplay=1&rel=0`;
    }

    /**
     * Get YouTube embed URL for hover preview (muted, no controls)
     */
    function getYouTubePreviewUrl(youtubeId) {
        return `https://www.youtube.com/embed/${youtubeId}?autoplay=1&mute=1&controls=0&showinfo=0&rel=0&loop=1&playlist=${youtubeId}&modestbranding=1&playsinline=1&enablejsapi=1`;
    }

    /**
     * Format category for display
     */
    function formatCategory(category) {
        return category.replace('-', ' ').toUpperCase();
    }

    // ============================================
    // Grid Generation
    // ============================================

    /**
     * Create a single grid item element
     */
    function createGridItem(project) {
        const item = document.createElement('div');
        item.className = 'grid-item';
        item.dataset.category = project.category;
        item.dataset.youtubeId = project.youtubeId;

        const thumbnailUrl = project.thumbnail || getYouTubeThumbnail(project.youtubeId);

        item.innerHTML = `
            <img src="${thumbnailUrl}" alt="${project.title}" loading="lazy"
                 onerror="this.src='https://img.youtube.com/vi/${project.youtubeId}/hqdefault.jpg'">
            <div class="grid-item-preview"></div>
            <div class="play-icon">
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z"/>
                </svg>
            </div>
            <div class="grid-item-overlay">
                <h3 class="grid-item-title">${project.title}</h3>
                <span class="grid-item-category">${formatCategory(project.category)}</span>
            </div>
        `;

        // Click handler to open lightbox
        item.addEventListener('click', () => openLightbox(project.youtubeId));

        // Hover preview handlers (desktop only)
        let hoverTimeout;
        const previewContainer = item.querySelector('.grid-item-preview');

        item.addEventListener('mouseenter', () => {
            // Delay before loading preview (like YouTube)
            hoverTimeout = setTimeout(() => {
                const previewUrl = getYouTubePreviewUrl(project.youtubeId);
                previewContainer.innerHTML = `
                    <iframe
                        src="${previewUrl}"
                        title="Video preview"
                        allow="autoplay; encrypted-media"
                        loading="lazy">
                    </iframe>
                `;
                item.classList.add('preview-active');
            }, 500);
        });

        item.addEventListener('mouseleave', () => {
            clearTimeout(hoverTimeout);
            item.classList.remove('preview-active');
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
    function openLightbox(youtubeId) {
        if (!lightbox || !videoContainer) return;

        const embedUrl = getYouTubeEmbedUrl(youtubeId);

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
