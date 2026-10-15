from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

@dataclass
class MediaAsset:
    id: str
    provider: str  # "pexels", "pixabay", "wikimedia", "google_ai", "local"
    title: str
    media_type: str  # "image" or "video"
    thumb_url: str
    preview_url: str
    download_url: str
    description: str = ""
    author: str = ""
    author_url: str = ""
    license: str = "Free to use"
    width: int = 1920
    height: int = 1080
    duration: float = 0.0  # in seconds for video
    aspect_ratio: str = "16:9"  # "16:9", "9:16", "1:1"
    orientation: str = "landscape"  # "landscape", "portrait", "square"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["url"] = self.download_url
        d["media_url"] = self.download_url
        credit_parts = [self.provider.capitalize()]
        if self.author:
            credit_parts.append(self.author)
        d["source_credit"] = f"Source: {' / '.join(credit_parts)}"
        return d

class BaseMediaProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        pass

    @abstractmethod
    def check_connection(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def search_images(
        self,
        query: str,
        page: int = 1,
        limit: int = 12,
        orientation: Optional[str] = None
    ) -> List[MediaAsset]:
        pass

    @abstractmethod
    def search_videos(
        self,
        query: str,
        page: int = 1,
        limit: int = 12,
        orientation: Optional[str] = None,
        duration: Optional[int] = None
    ) -> List[MediaAsset]:
        pass
