# IDLIX Downloader API 🎬

![Created by dewhush](https://img.shields.io/badge/Created%20by-dewhush-blue)
![Modified from](https://img.shields.io/badge/Modified%20from-sandrocods%2FIdlixDownloader-orange)
![Python](https://img.shields.io/badge/Python-3.8%2B-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal)

REST API wrapper for IDLIX movie/series downloader. Download movies from IDLIX with subtitle embedding support.

> **Permission granted by original author [sandrocods](https://github.com/sandrocods/IdlixDownloader)**

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎬 Featured Movies | Get list of featured movies from homepage |
| 📺 Video Info | Get video metadata (title, poster, ID) |
| 🔗 Streaming URL | Get M3U8 streaming URL with quality options |
| 📥 Download | Download video with auto subtitle embedding |
| 🔐 API Key Auth | Secure endpoints with API key authentication |
| 🔄 Auto URL Detection | Automatically detect active IDLIX domain |

---

## 📦 Installation

### 1. Clone Repository

```bash
git clone https://github.com/dewhush/Idlix-Downloader
cd Idlix-Downloader
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env and set your API_KEY
```

**.env configuration:**
```env
APP_NAME=Idlix-Downloader-API
APP_ENV=development
API_KEY=your-secret-api-key
```

### 4. Install FFmpeg (Optional - for subtitle embedding)

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

**Linux:**
```bash
sudo apt install ffmpeg
```

---

## 🚀 Running the API

### Windows

```batch
run_api.bat
```

### Manual / Linux

```bash
python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

---

## 📖 API Documentation

### Interactive Docs

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Authentication

All endpoints (except `/health`) require API key authentication.

**Header:**
```
X-API-Key: your-api-key
```

---

## 🔌 Endpoints

### Health Check

```
GET /health
```

No authentication required.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-17T01:45:00"
}
```

---

### API Status

```
GET /status
```

**Headers:** `X-API-Key: your-api-key`

**Response:**
```json
{
  "app_name": "Idlix-Downloader-API",
  "environment": "development",
  "uptime_seconds": 3600.5,
  "active_idlix_url": "https://tv12.idlixku.com/",
  "version": "1.0.0"
}
```

---

### Get Featured Movies

```
GET /v1/featured
```

**Headers:** `X-API-Key: your-api-key`

**Response:**
```json
{
  "status": true,
  "count": 10,
  "movies": [
    {
      "url": "https://tv12.idlixku.com/movie/example/",
      "title": "Example Movie",
      "year": "2024",
      "type": "movie",
      "poster": "https://..."
    }
  ]
}
```

---

### Get Video Info

```
POST /v1/video-info
```

**Headers:** `X-API-Key: your-api-key`

**Request Body:**
```json
{
  "url": "https://tv12.idlixku.com/movie/example/"
}
```

**Response:**
```json
{
  "status": true,
  "video_id": "12345",
  "video_name": "Example Movie",
  "poster": "https://..."
}
```

---

### Get Stream URL

```
POST /v1/get-stream
```

**Headers:** `X-API-Key: your-api-key`

**Request Body:**
```json
{
  "url": "https://tv12.idlixku.com/movie/example/",
  "quality_id": "0"
}
```

**Response:**
```json
{
  "status": true,
  "m3u8_url": "https://jeniusplay.com/.../master.m3u8",
  "qualities": [
    {"id": "0", "resolution": "1920x1080", "bandwidth": 5000000},
    {"id": "1", "resolution": "1280x720", "bandwidth": 2500000}
  ],
  "has_multiple_qualities": true,
  "subtitle_url": "https://..."
}
```

---

### Download Video

```
POST /v1/download
```

**Headers:** `X-API-Key: your-api-key`

**Request Body:**
```json
{
  "url": "https://tv12.idlixku.com/movie/example/",
  "quality_id": "0",
  "embed_subtitle": true
}
```

**Response:**
```json
{
  "status": true,
  "file_path": "/path/to/Example Movie.mp4",
  "file_name": "Example Movie.mp4",
  "message": "Download completed successfully"
}
```

---

## 🛠️ Project Structure

```
Idlix-Downloader/
├── api.py              # FastAPI app & routes
├── idlix_service.py    # Core scraping logic
├── src/
│   └── CryptoJsAesHelper.py
├── requirements.txt
├── .env.example
├── run_api.bat
├── .gitignore
└── README.md
```

---

## ⚠️ Disclaimer

This project is created for educational purposes only. Any misuse is the user's responsibility.

---

## 🙏 Credits

**Created by:** [dewhush](https://github.com/dewhush)

**Original Author:** [sandrocods](https://github.com/sandrocods/IdlixDownloader)

---

```
Created by dewhush
```
