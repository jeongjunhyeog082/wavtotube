import os
import shutil
from typing import Optional, Dict, Any, List, Tuple
from error_classifier import ErrorClassifier, ErrorCategory

class AuthManager:
    SUPPORTED_BROWSERS = ["chrome", "safari", "firefox", "edge", "brave", "opera", "chromium"]

    def __init__(self, cookie_file: Optional[str] = None, browser: Optional[str] = None):
        self.cookie_file = cookie_file
        self.browser = browser.lower() if browser else None

    def validate_cookie_file(self, file_path: str) -> Tuple[bool, str]:
        if not file_path:
            return False, "쿠키 파일 경로가 지정되지 않았습니다."

        if not os.path.exists(file_path):
            return False, f"쿠키 파일이 존재하지 않습니다: {file_path}"

        if not os.path.isfile(file_path):
            return False, f"지정된 경로가 일반 파일이 아닙니다: {file_path}"

        if not os.access(file_path, os.R_OK):
            return False, f"쿠키 파일 읽기 권한이 없습니다: {file_path}"

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "쿠키 파일이 비어 있습니다 (0 bytes)."

        valid_lines = 0
        has_youtube_domain = False
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line_clean = line.strip()
                    if not line_clean or line_clean.startswith("#"):
                        continue
                    parts = line_clean.split("\t")
                    if len(parts) >= 6:
                        valid_lines += 1
                        domain = parts[0]
                        if "youtube.com" in domain or ".google.com" in domain:
                            has_youtube_domain = True
        except Exception as e:
            return False, f"쿠키 파일을 읽는 중 오류가 발생했습니다: {str(e)}"

        if valid_lines == 0:
            return False, "올바른 Netscape 형식의 쿠키 항목이 존재하지 않습니다 (탭 구분 형식 필요)."

        if not has_youtube_domain:
            return False, "쿠키 파일에 youtube.com 또는 google.com 관련 인증 정보가 포함되어 있지 않습니다."

        return True, "유효한 Netscape 쿠키 파일입니다."

    def validate_browser_choice(self, browser_name: str) -> Tuple[bool, str]:
        if not browser_name:
            return False, "브라우저 이름이 지정되지 않았습니다."
        b_clean = browser_name.lower()
        if b_clean not in self.SUPPORTED_BROWSERS:
            return False, f"지원하지 않는 브라우저입니다: {browser_name}. 지원 브라우저: {', '.join(self.SUPPORTED_BROWSERS)}"
        return True, f"지원되는 브라우저입니다: {b_clean}"

    def configure_ytdlp_auth(self, ydl_opts: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        report: Dict[str, Any] = {
            "auth_type": "none",
            "status": "ready",
            "cookie_file": None,
            "browser": None,
            "warnings": []
        }

        if self.cookie_file:
            is_valid, reason = self.validate_cookie_file(self.cookie_file)
            if is_valid:
                ydl_opts["cookiefile"] = self.cookie_file
                report["auth_type"] = "cookie_file"
                report["cookie_file"] = self.cookie_file
            else:
                report["status"] = "warning"
                report["warnings"].append(f"지정된 쿠키 파일을 사용할 수 없습니다: {reason}")
        elif self.browser:
            is_valid, reason = self.validate_browser_choice(self.browser)
            if is_valid:
                ydl_opts["cookiesfrombrowser"] = (self.browser, None, None, None)
                report["auth_type"] = "browser"
                report["browser"] = self.browser
            else:
                report["status"] = "warning"
                report["warnings"].append(reason)

        if "extractor_args" not in ydl_opts:
            ydl_opts["extractor_args"] = {}
        if "youtube" not in ydl_opts["extractor_args"]:
            ydl_opts["extractor_args"]["youtube"] = {}

        ydl_opts["extractor_args"]["youtube"]["player_client"] = ["web_music", "ios", "android", "mweb"]
        ydl_opts["extractor_args"]["youtube"]["player_skip"] = ["configs", "webpage"]

        return ydl_opts, report

    def diagnose_and_suggest(self, error_msg: str) -> Dict[str, Any]:
        classification = ErrorClassifier.classify(error_msg)
        category = classification["category"]

        if category == ErrorCategory.AUTH_BOT_DETECTED:
            steps = [
                "1. 브라우저(Chrome/Safari 등)에서 YouTube에 접속하여 로그인 상태를 확인하세요.",
                "2. 크롬 확장프로그램 'Get cookies.txt LOCALLY'를 설치하고 YouTube 쿠키를 'cookies.txt'로 추출하세요.",
                "3. 추출한 cookies.txt를 프로젝트 폴더에 저장하고 앱 설정에서 쿠키 경로를 지정하세요.",
                "4. 또는 브라우저 쿠키 연동 옵션(예: browser='chrome')을 활성화하세요."
            ]
        elif category == ErrorCategory.AUTH_LOGIN_REQUIRED:
            steps = [
                "1. 해당 동영상은 연령 인증 또는 성인 인증, 회원 전용 동영상입니다.",
                "2. 로그인된 계정의 쿠키 파일을 등록해야 다운로드가 가능합니다."
            ]
        elif category == ErrorCategory.AUTH_COOKIE_INVALID:
            steps = [
                "1. 쿠키 파일이 깨졌거나 비어 있지 않은지 확인하세요.",
                "2. 파일 첫 줄에 '# Netscape HTTP Cookie File' 형식이 포함되어 있는지 확인하세요."
            ]
        elif category == ErrorCategory.AUTH_COOKIE_EXPIRED:
            steps = [
                "1. 세션 쿠키가 만료되었습니다. 웹 브라우저에서 YouTube에 재로그인하세요.",
                "2. 최신 쿠키를 다시 추출하여 기존 cookies.txt 파일을 덮어쓰세요."
            ]
        else:
            steps = [classification["solution"]]

        return {
            "error_category": category,
            "user_message": classification["user_message"],
            "action_steps": steps,
            "retryable": classification["retryable"]
        }