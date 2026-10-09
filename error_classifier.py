from enum import Enum
from typing import Dict, Any

class ErrorCategory(str, Enum):
    AUTH_BOT_DETECTED = "auth_bot_detected"
    AUTH_LOGIN_REQUIRED = "auth_login_required"
    AUTH_COOKIE_INVALID = "auth_cookie_invalid"
    AUTH_COOKIE_EXPIRED = "auth_cookie_expired"
    AUTH_COOKIE_MISSING = "auth_cookie_missing"
    VIDEO_UNAVAILABLE = "video_unavailable"
    VIDEO_PRIVATE_OR_DELETED = "video_private_or_deleted"
    GEO_RESTRICTED = "geo_restricted"
    INVALID_URL = "invalid_url"
    RATE_LIMITED = "rate_limited"
    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_CONNECTION_ERROR = "network_connection_error"
    FFMPEG_MISSING_OR_FAILED = "ffmpeg_error"
    DISK_FULL = "disk_full"
    PERMISSION_DENIED = "permission_denied"
    INTEGRITY_CHECK_FAILED = "integrity_check_failed"
    UNKNOWN_ERROR = "unknown_error"

class ErrorClassifier:
    @staticmethod
    def classify(error_or_message: Any) -> Dict[str, Any]:
        msg = str(error_or_message).strip()
        lower_msg = msg.lower()
        
        if "no space left on device" in lower_msg or "errno 28" in lower_msg:
            return {
                "category": ErrorCategory.DISK_FULL,
                "is_auth_error": False,
                "retryable": False,
                "user_message": "디스크 저장 공간이 부족합니다. 컴퓨터 저장 공간을 확보한 후 다시 시도해주세요.",
                "solution": "휴지통을 비우거나 디스크 공간을 최소 2GB 이상 확보해주세요."
            }

        if "permission denied" in lower_msg or "errno 13" in lower_msg:
            return {
                "category": ErrorCategory.PERMISSION_DENIED,
                "is_auth_error": False,
                "retryable": False,
                "user_message": "파일을 저장하거나 읽을 수 있는 권한이 없습니다.",
                "solution": "저장 경로 권한을 확인하거나 관리자 권한을 점검해주세요."
            }

        if "ffmpeg" in lower_msg and ("not found" in lower_msg or "ffprobe" in lower_msg or "no such file" in lower_msg):
            return {
                "category": ErrorCategory.FFMPEG_MISSING_OR_FAILED,
                "is_auth_error": False,
                "retryable": False,
                "user_message": "FFmpeg가 설치되어 있지 않거나 경로를 찾을 수 없습니다.",
                "solution": "터미널에서 'brew install ffmpeg' (Mac) 또는 FFmpeg를 설치해주세요."
            }

        if "sign in to confirm you’re not a bot" in lower_msg or "sign in to confirm you're not a bot" in lower_msg or "confirm you’re not a bot" in lower_msg or "bot detection" in lower_msg:
            return {
                "category": ErrorCategory.AUTH_BOT_DETECTED,
                "is_auth_error": True,
                "retryable": False,
                "user_message": "YouTube에서 봇 감지(Bot Detection)로 인해 접근을 제한했습니다.",
                "solution": "쿠키 파일(cookies.txt)을 설정하거나 브라우저 쿠키 연동 옵션을 사용해주세요."
            }

        if "sign in to confirm your age" in lower_msg or "private video" in lower_msg or "members-only content" in lower_msg:
            return {
                "category": ErrorCategory.AUTH_LOGIN_REQUIRED,
                "is_auth_error": True,
                "retryable": False,
                "user_message": "연령 제한 또는 회원 전용 콘텐츠로 YouTube 로그인이 필요합니다.",
                "solution": "로그인된 계정의 쿠키를 설정하여 다시 시도해주세요."
            }

        if "could not find any cookies" in lower_msg or "invalid cookie" in lower_msg or "malformed cookie" in lower_msg:
            return {
                "category": ErrorCategory.AUTH_COOKIE_INVALID,
                "is_auth_error": True,
                "retryable": False,
                "user_message": "지정된 쿠키 파일이 손상되었거나 올바른 Netscape 형식이 아닙니다.",
                "solution": "Get cookies.txt 확장 프로그램 등을 사용해 올바른 Netscape 형식의 쿠키 파일을 다시 추출해주세요."
            }
            
        if "cookie has expired" in lower_msg or "expired session" in lower_msg:
            return {
                "category": ErrorCategory.AUTH_COOKIE_EXPIRED,
                "is_auth_error": True,
                "retryable": False,
                "user_message": "설정된 YouTube 세션 쿠키가 만료되었습니다.",
                "solution": "브라우저에서 YouTube에 다시 로그인 후 새 쿠키 파일을 추출해주세요."
            }

        if "video unavailable" in lower_msg or "this video has been removed" in lower_msg:
            return {
                "category": ErrorCategory.VIDEO_PRIVATE_OR_DELETED,
                "is_auth_error": False,
                "retryable": False,
                "user_message": "존재하지 않거나 삭제된 동영상입니다.",
                "solution": "동영상 링크가 올바른지 웹 브라우저에서 먼저 확인해주세요."
            }

        if "not available in your country" in lower_msg or "uploader has not made this video available in your country" in lower_msg:
            return {
                "category": ErrorCategory.GEO_RESTRICTED,
                "is_auth_error": False,
                "retryable": False,
                "user_message": "해당 국가/지역에서는 시청할 수 없는 동영상입니다.",
                "solution": "지역 제한이 없는 링크를 사용하거나 네트워크 환경을 확인해주세요."
            }

        if "too many requests" in lower_msg or "http error 429" in lower_msg:
            return {
                "category": ErrorCategory.RATE_LIMITED,
                "is_auth_error": False,
                "retryable": True,
                "user_message": "단시간 내 너무 많은 요청으로 인해 일시적으로 요청이 제한되었습니다.",
                "solution": "잠시 후(약 1~2분 뒤) 다시 시도해주세요."
            }

        if "timed out" in lower_msg or "timeout" in lower_msg:
            return {
                "category": ErrorCategory.NETWORK_TIMEOUT,
                "is_auth_error": False,
                "retryable": True,
                "user_message": "네트워크 응답 시간이 초과되었습니다.",
                "solution": "인터넷 연결 상태를 확인하고 잠시 후 다시 시도해주세요."
            }
            
        if "connection refused" in lower_msg or "network is unreachable" in lower_msg or "dns" in lower_msg:
            return {
                "category": ErrorCategory.NETWORK_CONNECTION_ERROR,
                "is_auth_error": False,
                "retryable": True,
                "user_message": "네트워크 연결에 실패했습니다.",
                "solution": "인터넷 연결 상태를 점검해주세요."
            }

        if "is not a valid url" in lower_msg or "unsupported url" in lower_msg:
            return {
                "category": ErrorCategory.INVALID_URL,
                "is_auth_error": False,
                "retryable": False,
                "user_message": "지원하지 않거나 유효하지 않은 URL 형식입니다.",
                "solution": "올바른 YouTube 또는 Instagram 링크를 입력해주세요."
            }

        return {
            "category": ErrorCategory.UNKNOWN_ERROR,
            "is_auth_error": False,
            "retryable": False,
            "user_message": "다운로드 또는 변환 중 오류가 발생했습니다.",
            "solution": "로그 상세 내용을 확인하거나 링크를 다시 검토해주세요."
        }