import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_best_device():
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


def run_demucs(wav_files, output_dir, model, device, jobs, shifts=1, overlap=0.0):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = output_dir / "temp_demucs"
    temp_dir.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "demucs",
        "--two-stems",
        "vocals",
        "--name",
        model,
        "--device",
        device,
        "-j",
        str(jobs),
        "--out",
        str(temp_dir),
        "--filename",
        "{track}.{stem}.{ext}",
    ] + wav_files
    # add shifts and overlap if requested
    if shifts and shifts > 1:
        command[command.index("--out") : command.index("--out")] = ["--shifts", str(shifts)]
    if overlap and overlap > 0.0:
        command[command.index("--out") : command.index("--out")] = ["--overlap", str(overlap)]

    print("Running Demucs on:", ", ".join(os.path.basename(f) for f in wav_files))
    subprocess.run(command, check=True)

    saved_files = []
    for root, _, files in os.walk(temp_dir):
        for filename in files:
            if filename.endswith(".vocals.wav"):
                src = Path(root) / filename
                base = filename[: -len(".vocals.wav")]
                dest = output_dir / f"{base}_clean.wav"
                print(f"Moving {src.name} -> {dest.name}")
                shutil.move(str(src), str(dest))
                saved_files.append(dest)

    shutil.rmtree(temp_dir, ignore_errors=True)
    return saved_files


def parse_args():
    parser = argparse.ArgumentParser(
        description="Isolate speaker voice from podcast WAV files using Demucs."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        default=[],
        help="Input WAV files or folders containing WAV files."
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="enhanced_output",
        help="Directory to save clean vocals."
    )
    parser.add_argument(
        "--model",
        default="htdemucs_ft",
        help="Demucs model name. Default: htdemucs_ft (stronger fine-tuned model)"
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Device to use: cuda or cpu. Defaults to auto detect."
    )
    parser.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=1,
        help="Number of CPU jobs for Demucs. Default: 1"
    )
    parser.add_argument(
        "--shifts",
        type=int,
        default=1,
        help="Number of Demucs shifts for improved separation (higher -> better, slower)."
    )
    parser.add_argument(
        "--overlap",
        type=float,
        default=0.0,
        help="Demucs overlap fraction (0.0-0.75). Small overlap can reduce artifacts."
    )
    return parser.parse_args()


def gather_wav_files(paths):
    if not paths:
        paths = [os.getcwd()]

    wav_files = []
    for path in paths:
        p = Path(path)
        if p.is_dir():
            wav_files.extend(sorted(str(x) for x in p.glob("*.wav")))
        elif p.is_file() and p.suffix.lower() == ".wav":
            wav_files.append(str(p))
        else:
            raise FileNotFoundError(f"Invalid input path: {path}")
    return wav_files


def main():
    args = parse_args()
    wav_files = gather_wav_files(args.inputs)
    if not wav_files:
        raise SystemExit("No WAV files found to process.")

    device = args.device or find_best_device()
    print(f"Using device: {device}")

    output_files = run_demucs(
        wav_files,
        args.output_dir,
        args.model,
        device,
        args.jobs,
        args.shifts,
        args.overlap,
    )

    print("\nDone. Clean vocals saved to:")
    for path in output_files:
        print("  ", path)


if __name__ == "__main__":
    main()
