import os
import urllib.parse
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import audio_service

# 함수 호환성 처리
if hasattr(audio_service, "download_audio_core"):
    convert_fn = audio_service.download_audio_core
else:
    convert_fn = audio_service.download_and_convert

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
STATIC_DIR = os.path.join(BASE_DIR, "static")
INDEX_PATH = os.path.join(STATIC_DIR, "index.html")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(title="Wavtotube API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 루트(/) 접속 시 index.html 정상 서빙
@app.get("/", response_class=FileResponse)
async def serve_home():
    if os.path.exists(INDEX_PATH):
        return FileResponse(INDEX_PATH)
    return HTMLResponse("<h2>static/index.html 파일을 찾을 수 없습니다. static 폴더 안에 index.html 파일이 있는지 확인해주세요.</h2>")

class ConvertRequest(BaseModel):
    url: str
    format: str = "mp3"
    mode: str = "single"

@app.post("/api/convert")
async def convert(req: ConvertRequest):
    if not req.url:
        return JSONResponse(status_code=400, content={"success": False, "detail": "링크를 입력해주세요."})
    
    try:
        is_playlist = (req.mode == "playlist")
        tracks = convert_fn(req.url, req.format, is_playlist=is_playlist)
        
        if not tracks:
            raise Exception("음원을 추출하지 못했습니다. 링크를 확인해주세요.")

        for t in tracks:
            safe_name = urllib.parse.quote(t['file_name'])
            t['download_url'] = f"/api/download/{t['id']}?format={t['format']}&filename={safe_name}"

        return {"success": True, "data": tracks}
    except Exception as e:
        err = str(e)
        if "ffmpeg" in err.lower():
            err = "FFmpeg가 설치되어 있지 않습니다. 터미널에서 'brew install ffmpeg'를 실행해주세요."
        return JSONResponse(status_code=500, content={"success": False, "detail": err})

@app.get("/api/download/{file_id}")
async def download(file_id: str, format: str = "mp3", filename: str = Query(None)):
    target = os.path.join(DOWNLOAD_DIR, f"{file_id}.{format}")
    if not os.path.exists(target):
        for ext in [format, 'mp3', 'wav', 'm4a']:
            candidate = os.path.join(DOWNLOAD_DIR, f"{file_id}.{ext}")
            if os.path.exists(candidate):
                target = candidate
                break

    if not os.path.exists(target):
        raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다.")

    dl_name = filename if filename else f"{file_id}.{format}"
    return FileResponse(path=target, media_type=f"audio/{format}", filename=dl_name)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)