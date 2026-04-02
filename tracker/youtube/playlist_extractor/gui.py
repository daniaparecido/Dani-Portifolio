"""GUI for extracting video URLs from YouTube playlists."""

import os
import re
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from googleapiclient.discovery import build


class PlaylistExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Playlist Extractor")
        self.root.geometry("600x500")
        self.root.resizable(True, True)

        # Load API key
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))
        self.api_key = os.getenv("YOUTUBE_API_KEY")

        self.setup_ui()

    def setup_ui(self):
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Playlist URL input
        url_label = ttk.Label(main_frame, text="Playlist URL:")
        url_label.pack(anchor=tk.W)

        self.url_entry = ttk.Entry(main_frame, width=70)
        self.url_entry.pack(fill=tk.X, pady=(5, 10))

        # Run button
        self.run_button = ttk.Button(main_frame, text="Run", command=self.run_extraction)
        self.run_button.pack(pady=(0, 10))

        # Status label
        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.pack(anchor=tk.W)

        # Results text area
        results_label = ttk.Label(main_frame, text="Extracted URLs:")
        results_label.pack(anchor=tk.W, pady=(10, 5))

        # Text area with scrollbar
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.results_text = tk.Text(text_frame, wrap=tk.NONE, height=20)
        scrollbar_y = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        scrollbar_x = ttk.Scrollbar(text_frame, orient=tk.HORIZONTAL, command=self.results_text.xview)
        self.results_text.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.results_text.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        # Copy button
        self.copy_button = ttk.Button(main_frame, text="Copy All", command=self.copy_to_clipboard)
        self.copy_button.pack(pady=(10, 0))

    def extract_playlist_id(self, url: str) -> str | None:
        patterns = [
            r"[?&]list=([a-zA-Z0-9_-]+)",
            r"playlist\?list=([a-zA-Z0-9_-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def run_extraction(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a playlist URL")
            return

        if not self.api_key:
            messagebox.showerror("Error", "YouTube API key not found in .env file")
            return

        playlist_id = self.extract_playlist_id(url)
        if not playlist_id:
            messagebox.showerror("Error", "Could not extract playlist ID from URL")
            return

        # Disable button and start extraction in thread
        self.run_button.config(state=tk.DISABLED)
        self.results_text.delete(1.0, tk.END)
        self.status_label.config(text="Fetching videos...")

        thread = threading.Thread(target=self.fetch_videos, args=(playlist_id,))
        thread.start()

    def fetch_videos(self, playlist_id: str):
        try:
            youtube = build("youtube", "v3", developerKey=self.api_key)
            video_urls = []
            next_page_token = None

            while True:
                request = youtube.playlistItems().list(
                    part="contentDetails",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                )
                response = request.execute()

                for item in response.get("items", []):
                    video_id = item["contentDetails"]["videoId"]
                    video_urls.append(f"https://www.youtube.com/watch?v={video_id}")

                # Update status
                self.root.after(0, lambda c=len(video_urls): self.status_label.config(
                    text=f"Fetching... {c} videos found"))

                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break

            # Update UI with results
            self.root.after(0, lambda: self.show_results(video_urls))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.run_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.status_label.config(text=""))

    def show_results(self, video_urls: list[str]):
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "\n".join(video_urls))
        self.status_label.config(text=f"Found {len(video_urls)} videos")
        self.run_button.config(state=tk.NORMAL)

    def copy_to_clipboard(self):
        content = self.results_text.get(1.0, tk.END).strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.status_label.config(text="Copied to clipboard!")


def main():
    root = tk.Tk()
    app = PlaylistExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
