import os
import urllib.parse
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from config import default_config
from downloader import DownloadEngine
from ai_music_analyzer import AIMusicAnalyzer
from filename_formatter import FilenameFormatter

app = FastAPI(
    title="Wavtotube API",
    description="Full System Overhaul — Pure Audio Intelligence, AI Music Analyzer & Smart Filename Engine",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = DownloadEngine(default_config)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
INDEX_PATH = os.path.join(STATIC_DIR, "index.html")

# 1. 루트 HTML 서빙
@app.get("/", response_class=FileResponse)
async def serve_home():
    if os.path.exists(INDEX_PATH):
        return FileResponse(INDEX_PATH)
    return HTMLResponse("<h2>static/index.html 파일을 찾을 수 없습니다.</h2>")

# 2. 링크 사전 검사
class CheckRequest(BaseModel):
    url: str

@app.post("/api/check")
async def check_url(req: CheckRequest):
    if not req.url:
        return JSONResponse(status_code=400, content={"success": False, "detail": "URL을 입력해주세요."})
    res = engine.check_link_metadata(req.url)
    if not res.get("success"):
        return JSONResponse(status_code=400, content={
            "success": False,
            "detail": res.get("error"),
            "diagnosis": res.get("diagnosis")
        })
    return {"success": True, "data": res}

# 3. 변환 요청 모델 (Pydantic 최신 버전 호환 완벽 대응)
class ConvertRequest(BaseModel):
    url: str
    format: str = "mp3"
    mode: str = "single"

@app.post("/api/convert")
async def convert_audio(req: ConvertRequest):
    if not req.url:
        return JSONResponse(status_code=400, content={"success": False, "detail": "링크를 입력해주세요."})
    
    is_playlist = (req.mode == "playlist")
    result = engine.download_and_process(url=req.url, output_format=req.format, is_playlist=is_playlist)
    
    if not result.get("success"):
        diag = result.get("diagnosis", {})
        return JSONResponse(status_code=422, content={
            "success": False,
            "detail": diag.get("user_message", result.get("error")),
            "error_category": diag.get("error_category"),
            "action_steps": diag.get("action_steps", []),
            "timings": result.get("timings")
        })

    tracks = result.get("tracks", [])
    for t in tracks:
        safe_name = urllib.parse.quote(t["file_name"])
        t["download_url"] = f"/api/download/{t['id']}?format={t['format']}&filename={safe_name}"

    return {
        "success": True,
        "data": tracks,
        "timings": result.get("timings"),
        "auth_report": result.get("auth_report"),
        "under_10s": result.get("under_10s")
    }

# 4. AI 음악 분석 요청 모델
class AnalyzeRequest(BaseModel):
    file_id: str
    format: str = "mp3"
    raw_title: Optional[str] = None
    uploader: Optional[str] = None

@app.post("/api/analyze")
async def analyze_track(req: AnalyzeRequest):
    target_path = os.path.join(default_config.download_dir, f"{req.file_id}.{req.format}")
    if not os.path.exists(target_path):
        for ext in [req.format, 'mp3', 'wav', 'm4a']:
            cand = os.path.join(default_config.download_dir, f"{req.file_id}.{ext}")
            if os.path.exists(cand):
                target_path = cand
                break

    if not os.path.exists(target_path):
        return JSONResponse(status_code=404, content={"success": False, "detail": "분석할 오디오 파일을 찾을 수 없습니다."})

    res = AIMusicAnalyzer.analyze_audio_file(
        file_path=target_path,
        raw_video_title=req.raw_title,
        uploader=req.uploader
    )
    if not res.get("success"):
        return JSONResponse(status_code=500, content={"success": False, "detail": res.get("error")})

    return {"success": True, "data": res}

# 5. 파일명 포맷팅 요청 모델
class FormatFilenameRequest(BaseModel):
    title: str
    artist: Optional[str] = None
    bpm: Optional[float] = None
    key: Optional[str] = None
    format: str = "mp3"
    include_unknown: bool = False

@app.post("/api/format-filename")
async def format_filename(req: FormatFilenameRequest):
    formatted = FilenameFormatter.format_smart_filename(
        title=req.title,
        artist=req.artist,
        bpm=req.bpm,
        key=req.key,
        extension=req.format,
        include_unknown=req.include_unknown
    )
    return {"success": True, "data": {"filename": formatted}}

# 6. 파일명 적용 요청 모델
class ApplyFilenameRequest(BaseModel):
    file_id: str
    format: str = "mp3"
    new_filename: str
    collision_policy: str = "suffix"

@app.post("/api/apply-filename")
async def apply_filename(req: ApplyFilenameRequest):
    source_path = os.path.join(default_config.download_dir, f"{req.file_id}.{req.format}")
    if not os.path.exists(source_path):
        for ext in [req.format, 'mp3', 'wav', 'm4a']:
            cand = os.path.join(default_config.download_dir, f"{req.file_id}.{ext}")
            if os.path.exists(cand):
                source_path = cand
                break

    if not os.path.exists(source_path):
        return JSONResponse(status_code=404, content={"success": False, "detail": "원본 파일을 찾을 수 없습니다."})

    clean_name = FilenameFormatter.sanitize(req.new_filename)
    if not clean_name.lower().endswith(f".{req.format.lower()}"):
        clean_name = f"{clean_name}.{req.format.lower()}"

    resolved_filename = FilenameFormatter.resolve_collision(
        target_dir=default_config.download_dir,
        desired_filename=clean_name,
        policy=req.collision_policy
    )

    safe_encoded_name = urllib.parse.quote(resolved_filename)
    download_url = f"/api/download/{req.file_id}?format={req.format}&filename={safe_encoded_name}"

    return {
        "success": True,
        "data": {
            "applied_filename": resolved_filename,
            "download_url": download_url
        }
    }

# 7. 오디오 바이너리 파일 다운로드
@app.get("/api/download/{file_id}")
async def download_file(file_id: str, format: str = "mp3", filename: str = Query(None)):
    target = os.path.join(default_config.download_dir, f"{file_id}.{format}")
    if not os.path.exists(target):
        for ext in [format, 'mp3', 'wav', 'm4a']:
            cand = os.path.join(default_config.download_dir, f"{file_id}.{ext}")
            if os.path.exists(cand):
                target = cand
                break

    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="요청한 오디오 파일을 찾을 수 없습니다.")

    dl_name = filename if filename else f"{file_id}.{format}"
    return FileResponse(
        path=target,
        media_type=f"audio/{format}",
        filename=dl_name
    )

# 8. 헬스체크
@app.get("/api/health")
async def health_check():
    errors = default_config.validate()
    return {
        "status": "healthy" if not errors else "misconfigured",
        "ffmpeg_available": engine.ffmpeg_path is not None,
        "ffmpeg_path": engine.ffmpeg_path,
        "config_errors": errors,
        "download_dir": default_config.download_dir
    }

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

download_and_convert = engine.download_and_process
DOWNLOAD_DIR = default_config.download_dir

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)