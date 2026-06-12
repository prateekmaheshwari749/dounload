import os
import re
import struct
import wave
import shutil
import threading
from typing import Callable, List, Dict, Tuple, Optional
from pydub import AudioSegment
import yt_dlp as youtube_dl

# Import options builder from wav_dounload
try:
    from wav_dounload import build_ydl_opts
except ImportError:
    # Fallback in case pathing is weird
    def build_ydl_opts():
        return {
            'format': 'bestaudio/best',
            'outtmpl': '%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'noplaylist': True,
            'retries': 10,
            'socket_timeout': 30,
            'http_chunk_size': 1048576,
            'no_warnings': True,
            'quiet': False,
        }

def check_ffmpeg() -> bool:
    """Check if ffmpeg is installed and available in the system path."""
    return shutil.which('ffmpeg') is not None

def parse_time_to_seconds(time_str: str) -> float:
    """Parse time string in H:MM:SS, MM:SS, or SS formats to float seconds."""
    time_str = time_str.strip()
    if not time_str:
        raise ValueError("Empty time string")
    
    parts = time_str.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    elif len(parts) == 1:
        return float(parts[0])
    else:
        raise ValueError(f"Invalid time format: {time_str}")

def format_seconds(seconds: float) -> str:
    """Format float seconds to HH:MM:SS or MM:SS format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    else:
        return f"{m:02d}:{s:02d}"

def parse_interval_line(line: str) -> Tuple[Optional[float], Optional[float], str]:
    """
    Parse a single interval line. Supports formats like:
    00:05:30 -> 00:10:00
    0:05:30,0:10:00
    Returns (start_sec, end_sec, error_message).
    """
    line = line.strip()
    if not line:
        return None, None, "Empty line"
    
    # Try splitting by '->', ',', or '-'
    parts = None
    for delim in [r'->', r',', r'-']:
        split_parts = re.split(delim, line)
        if len(split_parts) == 2:
            parts = split_parts
            break
            
    if not parts:
        # Try whitespace split
        split_parts = re.split(r'\s+', line)
        if len(split_parts) == 2:
            parts = split_parts
            
    if not parts or len(parts) != 2:
        return None, None, "Invalid format. Use 'start -> end' or 'start,end'"
        
    start_str, end_str = parts[0].strip(), parts[1].strip()
    
    try:
        start_sec = parse_time_to_seconds(start_str)
    except Exception:
        return None, None, f"Invalid start time: '{start_str}'"
        
    try:
        end_sec = parse_time_to_seconds(end_str)
    except Exception:
        return None, None, f"Invalid end time: '{end_str}'"
        
    if start_sec < 0 or end_sec < 0:
        return None, None, "Times cannot be negative"
        
    if start_sec >= end_sec:
        return start_sec, end_sec, "Start time must be less than end time"
        
    return start_sec, end_sec, ""

class AudioProcessor:
    def __init__(self):
        self.current_download_thread: Optional[threading.Thread] = None
        self.current_process_thread: Optional[threading.Thread] = None
        
    def download_youtube_audio(
        self, 
        url: str, 
        output_dir: str, 
        progress_callback: Callable[[float], None], 
        log_callback: Callable[[str], None],
        completion_callback: Callable[[Optional[str], Optional[str]], None]
    ) -> None:
        """
        Downloads audio in a background thread.
        Calls completion_callback(wav_path, error_message) when done.
        """
        def _download_task():
            if not check_ffmpeg():
                log_callback("[WARNING] FFmpeg was not found in system PATH. Download conversion may fail!")
            
            try:
                log_callback(f"[INFO] Initializing download for: {url}")
                opts = build_ydl_opts()
                
                # Make sure output directory exists
                os.makedirs(output_dir, exist_ok=True)
                
                # Update outtmpl to point to the output directory
                opts['outtmpl'] = os.path.join(output_dir, '%(title)s.%(ext)s')
                
                # Progress Hook for yt-dlp
                def ydl_hook(d):
                    if d['status'] == 'downloading':
                        total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                        downloaded = d.get('downloaded_bytes', 0)
                        if total > 0:
                            pct = downloaded / total
                            progress_callback(pct)
                            speed = d.get('speed', 0)
                            speed_str = f"{speed / 1024 / 1024:.2f} MB/s" if speed else "unknown"
                            log_callback(f"[INFO] Downloading... {downloaded / 1024 / 1024:.1f}MB / {total / 1024 / 1024:.1f}MB ({speed_str})")
                        else:
                            log_callback(f"[INFO] Downloading... {downloaded / 1024 / 1024:.1f}MB (size unknown)")
                    elif d['status'] == 'finished':
                        log_callback("[INFO] Audio download finished. Converting to WAV...")
                        progress_callback(0.95)
                
                opts['progress_hooks'] = [ydl_hook]
                
                # Download audio
                with youtube_dl.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    raw_filename = ydl.prepare_filename(info)
                    
                    # The downloader postprocessor changes extension to wav
                    wav_path = os.path.splitext(raw_filename)[0] + '.wav'
                    
                    if os.path.exists(wav_path):
                        log_callback(f"[SUCCESS] Download & conversion complete: {os.path.basename(wav_path)}")
                        progress_callback(1.0)
                        completion_callback(wav_path, None)
                    else:
                        # Sometimes ydl prepends directory or changes format
                        # Let's search for any .wav files created recently in output_dir
                        log_callback("[WARNING] Checking alternative output locations...")
                        name_no_ext = os.path.splitext(os.path.basename(raw_filename))[0]
                        potential_wav = os.path.join(output_dir, f"{name_no_ext}.wav")
                        if os.path.exists(potential_wav):
                            log_callback(f"[SUCCESS] WAV file found: {os.path.basename(potential_wav)}")
                            progress_callback(1.0)
                            completion_callback(potential_wav, None)
                        else:
                            # Search in current directory too just in case
                            local_wav = f"{name_no_ext}.wav"
                            if os.path.exists(local_wav):
                                # Move to output_dir
                                final_dest = os.path.join(output_dir, local_wav)
                                shutil.move(local_wav, final_dest)
                                log_callback(f"[SUCCESS] WAV file moved to outputs: {os.path.basename(final_dest)}")
                                progress_callback(1.0)
                                completion_callback(final_dest, None)
                            else:
                                raise FileNotFoundError("Could not find the extracted WAV file.")
                                
            except Exception as e:
                log_callback(f"[ERROR] Download failed: {str(e)}")
                progress_callback(0.0)
                completion_callback(None, str(e))
                
        self.current_download_thread = threading.Thread(target=_download_task, daemon=True)
        self.current_download_thread.start()

    def get_wav_metadata(self, file_path: str) -> Dict:
        """Extract metadata details from a WAV file using the wave module."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        with wave.open(file_path, 'rb') as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            n_frames = wav_file.getnframes()
            duration = n_frames / float(sample_rate)
            
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        channels_str = "Mono" if channels == 1 else ("Stereo" if channels == 2 else f"{channels} channels")
        
        return {
            'filename': os.path.basename(file_path),
            'filepath': file_path,
            'duration': duration,
            'sample_rate': f"{sample_rate / 1000:.1f} kHz",
            'channels': channels_str,
            'file_size': f"{file_size_mb:.2f} MB"
        }

    def extract_waveform_points(self, file_path: str, num_points: int = 800) -> List[float]:
        """
        Downsamples WAV file to a list of normalized peak amplitudes.
        Highly memory-efficient and fast (doesn't read the whole file at once).
        """
        if not os.path.exists(file_path):
            return [0.0] * num_points
            
        try:
            with wave.open(file_path, 'rb') as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                n_frames = wav_file.getnframes()
                
                if n_frames == 0:
                    return [0.0] * num_points
                
                block_size = max(1, n_frames // num_points)
                peaks = []
                
                for i in range(num_points):
                    pos = min(n_frames - 1, i * block_size)
                    wav_file.setpos(pos)
                    
                    # Read a small chunk of frames
                    frames_to_read = min(block_size, 1024)
                    data = wav_file.readframes(frames_to_read)
                    if not data:
                        peaks.append(0.0)
                        continue
                        
                    # Unpack raw byte buffer to integer samples
                    if sample_width == 2:  # 16-bit PCM
                        fmt = f"<{len(data)//2}h"
                        samples = struct.unpack(fmt, data)
                    elif sample_width == 1:  # 8-bit PCM
                        fmt = f"<{len(data)}B"
                        samples = [s - 128 for s in struct.unpack(fmt, data)]
                    elif sample_width == 4:  # 32-bit PCM
                        fmt = f"<{len(data)//4}i"
                        samples = struct.unpack(fmt, data)
                    else:
                        samples = [0]
                        
                    if samples:
                        # Absolute amplitude peak in this window
                        peak = max(abs(s) for s in samples)
                        peaks.append(float(peak))
                    else:
                        peaks.append(0.0)
                        
            # Normalize to [0.0, 1.0] range
            max_peak = max(peaks) if peaks else 0
            if max_peak > 0:
                peaks = [p / max_peak for p in peaks]
            else:
                peaks = [0.0] * num_points
            return peaks
        except Exception:
            return [0.0] * num_points

    def cut_intervals_async(
        self,
        audio_path: str,
        intervals: List[Tuple[float, float]],
        output_dir: str,
        log_callback: Callable[[str], None],
        progress_callback: Callable[[float], None],
        completion_callback: Callable[[List[str], Optional[str]], None]
    ) -> None:
        """Splits audio into custom intervals in a background thread."""
        def _cut_task():
            try:
                os.makedirs(output_dir, exist_ok=True)
                log_callback(f"[INFO] Loading audio segment: {os.path.basename(audio_path)}")
                
                # Load WAV using pydub
                audio = AudioSegment.from_wav(audio_path)
                log_callback("[INFO] Audio loaded successfully. Starting extraction...")
                
                generated_files = []
                total = len(intervals)
                
                for idx, (start_sec, end_sec) in enumerate(intervals, 1):
                    # Precise millisecond conversion
                    start_ms = int(start_sec * 1000)
                    end_ms = int(end_sec * 1000)
                    
                    segment = audio[start_ms:end_ms]
                    out_name = f"segment_{idx:03d}.wav"
                    out_path = os.path.join(output_dir, out_name)
                    
                    log_callback(f"[INFO] Slicing: {format_seconds(start_sec)} -> {format_seconds(end_sec)}")
                    segment.export(out_path, format="wav")
                    log_callback(f"[SUCCESS] Segment {idx}/{total} exported: {out_name}")
                    
                    generated_files.append(out_path)
                    progress_callback(idx / total)
                    
                completion_callback(generated_files, None)
            except Exception as e:
                log_callback(f"[ERROR] Extraction failed: {str(e)}")
                completion_callback([], str(e))
                
        self.current_process_thread = threading.Thread(target=_cut_task, daemon=True)
        self.current_process_thread.start()

    def split_chunks_async(
        self,
        audio_path: str,
        chunk_duration_min: float,
        output_dir: str,
        log_callback: Callable[[str], None],
        progress_callback: Callable[[float], None],
        completion_callback: Callable[[List[str], Optional[str]], None]
    ) -> None:
        """Splits audio into fixed duration chunks in a background thread."""
        def _split_task():
            try:
                os.makedirs(output_dir, exist_ok=True)
                log_callback(f"[INFO] Loading audio segment: {os.path.basename(audio_path)}")
                
                # Load WAV
                audio = AudioSegment.from_wav(audio_path)
                total_duration_ms = len(audio)
                
                chunk_ms = int(chunk_duration_min * 60 * 1000)
                num_chunks = (total_duration_ms + chunk_ms - 1) // chunk_ms
                
                log_callback(f"[INFO] Splitting into {num_chunks} chunks of {chunk_duration_min} minutes...")
                
                generated_files = []
                for i in range(num_chunks):
                    start_ms = i * chunk_ms
                    end_ms = min((i + 1) * chunk_ms, total_duration_ms)
                    
                    segment = audio[start_ms:end_ms]
                    out_name = f"chunk_{i+1:03d}.wav"
                    out_path = os.path.join(output_dir, out_name)
                    
                    log_callback(f"[INFO] Exporting chunk {i+1}/{num_chunks}: {out_name}")
                    segment.export(out_path, format="wav")
                    log_callback(f"[SUCCESS] Chunk {i+1} exported: {out_name}")
                    
                    generated_files.append(out_path)
                    progress_callback((i + 1) / num_chunks)
                    
                completion_callback(generated_files, None)
            except Exception as e:
                log_callback(f"[ERROR] Splitting failed: {str(e)}")
                completion_callback([], str(e))
                
        self.current_process_thread = threading.Thread(target=_split_task, daemon=True)
        self.current_process_thread.start()

    def remove_waste_and_split_pipeline_async(
        self,
        audio_path: str,
        waste_intervals: List[Tuple[float, float]],
        cleaned_folder: str,
        split_folder: str,
        splitting_script_path: str,
        log_callback: Callable[[str], None],
        progress_callback: Callable[[float], None],
        completion_callback: Callable[[Optional[str], int, Optional[str]], None]
    ) -> None:
        """
        Runs the full automated pipeline:
        1. Slices out waste intervals and merges remaining parts.
        2. Auto-detects the next HindiXX.wav filename.
        3. Saves cleaned file to cleaned_folder.
        4. Runs splitting.py on that file to segment it.
        5. Saves split files in split_folder.
        """
        def _pipeline_task():
            try:
                # 1. LOAD AUDIO AND CUT WASTE
                log_callback(f"[INFO] Loading original audio file: {os.path.basename(audio_path)}")
                audio = AudioSegment.from_wav(audio_path)
                total_duration_ms = len(audio)
                
                # Merge overlapping waste intervals
                merged_waste = []
                if waste_intervals:
                    sorted_waste = sorted(waste_intervals, key=lambda x: x[0])
                    merged_waste = [sorted_waste[0]]
                    for curr in sorted_waste[1:]:
                        prev_start, prev_end = merged_waste[-1]
                        curr_start, curr_end = curr
                        if curr_start <= prev_end:
                            merged_waste[-1] = (prev_start, max(prev_end, curr_end))
                        else:
                            merged_waste.append(curr)
                            
                # Calculate complement (good segments)
                good_segments = []
                last_end_ms = 0
                for start_sec, end_sec in merged_waste:
                    start_ms = int(start_sec * 1000)
                    end_ms = int(end_sec * 1000)
                    
                    if start_ms > last_end_ms:
                        good_segments.append((last_end_ms, start_ms))
                    last_end_ms = end_ms
                    
                if last_end_ms < total_duration_ms:
                    good_segments.append((last_end_ms, total_duration_ms))
                    
                if not good_segments:
                    raise ValueError("All audio has been marked as waste! Cannot clean.")
                    
                log_callback(f"[INFO] Removing {len(merged_waste)} waste intervals...")
                cleaned_audio = AudioSegment.empty()
                total_parts = len(good_segments)
                for idx, (start_ms, end_ms) in enumerate(good_segments, 1):
                    cleaned_audio += audio[start_ms:end_ms]
                    progress_callback(0.1 + 0.3 * (idx / total_parts))
                    
                # 2. DETERMINE NEXT FILENAME
                os.makedirs(cleaned_folder, exist_ok=True)
                next_filename = get_next_hindi_filename(cleaned_folder)
                cleaned_filepath = os.path.join(cleaned_folder, next_filename)
                
                log_callback(f"[INFO] Next file determined: {next_filename}")
                
                # 3. SAVE CLEANED AUDIO
                log_callback(f"[INFO] Exporting cleaned audio to: {cleaned_filepath}...")
                cleaned_audio.export(cleaned_filepath, format="wav")
                log_callback(f"[SUCCESS] Cleaned file saved successfully.")
                progress_callback(0.5)
                
                # 4. EXECUTE SPLITTING SCRIPT
                log_callback(f"[INFO] Invoking splitting script splitting.py on {next_filename}...")
                
                if not os.path.exists(splitting_script_path):
                    raise FileNotFoundError(f"Splitting script splitting.py not found at: {splitting_script_path}")
                    
                # Execute splitting.py dynamically for only the new file
                import re
                with open(splitting_script_path, "r", encoding="utf-8") as f:
                    script_code = f.read()
                    
                # Replace INPUT_FOLDER and OUTPUT_FOLDER assignments dynamically (escaping backslashes for regex)
                cleaned_folder_esc = os.path.normpath(cleaned_folder).replace('\\', '\\\\')
                split_folder_esc = os.path.normpath(split_folder).replace('\\', '\\\\')
                script_code = re.sub(r'INPUT_FOLDER\s*=.*', f'INPUT_FOLDER = r"{cleaned_folder_esc}"', script_code)
                script_code = re.sub(r'OUTPUT_FOLDER\s*=.*', f'OUTPUT_FOLDER = r"{split_folder_esc}"', script_code)
                
                # Strip import statements so it doesn't overwrite MockOS or standard modules inside exec context
                script_code = re.sub(r'\bimport os\b', '', script_code)
                script_code = re.sub(r'\bimport subprocess\b', '', script_code)
                
                # Create a Mock os module to intercept listdir, so it only splits our newly generated file
                class MockOS:
                    def __init__(self):
                        for name in dir(os):
                            try:
                                setattr(self, name, getattr(os, name))
                            except Exception:
                                pass
                    def listdir(self, path):
                        return [next_filename]
                    def makedirs(self, name, mode=511, exist_ok=False):
                        return os.makedirs(name, mode=mode, exist_ok=exist_ok)
                
                import subprocess
                globals_dict = {
                    '__builtins__': __builtins__,
                    'os': MockOS(),
                    'subprocess': subprocess,
                }
                
                exec(script_code, globals_dict)
                log_callback(f"[SUCCESS] Splitting completed.")
                progress_callback(0.9)
                
                # Count split files generated
                name_no_ext = os.path.splitext(next_filename)[0]
                import glob
                split_pattern = os.path.join(split_folder, f"{name_no_ext}_part_*.wav")
                created_split_files = glob.glob(split_pattern)
                num_splits = len(created_split_files)
                
                log_callback(f"[SUCCESS] Created {num_splits} split segment files in {split_folder}.")
                progress_callback(1.0)
                
                completion_callback(next_filename, num_splits, None)
                
            except Exception as e:
                log_callback(f"[ERROR] Pipeline execution failed: {str(e)}")
                completion_callback(None, 0, str(e))
                
        self.current_process_thread = threading.Thread(target=_pipeline_task, daemon=True)
        self.current_process_thread.start()


def get_next_hindi_filename(folder_path: str) -> str:
    import re
    if not os.path.exists(folder_path):
        os.makedirs(folder_path, exist_ok=True)
        return "Hindi12.wav"
        
    highest_num = 11
    pattern = re.compile(r"^Hindi(\d+)\.wav$", re.IGNORECASE)
    for filename in os.listdir(folder_path):
        match = pattern.match(filename)
        if match:
            num = int(match.group(1))
            if num > highest_num:
                highest_num = num
                
    next_num = highest_num + 1
    return f"Hindi{next_num}.wav"
