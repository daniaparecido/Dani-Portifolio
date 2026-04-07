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
    // View Counter (live odometer ticker)
    // ============================================
    // Runs entirely client-side. No API calls, no backend.
    // Starts at (totalYouTubeViews - VIEW_TICKS_PER_LOOP), ticks +1 every
    // VIEW_TICK_INTERVAL_MS, and on reaching the real total snaps back and loops.
    // 150 ticks * 2000ms = 300s = 5 minutes per loop.
    //
    // Each digit lives in its own "slot" (overflow:hidden, height:1em) containing
    // a vertical strip of <span>0</span>...<span>9</span>. To show digit N we
    // translate the strip up by N em. Only digits whose value actually changed
    // animate, so the rightmost digit rolls every tick and higher digits roll
    // less often — exactly like a real odometer.

    const VIEW_TICK_INTERVAL_MS = 2000;
    const VIEW_TICKS_PER_LOOP = 150;

    function formatTotalViews(num) {
        return num.toLocaleString('en-US');
    }

    function updateViewCounter() {
        const counter = document.getElementById('view-counter');
        if (!counter || typeof totalYouTubeViews === 'undefined' || totalYouTubeViews <= 0) return;

        const realTotal = totalYouTubeViews;
        const startValue = realTotal - VIEW_TICKS_PER_LOOP;

        const stat = document.createElement('div');
        stat.className = 'hero-stat-count';
        stat.innerHTML = '<span class="hero-stat-number odometer"></span><span class="hero-stat-label">views on<br>edited videos</span>';
        counter.insertBefore(stat, counter.firstChild);

        const numberEl = stat.querySelector('.hero-stat-number');

        // Build the odometer DOM from the start value's formatted string.
        // Digit count is fixed at init; the value never crosses a power of 10.
        const initialFormatted = formatTotalViews(startValue);
        const slots = []; // { strip, currentDigit }

        for (let i = 0; i < initialFormatted.length; i++) {
            const ch = initialFormatted.charAt(i);
            if (ch >= '0' && ch <= '9') {
                const slot = document.createElement('span');
                slot.className = 'odometer-digit';
                const strip = document.createElement('span');
                strip.className = 'odometer-strip';
                // 11 children: 0..9 plus a duplicate 0 at the bottom so a
                // 9 -> 0 transition can roll FORWARD into the duplicate 0
                // and then silently snap back to the top 0 for the next tick.
                for (let d = 0; d <= 10; d++) {
                    const dEl = document.createElement('span');
                    dEl.className = 'odometer-d';
                    dEl.textContent = String(d % 10);
                    strip.appendChild(dEl);
                }
                slot.appendChild(strip);
                numberEl.appendChild(slot);
                const initDigit = parseInt(ch, 10);
                strip.style.transform = 'translateY(-' + initDigit + 'em)';
                slots.push({ strip: strip, currentDigit: initDigit, snapBackTimer: null });
            } else {
                const sep = document.createElement('span');
                sep.className = 'odometer-sep';
                sep.textContent = ch;
                numberEl.appendChild(sep);
            }
        }

        // Respect user's reduced-motion preference: snap to the static full
        // number with no animation, and never start the interval.
        const reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (reduceMotion) {
            setOdometer(slots, formatTotalViews(realTotal), false);
            return;
        }

        let current = startValue;
        let intervalId = null;

        function tick() {
            current += 1;
            let isReset = false;
            if (current > realTotal) {
                current = startValue;
                isReset = true;
            }
            setOdometer(slots, formatTotalViews(current), !isReset);
        }

        function start() {
            if (intervalId === null) {
                intervalId = setInterval(tick, VIEW_TICK_INTERVAL_MS);
            }
        }

        function stop() {
            if (intervalId !== null) {
                clearInterval(intervalId);
                intervalId = null;
            }
        }

        start();

        // Pause when tab is hidden so we don't burn battery in the background.
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                stop();
            } else {
                start();
            }
        });
    }

    /**
     * Update the odometer slots to show the given formatted string.
     * Only digits whose value changed will move. If `animate` is false,
     * the change snaps without transition (used for the loop reset).
     *
     * Rollover handling: when a digit goes 9 -> 0 we animate forward to
     * the duplicate 0 at position 10, then schedule a silent snap-back
     * to position 0 once the transition has finished.
     */
    function setOdometer(slots, formatted, animate) {
        let slotIdx = 0;
        for (let i = 0; i < formatted.length; i++) {
            const ch = formatted.charAt(i);
            if (ch < '0' || ch > '9') continue;
            const newDigit = parseInt(ch, 10);
            const slot = slots[slotIdx++];
            if (!slot) break;
            if (slot.currentDigit === newDigit) continue;
            const strip = slot.strip;

            // Cancel any pending snap-back from a previous rollover so we
            // don't clobber a freshly-set transform.
            if (slot.snapBackTimer !== null) {
                clearTimeout(slot.snapBackTimer);
                slot.snapBackTimer = null;
            }

            const isRollover = slot.currentDigit === 9 && newDigit === 0;

            if (!animate) {
                // Reset path: snap immediately, no transition.
                strip.style.transition = 'none';
                strip.style.transform = 'translateY(-' + newDigit + 'em)';
                void strip.offsetHeight;
                strip.style.transition = '';
            } else if (isRollover) {
                // Roll forward into the duplicate 0 at position 10, then
                // snap back to position 0 once the roll has finished.
                strip.style.transform = 'translateY(-10em)';
                slot.snapBackTimer = setTimeout(function() {
                    slot.snapBackTimer = null;
                    // Defensive: only snap if no later change has happened.
                    if (slot.currentDigit === 0) {
                        strip.style.transition = 'none';
                        strip.style.transform = 'translateY(0em)';
                        void strip.offsetHeight;
                        strip.style.transition = '';
                    }
                }, 650);
            } else {
                strip.style.transform = 'translateY(-' + newDigit + 'em)';
            }
            slot.currentDigit = newDigit;
        }
    }

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
        return `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0&vq=hd1080`;
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
            <div class="grid-item-thumb">
                <img src="${thumbnailUrl}" alt="${project.title}" loading="lazy"
                     ${fallbackUrl ? `onerror="this.src='${fallbackUrl}'"` : ''}>
                <div class="grid-item-preview"></div>
            </div>
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
        `;

        // Add button below video container
        let existingBtn = videoContainer.parentElement.querySelector('.watch-on-platform');
        if (existingBtn) existingBtn.remove();
        videoContainer.insertAdjacentHTML('afterend', `
            <a href="${url}" target="_blank" rel="noopener noreferrer" class="watch-on-platform">
                Watch on YouTube
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                    <polyline points="15 3 21 3 21 9"></polyline>
                    <line x1="10" y1="14" x2="21" y2="3"></line>
                </svg>
            </a>
        `);

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
            </div>
        `;

        // Add button below video container
        let existingBtn = videoContainer.parentElement.querySelector('.watch-on-platform');
        if (existingBtn) existingBtn.remove();
        videoContainer.insertAdjacentHTML('afterend', `
            <a href="${url}" target="_blank" rel="noopener noreferrer" class="watch-on-platform">
                Watch on ${platformName}
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                    <polyline points="15 3 21 3 21 9"></polyline>
                    <line x1="10" y1="14" x2="21" y2="3"></line>
                </svg>
            </a>
        `);

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
        // Remove button placed outside video container
        const btn = videoContainer.parentElement.querySelector('.watch-on-platform');
        if (btn) btn.remove();
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

    // ============================================
    // Mobile Tabs
    // ============================================

    function initMobileTabs() {
        const tabsContainer = document.getElementById('mobile-tabs');
        if (!tabsContainer) return;

        const tabs = tabsContainer.querySelectorAll('.mobile-tab');
        const longFormSection = document.getElementById('section-long-form');
        const shortFormSection = document.getElementById('section-short-form');

        function switchTab(tabName) {
            tabs.forEach(function(t) {
                t.classList.toggle('active', t.dataset.tab === tabName);
            });

            if (longFormSection) {
                longFormSection.classList.toggle('mobile-hidden', tabName !== 'long-form');
            }
            if (shortFormSection) {
                shortFormSection.classList.toggle('mobile-hidden', tabName !== 'short-form');
            }
        }

        tabs.forEach(function(tab) {
            tab.addEventListener('click', function() {
                switchTab(tab.dataset.tab);
            });
        });

        // Set initial state: show long-form, hide short-form
        var isMobile = window.matchMedia('(max-width: 768px)').matches;
        if (isMobile) {
            switchTab('long-form');
        }

        // Listen for resize to show/hide sections appropriately
        window.matchMedia('(max-width: 768px)').addEventListener('change', function(e) {
            if (e.matches) {
                // Switched to mobile — apply active tab
                var activeTab = tabsContainer.querySelector('.mobile-tab.active');
                switchTab(activeTab ? activeTab.dataset.tab : 'long-form');
            } else {
                // Switched to desktop — show both sections
                if (longFormSection) longFormSection.classList.remove('mobile-hidden');
                if (shortFormSection) shortFormSection.classList.remove('mobile-hidden');
            }
        });
    }

    function initVideoListDropdown() {
        const toggle = document.getElementById('video-list-toggle');
        const dropdown = toggle?.closest('.video-list-dropdown');
        if (!toggle || !dropdown) return;

        toggle.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('open');
        });

        const menu = dropdown.querySelector('.video-list-menu');
        menu.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        document.addEventListener('click', () => {
            dropdown.classList.remove('open');
        });
    }

    function initCopyEmail() {
        const btn = document.getElementById('copy-email-btn');
        if (!btn) return;

        btn.addEventListener('click', () => {
            const email = btn.dataset.email;
            navigator.clipboard.writeText(email).then(() => {
                btn.classList.add('copied');
                const tooltip = document.createElement('span');
                tooltip.className = 'copy-email-tooltip';
                tooltip.textContent = 'Copied!';
                btn.appendChild(tooltip);
                setTimeout(() => {
                    btn.classList.remove('copied');
                    tooltip.remove();
                }, 1500);
            });
        });
    }

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
        initVideoListDropdown();
        initCopyEmail();
        updateViewCounter();
        initMobileTabs();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
