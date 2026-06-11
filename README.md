# Techphotons YouTube Audio Dataset Downloader & Processor

A professional, high-performance desktop application built using Python, CustomTkinter, Pygame, and Pydub for downloading and processing YouTube audio datasets. The software provides precise millisecond-level slicing, visual waveform navigation, automatic fixed-duration chunking, metadata inspections, and dataset generation statistics.

Developed for **Techphotons Solution Pvt. Ltd.**

---

## Folder Structure

```
project/
│
├── main.py                     # Entry point for the application
├── wav_dounload.py             # YouTube WAV Downloader (using yt-dlp)
├── audio_processor.py          # Processing engine (slicing, metadata, waveform extractor)
├── ui/                         # CustomTkinter UI Components
│   ├── __init__.py
│   ├── app.py                  # Main layout coordinator and state controller
│   ├── download_panel.py       # Sidebar downloader & folder explorer panel
│   ├── player_panel.py         # Waveform canvas visualizer, player & metadata panel
│   ├── intervals_panel.py      # Slicing input editor, validation & dataset splitter panel
│   └── logs_panel.py           # Real-time scrolling logging console panel
├── outputs/                    # Output directory for extracted segments (Auto-created)
├── logs/                       # Application runtime log files (Auto-created)
└── requirements.txt            # Package dependencies
```

---

## Features

1. **Modern High-Tech UI**
   * High-contrast dark mode design system with glowing cyber-cyan highlights.
   * Responsive split-column layout designed for 1080p and resizable monitors.
   * Continuous progress reporting bars and animated visual states.
2. **Integrated YouTube Downloader**
   * Utilizes the existing `wav_dounload.py` script parameters to fetch and convert streams to `.wav`.
   * Real-time progress percentage bar, download speeds, and status logs directly integrated into the UI.
3. **Interactive Audio Visualizer**
   * Dynamic waveform viewer displaying audio peaks using lightweight, fast downsampling.
   * Playback tracker line highlighting the active/played section in real-time.
   * Seek playback dynamically by clicking or dragging directly on the waveform.
4. **Non-Blocking Player Engine**
   * Multi-threaded engine featuring Play, Pause, and Stop controls.
   * Zero UI freezes during audio streaming or seeking.
   * Continuous playback time indicator (e.g. `00:15 / 02:40`).
5. **Multiple Interval Slicing (Batch Extraction)**
   * Enter unlimited slicing intervals in either format:
     * `00:05:30 -> 00:10:00` (HH:MM:SS)
     * `0:05:30,0:10:00`
   * Real-time parsing and validation: checks format rules, verifies `start < end`, blocks values exceeding total audio duration, and highlights errors.
   * Batch extracts all valid intervals as `segment_001.wav`, `segment_002.wav`, etc., to your chosen output folder.
6. **Dataset Mode (Fixed Chunk Splitting)**
   * Split the entire audio into fixed-duration chunks (in minutes) e.g., 20-minute segments.
   * Saves chunks automatically as `chunk_001.wav`, `chunk_002.wav`, etc.
7. **Dataset Statistics**
   * Displays generated segment count, total accumulated duration, and average segment length in real-time.
8. **JSON Export & Import**
   * Export the current interval list as standard JSON files.
   * Load JSON interval configuration lists to restore slicing templates.

---

## Installation Instructions

### Prerequisites
1. **Python 3.8 to 3.12** installed on your system.
2. **FFmpeg** installed (see instructions below).

### Step-by-Step Setup

1. **Clone or Open Project Directory**
   Ensure all project files are placed in the same folder:
   ```bash
   cd c:\Users\prate\Desktop\video_dounload
   ```

2. **Set Up Virtual Environment** (If not already active)
   ```powershell
   # Create virtual environment
   python -m venv .venv

   # Activate on Windows PowerShell
   .venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies**
   Install all required libraries using pip:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Application**
   ```bash
   python main.py
   ```

---

## FFmpeg Setup Instructions for Windows

Pydub and yt-dlp require **FFmpeg** to decode and convert audio streams to WAV. Follow these steps to install and set up FFmpeg:

### Step 1: Download FFmpeg
1. Go to the official build site: [gyan.dev FFmpeg builds](https://www.gyan.dev/ffmpeg/builds/).
2. Under **git essentials builds**, download the zip file: `ffmpeg-git-essentials.7z` or `ffmpeg-release-essentials.zip`.

### Step 2: Extract File
1. Extract the downloaded zip file.
2. Rename the extracted folder to `ffmpeg` and move it to a simple location, for example: `C:\ffmpeg`.
3. Inside `C:\ffmpeg`, you should see a folder named `bin` (which contains `ffmpeg.exe`, `ffplay.exe`, and `ffprobe.exe`).

### Step 3: Add FFmpeg to Windows Environment PATH
1. Press the **Windows Key** and search for **"Edit the system environment variables"**, then press Enter.
2. In the System Properties window, click the **"Environment Variables..."** button at the bottom.
3. Under **"System variables"** (lower table), scroll down to find the variable named **Path**, select it, and click **"Edit..."**.
4. In the Edit Environment Variable window, click **"New"** and add the path to the ffmpeg bin folder:
   ```text
   C:\ffmpeg\bin
   ```
5. Click **OK** on all windows to save and apply the changes.

### Step 4: Verify Installation
Open a **new** Command Prompt or PowerShell and type:
```bash
ffmpeg -version
```
If configured correctly, you should see FFmpeg version details outputted to the screen. Restart your application if it was open.

---

## Usage Guidelines

1. **Download YouTube Audio:**
   * Enter a valid YouTube video URL into the download box.
   * Click **Download**. The download log and progress bar will update.
   * Once finished, the WAV file will load automatically.

2. **Load Local Audio:**
   * Select your desired output folder using the **Browse** button.
   * Any `.wav` files inside the directory will populate the explorer tree at the bottom left.
   * Click on any filename to load it into the visualizer.

3. **Preview & Seek:**
   * Use **Play**, **Pause**, and **Stop** buttons to preview.
   * Click anywhere along the Waveform Canvas to jump to that timestamp instantly.
   * Drag your mouse across the canvas to seek fluidly.

4. **Interval Slicing:**
   * Type timestamps into the editor, e.g.:
     ```text
     00:01:00 -> 00:02:15
     00:03:40 -> 00:04:10
     ```
   * Slicing stats and validation highlights update automatically.
   * Click **Extract Segments** to run the slicer.

5. **Splitting into Fixed Chunks:**
   * Enter a duration in minutes in the chunk size box (e.g. `10`).
   * Click **Split Chunks** to process the entire audio file.
