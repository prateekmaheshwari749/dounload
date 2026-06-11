import os
import tkinter as tk
import customtkinter as ctk
from typing import Callable, List, Optional
from audio_processor import format_seconds

class WaveformCanvas(tk.Canvas):
    def __init__(self, parent, on_seek: Callable[[float], None], **kwargs):
        # We use a standard tkinter.Canvas but styled to fit CustomTkinter dark theme
        super().__init__(
            parent, 
            bg="#121216", 
            highlightthickness=1, 
            highlightbackground="#2D2D35", 
            cursor="hand2",
            **kwargs
        )
        self.on_seek = on_seek
        self.waveform_data: List[float] = []
        self.duration = 0.0
        self.current_time = 0.0
        
        self.bind("<Configure>", self._on_resize)
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_click)  # Allow dragging to seek

    def set_data(self, data: List[float], duration: float):
        self.waveform_data = data
        self.duration = duration
        self.current_time = 0.0
        self.redraw()

    def set_playback_position(self, current_time: float):
        self.current_time = max(0.0, min(current_time, self.duration))
        self.redraw()

    def _on_resize(self, event):
        self.redraw()

    def _on_click(self, event):
        if self.duration <= 0:
            return
        width = self.winfo_width()
        x = max(0, min(event.x, width))
        seek_pct = x / width
        target_time = seek_pct * self.duration
        self.on_seek(target_time)

    def redraw(self):
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        
        if width <= 1 or height <= 1:
            return
            
        # Draw background grid lines (subtle)
        grid_color = "#1E1E24"
        for i in range(1, 10):
            x = (i / 10) * width
            self.create_line(x, 0, x, height, fill=grid_color, dash=(2, 4))
            
        self.create_line(0, height // 2, width, height // 2, fill="#25252D")
        
        if not self.waveform_data:
            # Draw a placeholder line
            self.create_text(
                width // 2, 
                height // 2, 
                text="No Audio File Loaded", 
                fill="#555560", 
                font=("Outfit", 12)
            )
            return

        num_points = len(self.waveform_data)
        bar_width = max(1, width // num_points)
        spacing = 1  # px spacing between bars
        
        # Calculate playback percentage index
        play_pct = self.current_time / self.duration if self.duration > 0 else 0.0
        play_index = int(play_pct * num_points)
        
        center_y = height / 2
        max_h = (height - 20) / 2
        
        for idx in range(num_points):
            x = (idx / num_points) * width
            val = self.waveform_data[idx]
            
            # Amplitude height
            h = max(2.0, val * max_h)
            
            # Highlight parts that are already played
            if idx <= play_index:
                color = "#00E5FF" # Vibrant glowing cyan for active playback
            else:
                color = "#3E3E4C" # Slate dark grey for inactive parts
                
            self.create_line(x, center_y - h, x, center_y + h, fill=color, width=bar_width)

        # Draw red playback cursor line
        cursor_x = play_pct * width
        self.create_line(cursor_x, 0, cursor_x, height, fill="#FF5555", width=2)
        # Cursor handle at the top
        self.create_polygon(
            cursor_x - 5, 0,
            cursor_x + 5, 0,
            cursor_x, 8,
            fill="#FF5555"
        )


class PlayerPanel(ctk.CTkFrame):
    def __init__(
        self, 
        parent, 
        on_play_click: Callable[[], None],
        on_pause_click: Callable[[], None],
        on_stop_click: Callable[[], None],
        on_seek: Callable[[float], None],
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.on_play = on_play_click
        self.on_pause = on_pause_click
        self.on_stop = on_stop_click
        self.on_seek = on_seek
        
        self.duration = 0.0
        
        # Configuration
        self.grid_columnconfigure(0, weight=1)
        
        # METADATA PANEL (TOP)
        self.meta_frame = ctk.CTkFrame(self, fg_color="#1E1E24", border_width=1, border_color="#2D2D35")
        self.meta_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        self.meta_frame.grid_columnconfigure((0,1,2,3), weight=1)
        
        # Metadata values labels
        self.meta_filename_lbl = self._create_meta_item(self.meta_frame, "File Name", "-", 0, 0, colspan=4)
        self.meta_duration_lbl = self._create_meta_item(self.meta_frame, "Duration", "00:00", 1, 0)
        self.meta_rate_lbl = self._create_meta_item(self.meta_frame, "Sample Rate", "-", 1, 1)
        self.meta_channels_lbl = self._create_meta_item(self.meta_frame, "Channels", "-", 1, 2)
        self.meta_size_lbl = self._create_meta_item(self.meta_frame, "File Size", "-", 1, 3)
        
        # WAVEFORM PANEL (MIDDLE)
        self.wave_label = ctk.CTkLabel(
            self, 
            text="WAVEFORM VISUALIZER & TRACKER", 
            font=ctk.CTkFont(family="Outfit", size=13, weight="bold")
        )
        self.wave_label.grid(row=1, column=0, sticky="w", padx=15, pady=(5, 5))
        
        self.waveform_canvas = WaveformCanvas(self, on_seek=self.on_seek, height=130)
        self.waveform_canvas.grid(row=2, column=0, sticky="ew", padx=15, pady=5)
        
        # TIME TRACKER INDICATOR ROW
        self.time_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.time_frame.grid(row=3, column=0, sticky="ew", padx=15, pady=2)
        self.time_frame.grid_columnconfigure(1, weight=1)
        
        self.curr_time_lbl = ctk.CTkLabel(
            self.time_frame, 
            text="00:00", 
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color="#00E5FF"
        )
        self.curr_time_lbl.pack(side="left")
        
        self.total_time_lbl = ctk.CTkLabel(
            self.time_frame, 
            text="/ 00:00", 
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color="#A0A0A5"
        )
        self.total_time_lbl.pack(side="left", padx=5)
        
        # CONTROLS ROW (BOTTOM)
        self.controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.controls_frame.grid(row=4, column=0, sticky="ew", padx=15, pady=(10, 15))
        self.controls_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.play_btn = ctk.CTkButton(
            self.controls_frame,
            text="▶  Play",
            fg_color="#1F538D",
            hover_color="#184370",
            font=ctk.CTkFont(family="Outfit", size=12, weight="bold"),
            height=35,
            command=self.on_play
        )
        self.play_btn.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.pause_btn = ctk.CTkButton(
            self.controls_frame,
            text="⏸  Pause",
            fg_color="#3A3A45",
            hover_color="#4F4F5A",
            font=ctk.CTkFont(family="Outfit", size=12, weight="bold"),
            height=35,
            command=self.on_pause
        )
        self.controls_frame.grid_columnconfigure(1, weight=1)
        self.pause_btn.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.stop_btn = ctk.CTkButton(
            self.controls_frame,
            text="⏹  Stop",
            fg_color="#5E3030",
            hover_color="#7D3E3E",
            font=ctk.CTkFont(family="Outfit", size=12, weight="bold"),
            height=35,
            command=self.on_stop
        )
        self.stop_btn.grid(row=0, column=2, padx=5, sticky="ew")

    def _create_meta_item(self, parent, label_text: str, value_text: str, row: int, col: int, colspan: int = 1) -> ctk.CTkLabel:
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.grid(row=row, column=col, columnspan=colspan, sticky="w", padx=12, pady=6)
        
        lbl = ctk.CTkLabel(
            container, 
            text=label_text.upper(), 
            font=ctk.CTkFont(family="Outfit", size=9, weight="bold"),
            text_color="#6A6A75"
        )
        lbl.pack(anchor="w")
        
        val = ctk.CTkLabel(
            container, 
            text=value_text, 
            font=ctk.CTkFont(family="Outfit", size=12, weight="bold"),
            text_color="#C8C8CD"
        )
        val.pack(anchor="w")
        return val

    def load_audio(self, metadata: dict, waveform_data: List[float]):
        self.duration = metadata['duration']
        
        # Set Metadata
        self.meta_filename_lbl.configure(text=metadata['filename'])
        self.meta_duration_lbl.configure(text=format_seconds(self.duration))
        self.meta_rate_lbl.configure(text=metadata['sample_rate'])
        self.meta_channels_lbl.configure(text=metadata['channels'])
        self.meta_size_lbl.configure(text=metadata['file_size'])
        
        # Set waveform data
        self.waveform_canvas.set_data(waveform_data, self.duration)
        
        # Set indicators
        self.curr_time_lbl.configure(text="00:00")
        self.total_time_lbl.configure(text=f"/ {format_seconds(self.duration)}")

    def update_playback(self, current_time: float):
        self.curr_time_lbl.configure(text=format_seconds(current_time))
        self.waveform_canvas.set_playback_position(current_time)
