import os
import pygame
import customtkinter as ctk
from tkinter import messagebox
from typing import List, Tuple, Optional

# Import panels
from ui.download_panel import DownloadPanel
from ui.player_panel import PlayerPanel
from ui.intervals_panel import IntervalsPanel
from ui.logs_panel import LogsPanel

# Import Backend
from audio_processor import AudioProcessor, format_seconds, get_next_hindi_filename

class AudioPlayer:
    """A wrapper for pygame mixer to handle non-blocking audio playback with seek/pause support."""
    def __init__(self):
        pygame.mixer.init()
        self.current_file: Optional[str] = None
        self.is_playing = False
        self.is_paused = False
        self.playback_start_offset = 0.0  # seconds
        self.duration = 0.0

    def load(self, file_path: str, duration: float):
        self.stop()
        self.current_file = file_path
        self.duration = duration
        pygame.mixer.music.load(file_path)

    def play(self, start_time: float = 0.0):
        if not self.current_file:
            return
        
        # In Pygame, we can start playback at a specific second offset
        # Note: start_time seeking works best with WAV files natively.
        pygame.mixer.music.play(start=start_time)
        self.playback_start_offset = start_time
        self.is_playing = True
        self.is_paused = False

    def pause(self):
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True

    def resume(self):
        if self.is_playing and self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False

    def stop(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.playback_start_offset = 0.0

    def get_current_position(self) -> float:
        if not self.is_playing:
            return 0.0

        # If music stopped playing and we are not paused, then playback finished
        if not pygame.mixer.music.get_busy() and not self.is_paused:
            self.is_playing = False
            return 0.0

        # get_pos returns milliseconds since play() was called
        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms < 0:
            return self.playback_start_offset

        current_pos = self.playback_start_offset + (pos_ms / 1000.0)
        return min(current_pos, self.duration)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure Main Window
        self.title("Techphotons Solution Pvt. Ltd. - YouTube Audio Dataset Downloader & Processor")
        self.geometry("1200x800")
        self.minsize(1100, 750)
        
        # Set Dark Mode Theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Initialize Backend & Player
        self.processor = AudioProcessor()
        self.player = AudioPlayer()
        
        self.current_wav_path: Optional[str] = None
        self.current_metadata: Optional[dict] = None
        self.is_playing_loop_running = False

        # Build UI layout
        self._build_ui()
        
        # Refresh filename label
        self.refresh_next_hindi_filename()
        
        self.logs_panel.log("[SUCCESS] Techphotons YouTube Audio Processor launched successfully.")

    def _build_ui(self):
        # 1. HEADER BRANDING PANEL
        header = ctk.CTkFrame(self, fg_color="#121216", height=60, corner_radius=0)
        header.pack(fill="x", side="top", ipady=2)
        
        logo_lbl = ctk.CTkLabel(
            header, 
            text="TECHPHOTONS SOLUTION PVT. LTD.", 
            font=ctk.CTkFont(family="Outfit", size=15, weight="bold"),
            text_color="#00E5FF"  # High-tech glowing cyan
        )
        logo_lbl.pack(side="left", padx=20, pady=10)
        
        version_lbl = ctk.CTkLabel(
            header,
            text="YouTube Audio Dataset Downloader & Processor v1.0",
            font=ctk.CTkFont(family="Outfit", size=11),
            text_color="#6C6C75"
        )
        version_lbl.pack(side="right", padx=20, pady=10)

        # Main Workspace Container (splits left/right)
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        main_container.grid_columnconfigure((0, 1), weight=1, uniform="group1")
        main_container.grid_rowconfigure(0, weight=1)

        # LEFT COLUMN (Downloads + Logs)
        left_col = ctk.CTkFrame(main_container, fg_color="transparent")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_col.grid_columnconfigure(0, weight=1)
        left_col.grid_rowconfigure(1, weight=1)

        # Download Panel
        self.download_panel = DownloadPanel(
            left_col, 
            on_download_click=self.handle_youtube_download,
            on_folder_change=self.handle_folder_change,
            on_file_select=self.handle_file_select,
            border_width=1,
            border_color="#2D2D35"
        )
        self.download_panel.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Logs Panel
        self.logs_panel = LogsPanel(
            left_col,
            border_width=1,
            border_color="#2D2D35"
        )
        self.logs_panel.grid(row=1, column=0, sticky="nsew", pady=(5, 0))

        # RIGHT COLUMN (Player + Slicing)
        right_col = ctk.CTkFrame(main_container, fg_color="transparent")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        right_col.grid_columnconfigure(0, weight=1)
        right_col.grid_rowconfigure(1, weight=1)

        # Audio Player Panel
        self.player_panel = PlayerPanel(
            right_col,
            on_play_click=self.handle_play,
            on_pause_click=self.handle_pause,
            on_stop_click=self.handle_stop,
            on_seek=self.handle_seek,
            border_width=1,
            border_color="#2D2D35"
        )
        self.player_panel.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        # Slicing/Intervals Panel
        self.intervals_panel = IntervalsPanel(
            right_col,
            on_remove_waste_click=self.handle_remove_waste_intervals,
            border_width=1,
            border_color="#2D2D35"
        )
        self.intervals_panel.grid(row=1, column=0, sticky="nsew", pady=(5, 0))

    # --- ACTION HANDLERS ---

    def handle_youtube_download(self, url: str):
        self.logs_panel.log(f"[INFO] Download requested: {url}")
        self.download_panel.set_download_progress(0.01, "Initializing...")
        
        output_dir = self.download_panel.output_dir
        
        def on_progress(pct):
            self.after(0, lambda: self.download_panel.set_download_progress(pct, f"Downloading... {int(pct*100)}%"))
            
        def on_log(msg):
            self.logs_panel.log(msg)
            
        def on_complete(wav_path, error_msg):
            def _ui_complete():
                if error_msg:
                    self.download_panel.set_download_progress(0.0, "Download failed")
                    messagebox.showerror("Download Error", f"Failed to download audio:\n{error_msg}")
                else:
                    self.download_panel.set_download_progress(1.0, "Completed")
                    self.download_panel.refresh_file_list()
                    if wav_path and os.path.exists(wav_path):
                        self.load_audio_file(wav_path)
            self.after(0, _ui_complete)
            
        self.processor.download_youtube_audio(
            url=url,
            output_dir=output_dir,
            progress_callback=on_progress,
            log_callback=on_log,
            completion_callback=on_complete
        )

    def handle_folder_change(self, new_dir: str):
        self.logs_panel.log(f"[INFO] Output folder changed to: {new_dir}")
        self.download_panel.refresh_file_list()

    def handle_file_select(self, filepath: str):
        self.logs_panel.log(f"[INFO] Selected audio file: {os.path.basename(filepath)}")
        self.load_audio_file(filepath)

    def load_audio_file(self, filepath: str):
        self.handle_stop()
        
        try:
            self.current_wav_path = filepath
            # Extract metadata
            self.current_metadata = self.processor.get_wav_metadata(filepath)
            
            # Extract Waveform Data
            self.logs_panel.log("[INFO] Extracting waveform peaks...")
            waveform_peaks = self.processor.extract_waveform_points(filepath)
            
            # Update UI Panels
            self.player_panel.load_audio(self.current_metadata, waveform_peaks)
            self.intervals_panel.set_audio_duration(self.current_metadata['duration'])
            
            # Load in Pygame Player
            self.player.load(filepath, self.current_metadata['duration'])
            
            self.logs_panel.log(f"[SUCCESS] Loaded audio file successfully: {self.current_metadata['filename']}")
        except Exception as e:
            self.logs_panel.log(f"[ERROR] Failed to load WAV file: {str(e)}")
            messagebox.showerror("File Load Error", f"Failed to load audio file:\n{str(e)}")

    # --- PLAYER METHODS ---

    def handle_play(self):
        if not self.current_wav_path:
            return
            
        if self.player.is_paused:
            self.logs_panel.log("[INFO] Resuming playback.")
            self.player.resume()
        else:
            self.logs_panel.log("[INFO] Playing audio from start.")
            self.player.play(0.0)
            
        self._start_playback_loop()

    def handle_pause(self):
        if self.player.is_playing and not self.player.is_paused:
            self.logs_panel.log("[INFO] Playback paused.")
            self.player.pause()

    def handle_stop(self):
        if self.player.is_playing:
            self.logs_panel.log("[INFO] Playback stopped.")
        self.player.stop()
        self.player_panel.update_playback(0.0)

    def handle_seek(self, target_time: float):
        if not self.current_wav_path:
            return
            
        self.logs_panel.log(f"[INFO] Seeking to {format_seconds(target_time)}.")
        self.player.play(target_time)
        self.player_panel.update_playback(target_time)
        self._start_playback_loop()

    def _start_playback_loop(self):
        if not self.is_playing_loop_running:
            self.is_playing_loop_running = True
            self._playback_loop()

    def _playback_loop(self):
        if self.player.is_playing:
            pos = self.player.get_current_position()
            self.player_panel.update_playback(pos)
            self.after(50, self._playback_loop)
        else:
            self.is_playing_loop_running = False
            self.player_panel.update_playback(0.0)

    # --- BATCH EXTRACT / DATASET MODES ---

    def refresh_next_hindi_filename(self):
        cleaned_folder = r"C:\Users\prate\Desktop\22hr hindi"
        next_name = get_next_hindi_filename(cleaned_folder)
        self.intervals_panel.update_next_filename(next_name)

    def handle_remove_waste_intervals(self, waste_intervals: List[Tuple[float, float]]):
        if not self.current_wav_path:
            messagebox.showwarning("No Audio File", "Please download or load a WAV file first!")
            return
            
        cleaned_folder = r"C:\Users\prate\Desktop\22hr hindi"
        split_folder = r"C:\Users\prate\Desktop\splitting\split_audio"
        splitting_script = os.path.abspath("splitting.py")
        
        self.logs_panel.log(f"[INFO] Starting clean pipeline, removing {len(waste_intervals)} waste intervals...")
        
        # Disable buttons to prevent duplicate runs
        self.intervals_panel.remove_btn.configure(state="disabled")
        
        def on_log(msg):
            self.logs_panel.log(msg)
            
        def on_progress(pct):
            pass
            
        def on_complete(cleaned_filename, split_files_created, error_msg):
            def _ui_complete():
                self.intervals_panel.remove_btn.configure(state="normal")
                self.download_panel.refresh_file_list()
                self.refresh_next_hindi_filename()
                
                if error_msg:
                    messagebox.showerror("Pipeline Error", f"Pipeline execution failed:\n{error_msg}")
                else:
                    success_msg = (
                        f"Cleaned File:\n{cleaned_filename}\n\n"
                        f"Split Files Created:\n{split_files_created}\n\n"
                        f"Output Folder:\n{split_folder}"
                    )
                    messagebox.showinfo("Success", success_msg)
            self.after(0, _ui_complete)

        self.processor.remove_waste_and_split_pipeline_async(
            audio_path=self.current_wav_path,
            waste_intervals=waste_intervals,
            cleaned_folder=cleaned_folder,
            split_folder=split_folder,
            splitting_script_path=splitting_script,
            log_callback=on_log,
            progress_callback=on_progress,
            completion_callback=on_complete
        )
