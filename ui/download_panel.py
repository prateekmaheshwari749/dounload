import os
from typing import Callable, Optional
import customtkinter as ctk
from tkinter import filedialog

class DownloadPanel(ctk.CTkFrame):
    def __init__(
        self, 
        parent, 
        on_download_click: Callable[[str], None], 
        on_folder_change: Callable[[str], None],
        on_file_select: Callable[[str], None],
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.on_download_click = on_download_click
        self.on_folder_change = on_folder_change
        self.on_file_select = on_file_select
        
        self.output_dir = os.path.abspath("outputs")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        
        # Section 1: YouTube Downloader
        self.dl_label = ctk.CTkLabel(
            self, 
            text="YOUTUBE AUDIO DOWNLOAD", 
            font=ctk.CTkFont(family="Outfit", size=13, weight="bold")
        )
        self.dl_label.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        # URL Input Row
        self.url_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.url_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        self.url_frame.grid_columnconfigure(0, weight=1)
        
        self.url_entry = ctk.CTkEntry(
            self.url_frame, 
            placeholder_text="Enter YouTube Video URL...",
            height=35,
            border_color="#2D2D35"
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        self.download_btn = ctk.CTkButton(
            self.url_frame, 
            text="Download", 
            width=100, 
            height=35,
            fg_color="#1F538D",
            hover_color="#184370",
            font=ctk.CTkFont(family="Outfit", size=12, weight="bold"),
            command=self._download_clicked
        )
        self.download_btn.grid(row=0, column=1, sticky="e")
        
        # Download Progress
        self.progress_bar = ctk.CTkProgressBar(self, height=8, progress_color="#1F538D")
        self.progress_bar.grid(row=2, column=0, sticky="ew", padx=15, pady=(5, 2))
        self.progress_bar.set(0.0)
        
        self.progress_label = ctk.CTkLabel(
            self, 
            text="Ready to download", 
            font=ctk.CTkFont(family="Outfit", size=11),
            text_color="#808085"
        )
        self.progress_label.grid(row=3, column=0, sticky="w", padx=15, pady=(0, 15))
        
        # Section 2: Output Settings
        self.out_label = ctk.CTkLabel(
            self, 
            text="OUTPUT DIRECTORY", 
            font=ctk.CTkFont(family="Outfit", size=13, weight="bold")
        )
        self.out_label.grid(row=4, column=0, sticky="w", padx=15, pady=(5, 5))
        
        # Folder Select Row
        self.folder_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.folder_frame.grid(row=5, column=0, sticky="ew", padx=15, pady=5)
        self.folder_frame.grid_columnconfigure(0, weight=1)
        
        self.folder_entry = ctk.CTkEntry(
            self.folder_frame, 
            height=35,
            border_color="#2D2D35"
        )
        self.folder_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.folder_entry.insert(0, self.output_dir)
        self.folder_entry.configure(state="readonly")
        
        self.browse_btn = ctk.CTkButton(
            self.folder_frame, 
            text="Browse", 
            width=80, 
            height=35,
            fg_color="#3A3A45",
            hover_color="#4F4F5A",
            font=ctk.CTkFont(family="Outfit", size=12),
            command=self._browse_folder
        )
        self.browse_btn.grid(row=0, column=1, sticky="e")
        
        # Section 3: File Explorer (List generated/cached files)
        self.file_label = ctk.CTkLabel(
            self, 
            text="GENERATED & WAV FILES", 
            font=ctk.CTkFont(family="Outfit", size=13, weight="bold")
        )
        self.file_label.grid(row=6, column=0, sticky="w", padx=15, pady=(15, 5))
        
        self.explorer_frame = ctk.CTkScrollableFrame(
            self, 
            fg_color="#1E1E24", 
            border_width=1, 
            border_color="#2D2D35",
            height=200
        )
        self.explorer_frame.grid(row=7, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.grid_rowconfigure(7, weight=1)
        
        # Initial scan
        self.refresh_file_list()
        
    def _download_clicked(self):
        url = self.url_entry.get().strip()
        if url:
            self.on_download_click(url)
            
    def _browse_folder(self):
        dir_selected = filedialog.askdirectory(initialdir=self.output_dir)
        if dir_selected:
            self.output_dir = os.path.abspath(dir_selected)
            self.folder_entry.configure(state="normal")
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, self.output_dir)
            self.folder_entry.configure(state="readonly")
            self.on_folder_change(self.output_dir)
            self.refresh_file_list()
            
    def set_download_progress(self, progress: float, status_text: str):
        self.progress_bar.set(progress)
        self.progress_label.configure(text=status_text)
        
    def refresh_file_list(self):
        # Clear frame
        for child in self.explorer_frame.winfo_children():
            child.destroy()
            
        if not os.path.exists(self.output_dir):
            return
            
        try:
            files = sorted([f for f in os.listdir(self.output_dir) if f.lower().endswith(".wav")])
            if not files:
                empty_lbl = ctk.CTkLabel(
                    self.explorer_frame, 
                    text="No WAV files found in output directory.",
                    font=ctk.CTkFont(family="Outfit", size=11, slant="italic"),
                    text_color="#606065"
                )
                empty_lbl.pack(pady=20)
                return
                
            for filename in files:
                full_path = os.path.join(self.output_dir, filename)
                
                # File row container
                row = ctk.CTkFrame(self.explorer_frame, fg_color="transparent")
                row.pack(fill="x", pady=2, padx=2)
                
                # Selectable button representing the file
                btn = ctk.CTkButton(
                    row,
                    text=f"🎵  {filename}",
                    anchor="w",
                    fg_color="transparent",
                    text_color="#C8C8CD",
                    hover_color="#2D2D35",
                    font=ctk.CTkFont(family="Outfit", size=12),
                    height=28,
                    command=lambda path=full_path: self.on_file_select(path)
                )
                btn.pack(fill="x")
        except Exception as e:
            err_lbl = ctk.CTkLabel(
                self.explorer_frame, 
                text=f"Error listing files: {str(e)}", 
                text_color="#FF5555"
            )
            err_lbl.pack(pady=10)
