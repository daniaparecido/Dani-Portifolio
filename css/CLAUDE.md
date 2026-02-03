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
- `.grid-item` - 16:9 aspect ratio container
- `.grid-item.vertical-item` - 9:16 for Instagram/TikTok
- `.grid-item-preview` - Hover preview container (video/iframe)
- `.grid-item-overlay` - Title/meta with gradient background

**Lightbox:**
- `.lightbox` - Full-screen modal overlay with blur
- `.lightbox.active` - Visible state
- `.lightbox-content` - Video container (max-width: 1200px)
- `.video-container` - 16:9 responsive iframe wrapper

**States:**
- `.preview-active` - Shows preview, hides thumbnail
- `.has-preview:hover .play-icon` - Hides play button during preview

### Responsive Breakpoints

| Breakpoint | Target | Changes |
|------------|--------|---------|
| Default | Desktop | Full styling |
| 1024px | Tablet | Reduced padding |
| 768px | Mobile | Stack layout, always show overlay, no hover previews |

### Mobile Considerations
- Hover previews disabled (`.grid-item-preview { display: none }`)
- Play icon always visible
- Overlay always visible (no hover state on touch)
- Smaller fonts and padding

### Animations
- `fadeIn` - Simple opacity transition
- `slideUp` - Opacity + translateY for page load
- Header/nav/main have staggered load animations
