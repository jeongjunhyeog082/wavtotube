import os
import re
import shutil
import numpy as np
import librosa
from yt_dlp import YoutubeDL
from yt_dlp.utils import MaxDownloadsReached

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Mac 환경 FFmpeg 경로 탐색
FFMPEG_PATH = shutil.which("ffmpeg")
if not FFMPEG_PATH:
    for p in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg"]:
        if os.path.exists(p):
            FFMPEG_PATH = p
            break

PITCH_CLASSES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

def estimate_key(y, sr):
    try:
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_avg = np.mean(chroma, axis=1)
        best_score = -np.inf
        best_key = "C Major"
        for i in range(12):
            rotated = np.roll(chroma_avg, -i)
            major_corr = np.corrcoef(rotated, MAJOR_PROFILE)[0, 1]
            minor_corr = np.corrcoef(rotated, MINOR_PROFILE)[0, 1]
            if major_corr > best_score:
                best_score = major_corr
                best_key = f"{PITCH_CLASSES[i]} Major"
            if minor_corr > best_score:
                best_score = minor_corr
                best_key = f"{PITCH_CLASSES[i]} Minor"
        return best_key
    except Exception:
        return "C Major"

def fast_analyze_audio(file_path):
    try:
        y, sr = librosa.load(file_path, sr=22050, duration=25)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = round(float(tempo[0] if isinstance(tempo, (list, np.ndarray)) else tempo), 1)
        key = estimate_key(y, sr)
        duration = round(librosa.get_duration(path=file_path), 1)
        return {"bpm": bpm, "key": key, "duration": duration}
    except Exception as e:
        return {"bpm": 120.0, "key": "C Major", "duration": 180.0}

def sanitize_filename(name):
    return re.sub(r'[\/*?:"<>|]', "", name).strip() or "track"

def download_audio_core(url: str, output_format: str = "mp3", is_playlist: bool = False):
    output_format = output_format.lower()
    if output_format not in ["mp3", "wav"]:
        output_format = "mp3"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s'),
        'noplaylist': not is_playlist,
        'playlistend': 5 if is_playlist else 1,
        # max_downloads 옵션 제거 (예외 충돌 방지)
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': output_format,
            'preferredquality': '320' if output_format == 'mp3' else None,
        }],
        'quiet': True,
        'no_warnings': True,
    }

    if FFMPEG_PATH:
        ydl_opts['ffmpeg_location'] = os.path.dirname(FFMPEG_PATH)

    results = []
    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
        except MaxDownloadsReached:
            pass

        entries = []
        if 'entries' in info and info['entries']:
            entries = info['entries']
        else:
            entries = [info]

        for item in entries:
            if not item:
                continue
            video_id = item.get('id')
            title = item.get('title', 'Unknown Title')
            uploader = item.get('uploader') or item.get('channel') or '아티스트'
            thumbnail = item.get('thumbnail')
            file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.{output_format}")

            # 파일 존재 여부 탐색
            if not os.path.exists(file_path):
                for ext in [output_format, 'm4a', 'webm', 'mp3', 'wav']:
                    chk = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")
                    if os.path.exists(chk):
                        file_path = chk
                        break

            if os.path.exists(file_path):
                analysis = fast_analyze_audio(file_path)
                results.append({
                    "id": video_id,
                    "title": title,
                    "artist": uploader,
                    "thumbnail": thumbnail,
                    "file_name": f"{sanitize_filename(title)}.{output_format}",
                    "file_path": file_path,
                    "format": output_format,
                    "bpm": analysis["bpm"],
                    "key": analysis["key"],
                    "duration": analysis["duration"]
                })

    return results

download_and_convert = download_audio_core