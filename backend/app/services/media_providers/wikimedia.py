import urllib.request
import urllib.parse
import json
import re
import ssl
from typing import Optional, List, Dict, Any
from .base import BaseMediaProvider, MediaAsset

try:
    import certifi
    _ssl_ctx = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _ssl_ctx = ssl.create_default_context()

class WikimediaProvider(BaseMediaProvider):
    @property
    def name(self) -> str:
        return "wikimedia"

    def is_configured(self) -> bool:
        return True  # Open API, does not require a private key

    def check_connection(self) -> Dict[str, Any]:
        try:
            url = "https://commons.wikimedia.org/w/api.php?action=query&format=json&meta=siteinfo"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ResolveAICompanion/1.0 (educational media acquisition)"}
            )
            with urllib.request.urlopen(req, timeout=5, context=_ssl_ctx) as res:
                if res.status == 200:
                    return {
                        "provider": "wikimedia",
                        "connected": True,
                        "status": "connected",
                        "message": "Wikimedia Commons public domain archive connected (No API key needed)",
                        "masked_key": "None (Public Domain)"
                    }
        except Exception as e:
            return {
                "provider": "wikimedia",
                "connected": False,
                "status": "network_error",
                "message": f"Cannot reach Wikimedia Commons: {str(e)}",
                "masked_key": "None (Public Domain)"
            }
        return {
            "provider": "wikimedia",
            "connected": False,
            "status": "error",
            "message": "Unknown Wikimedia error",
            "masked_key": "None (Public Domain)"
        }

    def search_images(
        self,
        query: str,
        page: int = 1,
        limit: int = 12,
        orientation: Optional[str] = None
    ) -> List[MediaAsset]:
        # 1. First, check Wikipedia for exact named entity, article lead images, and brand names
        entity_assets = self._search_wikipedia_entity(query, limit=limit, orientation=orientation)
        commons_assets = self._search_commons(query, limit=limit, media_filter="image", orientation=orientation)
        
        # Combine: entity assets first, deduplicated by url
        combined = []
        seen_urls = set()
        for a in entity_assets + commons_assets:
            clean_u = a.download_url.split('?')[0]
            if clean_u not in seen_urls:
                seen_urls.add(clean_u)
                combined.append(a)
        return combined[:limit]

    def _search_wikipedia_entity(
        self,
        query: str,
        limit: int = 6,
        orientation: Optional[str] = None
    ) -> List[MediaAsset]:
        clean = query.strip()
        if not clean or len(clean) < 3:
            return []
        assets: List[MediaAsset] = []
        try:
            # Query Wikipedia API for article lead images and extracts
            wiki_url = (
                f"https://en.wikipedia.org/w/api.php?action=query"
                f"&titles={urllib.parse.quote(clean)}"
                f"&prop=pageimages|extracts|images"
                f"&piprop=original|thumbnail&pithumbsize=1200&exintro=1&explaintext=1&format=json"
            )
            req = urllib.request.Request(
                wiki_url,
                headers={"User-Agent": "ResolveAICompanion/1.0 (educational media acquisition; mailto:admin@local)"}
            )
            with urllib.request.urlopen(req, timeout=6, context=_ssl_ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            pages = data.get("query", {}).get("pages", {})
            brand_names = []
            for pid, pdata in pages.items():
                if pid == "-1":
                    continue
                extract = pdata.get("extract", "")
                # Extract brand names if pharmaceutical (e.g., 'sold under the brand name Kisqali')
                brands = re.findall(r'brand name[s]?\s+([A-Z][a-zA-Z0-9\-]+)', extract, re.I)
                brand_names.extend(brands)

                # Check lead image
                orig = pdata.get("original", {})
                thumb = pdata.get("thumbnail", {})
                img_url = orig.get("source") or thumb.get("source")
                if img_url and not any(img_url.lower().endswith(ext) for ext in ('.pdf', '.djvu', '.tif')):
                    w = int(orig.get("width") or thumb.get("width") or 1200)
                    h = int(orig.get("height") or thumb.get("height") or 800)
                    calc_ori = "portrait" if h > w else ("square" if w == h else "landscape")
                    calc_ar = "9:16" if h > w else ("1:1" if w == h else "16:9")
                    raw_title = pdata.get("pageimage") or pdata.get("title") or clean
                    assets.append(MediaAsset(
                        id=f"wiki_{pid}",
                        provider="wikimedia",
                        title=f"{pdata.get('title', clean)} (Wikipedia)",
                        media_type="image",
                        thumb_url=thumb.get("source") or img_url,
                        preview_url=img_url,
                        download_url=img_url,
                        author="Wikipedia / Wikimedia",
                        author_url=f"https://en.wikipedia.org/wiki/{urllib.parse.quote(pdata.get('title', clean))}",
                        license="CC BY-SA / Public Domain",
                        width=w,
                        height=h,
                        duration=0.0,
                        aspect_ratio=calc_ar,
                        orientation=calc_ori
                    ))

            # If brand names were detected, search Commons for the brand name directly
            for brand in dict.fromkeys(brand_names):
                brand_assets = self._search_commons(brand, limit=4, media_filter="image", orientation=orientation)
                assets.extend(brand_assets)

        except Exception as e:
            print(f"[Wikipedia Entity Search Error] {e}")
        return assets

    def search_videos(
        self,
        query: str,
        page: int = 1,
        limit: int = 12,
        orientation: Optional[str] = None,
        duration: Optional[int] = None
    ) -> List[MediaAsset]:
        return self._search_commons(query, limit=limit, media_filter="video", orientation=orientation)

    def _search_commons(
        self,
        query: str,
        limit: int = 12,
        media_filter: str = "image",
        orientation: Optional[str] = None
    ) -> List[MediaAsset]:
        clean_query = query.strip()
        if not clean_query:
            return []

        search_term = f"filetype:{media_filter} {clean_query}" if media_filter == "video" else clean_query
        encoded_query = urllib.parse.quote(search_term)

        api_url = (
            f"https://commons.wikimedia.org/w/api.php?action=query"
            f"&generator=search&gsrsearch={encoded_query}&gsrnamespace=6&gsrlimit={min(50, limit*3)}"
            f"&prop=imageinfo&iiprop=url|size|mime|extmetadata&iiurlwidth=400&format=json"
        )

        assets: List[MediaAsset] = []
        try:
            req = urllib.request.Request(
                api_url,
                headers={"User-Agent": "ResolveAICompanion/1.0 (educational media acquisition; mailto:admin@local)"}
            )
            with urllib.request.urlopen(req, timeout=7, context=_ssl_ctx) as response:
                data = json.loads(response.read().decode("utf-8"))

            pages = data.get("query", {}).get("pages", {})
            for pid, pdata in pages.items():
                imageinfo = pdata.get("imageinfo", [])
                if not imageinfo:
                    continue
                info = imageinfo[0]
                url = info.get("url", "")
                if not url:
                    continue

                mime = info.get("mime", "").lower()
                is_video = "video" in mime or url.lower().endswith((".mp4", ".webm", ".ogv"))

                if media_filter == "video" and not is_video:
                    continue
                # Strictly reject PDFs, DJVU, and non-image document formats
                if media_filter == "image":
                    if is_video or "pdf" in mime or "djvu" in mime or any(url.lower().endswith(ext) for ext in ('.pdf', '.djvu', '.tif', '.tiff', '.txt')):
                        continue

                w = int(info.get("width", 1920) or 1920)
                h = int(info.get("height", 1080) or 1080)
                calc_ori = "portrait" if h > w else ("square" if w == h else "landscape")
                calc_ar = "9:16" if h > w else ("1:1" if w == h else "16:9")

                if orientation in ["portrait", "landscape"] and calc_ori != orientation:
                    continue

                thumb = info.get("thumburl") or url
                raw_title = pdata.get("title", "").replace("File:", "")
                clean_title = re.sub(r"\.[a-zA-Z0-9]+$", "", raw_title).replace("_", " ")

                ext = info.get("extmetadata", {})
                artist_meta = ext.get("Artist", {}).get("value", "")
                artist = re.sub(r"<[^>]+>", "", artist_meta).strip()
                license_name = ext.get("LicenseShortName", {}).get("value", "Public Domain / CC")

                assets.append(MediaAsset(
                    id=str(pid),
                    provider="wikimedia",
                    title=clean_title or f"{clean_query.title()} Visual",
                    media_type="video" if is_video else "image",
                    thumb_url=thumb,
                    preview_url=url,
                    download_url=url,
                    author=artist[:40] if artist else "Wikimedia Commons",
                    author_url=f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(raw_title)}",
                    license=license_name,
                    width=w,
                    height=h,
                    duration=0.0,
                    aspect_ratio=calc_ar,
                    orientation=calc_ori
                ))

                if len(assets) >= limit:
                    break
        except Exception as e:
            print(f"[Wikimedia Search Error] {e}")

        return assets
