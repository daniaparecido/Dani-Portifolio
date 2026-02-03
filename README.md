# Daniel Aparecido Portfolio

A clean, minimal portfolio website for showcasing video editing and motion design work.

## Quick Start

1. Open `index.html` in your browser to preview the site
2. Edit `js/projects.js` to add your projects

## How to Add/Edit Projects

Open `js/projects.js` and add projects to the array:

```javascript
{
    title: "Project Title",
    category: "long-form",  // Options: "long-form", "short-form", "motion-design"
    youtubeId: "VIDEO_ID",  // From YouTube URL after "v="
    thumbnail: ""           // Leave empty to use YouTube's thumbnail
}
```

### Finding the YouTube Video ID

From a URL like `https://www.youtube.com/watch?v=DW3F1OHfZeo`, the video ID is `DW3F1OHfZeo`

## File Structure

```
├── index.html          # Homepage with portfolio grid
├── about.html          # About page
├── css/
│   └── styles.css      # All styling
├── js/
│   ├── projects.js     # YOUR PROJECT DATA (edit this!)
│   └── main.js         # Site functionality
├── images/
│   ├── logo.png        # Your logo
│   └── thumbnails/     # Custom thumbnails (optional)
└── README.md           # This file
```

## Deployment

### Option 1: Netlify (Recommended)
1. Create account at netlify.com
2. Drag and drop this folder to deploy
3. Get a free URL instantly

### Option 2: GitHub Pages
1. Push this folder to a GitHub repository
2. Go to Settings > Pages
3. Select "Deploy from branch" and choose main

### Option 3: Vercel
1. Create account at vercel.com
2. Import your GitHub repository
3. Auto-deploys on every push

## Customization

### Colors
Edit the color values in `css/styles.css`:
- Background: `#000000`
- Text: `#ffffff`
- Accent: `#888888`

### About Page
Edit `about.html` directly to update your bio and contact info.

## Support

For questions, contact: daniaparecidocontato@gmail.com
