import os
import re
import json
import time
import urllib.request
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from app.core.config import settings

class AssetDownloaderService:
    """Service to download remote image and video assets into local project storage."""

    def get_download_dir(self, project_id: str) -> Path:
        pdir = settings.projects_dir / project_id / "media" / "downloaded"
        pdir.mkdir(parents=True, exist_ok=True)
        return pdir

    def sanitize_id(self, raw_id: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_-]", "_", str(raw_id))

    def guess_extension(self, url: str, media_type: str) -> str:
        clean_url = url.split("?")[0].lower()
        for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov", ".webm", ".m4v"]:
            if clean_url.endswith(ext):
                return ext[1:]
        return "mp4" if media_type == "video" else "jpg"

    def download_asset(
        self,
        project_id: str,
        asset_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Downloads a remote asset into project storage with deduplication and metadata caching.
        """
        download_dir = self.get_download_dir(project_id)

        provider = asset_info.get("provider", "web")
        raw_id = asset_info.get("id") or str(int(time.time() * 1000))
        safe_id = self.sanitize_id(raw_id)
        media_type = asset_info.get("media_type", "image")
        remote_url = asset_info.get("download_url") or asset_info.get("url") or asset_info.get("media_url")

        if not remote_url:
            raise ValueError("No download URL provided in asset_info")

        # If the URL is already a local URL or file path, return it directly
        if "api/media" in remote_url and "/asset/" in remote_url:
            filename = remote_url.split("/")[-1]
            local_path = download_dir / filename
            return {
                "success": True,
                "filename": filename,
                "local_path": str(local_path),
                "media_url": remote_url,
                "is_new": False,
                "media_type": media_type
            }

        ext = self.guess_extension(remote_url, media_type)
        filename = f"{provider}_{safe_id}.{ext}"
        target_file = download_dir / filename
        meta_file = download_dir / f"{provider}_{safe_id}.json"

        # Deduplication check: if file already exists with valid size, reuse it
        if target_file.exists() and target_file.stat().st_size > 1024:
            print(f"[AssetDownloader] Deduplication hit: Reusing {target_file.name}")
            return {
                "success": True,
                "filename": filename,
                "local_path": str(target_file),
                "media_url": f"/api/media/{project_id}/asset/downloaded/{filename}",
                "full_url": f"http://localhost:8002/api/media/{project_id}/asset/downloaded/{filename}",
                "is_new": False,
                "media_type": media_type,
                "file_size": target_file.stat().st_size,
                "title": asset_info.get("title", ""),
                "source_credit": asset_info.get("source_credit", "")
            }

        # Download from remote URL
        print(f"[AssetDownloader] Fetching {remote_url[:70]}... into {target_file.name}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            with requests.get(remote_url, headers=headers, stream=True, timeout=25) as r:
                r.raise_for_status()
                with open(target_file, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
        except Exception as e:
            # Fallback to urllib
            print(f"[AssetDownloader] Requests failed ({e}), trying urllib fallback...")
            req = urllib.request.Request(remote_url, headers=headers)
            with urllib.request.urlopen(req, timeout=25) as resp:
                with open(target_file, "wb") as f:
                    f.write(resp.read())

        if not target_file.exists() or target_file.stat().st_size == 0:
            raise RuntimeError(f"Failed to download asset {remote_url}: target file empty")

        # Save metadata sidecar JSON
        metadata = {
            **asset_info,
            "downloaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "local_filename": filename,
            "file_size": target_file.stat().st_size,
            "project_id": project_id
        }
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return {
            "success": True,
            "filename": filename,
            "local_path": str(target_file),
            "media_url": f"/api/media/{project_id}/asset/downloaded/{filename}",
            "full_url": f"http://localhost:8002/api/media/{project_id}/asset/downloaded/{filename}",
            "is_new": True,
            "media_type": media_type,
            "file_size": target_file.stat().st_size,
            "title": asset_info.get("title", ""),
            "source_credit": asset_info.get("source_credit", "")
        }

asset_downloader = AssetDownloaderService()
