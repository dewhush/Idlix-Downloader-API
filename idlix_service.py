"""
Idlix Service - Core Scraping Logic

Created by: dewhush
Original by: sandrocods (https://github.com/sandrocods/IdlixDownloader)
"""

import os
import re
import json
import random
import shutil
import subprocess
import m3u8
import m3u8_To_MP4
import requests
from loguru import logger
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse
from vtt_to_srt.vtt_to_srt import ConvertFile
from curl_cffi import requests as cffi_requests
from src.CryptoJsAesHelper import CryptoJsAes, dec


class IdlixService:
    """
    Service class for IDLIX video scraping and downloading.
    Refactored from idlixHelper.py for use as an API service.
    """
    
    MAIN_DOMAIN = "https://idlixian.com/"
    BASE_WEB_URL = None
    BASE_STATIC_HEADERS = {
        "Connection": "keep-alive",
        "sec-ch-ua": "Not)A;Brand;v=99, Google Chrome;v=127, Chromium;v=127",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "Windows",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8"
    }
    
    @classmethod
    def detect_active_url(cls) -> str:
        """Auto-detect active IDLIX URL by following redirect from main domain"""
        try:
            logger.info(f"Detecting active URL from {cls.MAIN_DOMAIN}...")
            response = requests.get(
                cls.MAIN_DOMAIN,
                headers={"User-Agent": cls.BASE_STATIC_HEADERS["User-Agent"]},
                allow_redirects=True,
                timeout=15
            )
            final_url = response.url
            parsed = urlparse(final_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}/"
            logger.success(f"Active URL detected: {base_url}")
            return base_url
        except Exception as e:
            logger.warning(f"Failed to auto-detect URL: {e}")
            return "https://tv12.idlixku.com/"
    
    def __init__(self):
        """Initialize the Idlix service"""
        self._poster = None
        self._m3u8_url = None
        self._video_id = None
        self._embed_url = None
        self._video_name = None
        self._is_subtitle = None
        self._variant_playlist = None
        
        # Auto-detect active URL if not set
        if IdlixService.BASE_WEB_URL is None:
            IdlixService.BASE_WEB_URL = self.detect_active_url()
        
        # Update headers with detected host
        parsed_url = urlparse(IdlixService.BASE_WEB_URL)
        self.BASE_STATIC_HEADERS["Host"] = parsed_url.netloc
        self.BASE_STATIC_HEADERS["Referer"] = IdlixService.BASE_WEB_URL
        
        # Initialize session with browser impersonation
        self._session = cffi_requests.Session(
            impersonate=random.choice(["chrome124", "chrome119", "chrome104"]),
            headers=self.BASE_STATIC_HEADERS,
            debug=False,
        )
        
        # Check FFMPEG availability
        self._check_ffmpeg()
    
    def _check_ffmpeg(self) -> None:
        """Check if FFMPEG is available in PATH"""
        if shutil.which('ffmpeg') is None:
            logger.warning("FFMPEG not found in PATH. Subtitle embedding will be disabled.")
    
    def get_active_url(self) -> str:
        """Get the currently active IDLIX URL"""
        return IdlixService.BASE_WEB_URL or "unknown"
    
    def get_featured_movies(self) -> dict:
        """Get featured movies from IDLIX homepage"""
        try:
            response = self._session.get(
                url=self.BASE_WEB_URL,
                timeout=10
            )
            
            if response.status_code != 200:
                return {
                    "status": False,
                    "message": "Failed to get home page"
                }
            
            soup = BeautifulSoup(response.text, "html.parser")
            featured_container = soup.find("div", {"class": "items featured"})
            
            if not featured_container:
                return {
                    "status": False,
                    "message": "Featured movies container not found"
                }
            
            movies = []
            for article in featured_container.find_all("article"):
                link = article.find("a")
                if not link:
                    continue
                
                url = link.get("href", "")
                
                # Skip TV series
                url_parts = url.split("/")
                if len(url_parts) > 3 and url_parts[3] == "tvseries":
                    continue
                
                title_elem = article.find("h3")
                year_elem = article.find("span")
                poster_elem = article.find("img")
                
                movies.append({
                    "url": url,
                    "title": title_elem.text if title_elem else "Unknown",
                    "year": year_elem.text if year_elem else "Unknown",
                    "type": url_parts[3] if len(url_parts) > 3 else "movie",
                    "poster": poster_elem.get("src", "") if poster_elem else ""
                })
            
            return {
                "status": True,
                "featured_movie": movies
            }
            
        except Exception as e:
            logger.error(f"Error fetching featured movies: {e}")
            return {
                "status": False,
                "message": str(e)
            }
    
    def get_video_info(self, url: str) -> dict:
        """Get video information from IDLIX URL"""
        if not url:
            return {
                "status": False,
                "message": "URL is required"
            }
        
        # Validate URL belongs to IDLIX
        if not self._is_valid_idlix_url(url):
            return {
                "status": False,
                "message": "Invalid IDLIX URL"
            }
        
        try:
            response = self._session.get(url=url, timeout=10)
            
            if response.status_code != 200:
                return {
                    "status": False,
                    "message": "Failed to get video data"
                }
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract video ID
            ajax_meta = soup.find("meta", {"id": "dooplay-ajax-counter"})
            if not ajax_meta:
                return {
                    "status": False,
                    "message": "Video ID not found"
                }
            
            self._video_id = ajax_meta.get("data-postid")
            
            # Extract video name
            name_meta = soup.find("meta", {"itemprop": "name"})
            self._video_name = unquote(name_meta.get("content", "video")) if name_meta else "video"
            
            # Extract poster
            poster_img = soup.find("img", {"itemprop": "image"})
            self._poster = poster_img.get("src", "") if poster_img else ""
            
            return {
                "status": True,
                "video_id": self._video_id,
                "video_name": self._video_name,
                "poster": self._poster
            }
            
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return {
                "status": False,
                "message": str(e)
            }
    
    def _is_valid_idlix_url(self, url: str) -> bool:
        """Check if URL is a valid IDLIX URL"""
        if not url.startswith("https://"):
            return False
        
        # Check if URL contains idlix domain indicators
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        return "idlix" in domain or domain == urlparse(self.BASE_WEB_URL).netloc
    
    def get_embed_url(self) -> dict:
        """Get embed URL for the video"""
        if not self._video_id:
            return {
                "status": False,
                "message": "Video ID is required. Call get_video_info first."
            }
        
        try:
            response = self._session.post(
                url=f"{self.BASE_WEB_URL}wp-admin/admin-ajax.php",
                data={
                    "action": "doo_player_ajax",
                    "post": self._video_id,
                    "nume": "1",
                    "type": "movie",
                }
            )
            
            if response.status_code != 200:
                return {
                    "status": False,
                    "message": "Failed to get embed URL"
                }
            
            json_response = response.json()
            
            if not json_response.get("embed_url"):
                return {
                    "status": False,
                    "message": "No embed URL in response"
                }
            
            # Decrypt embed URL
            self._embed_url = CryptoJsAes.decrypt(
                json_response.get("embed_url"),
                dec(
                    json_response.get("key"),
                    json.loads(json_response.get("embed_url")).get("m")
                )
            )
            
            return {
                "status": True,
                "embed_url": self._embed_url
            }
            
        except Exception as e:
            logger.error(f"Error getting embed URL: {e}")
            return {
                "status": False,
                "message": str(e)
            }
    
    def get_m3u8_url(self) -> dict:
        """Get M3U8 streaming URL"""
        if not self._embed_url:
            return {
                "status": False,
                "message": "Embed URL is required. Call get_embed_url first."
            }
        
        try:
            # Parse embed URL to get video hash
            embed_parsed = urlparse(self._embed_url)
            
            if "/video/" in embed_parsed.path:
                video_hash = embed_parsed.path.split("/")[2]
            elif embed_parsed.query:
                video_hash = embed_parsed.query.split("=")[1]
            else:
                return {
                    "status": False,
                    "message": "Could not extract video hash from embed URL"
                }
            
            # Request m3u8 URL from player
            response = cffi_requests.post(
                url="https://jeniusplay.com/player/index.php",
                params={
                    "data": video_hash,
                    "do": "getVideo"
                },
                headers={
                    "Host": "jeniusplay.com",
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
                data={
                    "hash": video_hash,
                    "r": self.BASE_WEB_URL,
                },
                impersonate="chrome",
            )
            
            if response.status_code != 200:
                return {
                    "status": False,
                    "message": "Failed to get M3U8 URL"
                }
            
            json_response = response.json()
            
            if not json_response.get("videoSource"):
                return {
                    "status": False,
                    "message": "No video source in response"
                }
            
            # Build m3u8 URL
            self._m3u8_url = json_response.get("videoSource").rsplit(".", 1)[0] + ".m3u8"
            
            # Load variant playlist
            self._variant_playlist = m3u8.load(self._m3u8_url)
            
            # Extract quality options
            qualities = []
            for idx, playlist in enumerate(self._variant_playlist.playlists):
                qualities.append({
                    "bandwidth": playlist.stream_info.bandwidth,
                    "resolution": f"{playlist.stream_info.resolution[0]}x{playlist.stream_info.resolution[1]}",
                    "uri": playlist.uri,
                    "id": str(idx)
                })
            
            return {
                "status": True,
                "m3u8_url": self._m3u8_url,
                "variant_playlist": qualities,
                "is_variant_playlist": len(qualities) > 1
            }
            
        except Exception as e:
            logger.error(f"Error getting M3U8 URL: {e}")
            return {
                "status": False,
                "message": str(e)
            }
    
    def set_m3u8_url(self, m3u8_url: str) -> None:
        """Set specific M3U8 URL (for quality selection)"""
        if "https://jeniusplay.com" not in m3u8_url:
            self._m3u8_url = "https://jeniusplay.com" + m3u8_url
        else:
            self._m3u8_url = m3u8_url
    
    def get_current_m3u8_url(self) -> str:
        """Get current M3U8 URL"""
        return self._m3u8_url or ""
    
    def get_subtitle_url(self, download: bool = False) -> dict:
        """Get subtitle URL for the video"""
        if not self._embed_url:
            return {
                "status": False,
                "message": "Embed URL is required"
            }
        
        try:
            # Parse embed URL to get video hash
            embed_parsed = urlparse(self._embed_url)
            
            if "/video/" in embed_parsed.path:
                video_hash = embed_parsed.path.split("/")[2]
            elif embed_parsed.query:
                video_hash = embed_parsed.query.split("=")[1]
            else:
                video_hash = self._embed_url
            
            response = cffi_requests.post(
                url="https://jeniusplay.com/player/index.php",
                params={
                    "data": video_hash,
                    "do": "getVideo"
                },
                headers={
                    "Host": "jeniusplay.com",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
                data={
                    "hash": video_hash,
                    "r": self.BASE_WEB_URL
                },
                impersonate="chrome",
            )
            
            # Search for subtitle URL in response
            regex_match = re.search(r'var playerjsSubtitle = "(.*)";', response.text)
            
            if not regex_match:
                self._is_subtitle = False
                return {
                    "status": False,
                    "message": "Subtitle not found"
                }
            
            subtitle_url = "https://" + regex_match.group(1).split("https://")[1]
            self._is_subtitle = True
            
            if download and self._video_name:
                # Download and convert subtitle
                subtitle_response = requests.get(url=subtitle_url)
                vtt_filename = self._video_name.replace(" ", "_") + ".vtt"
                
                with open(vtt_filename, "wb") as f:
                    f.write(subtitle_response.content)
                
                self._convert_vtt_to_srt(vtt_filename)
                
                return {
                    "status": True,
                    "subtitle": self._video_name.replace(" ", "_") + ".srt"
                }
            
            return {
                "status": True,
                "subtitle": subtitle_url
            }
            
        except Exception as e:
            logger.error(f"Error getting subtitle: {e}")
            return {
                "status": False,
                "message": str(e)
            }
    
    @staticmethod
    def _convert_vtt_to_srt(vtt_file: str) -> None:
        """Convert VTT subtitle to SRT format"""
        try:
            convert_file = ConvertFile(vtt_file, "utf-8")
            convert_file.convert()
        except Exception as e:
            logger.warning(f"Failed to convert VTT to SRT: {e}")
    
    def download_video(self, embed_subtitle: bool = True) -> dict:
        """Download video from M3U8 URL"""
        if not self._m3u8_url:
            return {
                "status": False,
                "message": "M3U8 URL is required. Call get_m3u8_url first."
            }
        
        try:
            # Create tmp directory
            tmp_dir = os.path.join(os.getcwd(), "tmp")
            if not os.path.exists(tmp_dir):
                os.makedirs(tmp_dir)
            
            # Download video
            logger.info(f"Downloading video: {self._video_name}")
            
            m3u8_To_MP4.multithread_download(
                m3u8_uri=self._m3u8_url,
                max_num_workers=10,
                mp4_file_name=self._video_name,
                mp4_file_dir=os.getcwd() + "/",
                tmpdir=tmp_dir + "/"
            )
            
            # Cleanup tmp directory
            shutil.rmtree(tmp_dir, ignore_errors=True)
            
            video_path = os.path.join(os.getcwd(), f"{self._video_name}.mp4")
            final_path = video_path
            
            # Embed subtitle if requested
            if embed_subtitle:
                final_path = self._embed_subtitle(video_path)
            
            return {
                "status": True,
                "message": "Download success",
                "path": final_path
            }
            
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            return {
                "status": False,
                "message": str(e)
            }
    
    def _embed_subtitle(self, video_path: str) -> str:
        """Embed subtitle into video file"""
        try:
            # Check if FFMPEG is available
            if shutil.which("ffmpeg") is None:
                logger.warning("FFMPEG not found, skipping subtitle embedding")
                return video_path
            
            # Get subtitle
            subtitle_result = self.get_subtitle_url(download=True)
            
            if not subtitle_result.get("status"):
                logger.info("No subtitle available for this video")
                return video_path
            
            srt_path = subtitle_result.get("subtitle")
            
            if not srt_path or not os.path.exists(srt_path):
                return video_path
            
            logger.info(f"Embedding subtitle: {srt_path}")
            
            # Output path with subtitle
            output_path = video_path.replace(".mp4", "_subbed.mp4")
            
            # Use FFmpeg to embed subtitle
            ffmpeg_cmd = [
                "ffmpeg",
                "-i", video_path,
                "-i", srt_path,
                "-c", "copy",
                "-c:s", "mov_text",
                "-metadata:s:s:0", "language=ind",
                "-y",
                output_path
            ]
            
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                # Remove original video and rename
                os.remove(video_path)
                final_path = video_path  # Same name as original
                os.rename(output_path, final_path)
                logger.success("Subtitle embedded successfully")
                
                # Cleanup subtitle files
                self._cleanup_subtitle_files(srt_path)
                
                return final_path
            else:
                logger.warning(f"FFmpeg subtitle embed failed: {result.stderr}")
                return video_path
            
        except Exception as e:
            logger.warning(f"Subtitle embedding failed: {e}")
            return video_path
    
    def _cleanup_subtitle_files(self, srt_path: str) -> None:
        """Clean up subtitle files after embedding"""
        try:
            if os.path.exists(srt_path):
                os.remove(srt_path)
            
            vtt_path = srt_path.replace(".srt", ".vtt")
            if os.path.exists(vtt_path):
                os.remove(vtt_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup subtitle files: {e}")
