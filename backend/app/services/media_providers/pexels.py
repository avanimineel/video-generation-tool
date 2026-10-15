import os
import requests
from typing import Optional, List, Dict, Any
from .base import BaseMediaProvider, MediaAsset

class PexelsProvider(BaseMediaProvider):
    def __init__(self, api_key: Optional[str] = None):
        self._custom_key = api_key
        self.last_diagnostic: Dict[str, Any] = {
            "provider": "pexels",
            "status": "initialized",
            "http_code": None,
            "error": None,
            "count": 0
        }

    @property
    def name(self) -> str:
        return "pexels"

    def get_api_key(self) -> Optional[str]:
        return self._custom_key or os.environ.get("PEXELS_API_KEY") or None

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
                "provider": "pexels",
                "connected": False,
                "status": "unconfigured",
                "http_code": 401,
                "message": "PEXELS_API_KEY is not configured in backend/.env",
                "masked_key": self.mask_key()
            }
            self.last_diagnostic = diag
            print(f"[Pexels Check] {diag['message']}")
            return diag
        
        try:
            headers = {"Authorization": api_key.strip()}
            endpoint = "https://api.pexels.com/v1/curated?per_page=1"
            print(f"[Pexels Check] Calling GET {endpoint} server-side...")
            res = requests.get(endpoint, headers=headers, timeout=8)
            print(f"[Pexels Check] Response: HTTP {res.status_code}")
            if res.status_code == 200:
                diag = {
                    "provider": "pexels",
                    "connected": True,
                    "status": "connected",
                    "http_code": 200,
                    "message": "Connected to Pexels API",
                    "masked_key": self.mask_key()
                }
            elif res.status_code == 401:
                diag = {
                    "provider": "pexels",
                    "connected": False,
                    "status": "invalid_key",
                    "http_code": 401,
                    "message": "Pexels returned 401 Unauthorized: Invalid API key",
                    "masked_key": self.mask_key()
                }
            elif res.status_code == 429:
                diag = {
                    "provider": "pexels",
                    "connected": False,
                    "status": "rate_limited",
                    "http_code": 429,
                    "message": "Pexels rate limit reached (200 req/hr on free tier)",
                    "masked_key": self.mask_key()
                }
            else:
                diag = {
                    "provider": "pexels",
                    "connected": False,
                    "status": "error",
                    "http_code": res.status_code,
                    "message": f"Pexels returned HTTP {res.status_code}: {res.text[:100]}",
                    "masked_key": self.mask_key()
                }
            self.last_diagnostic = diag
            return diag
        except Exception as e:
            diag = {
                "provider": "pexels",
                "connected": False,
                "status": "network_error",
                "http_code": None,
                "message": f"Could not reach Pexels API: {str(e)}",
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
                "provider": "pexels",
                "media_type": "image",
                "query": clean_q,
                "status": "missing_key",
                "http_code": 401,
                "error": "PEXELS_API_KEY is not configured in backend/.env",
                "count": 0
            }
            print(f"[Pexels Image] Missing PEXELS_API_KEY for query '{clean_q}'")
            return []

        endpoint = "https://api.pexels.com/v1/search"
        headers = {"Authorization": api_key.strip()}
        params: Dict[str, Any] = {
            "query": clean_q,
            "page": max(1, page),
            "per_page": min(80, max(1, limit))
        }
        if orientation in ["landscape", "portrait", "square"]:
            params["orientation"] = orientation

        print(f"[Pexels Image] Server-side GET {endpoint} | query='{clean_q}', per_page={params['per_page']}")
        try:
            import time
            t0 = time.time()
            res = requests.get(endpoint, headers=headers, params=params, timeout=10)
            elapsed_ms = int((time.time() - t0) * 1000)
            print(f"[Pexels Image] HTTP {res.status_code} in {elapsed_ms}ms")

            if res.status_code != 200:
                err_msg = res.text[:200]
                print(f"[Pexels Image Error] HTTP {res.status_code}: {err_msg}")
                self.last_diagnostic = {
                    "provider": "pexels",
                    "media_type": "image",
                    "query": clean_q,
                    "status": "http_error",
                    "http_code": res.status_code,
                    "error": err_msg,
                    "count": 0
                }
                return []

            data = res.json()
            photos = data.get("photos", [])
            assets: List[MediaAsset] = []

            for p in photos:
                w = p.get("width", 1920)
                h = p.get("height", 1080)
                calc_ori = "portrait" if h > w else ("square" if w == h else "landscape")
                calc_ar = "9:16" if h > w else ("1:1" if w == h else "16:9")

                src = p.get("src", {})
                thumb = src.get("medium") or src.get("small") or src.get("tiny")
                full = src.get("large2x") or src.get("original") or src.get("large") or thumb

                photographer = p.get("photographer", "")
                alt_text = p.get("alt") or f"{clean_q.title()} Photo"

                assets.append(MediaAsset(
                    id=str(p.get("id")),
                    provider="pexels",
                    title=alt_text,
                    media_type="image",
                    thumb_url=thumb,
                    preview_url=src.get("large") or thumb,
                    download_url=full,
                    author=photographer,
                    author_url=p.get("photographer_url", ""),
                    license="Pexels Free License",
                    width=w,
                    height=h,
                    duration=0.0,
                    aspect_ratio=calc_ar,
                    orientation=calc_ori
                ))

            self.last_diagnostic = {
                "provider": "pexels",
                "media_type": "image",
                "query": clean_q,
                "status": "success",
                "http_code": 200,
                "count": len(assets),
                "total_available": data.get("total_results", len(assets)),
                "endpoint": endpoint
            }
            print(f"[Pexels Image] Successfully parsed {len(assets)} images for '{clean_q}'")
            return assets
        except Exception as e:
            print(f"[Pexels Search Exception] {e}")
            self.last_diagnostic = {
                "provider": "pexels",
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
                "provider": "pexels",
                "media_type": "video",
                "query": clean_q,
                "status": "missing_key",
                "http_code": 401,
                "error": "PEXELS_API_KEY is not configured in backend/.env",
                "count": 0
            }
            print(f"[Pexels Video] Missing PEXELS_API_KEY for query '{clean_q}'")
            return []

        endpoint = "https://api.pexels.com/videos/search"
        headers = {"Authorization": api_key.strip()}
        params: Dict[str, Any] = {
            "query": clean_q,
            "page": max(1, page),
            "per_page": min(80, max(1, limit))
        }
        if orientation in ["landscape", "portrait", "square"]:
            params["orientation"] = orientation

        print(f"[Pexels Video] Server-side GET {endpoint} | query='{clean_q}', per_page={params['per_page']}")
        try:
            import time
            t0 = time.time()
            res = requests.get(endpoint, headers=headers, params=params, timeout=12)
            elapsed_ms = int((time.time() - t0) * 1000)
            print(f"[Pexels Video] HTTP {res.status_code} in {elapsed_ms}ms")

            if res.status_code != 200:
                err_msg = res.text[:200]
                print(f"[Pexels Video Error] HTTP {res.status_code}: {err_msg}")
                self.last_diagnostic = {
                    "provider": "pexels",
                    "media_type": "video",
                    "query": clean_q,
                    "status": "http_error",
                    "http_code": res.status_code,
                    "error": err_msg,
                    "count": 0
                }
                return []

            data = res.json()
            videos = data.get("videos", [])
            assets: List[MediaAsset] = []

            for v in videos:
                w = v.get("width", 1920)
                h = v.get("height", 1080)
                calc_ori = "portrait" if h > w else ("square" if w == h else "landscape")
                calc_ar = "9:16" if h > w else ("1:1" if w == h else "16:9")
                vid_dur = float(v.get("duration", 0.0))

                video_files = v.get("video_files", [])
                if not video_files:
                    continue

                mp4_files = [f for f in video_files if f.get("file_type") == "video/mp4"] or video_files
                hd_files = [f for f in mp4_files if f.get("quality") == "hd" or (f.get("width", 0) >= 1280)]
                download_file = hd_files[0] if hd_files else mp4_files[0]

                sd_files = [f for f in mp4_files if f.get("quality") == "sd" or (f.get("width", 0) <= 960 and f.get("width", 0) > 0)]
                preview_file = sd_files[0] if sd_files else download_file

                thumb_img = v.get("image", "")
                user_info = v.get("user", {})

                assets.append(MediaAsset(
                    id=str(v.get("id")),
                    provider="pexels",
                    title=f"{clean_q.title()} Footage #{v.get('id')}",
                    media_type="video",
                    thumb_url=thumb_img,
                    preview_url=preview_file.get("link", ""),
                    download_url=download_file.get("link", ""),
                    author=user_info.get("name", ""),
                    author_url=user_info.get("url", ""),
                    license="Pexels Free Video License",
                    width=w,
                    height=h,
                    duration=vid_dur,
                    aspect_ratio=calc_ar,
                    orientation=calc_ori
                ))

            self.last_diagnostic = {
                "provider": "pexels",
                "media_type": "video",
                "query": clean_q,
                "status": "success",
                "http_code": 200,
                "count": len(assets),
                "total_available": data.get("total_results", len(assets)),
                "endpoint": endpoint
            }
            print(f"[Pexels Video] Successfully parsed {len(assets)} videos for '{clean_q}'")
            return assets
        except Exception as e:
            print(f"[Pexels Video Search Exception] {e}")
            self.last_diagnostic = {
                "provider": "pexels",
                "media_type": "video",
                "query": clean_q,
                "status": "exception",
                "http_code": None,
                "error": str(e),
                "count": 0
            }
            return []
