import os
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class AppConfig:
    download_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
    temp_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
    
    # 1. 로컬 또는 Render Secret Files 경로(/etc/secrets/cookies.txt 또는 프로젝트 내 cookies.txt) 자동 탐색
    cookie_file: Optional[str] = None
    browser_cookies: Optional[str] = None
    default_format: str = "mp3"
    mp3_quality: str = "320"
    max_concurrent_downloads: int = 4
    connection_timeout: int = 15
    socket_timeout: int = 15
    max_retries: int = 2
    retry_backoff_factor: float = 1.5
    target_10s_optimization: bool = True
    verify_file_integrity: bool = True
    ffmpeg_threads: int = 4
    analysis_sample_duration: int = 25
    log_level: str = "INFO"

    def __post_init__(self):
        os.makedirs(self.download_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

        # 쿠키 파일 자동 탐색 로직 (Render 및 로컬 겸용)
        possible_paths = [
            "/etc/secrets/cookies.txt",  # Render.com Secret File 기본 경로
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt"),
            os.path.join(os.getcwd(), "cookies.txt")
        ]
        for p in possible_paths:
            if os.path.exists(p) and os.path.getsize(p) > 0:
                self.cookie_file = p
                break

    def validate(self) -> List[str]:
        errors = []
        if self.default_format not in ["mp3", "wav"]:
            errors.append(f"지원하지 않는 기본 오디오 포맷입니다: {self.default_format} ('mp3' 또는 'wav' 필요)")
        if self.max_concurrent_downloads < 1 or self.max_concurrent_downloads > 16:
            errors.append(f"최대 동시 다운로드 수는 1에서 16 사이여야 합니다: {self.max_concurrent_downloads}")
        if self.connection_timeout < 3:
            errors.append("연결 타임아웃은 최소 3초 이상이어야 합니다.")
        if self.cookie_file and not os.path.isfile(self.cookie_file):
            errors.append(f"지정된 쿠키 파일이 존재하지 않습니다: {self.cookie_file}")
        return errors

default_config = AppConfig()