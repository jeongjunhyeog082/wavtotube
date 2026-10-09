import os
import re
from typing import Optional

class FilenameFormatter:
    INVALID_CHARS_REGEX = re.compile(r'[/\\:*?"<>|]')

    @classmethod
    def sanitize(cls, text: str) -> str:
        if not text:
            return ""
        cleaned = re.sub(r'\.\.+', ' ', text)
        cleaned = cls.INVALID_CHARS_REGEX.sub(" ", cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.strip()

    @classmethod
    def format_smart_filename(
        cls,
        title: Optional[str],
        artist: Optional[str],
        bpm: Optional[float],
        key: Optional[str],
        extension: str,
        include_unknown: bool = False
    ) -> str:
        ext = extension.lstrip(".").lower()
        if not ext:
            ext = "mp3"

        parts = []

        clean_title = cls.sanitize(title) if title else ""
        if clean_title:
            if clean_title.lower().endswith(f".{ext}"):
                clean_title = clean_title[:-len(ext)-1].strip()
            parts.append(clean_title)
        elif include_unknown:
            parts.append("Unknown Title")
        else:
            parts.append("Track")

        clean_artist = cls.sanitize(artist) if artist else ""
        if clean_artist and clean_artist.lower() not in ["unknown", "unknown artist", "알 수 없음"]:
            parts.append(clean_artist)
        elif include_unknown:
            parts.append("Unknown Artist")

        if bpm and bpm > 0:
            bpm_val = int(round(bpm)) if round(bpm, 1).is_integer() else round(bpm, 1)
            parts.append(f"{bpm_val} BPM")
        elif include_unknown:
            parts.append("Unknown BPM")

        clean_key = cls.sanitize(key) if key else ""
        if clean_key and clean_key.lower() not in ["unknown", "unknown key", "분석 불가", "알 수 없음"]:
            parts.append(clean_key)
        elif include_unknown:
            parts.append("Unknown Key")

        base_name = " - ".join(parts)
        base_name = re.sub(r'\s+', ' ', base_name).strip().rstrip(". ")
        if not base_name:
            base_name = "audio_track"

        return f"{base_name}.{ext}"

    @classmethod
    def resolve_collision(
        cls,
        target_dir: str,
        desired_filename: str,
        policy: str = "suffix"
    ) -> str:
        target_path = os.path.join(target_dir, desired_filename)
        if not os.path.exists(target_path) or policy == "overwrite":
            return desired_filename

        name, ext = os.path.splitext(desired_filename)
        counter = 1
        while True:
            candidate = f"{name} ({counter}){ext}"
            cand_path = os.path.join(target_dir, candidate)
            if not os.path.exists(cand_path):
                return candidate
            counter += 1