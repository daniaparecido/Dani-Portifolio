# CSS Directory

## styles.css

### Design System
- **Background**: #000000 (black)
- **Text Primary**: #ffffff (white)
- **Text Secondary**: #888888 (gray)
- **Text Muted**: #aaaaaa
- **Border**: #222222
- **Font**: Inter, Helvetica Neue, sans-serif

### Grid Layout
```css
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 8px;
}
```

### Key Components

**Grid Items:**
- `.grid-item` - 16:9 aspect ratio container with scale transition
  - Scales to 1.05x on hover (immediate)
  - Additional 1.05x scale when `.preview-active` class added
  - z-index: 10 on hover to appear above neighbors
- `.grid-item.vertical-item` - 9:16 for Instagram/TikTok
- `.grid-item-preview` - Hover preview container (video/iframe)
- `.grid-item-overlay` - Title/meta with gradient background
  - **Always visible** (opacity: 1 by default)
  - No longer requires hover to show
- `.play-icon` - Play button overlay
  - Subtle visibility (opacity: 0.6) at rest
  - Full opacity (1.0) on hover
  - Hidden during preview playback

**Lightbox:**
- `.lightbox` - Full-screen modal overlay with blur
- `.lightbox.active` - Visible state
- `.lightbox-content` - Video container (max-width: 1200px)
- `.video-container` - 16:9 responsive iframe wrapper for YouTube
- `.video-container.vertical-video` - Vertical video container (90vh height) for Instagram/TikTok
- `.vertical-video-wrapper` - Wraps video and button (position: relative, display: inline-block)
- `.lightbox-video` - HTML5 video player for Instagram/TikTok
  - max-width: 90vw, max-height: 90vh
  - object-fit: contain (prevents cropping)
  - Native HTML5 controls visible
- `.watch-on-platform` - Platform link button
  - Position: absolute top-right
  - Pill-shaped (border-radius: 50px)
  - Glassmorphism effect (backdrop-filter: blur(10px))
  - Semi-transparent background: rgba(0, 0, 0, 0.6)
  - Hover: fills white, text turns black, lifts up 1px
  - External link icon animates diagonally on hover

**States:**
- `.preview-active` - Shows preview, hides thumbnail, scales item
- `.has-preview:hover .play-icon` - Hides play button during preview

### Responsive Breakpoints

| Breakpoint | Target | Changes |
|------------|--------|---------|
| Default | Desktop | Full styling, hover effects active |
| 1024px | Tablet | Reduced padding |
| 768px | Mobile | Stack layout, overlay always visible, no hover previews |

### Mobile Considerations
- Hover previews disabled (`.grid-item-preview { display: none }`)
- Play icon always visible
- Overlay always visible (matches desktop now)
- Smaller fonts and padding

### Animations
- `fadeIn` - Simple opacity transition
- `slideUp` - Opacity + translateY for page load
- Header/nav/main have staggered load animations
- Grid items scale smoothly with cubic-bezier easing
- Play icon has bouncy scale effect: cubic-bezier(0.34, 1.56, 0.64, 1)

### Recent Changes
- **Always-visible overlay**: Removed hover requirement for metadata display
- **Immediate scale on hover**: Grid items scale to 1.05x as soon as mouse enters
- **Watch on Platform button**: New glassmorphism pill button in lightbox top-right
- **Vertical video support**: Proper sizing for Instagram/TikTok with wrapper
- **Object-fit contain**: Videos display in full without cropping
- **Improved hover states**: Play icon has subtle visibility at rest (0.6 opacity)
