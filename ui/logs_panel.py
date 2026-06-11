import os
import datetime
import customtkinter as ctk

class LogsPanel(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Title
        self.label = ctk.CTkLabel(
            self, 
            text="STATUS LOGS", 
            font=ctk.CTkFont(family="Outfit", size=13, weight="bold")
        )
        self.label.pack(anchor="w", padx=15, pady=(10, 5))
        
        # TextBox for scrolling logs
        self.textbox = ctk.CTkTextbox(
            self, 
            wrap="word", 
            state="disabled", 
            fg_color="#1E1E24", 
            text_color="#E0E0E6",
            font=ctk.CTkFont(family="Consolas", size=11),
            border_width=1,
            border_color="#2D2D35"
        )
        self.textbox.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Config tags for color code formatting
        self.textbox.tag_config("INFO", foreground="#A0A0A5")
        self.textbox.tag_config("SUCCESS", foreground="#50FA7B")  # Glowing green
        self.textbox.tag_config("WARNING", foreground="#FFB86C")  # Glowing orange
        self.textbox.tag_config("ERROR", foreground="#FF5555")    # Glowing red
        
        # Setup log folder
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        self.log_filepath = os.path.join(self.log_dir, f"log_{today}.txt")
        
        self.log(f"[INFO] Logging initialized. Log file: {self.log_filepath}")

    def log(self, message: str):
        # Extract tag
        tag = "INFO"
        if message.startswith("[SUCCESS]"):
            tag = "SUCCESS"
        elif message.startswith("[WARNING]"):
            tag = "WARNING"
        elif message.startswith("[ERROR]"):
            tag = "ERROR"
            
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        
        # Append to UI Textbox safely (using thread-safe methods if needed, but tkinter is single threaded.
        # However, since background threads call this, we should run it using a safe scheduler or direct call.
        # CustomTkinter's after queue makes sure it runs on UI thread)
        def _insert():
            self.textbox.configure(state="normal")
            self.textbox.insert("end", full_message + "\n", tag)
            self.textbox.configure(state="disabled")
            self.textbox.see("end")
            
        self.after(0, _insert)
        
        # Write to file
        try:
            with open(self.log_filepath, "a", encoding="utf-8") as f:
                f.write(full_message + "\n")
        except Exception:
            pass
            
    def clear(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
