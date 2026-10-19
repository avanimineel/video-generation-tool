from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from sqlmodel import SQLModel, Field as DBField

# --- Caption and Subtitle Schemas ---

class WordTiming(BaseModel):
    word: str
    start: float
    end: float
    highlight: bool = False
    is_keyword: bool = False
    keyword_category: Optional[str] = None
    keyword_font: Optional[str] = None
    keyword_color: Optional[str] = None

class CaptionStyle(BaseModel):
    font_family: str = "Montserrat"
    font_weight: str = "bold"
    font_size: int = 42
    text_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    outline_width: int = 2
    shadow_color: str = "rgba(0,0,0,0.7)"
    shadow_blur: int = 4
    shadow_offset_x: int = 2
    shadow_offset_y: int = 2
    has_background: bool = True
    background_color: str = "#000000"
    background_opacity: float = 0.75
    corner_radius: int = 16
    padding_x: int = 18
    padding_y: int = 10
    line_height: float = 1.2
    letter_spacing: float = 0.5
    text_align: str = "center"
    is_uppercase: bool = False
    animation_type: str = "none"
    highlight_active_color: str = "#CCFF00"
    highlight_past_color: str = "#B0B0B0"
    highlight_future_color: str = "#FFFFFF"
    highlight_scale: float = 1.0
    highlight_bounce: bool = False
    max_lines: int = 1
    has_highlight: bool = False
    has_shadow: bool = True
    pacing_mode: str = "full_line"
    has_keyword_emphasis: bool = False
    keyword_accent_color: str = "#CCFF00"
    keyword_font_family: str = "Playfair Display"
    keyword_contrast_badge: bool = True
    contrast_block_mode: str = "pill"

class CaptionItem(BaseModel):
    id: str
    start: float
    end: float
    text: str
    pos_x: float = 0.5
    pos_y: float = 0.82
    words: List[WordTiming] = Field(default_factory=list)
    style: CaptionStyle = Field(default_factory=CaptionStyle)
    source_language: str = "en"
    source_caption_ids: List[str] = Field(default_factory=list)
    timing_basis: str = "unverified"
    translated_text: Optional[str] = None
    pos_x_during_graphic: Optional[float] = None
    pos_y_during_graphic: Optional[float] = None

# --- Motion Graphic Schema ---

class MotionGraphicItem(BaseModel):
    id: str
    start: float
    end: float
    template_id: str
    title: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    pos_x: float = 0.5
    pos_y: float = 0.5
    scale: float = 1.0
    media_url: Optional[str] = None
    media_type: Optional[str] = "image"
    fusion_comp_code: Optional[str] = None
    track: Optional[str] = "V3"
    placement_mode: Optional[str] = "overlay"  # "overlay" or "insert"
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    animation: Optional[str] = "none"  # "none", "slow_zoom_in", "slow_zoom_out", "pan_left", "pan_right"
    split_layout: Optional[str] = "none"  # "none", "split_50_50_vertical", "pip_top_right", "pip_bottom_right"

# --- Audio beds (licensed music) ---

class AudioTrackItem(BaseModel):
    id: str
    title: str
    type: str = "music"  # "music" or "sfx"
    url: str = ""
    duration: float = 0.0
    start: float = 0.0
    volume: float = 0.35  # 0..1 of full scale, before ducking
    duck_under_speech: bool = True
    music_id: Optional[str] = None  # Openverse id; the file lives in the shared music cache.
    license: Optional[str] = None
    attribution: Optional[str] = None
    credit_required: bool = False

# --- Project Settings ---

class ProjectSettings(BaseModel):
    aspect_ratio: str = "9:16"
    safe_area_guide: bool = True
    center_snapping: bool = True
    default_brand_preset: str = "podcast_lime_minimal"
    brand_preset: str = "documentary_minimalist"
    corner_bug_enabled: bool = False
    corner_bug_text: str = "ARCHIVE DOCS"
    davinci_project_name: Optional[str] = None
    davinci_timeline_name: Optional[str] = None
    sub_lines_mode: int = 1

# --- Full Project State (Saved to project.json & SQLite) ---

class ProjectState(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str
    source_media_path: Optional[str] = None
    proxy_media_path: Optional[str] = None
    waveform_data: List[float] = Field(default_factory=list)
    duration_seconds: float = 0.0
    fps: float = 30.0
    settings: ProjectSettings = Field(default_factory=ProjectSettings)
    captions: List[CaptionItem] = Field(default_factory=list)
    graphics: List[MotionGraphicItem] = Field(default_factory=list)
    detected_language: str = "en"
    ai_ingestion: Optional[Dict[str, Any]] = Field(default_factory=dict)
    audio_tracks: List[AudioTrackItem] = Field(default_factory=list)

# --- SQLModel Database Table for Fast Querying & Relinking ---

class ProjectRecord(SQLModel, table=True):
    __tablename__ = "projects"
    
    id: str = DBField(primary_key=True)
    name: str = DBField(index=True)
    created_at: str
    updated_at: str
    source_media_path: Optional[str] = None
    proxy_media_path: Optional[str] = None
    duration_seconds: float = 0.0
    aspect_ratio: str = "9:16"
    caption_count: int = 0
    graphic_count: int = 0
    davinci_project_name: Optional[str] = None
    davinci_timeline_name: Optional[str] = None
