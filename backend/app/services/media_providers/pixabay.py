import os
import requests
from typing import Optional, List, Dict, Any
from .base import BaseMediaProvider, MediaAsset

class PixabayProvider(BaseMediaProvider):
    def __init__(self, api_key: Optional[str] = None):
        self._custom_key = api_key
        self.last_diagnostic: Dict[str, Any] = {
            "provider": "pixabay",
            "status": "initialized",
            "http_code": None,
            "error": None,
            "count": 0
        }

    @property
    def name(self) -> str:
        return "pixabay"

    def get_api_key(self) -> Optional[str]:
        return self._custom_key or os.environ.get("PIXABAY_API_KEY") or None

    def is_configured(self) -> bool:
        k = self.get_api_key()
        return bool(k and len(k.strip()) > 5)

    def mask_key(self) -> str:
        k = self.get_api_key()
        if not k:
            return "Not configured"
        k = k.strip()
        if len(k) <= 8:
            return "***"
        return f"{k[:4]}...{k[-3:]}"

    def check_connection(self) -> Dict[str, Any]:
        api_key = self.get_api_key()
        if not api_key:
            diag = {
                "provider": "pixabay",
                "connected": False,
                "status": "unconfigured",
                "http_code": 401,
                "message": "PIXABAY_API_KEY is not configured in backend/.env",
                "masked_key": self.mask_key()
            }
            self.last_diagnostic = diag
            print(f"[Pixabay Check] {diag['message']}")
            return diag

        try:
            import time
            params = {
                "key": api_key.strip(),
                "q": "nature",
                "per_page": 3
            }
            endpoint = "https://pixabay.com/api/"
            print(f"[Pixabay Check] Calling GET {endpoint} server-side...")
            t0 = time.time()
            res = requests.get(endpoint, params=params, timeout=8)
            duration_ms = int((time.time() - t0) * 1000)
            print(f"[Pixabay Check] Response: HTTP {res.status_code} in {duration_ms}ms")

            if res.status_code == 200:
                diag = {
                    "provider": "pixabay",
                    "connected": True,
                    "status": "connected",
                    "http_code": 200,
                    "message": "Connected to Pixabay API successfully",
                    "masked_key": self.mask_key()
                }
            elif res.status_code in (400, 401):
                diag = {
                    "provider": "pixabay",
                    "connected": False,
                    "status": "invalid_key",
                    "http_code": res.status_code,
                    "message": f"Pixabay returned HTTP {res.status_code}: Invalid or missing API key",
                    "masked_key": self.mask_key()
                }
            elif res.status_code == 429:
                diag = {
                    "provider": "pixabay",
                    "connected": False,
                    "status": "rate_limited",
                    "http_code": 429,
                    "message": "Pixabay returned HTTP 429: Rate limit exceeded (or missing key)",
                    "masked_key": self.mask_key()
                }
            else:
                diag = {
                    "provider": "pixabay",
                    "connected": False,
                    "status": "error",
                    "http_code": res.status_code,
                    "message": f"Pixabay returned HTTP {res.status_code}: {res.text[:100]}",
                    "masked_key": self.mask_key()
                }
            self.last_diagnostic = diag
            return diag
        except Exception as e:
            diag = {
                "provider": "pixabay",
                "connected": False,
                "status": "network_error",
                "http_code": None,
                "message": f"Could not reach Pixabay API: {str(e)}",
                "masked_key": self.mask_key()
            }
            self.last_diagnostic = diag
            return diag

    def search_images(
        self,
        query: str,
        page: int = 1,
        limit: int = 12,
        orientation: Optional[str] = None
    ) -> List[MediaAsset]:
        clean_q = query.strip()
        if not clean_q:
            return []

        api_key = self.get_api_key()
        if not api_key:
            self.last_diagnostic = {
                "provider": "pixabay",
                "media_type": "image",
                "query": clean_q,
                "status": "missing_key",
                "http_code": 401,
                "error": "PIXABAY_API_KEY is not configured in backend/.env",
                "count": 0
            }
            print(f"[Pixabay Image] Missing PIXABAY_API_KEY for query '{clean_q}'")
            return []

        pix_ori = "all"
        if orientation == "portrait":
            pix_ori = "vertical"
        elif orientation == "landscape":
            pix_ori = "horizontal"

        endpoint = "https://pixabay.com/api/"
        params: Dict[str, Any] = {
            "key": api_key.strip(),
            "q": clean_q,
            "image_type": "photo",
            "page": max(1, page),
            "per_page": min(50, max(3, limit)),
            "safesearch": "true"
        }
        if pix_ori != "all":
            params["orientation"] = pix_ori

        print(f"[Pixabay Image] Server-side GET {endpoint} | query='{clean_q}', per_page={params['per_page']}")
        try:
            import time
            t0 = time.time()
            res = requests.get(endpoint, params=params, timeout=10)
            elapsed_ms = int((time.time() - t0) * 1000)
            print(f"[Pixabay Image] HTTP {res.status_code} in {elapsed_ms}ms")

            if res.status_code != 200:
                err_msg = res.text[:200]
                print(f"[Pixabay Image Error] HTTP {res.status_code}: {err_msg}")
                self.last_diagnostic = {
                    "provider": "pixabay",
                    "media_type": "image",
                    "query": clean_q,
                    "status": "http_error",
                    "http_code": res.status_code,
                    "error": err_msg,
                    "count": 0
                }
                return []

            data = res.json()
            hits = data.get("hits", [])
            assets: List[MediaAsset] = []

            for h in hits:
                w = h.get("imageWidth", 1920)
                height = h.get("imageHeight", 1080)
                calc_ori = "portrait" if height > w else ("square" if w == height else "landscape")
                calc_ar = "9:16" if height > w else ("1:1" if w == height else "16:9")

                thumb = h.get("webformatURL") or h.get("previewURL")
                large = h.get("largeImageURL") or thumb
                tags = h.get("tags") or clean_q.title()

                assets.append(MediaAsset(
                    id=str(h.get("id")),
                    provider="pixabay",
                    title=f"{tags.split(',')[0].strip().title()} Photo",
                    media_type="image",
                    thumb_url=thumb,
                    preview_url=large,
                    download_url=large,
                    author=h.get("user", ""),
                    author_url=f"https://pixabay.com/users/{h.get('user', '')}-{h.get('user_id', '')}/",
                    license="Pixabay Content License",
                    width=w,
                    height=height,
                    duration=0.0,
                    aspect_ratio=calc_ar,
                    orientation=calc_ori
                ))

            self.last_diagnostic = {
                "provider": "pixabay",
                "media_type": "image",
                "query": clean_q,
                "status": "success",
                "http_code": 200,
                "count": len(assets),
                "total_available": data.get("totalHits", len(assets)),
                "endpoint": endpoint
            }
            print(f"[Pixabay Image] Successfully parsed {len(assets)} images for '{clean_q}'")
            return assets
        except Exception as e:
            print(f"[Pixabay Image Search Exception] {e}")
            self.last_diagnostic = {
                "provider": "pixabay",
                "media_type": "image",
                "query": clean_q,
                "status": "exception",
                "http_code": None,
                "error": str(e),
                "count": 0
            }
            return []

    def search_videos(
        self,
        query: str,
        page: int = 1,
        limit: int = 12,
        orientation: Optional[str] = None,
        duration: Optional[int] = None
    ) -> List[MediaAsset]:
        clean_q = query.strip()
        if not clean_q:
            return []

        api_key = self.get_api_key()
        if not api_key:
            self.last_diagnostic = {
                "provider": "pixabay",
                "media_type": "video",
                "query": clean_q,
                "status": "missing_key",
                "http_code": 401,
                "error": "PIXABAY_API_KEY is not configured in backend/.env",
                "count": 0
            }
            print(f"[Pixabay Video] Missing PIXABAY_API_KEY for query '{clean_q}'")
            return []

        endpoint = "https://pixabay.com/api/videos/"
        params: Dict[str, Any] = {
            "key": api_key.strip(),
            "q": clean_q,
            "page": max(1, page),
            "per_page": min(50, max(3, limit)),
            "safesearch": "true"
        }

        print(f"[Pixabay Video] Server-side GET {endpoint} | query='{clean_q}', per_page={params['per_page']}")
        try:
            import time
            t0 = time.time()
            res = requests.get(endpoint, params=params, timeout=12)
            elapsed_ms = int((time.time() - t0) * 1000)
            print(f"[Pixabay Video] HTTP {res.status_code} in {elapsed_ms}ms")

            if res.status_code != 200:
                err_msg = res.text[:200]
                print(f"[Pixabay Video Error] HTTP {res.status_code}: {err_msg}")
                self.last_diagnostic = {
                    "provider": "pixabay",
                    "media_type": "video",
                    "query": clean_q,
                    "status": "http_error",
                    "http_code": res.status_code,
                    "error": err_msg,
                    "count": 0
                }
                return []

            data = res.json()
            hits = data.get("hits", [])
            assets: List[MediaAsset] = []

            for h in hits:
                vid_dur = float(h.get("duration", 0.0))
                videos = h.get("videos", {})
                
                download_info = videos.get("large") or videos.get("medium") or videos.get("small") or {}
                preview_info = videos.get("medium") or videos.get("small") or download_info

                download_url = download_info.get("url", "")
                if not download_url:
                    continue

                w = download_info.get("width", 1920)
                height = download_info.get("height", 1080)
                calc_ori = "portrait" if height > w else ("square" if w == height else "landscape")
                calc_ar = "9:16" if height > w else ("1:1" if w == height else "16:9")

                if orientation in ["portrait", "landscape"] and calc_ori != orientation:
                    continue

                # Pixabay now returns a thumbnail per rendition; picture_id is legacy.
                picture_id = h.get("picture_id", "")
                thumb = (preview_info.get("thumbnail") or download_info.get("thumbnail")
                         or (f"https://i.vimeocdn.com/video/{picture_id}_640x360.jpg" if picture_id else ""))
                tags = h.get("tags") or clean_q.title()

                assets.append(MediaAsset(
                    id=str(h.get("id")),
                    provider="pixabay",
                    title=f"{tags.split(',')[0].strip().title()} Video Clip",
                    media_type="video",
                    thumb_url=thumb,
                    preview_url=preview_info.get("url", download_url),
                    download_url=download_url,
                    author=h.get("user", ""),
                    author_url=f"https://pixabay.com/users/{h.get('user', '')}-{h.get('user_id', '')}/",
                    license="Pixabay Content License",
                    width=w,
                    height=height,
                    duration=vid_dur,
                    aspect_ratio=calc_ar,
                    orientation=calc_ori
                ))

            self.last_diagnostic = {
                "provider": "pixabay",
                "media_type": "video",
                "query": clean_q,
                "status": "success",
                "http_code": 200,
                "count": len(assets),
                "total_available": data.get("totalHits", len(assets)),
                "endpoint": endpoint
            }
            print(f"[Pixabay Video] Successfully parsed {len(assets)} videos for '{clean_q}'")
            return assets
        except Exception as e:
            print(f"[Pixabay Video Search Exception] {e}")
            self.last_diagnostic = {
                "provider": "pixabay",
                "media_type": "video",
                "query": clean_q,
                "status": "exception",
                "http_code": None,
                "error": str(e),
                "count": 0
            }
            return []
