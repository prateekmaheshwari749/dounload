import argparse
import yt_dlp as youtube_dl


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


def parse_args():
    parser = argparse.ArgumentParser(description='Download YouTube audio to WAV.')
    parser.add_argument('url', nargs='?', help='YouTube video URL')
    return parser.parse_args()


def main():
    args = parse_args()
    video_url = args.url or input('Enter the YouTube video URL: ')

    with youtube_dl.YoutubeDL(build_ydl_opts()) as ydl:
        try:
            ydl.download([video_url])
            print('Downloaded to WAV format.')
        except youtube_dl.DownloadError as exc:
            print('Download failed:')
            print(exc)


if __name__ == '__main__':
    main()