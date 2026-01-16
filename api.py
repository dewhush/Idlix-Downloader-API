"""
Idlix Downloader API - FastAPI REST API Wrapper

Created by: dewhush
Original by: sandrocods (https://github.com/sandrocods/IdlixDownloader)
"""

import os
import time
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

from idlix_service import IdlixService

# Load environment variables
load_dotenv()

# Configuration
APP_NAME = os.getenv("APP_NAME", "Idlix-Downloader-API")
APP_ENV = os.getenv("APP_ENV", "development")
API_KEY = os.getenv("API_KEY", "")

# Startup time for uptime calculation
START_TIME = None


# =============================================================================
#                           STARTUP BANNER
# =============================================================================
def print_banner():
    banner = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║     ██╗██████╗ ██╗     ██╗██╗  ██╗     █████╗ ██████╗ ██╗        ║
║     ██║██╔══██╗██║     ██║╚██╗██╔╝    ██╔══██╗██╔══██╗██║        ║
║     ██║██║  ██║██║     ██║ ╚███╔╝     ███████║██████╔╝██║        ║
║     ██║██║  ██║██║     ██║ ██╔██╗     ██╔══██║██╔═══╝ ██║        ║
║     ██║██████╔╝███████╗██║██╔╝ ██╗    ██║  ██║██║     ██║        ║
║     ╚═╝╚═════╝ ╚══════╝╚═╝╚═╝  ╚═╝    ╚═╝  ╚═╝╚═╝     ╚═╝        ║
║                                                                   ║
║                   Created by: dewhush                             ║
║        Original: sandrocods/IdlixDownloader                       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


# =============================================================================
#                           LIFESPAN EVENTS
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global START_TIME
    print_banner()
    START_TIME = time.time()
    print(f"🚀 {APP_NAME} starting in {APP_ENV} mode...")
    
    # Initialize service to detect active URL on startup
    try:
        service = IdlixService()
        print(f"✅ Active IDLIX URL: {service.get_active_url()}")
    except Exception as e:
        print(f"⚠️ Failed to detect active URL: {e}")
    
    yield
    
    print(f"👋 {APP_NAME} shutting down...")


# =============================================================================
#                           FASTAPI APP
# =============================================================================
app = FastAPI(
    title=APP_NAME,
    description="REST API wrapper for IDLIX Downloader - Download movies from IDLIX",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# =============================================================================
#                           AUTHENTICATION
# =============================================================================
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API Key from header"""
    if not API_KEY:
        # If no API_KEY configured, skip authentication
        return True
    
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API Key. Provide 'X-API-Key' header."
        )
    
    if x_api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key"
        )
    
    return True


# =============================================================================
#                           REQUEST/RESPONSE MODELS
# =============================================================================
class VideoUrlRequest(BaseModel):
    url: str = Field(..., description="IDLIX movie URL", example="https://tv12.idlixku.com/movie/example/")


class StreamRequest(BaseModel):
    url: str = Field(..., description="IDLIX movie URL")
    quality_id: Optional[str] = Field(None, description="Quality ID from variant playlist (optional)")


class DownloadRequest(BaseModel):
    url: str = Field(..., description="IDLIX movie URL")
    quality_id: Optional[str] = Field(None, description="Quality ID from variant playlist (optional)")
    embed_subtitle: bool = Field(True, description="Embed subtitle into video file")


class HealthResponse(BaseModel):
    status: str
    timestamp: str


class StatusResponse(BaseModel):
    app_name: str
    environment: str
    uptime_seconds: float
    active_idlix_url: str
    version: str


class MovieItem(BaseModel):
    url: str
    title: str
    year: str
    type: str
    poster: str


class FeaturedResponse(BaseModel):
    status: bool
    count: int
    movies: list[MovieItem]


class VideoInfoResponse(BaseModel):
    status: bool
    video_id: Optional[str] = None
    video_name: Optional[str] = None
    poster: Optional[str] = None
    message: Optional[str] = None


class QualityOption(BaseModel):
    id: str
    resolution: str
    bandwidth: int


class StreamResponse(BaseModel):
    status: bool
    m3u8_url: Optional[str] = None
    qualities: Optional[list[QualityOption]] = None
    has_multiple_qualities: bool = False
    subtitle_url: Optional[str] = None
    message: Optional[str] = None


class DownloadResponse(BaseModel):
    status: bool
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    message: Optional[str] = None


# =============================================================================
#                           ENDPOINTS
# =============================================================================

# -----------------------------------------------------------------------------
# Health & Status (No Auth Required)
# -----------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint - no authentication required"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/status", response_model=StatusResponse, tags=["Health"])
async def get_status(_: bool = Depends(verify_api_key)):
    """Get API status and configuration"""
    try:
        service = IdlixService()
        active_url = service.get_active_url()
    except Exception:
        active_url = "unknown"
    
    uptime = time.time() - START_TIME if START_TIME else 0
    
    return {
        "app_name": APP_NAME,
        "environment": APP_ENV,
        "uptime_seconds": round(uptime, 2),
        "active_idlix_url": active_url,
        "version": "1.0.0"
    }


# -----------------------------------------------------------------------------
# V1 API Endpoints
# -----------------------------------------------------------------------------
@app.get("/v1/featured", response_model=FeaturedResponse, tags=["Movies"])
async def get_featured_movies(_: bool = Depends(verify_api_key)):
    """Get featured movies from IDLIX homepage"""
    try:
        service = IdlixService()
        result = service.get_featured_movies()
        
        if not result.get("status"):
            raise HTTPException(
                status_code=500,
                detail=result.get("message", "Failed to fetch featured movies")
            )
        
        movies = result.get("featured_movie", [])
        return {
            "status": True,
            "count": len(movies),
            "movies": movies
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/video-info", response_model=VideoInfoResponse, tags=["Movies"])
async def get_video_info(
    request: VideoUrlRequest,
    _: bool = Depends(verify_api_key)
):
    """Get video information from IDLIX URL"""
    try:
        service = IdlixService()
        result = service.get_video_info(request.url)
        
        if not result.get("status"):
            return JSONResponse(
                status_code=400,
                content={
                    "status": False,
                    "message": result.get("message", "Failed to get video info")
                }
            )
        
        return {
            "status": True,
            "video_id": result.get("video_id"),
            "video_name": result.get("video_name"),
            "poster": result.get("poster")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/get-stream", response_model=StreamResponse, tags=["Streaming"])
async def get_stream_url(
    request: StreamRequest,
    _: bool = Depends(verify_api_key)
):
    """Get M3U8 streaming URL and quality options"""
    try:
        service = IdlixService()
        
        # Get video info first
        video_info = service.get_video_info(request.url)
        if not video_info.get("status"):
            return JSONResponse(
                status_code=400,
                content={
                    "status": False,
                    "message": video_info.get("message", "Failed to get video info")
                }
            )
        
        # Get embed URL
        embed_result = service.get_embed_url()
        if not embed_result.get("status"):
            return JSONResponse(
                status_code=400,
                content={
                    "status": False,
                    "message": embed_result.get("message", "Failed to get embed URL")
                }
            )
        
        # Get M3U8 URL
        m3u8_result = service.get_m3u8_url()
        if not m3u8_result.get("status"):
            return JSONResponse(
                status_code=400,
                content={
                    "status": False,
                    "message": m3u8_result.get("message", "Failed to get stream URL")
                }
            )
        
        # Get subtitle URL
        subtitle_result = service.get_subtitle_url()
        subtitle_url = subtitle_result.get("subtitle") if subtitle_result.get("status") else None
        
        # Process quality options
        qualities = []
        variant_playlist = m3u8_result.get("variant_playlist", [])
        for v in variant_playlist:
            qualities.append({
                "id": v.get("id"),
                "resolution": v.get("resolution"),
                "bandwidth": v.get("bandwidth")
            })
        
        # If specific quality requested, set that m3u8 URL
        final_m3u8_url = m3u8_result.get("m3u8_url")
        if request.quality_id and variant_playlist:
            for v in variant_playlist:
                if v.get("id") == request.quality_id:
                    service.set_m3u8_url(v.get("uri"))
                    final_m3u8_url = service.get_current_m3u8_url()
                    break
        
        return {
            "status": True,
            "m3u8_url": final_m3u8_url,
            "qualities": qualities,
            "has_multiple_qualities": len(qualities) > 1,
            "subtitle_url": subtitle_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/download", response_model=DownloadResponse, tags=["Download"])
async def download_video(
    request: DownloadRequest,
    _: bool = Depends(verify_api_key)
):
    """Download video from IDLIX URL"""
    try:
        service = IdlixService()
        
        # Get video info first
        video_info = service.get_video_info(request.url)
        if not video_info.get("status"):
            return JSONResponse(
                status_code=400,
                content={
                    "status": False,
                    "message": video_info.get("message", "Failed to get video info")
                }
            )
        
        # Get embed URL
        embed_result = service.get_embed_url()
        if not embed_result.get("status"):
            return JSONResponse(
                status_code=400,
                content={
                    "status": False,
                    "message": embed_result.get("message", "Failed to get embed URL")
                }
            )
        
        # Get M3U8 URL
        m3u8_result = service.get_m3u8_url()
        if not m3u8_result.get("status"):
            return JSONResponse(
                status_code=400,
                content={
                    "status": False,
                    "message": m3u8_result.get("message", "Failed to get stream URL")
                }
            )
        
        # If specific quality requested, set that m3u8 URL
        variant_playlist = m3u8_result.get("variant_playlist", [])
        if request.quality_id and variant_playlist:
            for v in variant_playlist:
                if v.get("id") == request.quality_id:
                    service.set_m3u8_url(v.get("uri"))
                    break
        
        # Download video
        download_result = service.download_video(embed_subtitle=request.embed_subtitle)
        
        if not download_result.get("status"):
            return JSONResponse(
                status_code=500,
                content={
                    "status": False,
                    "message": download_result.get("message", "Download failed")
                }
            )
        
        file_path = download_result.get("path")
        return {
            "status": True,
            "file_path": file_path,
            "file_name": os.path.basename(file_path) if file_path else None,
            "message": "Download completed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
#                           MAIN ENTRY
# =============================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=APP_ENV == "development"
    )
