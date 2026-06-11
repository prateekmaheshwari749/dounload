import json
from typing import Callable, List, Tuple, Dict, Optional
import customtkinter as ctk
from tkinter import filedialog
from audio_processor import parse_interval_line, format_seconds

class IntervalsPanel(ctk.CTkFrame):
    def __init__(
        self, 
        parent, 
        on_remove_waste_click: Callable[[List[Tuple[float, float]]], None],
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        
        self.on_remove_waste_click = on_remove_waste_click
        self.audio_duration = 0.0
        self.validated_intervals: List[Tuple[float, float]] = []
        
        # Grid layout
        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Left Side: Input & Actions
        self.left_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.left_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(15, 7), pady=15)
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(1, weight=1)
        
        self.input_lbl = ctk.CTkLabel(
            self.left_frame, 
            text="WASTE INTERVALS TO REMOVE", 
            font=ctk.CTkFont(family="Outfit", size=13, weight="bold")
        )
        self.input_lbl.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        # Interval text editor
        self.textbox = ctk.CTkTextbox(
            self.left_frame, 
            font=ctk.CTkFont(family="Consolas", size=12),
            border_width=1,
            border_color="#2D2D35"
        )
        self.textbox.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.textbox.bind("<KeyRelease>", self._debounce_validate)
        
        # JSON Save/Load Row
        self.json_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.json_frame.grid(row=2, column=0, sticky="ew", pady=5)
        self.json_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.load_json_btn = ctk.CTkButton(
            self.json_frame,
            text="📂  Load JSON",
            fg_color="#3A3A45",
            hover_color="#4F4F5A",
            command=self._load_intervals_json
        )
        self.load_json_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        self.save_json_btn = ctk.CTkButton(
            self.json_frame,
            text="💾  Save JSON",
            fg_color="#3A3A45",
            hover_color="#4F4F5A",
            command=self._save_intervals_json
        )
        self.save_json_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")
        
        # Right Side: Validation & Next Filename Display
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(7, 15), pady=15)
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(1, weight=1)
        
        self.status_lbl = ctk.CTkLabel(
            self.right_frame, 
            text="VALIDATION FEEDBACK", 
            font=ctk.CTkFont(family="Outfit", size=13, weight="bold")
        )
        self.status_lbl.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        # Scrollable validation feedback list
        self.feedback_frame = ctk.CTkScrollableFrame(
            self.right_frame, 
            fg_color="#1E1E24", 
            border_width=1, 
            border_color="#2D2D35",
            height=150
        )
        self.feedback_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        
        # Filename Display Frame
        self.filename_frame = ctk.CTkFrame(self.right_frame, fg_color="#1E1E24", border_width=1, border_color="#2D2D35")
        self.filename_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.filename_frame.grid_columnconfigure(0, weight=1)
        
        filename_title = ctk.CTkLabel(
            self.filename_frame,
            text="NEXT HINDI FILENAME",
            font=ctk.CTkFont(family="Outfit", size=9, weight="bold"),
            text_color="#6A6A75"
        )
        filename_title.pack(anchor="center", pady=(6, 2))
        
        self.next_file_lbl = ctk.CTkLabel(
            self.filename_frame,
            text="Scanning...",
            font=ctk.CTkFont(family="Outfit", size=14, weight="bold"),
            text_color="#00E5FF"
        )
        self.next_file_lbl.pack(anchor="center", pady=(0, 6))
        
        # Action Panel: Remove Waste Button
        self.action_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.action_frame.grid(row=3, column=0, sticky="ew")
        self.action_frame.grid_columnconfigure(0, weight=1)
        
        self.remove_btn = ctk.CTkButton(
            self.action_frame,
            text="🚫  Remove Waste",
            fg_color="#8D1F1F",
            hover_color="#701818",
            font=ctk.CTkFont(family="Outfit", size=13, weight="bold"),
            height=35,
            command=self._remove_clicked
        )
        self.remove_btn.grid(row=0, column=0, sticky="ew")
        
        self.validation_timer = None

    def set_audio_duration(self, duration: float):
        self.audio_duration = duration
        self.validate_intervals()

    def update_next_filename(self, filename: str):
        self.next_file_lbl.configure(text=filename)

    def _debounce_validate(self, event=None):
        if self.validation_timer:
            self.after_cancel(self.validation_timer)
        self.validation_timer = self.after(400, self.validate_intervals)

    def validate_intervals(self) -> bool:
        # Clear feedback
        for child in self.feedback_frame.winfo_children():
            child.destroy()
            
        raw_text = self.textbox.get("1.0", "end")
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        
        if not lines:
            empty_lbl = ctk.CTkLabel(
                self.feedback_frame, 
                text="No waste intervals entered yet.",
                font=ctk.CTkFont(family="Outfit", size=11, slant="italic"),
                text_color="#606065"
            )
            empty_lbl.pack(pady=15)
            self.validated_intervals = []
            return True
            
        valid_list = []
        all_valid = True
        
        for idx, line in enumerate(lines, 1):
            start, end, err = parse_interval_line(line)
            
            if not err and self.audio_duration > 0:
                if start >= self.audio_duration:
                    err = f"Start time exceeds audio duration ({format_seconds(self.audio_duration)})"
                elif end > self.audio_duration:
                    err = f"End time exceeds audio duration ({format_seconds(self.audio_duration)})"
            
            row = ctk.CTkFrame(self.feedback_frame, fg_color="transparent")
            row.pack(fill="x", pady=2, padx=5)
            
            if err:
                all_valid = False
                icon = "❌ "
                color = "#FF5555"
                desc = f"Line {idx}: {err}"
            else:
                icon = "✔ "
                color = "#50FA7B"
                desc = f"Line {idx}: {format_seconds(start)} ➜ {format_seconds(end)} (Remove {format_seconds(end - start)})"
                valid_list.append((start, end))
                
            lbl = ctk.CTkLabel(
                row, 
                text=f"{icon}{desc}", 
                text_color=color,
                font=ctk.CTkFont(family="Outfit", size=11),
                anchor="w",
                justify="left"
            )
            lbl.pack(fill="x")
            
        self.validated_intervals = valid_list
        return all_valid

    def _remove_clicked(self):
        if not self.validated_intervals:
            self.validate_intervals()
            
        if not self.validated_intervals:
            # Check if there is text but it's invalid
            raw_text = self.textbox.get("1.0", "end").strip()
            if raw_text:
                return  # don't run if user has input but it's completely invalid
            
        # Call the parent callback
        self.on_remove_waste_click(self.validated_intervals)

    def _load_intervals_json(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filepath:
            return
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            if not isinstance(data, list):
                raise ValueError("JSON must contain an array of intervals")
                
            lines = []
            for item in data:
                if 'start' in item and 'end' in item:
                    lines.append(f"{item['start']} -> {item['end']}")
                    
            self.textbox.delete("1.0", "end")
            self.textbox.insert("1.0", "\n".join(lines))
            self.validate_intervals()
        except Exception as e:
            self.textbox.delete("1.0", "end")
            self.textbox.insert("1.0", f"# Error loading JSON: {str(e)}")

    def _save_intervals_json(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if not filepath:
            return
            
        raw_text = self.textbox.get("1.0", "end")
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        
        json_data = []
        for line in lines:
            start, end, err = parse_interval_line(line)
            if not err:
                json_data.append({
                    "start": format_seconds(start),
                    "end": format_seconds(end)
                })
                
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2)
        except Exception:
            pass
