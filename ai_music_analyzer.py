import os
import re
from typing import Dict, Any, Optional
from audio_metadata import AudioMetadataExtractor
from analyzer import AudioAnalyzer
from filename_formatter import FilenameFormatter

class AIMusicAnalyzer:
    CLEAN_PATTERNS = [
        r'\[.*?(?:official|audio|video|mv|hd|4k|lyrics|m/v|visualizer|remastered|performance).*?\]',
        r'\(.*?\b(?:official|audio|video|mv|hd|4k|lyrics|m/v|visualizer|remastered|color coded|live|performance ver\.?|performance version)\b.*?\)',
        r'\b(?:official\s+(?:music\s+)?video|official\s+audio|lyric\s+video|music\s+video|m/v|mv)\b',
        r'\b(?:hd|4k|1080p|hq)\b',
        r'【.*?】',
    ]

    GENERIC_CHANNELS = {
        "vevo", "topic", "records", "entertainment", "music", "official", "studio",
        "label", "channel", "tv", "sound", "media", "audio", "crew"
    }

    @classmethod
    def clean_title(cls, raw_title: str) -> str:
        cleaned = raw_title
        for pattern in cls.CLEAN_PATTERNS:
            cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        cleaned = cleaned.strip(" -_|~•·")
        return cleaned

    @classmethod
    def parse_artist_title_heuristic(cls, raw_title: str, uploader: Optional[str]) -> Dict[str, Any]:
        cleaned = cls.clean_title(raw_title)

        delimiters = [" - ", " – ", " — ", " : ", " | "]
        for d in delimiters:
            if d in cleaned:
                parts = cleaned.split(d, 1)
                left, right = parts[0].strip(), parts[1].strip()
                if left and right:
                    return {
                        "title": right,
                        "artist": left,
                        "confidence_title": 0.85,
                        "confidence_artist": 0.80,
                        "source": "title_delimeter_heuristic"
                    }

        if '"' in cleaned or "'" in cleaned:
            m = re.match(r'^(.*?)\s+["\'](.*?)["\']', cleaned)
            if m:
                left, right = m.group(1).strip(), m.group(2).strip()
                if left and right:
                    return {
                        "title": right,
                        "artist": left,
                        "confidence_title": 0.80,
                        "confidence_artist": 0.75,
                        "source": "title_quote_heuristic"
                    }

        title = cleaned or raw_title
        artist = None
        conf_artist = 0.30

        if uploader:
            u_clean = uploader.strip()
            u_clean = re.sub(r'\s*-\s*topic$', '', u_clean, flags=re.IGNORECASE).strip()
            u_clean = re.sub(r'vevo$', '', u_clean, flags=re.IGNORECASE).strip()
            if u_clean and not any(gen in u_clean.lower() for gen in cls.GENERIC_CHANNELS):
                artist = u_clean
                conf_artist = 0.65

        return {
            "title": title,
            "artist": artist or "Unknown Artist",
            "confidence_title": 0.70,
            "confidence_artist": conf_artist,
            "source": "raw_fallback_heuristic"
        }

    @classmethod
    def analyze_audio_file(
        cls,
        file_path: str,
        raw_video_title: Optional[str] = None,
        uploader: Optional[str] = None
    ) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "error": "오디오 파일이 존재하지 않습니다."
            }

        meta = AudioMetadataExtractor.extract_metadata(file_path)

        final_title = None
        final_artist = None
        source_title = "unknown"
        source_artist = "unknown"
        conf_title = 0.5
        conf_artist = 0.5

        if meta.get("success") and meta.get("has_embedded_info"):
            if meta.get("title"):
                final_title = meta.get("title")
                source_title = "embedded_tag"
                conf_title = 0.95
            if meta.get("artist"):
                final_artist = meta.get("artist")
                source_artist = "embedded_tag"
                conf_artist = 0.95

        if not final_title or not final_artist:
            heuristic = cls.parse_artist_title_heuristic(
                raw_title=raw_video_title or os.path.basename(file_path),
                uploader=uploader
            )
            if not final_title:
                final_title = heuristic["title"]
                source_title = heuristic["source"]
                conf_title = heuristic["confidence_title"]
            if not final_artist or final_artist == "Unknown Artist":
                final_artist = heuristic["artist"]
                source_artist = heuristic["source"]
                conf_artist = heuristic["confidence_artist"]

        audio_res = AudioAnalyzer.analyze(file_path, max_seconds=25.0)
        bpm = audio_res.get("bpm")
        key = audio_res.get("key")
        duration = audio_res.get("duration", meta.get("duration", 0.0))

        _, ext = os.path.splitext(file_path)
        smart_filename = FilenameFormatter.format_smart_filename(
            title=final_title,
            artist=final_artist,
            bpm=bpm,
            key=key,
            extension=ext
        )

        return {
            "success": True,
            "file_path": file_path,
            "original_filename": os.path.basename(file_path),
            "suggested_filename": smart_filename,
            "title": final_title,
            "artist": final_artist,
            "bpm": bpm,
            "key": key,
            "duration": duration,
            "confidence": {
                "title": conf_title,
                "artist": conf_artist,
                "bpm": 0.90 if (bpm and bpm > 0) else 0.0,
                "key": 0.85 if key and key != "C Major" else 0.70
            },
            "sources": {
                "title": source_title,
                "artist": source_artist,
                "bpm": "audio_signal_autocorrelation",
                "key": "audio_signal_chromagram"
            }
        }