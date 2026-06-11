import argparse
import glob
import os
import shutil
import subprocess
import sys


def parse_args():
    parser = argparse.ArgumentParser(
        description='Use Demucs to isolate speech from podcast WAV files.'
    )
    parser.add_argument(
        'inputs', nargs='*',
        help='Input WAV file(s) or folders containing WAV files. If omitted, the current directory is used.'
    )
    parser.add_argument(
        '--output-dir', '-o', default='demucs_output',
        help='Directory to save Demucs-enhanced WAV files. Defaults to demucs_output/'
    )
    parser.add_argument(
        '--model', default='htdemucs',
        help='Demucs model name. Default: htdemucs'
    )
    parser.add_argument(
        '--device', default='cpu',
        help='Device to use for Demucs. Default: cpu'
    )
    parser.add_argument(
        '--jobs', '-j', type=int, default=1,
        help='Number of CPU jobs for Demucs. Default: 1'
    )
    return parser.parse_args()


def gather_wav_files(paths):
    if not paths:
        paths = [os.getcwd()]

    wav_files = []
    for path in paths:
        if os.path.isdir(path):
            wav_files.extend(sorted(glob.glob(os.path.join(path, '*.wav'))))
        elif os.path.isfile(path) and path.lower().endswith('.wav'):
            wav_files.append(path)
        else:
            raise ValueError(f'Invalid input path: {path}')

    return wav_files


def run_demucs(wav_files, output_dir, model, device, jobs):
    os.makedirs(output_dir, exist_ok=True)
    temp_dir = os.path.join(output_dir, 'temp_demucs')
    os.makedirs(temp_dir, exist_ok=True)

    command = [
        sys.executable,
        '-m',
        'demucs',
        '--two-stems',
        'vocals',
        '--name',
        model,
        '--device',
        device,
        '-j',
        str(jobs),
        '--out',
        temp_dir,
        '--filename',
        '{track}.{stem}.{ext}',
    ] + wav_files

    print('Running Demucs on:', ', '.join(os.path.basename(f) for f in wav_files))
    subprocess.check_call(command)

    moved_files = []
    for root, _, files in os.walk(temp_dir):
        for filename in files:
            if filename.endswith('.vocals.wav'):
                src = os.path.join(root, filename)
                track_name = filename[: -len('.vocals.wav')]
                dest_file = os.path.join(output_dir, f'{track_name}_demucs.wav')
                print(f'Moving {filename} -> {dest_file}')
                shutil.move(src, dest_file)
                moved_files.append(dest_file)

    shutil.rmtree(temp_dir, ignore_errors=True)
    return moved_files


def main():
    args = parse_args()
    wav_files = gather_wav_files(args.inputs)
    if not wav_files:
        raise SystemExit('No WAV files found to process.')

    output_files = run_demucs(wav_files, args.output_dir, args.model, args.device, args.jobs)
    print('\nDone. Demucs outputs saved to:')
    for path in output_files:
        print('  ', path)


if __name__ == '__main__':
    main()
