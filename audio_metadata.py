import os
import json
import shutil
import subprocess
from typing import Dict, Any, Optional

class AudioMetadataExtractor:
    @staticmethod
    def _locate_ffprobe() -> Optional[str]:
        p = shutil.which("ffprobe")
        if p:
            return p
        for candidate in ["/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe", "/usr/bin/ffprobe"]:
            if os.path.exists(candidate):
                return candidate
        return None

    @classmethod
    def extract_metadata(cls, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {"success": False, "error": "파일이 존재하지 않습니다."}

        ffprobe_bin = cls._locate_ffprobe()
        if not ffprobe_bin:
            return {"success": False, "error": "ffprobe를 찾을 수 없습니다."}

        cmd = [
            ffprobe_bin,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
            data = json.loads(res.stdout)
            format_info = data.get("format", {})
            tags = format_info.get("tags", {})
            tags_lower = {k.lower(): v for k, v in tags.items()}

            title = tags_lower.get("title") or tags_lower.get("track")
            artist = tags_lower.get("artist") or tags_lower.get("album_artist") or tags_lower.get("composer")
            album = tags_lower.get("album")
            duration = float(format_info.get("duration", 0.0))
            format_name = format_info.get("format_name", "")

            has_embedded_info = bool(title or artist)

            return {
                "success": True,
                "has_embedded_info": has_embedded_info,
                "title": title.strip() if title else None,
                "artist": artist.strip() if artist else None,
                "album": album.strip() if album else None,
                "duration": round(duration, 1),
                "format": format_name,
                "raw_tags": tags
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "has_embedded_info": False
            }