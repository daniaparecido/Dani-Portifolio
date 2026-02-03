/**
 * ============================================
 * PROJECT DATA - EDIT THIS FILE TO ADD/REMOVE PROJECTS
 * ============================================
 *
 * To add a new project, copy one of the objects below and fill in:
 * - title: The name of your project
 * - category: Must be one of: "long-form", "short-form", or "motion-design"
 * - youtubeId: The video ID from the YouTube URL (the part after "v=")
 * - channelName: The YouTube channel name
 * - viewCount: View count (e.g., "1.2M views")
 * - thumbnail: (optional) Path to custom thumbnail, or leave empty to use YouTube's thumbnail
 * - previewVideo: (optional) Path to local video preview, or leave empty for YouTube iframe fallback
 *
 * Example YouTube URL: https://www.youtube.com/watch?v=DW3F1OHfZeo
 * The youtubeId would be: DW3F1OHfZeo
 *
 * To generate preview videos, run: scripts/process-videos.bat
 */

const projects = [
    {
        title: "Beat me in League, win $1000",
        category: "long-form",
        youtubeId: "DW3F1OHfZeo",
        channelName: "Team Liquid League of Legends",
        viewCount: "64K views",
        thumbnail: "",
        previewVideo: "videos/previews/DW3F1OHfZeo.mp4"
    },
    // ============================================
    // ADD MORE PROJECTS BELOW
    // ============================================
    // {
    //     title: "Project Title Here",
    //     category: "short-form",
    //     youtubeId: "YOUR_VIDEO_ID",
    //     channelName: "Channel Name",
    //     viewCount: "100K views",
    //     thumbnail: "",
    //     previewVideo: "videos/previews/YOUR_VIDEO_ID.mp4"
    // },
];
