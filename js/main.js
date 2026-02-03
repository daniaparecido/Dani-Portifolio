/**
 * ============================================
 * PORTFOLIO MAIN JAVASCRIPT
 * Cinema Noir Editorial Theme
 * ============================================
 * Handles: Grid generation, filtering, lightbox, scroll reveals
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
    const filterNav = document.querySelector('.filter-nav');
    const navLinks = filterNav ? filterNav.querySelectorAll('.nav-link[data-category]') : [];
    const sectionHeader = document.querySelector('.section-header');

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
     * Format category for display
     */
    function formatCategory(category) {
        return category.replace('-', ' ').toUpperCase();
    }

    // ============================================
    // Scroll Reveal Observer
    // ============================================

    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('revealed');
                revealObserver.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    // ============================================
    // Grid Generation
    // ============================================

    /**
     * Create a single grid item element
     */
    function createGridItem(project, index) {
        const item = document.createElement('div');
        item.className = 'grid-item';
        if (project.featured) {
            item.classList.add('featured');
        }
        item.dataset.category = project.category;
        item.dataset.youtubeId = project.youtubeId;

        const thumbnailUrl = project.thumbnail || getYouTubeThumbnail(project.youtubeId);

        item.innerHTML = `
            <img src="${thumbnailUrl}" alt="${project.title}" loading="lazy"
                 onerror="this.src='https://img.youtube.com/vi/${project.youtubeId}/hqdefault.jpg'">
            <div class="play-icon">
                <svg viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z"/>
                </svg>
            </div>
            <div class="grid-item-overlay">
                <span class="grid-item-category">${formatCategory(project.category)}</span>
                <h3 class="grid-item-title">${project.title}</h3>
            </div>
        `;

        // Click handler to open lightbox
        item.addEventListener('click', () => openLightbox(project.youtubeId));

        // Observe for scroll reveal
        revealObserver.observe(item);

        return item;
    }

    /**
     * Render all projects to the grid
     */
    function renderGrid(projectsToShow) {
        if (!grid) return;

        grid.innerHTML = '';

        projectsToShow.forEach((project, index) => {
            const item = createGridItem(project, index);
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
        navLinks.forEach(link => {
            link.classList.remove('active');
            link.style.color = 'var(--text-secondary)';
        });
        e.target.classList.add('active');
        e.target.style.color = 'var(--text-primary)';

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
    // Scroll Reveal Setup
    // ============================================

    function initScrollReveal() {
        // Reveal section header
        if (sectionHeader) {
            revealObserver.observe(sectionHeader);
        }
    }

    // ============================================
    // Smooth Scroll for Anchor Links
    // ============================================

    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (href === '#') return;

                const target = document.querySelector(href);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
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

        // Render all projects by default
        renderGrid(projects);
        initNavigation();
        initLightbox();
        initScrollReveal();
        initSmoothScroll();

        // Handle hash in URL
        const hash = window.location.hash.slice(1);
        if (hash && hash !== 'work') {
            const matchingLink = document.querySelector(`.filter-nav .nav-link[data-category="${hash}"]`);
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
