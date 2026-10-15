import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from app.core.config import settings
from app.core.models import ProjectState, MotionGraphicItem
from app.services.project_manager import project_manager

VISUAL_MEDIA_TEMPLATES = {
    'split_screen_vertical',
    'youtube_insert',
    'broll_cutaway',
    'side_by_side',
    'picture_in_picture',
    'image_overlay',
    'video_overlay'
}

def is_visual_media_graphic(g: Any) -> bool:
    """Determine if a graphic item acts as visual media cutaway or underlay."""
    template_id = getattr(g, 'template_id', '') or ''
    media_url = getattr(g, 'media_url', None) or ''
    track = getattr(g, 'track', '') or ''
    
    if template_id in VISUAL_MEDIA_TEMPLATES and media_url:
        return True
    if track in ('V2', 'V3', 'V4') and media_url:
        return True
    return False

def merge_intervals(intervals: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Merge overlapping or contiguous [start, end] intervals."""
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_intervals[0]]
    for current in sorted_intervals[1:]:
        prev_start, prev_end = merged[-1]
        if current[0] <= prev_end + 0.15:
            merged[-1] = (prev_start, max(prev_end, current[1]))
        else:
            merged.append(current)
    return merged

def calculate_media_coverage(project_id: str) -> Dict[str, Any]:
    """Calculate visual media coverage metrics and list uncovered gaps."""
    state = project_manager.get_project(project_id)
    if not state:
        return {
            'total_duration': 0.0,
            'covered_duration': 0.0,
            'coverage_ratio': 0.0,
            'coverage_percentage': 0.0,
            'media_count': 0,
            'gaps': []
        }
    
    total_duration = float(state.duration_seconds or 0.0)
    if total_duration <= 0 and state.captions:
        total_duration = max(c.end for c in state.captions)
    if total_duration <= 0 and state.graphics:
        total_duration = max(g.end for g in state.graphics)
    total_duration = max(total_duration, 1.0)
    
    media_intervals: List[Tuple[float, float]] = []
    media_count = 0
    for g in state.graphics:
        if is_visual_media_graphic(g):
            media_count += 1
            s = max(0.0, float(g.start))
            e = min(total_duration, float(g.end))
            if e > s:
                media_intervals.append((s, e))
                
    merged = merge_intervals(media_intervals)
    covered_duration = sum(e - s for s, e in merged)
    coverage_ratio = min(1.0, covered_duration / total_duration)
    coverage_percentage = round(coverage_ratio * 100.0, 1)
    
    gaps: List[Dict[str, float]] = []
    last_end = 0.0
    for s, e in merged:
        if s - last_end >= 0.8:
            gaps.append({'start': round(last_end, 2), 'end': round(s, 2), 'duration': round(s - last_end, 2)})
        last_end = max(last_end, e)
    if total_duration - last_end >= 0.8:
        gaps.append({'start': round(last_end, 2), 'end': round(total_duration, 2), 'duration': round(total_duration - last_end, 2)})
        
    return {
        'total_duration': round(total_duration, 2),
        'covered_duration': round(covered_duration, 2),
        'coverage_ratio': round(coverage_ratio, 4),
        'coverage_percentage': coverage_percentage,
        'media_count': media_count,
        'gaps': gaps
    }

def get_available_assets(project_id: str) -> List[Dict[str, Any]]:
    """List all downloaded authentic videos and images with metadata."""
    pdir = settings.projects_dir / project_id
    downloaded_dir = pdir / 'media' / 'downloaded'
    if not downloaded_dir.exists():
        return []
    
    assets = []
    for f in sorted(downloaded_dir.iterdir()):
        if f.suffix.lower() in ('.mp4', '.mov', '.webm', '.jpg', '.jpeg', '.png', '.webp'):
            meta_file = f.with_suffix('.json')
            meta = {}
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text())
                except Exception:
                    pass
            is_video = f.suffix.lower() in ('.mp4', '.mov', '.webm')
            assets.append({
                'filename': f.name,
                'path': str(f),
                'media_url': f'/api/media/{project_id}/asset/downloaded/{f.name}',
                'type': 'video' if is_video else 'image',
                'title': meta.get('title') or meta.get('query') or f.stem,
                'description': meta.get('description') or meta.get('alt') or ''
            })
    return assets

def split_gap_by_speech(gap_start: float, gap_end: float, captions: list) -> List[Tuple[float, float, str]]:
    """Split a gap into natural 2.5s - 6s editorial segments aligned to spoken sentences."""
    gap_dur = gap_end - gap_start
    if gap_dur <= 5.5:
        # Single segment
        text = ' '.join(c.text.lower() for c in captions if (c.start <= gap_end and c.end >= gap_start))
        return [(gap_start, gap_end, text)]
        
    # Find captions inside this gap
    inside_caps = [c for c in captions if (c.start >= gap_start - 0.2 and c.end <= gap_end + 0.2)]
    if not inside_caps:
        # Uniform 4s subdivision
        segments = []
        cur = gap_start
        while cur < gap_end:
            nxt = min(gap_end, cur + 4.5)
            segments.append((round(cur, 2), round(nxt, 2), ''))
            cur = nxt
        return segments
        
    # Target segment length ~3.5 to 5.0 seconds
    segments = []
    cur_start = gap_start
    cur_text = []
    for c in inside_caps:
        cur_text.append(c.text.lower())
        if c.end - cur_start >= 3.2 and (gap_end - c.end >= 2.2):
            segments.append((round(cur_start, 2), round(c.end, 2), ' '.join(cur_text)))
            cur_start = c.end
            cur_text = []
            
    if gap_end > cur_start:
        segments.append((round(cur_start, 2), round(gap_end, 2), ' '.join(cur_text)))
        
    return segments

def maximize_media_density(project_id: str, target_coverage: float = 0.85) -> Dict[str, Any]:
    """Compatibility entry point: density must use the reviewed editorial pipeline.

    Cached file names and keyword overlap are not evidence of visual relevance.
    Never replace curated graphics or resurrect rejected items in a second pass.
    """
    if not project_manager.get_project(project_id):
        raise ValueError(f'Project {project_id} not found')
    return {
        'success': False, 'status': 'requires_reviewed_edit', 'added_count': 0,
        'added_titles_count': 0, 'metrics': calculate_media_coverage(project_id),
        'message': 'Use Review automatic edit to find more visuals with speech alignment and media review. Unreviewed gap filling has been removed.'
    }


def generate_hook_title_graphics(state: ProjectState) -> List[MotionGraphicItem]:
    """Legacy hook synthesis is disabled; titles require reviewed verbatim phrases."""
    return []
