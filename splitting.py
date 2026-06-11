import os
import subprocess

INPUT_FOLDER = r"C:\Users\prate\Desktop\22hr hindi"
OUTPUT_FOLDER = r"split_audio"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

CHUNK_DURATION = 20 * 60  # 20 minutes

for filename in os.listdir(INPUT_FOLDER):
    if filename.lower().endswith((".wav", ".mp3", ".flac", ".m4a")):

        print(f"Processing: {filename}")

        input_file = os.path.join(INPUT_FOLDER, filename)

        name, ext = os.path.splitext(filename)

        output_pattern = os.path.join(
            OUTPUT_FOLDER,
            f"{name}_part_%03d.wav"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_file,
            "-af",
            "silenceremove=start_periods=1:start_duration=0.3:start_threshold=-45dB",
            "-f", "segment",
            "-segment_time", str(CHUNK_DURATION),
            "-c:a", "pcm_s16le",
            output_pattern
        ]

        subprocess.run(cmd)

        print(f"Finished: {filename}")

print("All files split successfully!")