export interface WordTiming {
  word: string;
  start: number;
  end: number;
  highlight?: boolean;
  is_keyword?: boolean;
  keyword_category?: 'condition' | 'organ' | 'metric' | 'impact';
  keyword_font?: string;
  keyword_color?: string;
}

export interface CaptionStyle {
  font_family: string;
  font_weight: string;
  font_size: number;
  text_color: string;
  outline_color: string;
  outline_width: number;
  shadow_color: string;
  shadow_blur: number;
  shadow_offset_x: number;
  shadow_offset_y: number;
  has_background: boolean;
  background_color: string;
  background_opacity: number;
  corner_radius: number;
  padding_x: number;
  padding_y: number;
  line_height: number;
  letter_spacing: number;
  text_align: 'left' | 'center' | 'right';
  is_uppercase: boolean;
  animation_type: 'none' | 'pop' | 'fade' | 'slide_up' | 'bounce' | 'word_reveal';
  highlight_active_color: string;
  highlight_past_color: string;
  highlight_future_color: string;
  highlight_scale: number;
  highlight_bounce: boolean;
  max_lines?: 1 | 2 | 3;
  has_highlight?: boolean;
  has_shadow?: boolean;
  pacing_mode?: 'full_line' | 'word_reveal' | 'phrase_chunk';
  has_keyword_emphasis?: boolean;
  keyword_accent_color?: string;
  keyword_font_family?: string;
  keyword_contrast_badge?: boolean;
  contrast_block_mode?: 'pill' | 'per_word' | 'solid_box';
}

export interface CaptionItem {
  id: string;
  start: number;
  end: number;
  text: string;
  pos_x: number; // normalized 0..1
  pos_y: number; // normalized 0..1
  pos_x_during_graphic?: number; // custom position when graphics/split-screen active
  pos_y_during_graphic?: number; // custom position when graphics/split-screen active
  words: WordTiming[];
  style: CaptionStyle;
  source_language: string;
  translated_text?: string | null;
}

export interface MotionGraphicItem {
  id: string;
  start: number;
  end: number;
  template_id: string;
  title: string;
  parameters: Record<string, any>;
  pos_x: number;
  pos_y: number;
  scale: number;
  media_url?: string;
  media_type?: 'image' | 'video';
  fusion_comp_code?: string | null;
  track?: 'V3' | 'V4' | 'V5';
  placement_mode?: 'overlay' | 'insert';
  source_name?: string;
  source_url?: string;
  author?: string;
  license?: string;
  animation?: 'none' | 'slow_zoom_in' | 'slow_zoom_out' | 'push_in' | 'pan_left' | 'pan_right' | 'tilt_up' | 'tilt_down' | 'crane_up' | 'dutch' | 'handheld';
  split_layout?: 'none' | 'split_50_50_vertical' | 'pip_top_right' | 'pip_bottom_right';
}

export interface ProjectSettings {
  aspect_ratio: '9:16' | '16:9' | '1:1';
  safe_area_guide: boolean;
  center_snapping: boolean;
  default_brand_preset: string;
  brand_preset?: 'documentary_minimalist' | 'medical_evidence' | 'podcast_lime';
  corner_bug_enabled?: boolean;
  corner_bug_text?: string;
  davinci_project_name?: string | null;
  davinci_timeline_name?: string | null;
  sub_lines_mode?: 1 | 2;
}

export interface AudioTrackItem {
  id: string;
  title: string;
  type: 'music' | 'sfx';
  url: string;
  duration: number;
  start: number;
  volume: number; // 0..1
  duck_under_speech?: boolean;
  music_id?: string;
  license?: string;
  attribution?: string;
  credit_required?: boolean;
}

export interface ProjectState {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  source_media_path?: string | null;
  proxy_media_path?: string | null;
  video_url?: string | null;
  waveform_data: number[];
  duration_seconds: number;
  fps: number;
  settings: ProjectSettings;
  captions: CaptionItem[];
  graphics: MotionGraphicItem[];
  audio_tracks?: AudioTrackItem[];
  detected_language: string;
  ai_ingestion?: Record<string, any>;
}

export interface ProjectSummary {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  duration_seconds: number;
  aspect_ratio: string;
  caption_count: number;
  graphic_count: number;
  source_media_path?: string | null;
  source_media_exists: boolean;
  davinci_project_name?: string | null;
  davinci_timeline_name?: string | null;
}

export interface DaVinciStatus {
  is_running: boolean;
  is_connected: boolean;
  project_name?: string | null;
  timeline_name?: string | null;
  fps: number;
  script_api_available: boolean;
}

export interface GraphicTemplate {
  id: string;
  name: string;
  category: string;
  description: string;
  default_params: Record<string, any>;
}

export interface DynamicGraphicSample {
  sample_id: string;
  beat_id: string;
  start_time: number;
  end_time: number;
  duration_seconds: number;
  beat_type: 'hook' | 'payoff' | 'evidence' | 'narrative';
  mode: 'background_only' | 'full_sequence';
  style_preset: string;
  prompt: string;
  reason: string;
  category_pattern: string;
  pattern_confidence: string;
  camera_motion: string;
  overlay_headline: string;
  template_id: string;
  parameters: Record<string, any>;
  dialogue_snippet?: string;
  visual_type?: string;
  motion_intensity?: string;
}

export interface DynamicSamplesResponse {
  category: string;
  total_runtime_seconds: number;
  total_beats_count: number;
  enhanced_beats_count: number;
  total_enhanced_seconds: number;
  budget_pct_used: number;
  max_budget_pct: number;
  patterns: Array<{
    pattern: string;
    support_count: number;
    confidence: string;
  }>;
  samples: DynamicGraphicSample[];
}

export interface TwelveLabsCredits {
  has_api_key: boolean;
  total_credit_minutes: number;
  consumed_minutes: number;
  consumed_seconds: number;
  remaining_minutes: number;
  one_minute_videos_left: number;
  percent_used: number;
  expiry_date: string;
  days_remaining: number;
  is_expired: boolean;
}

export interface EditorialDecision {
  id: string;
  project_id: string;
  cue_id: string;
  decision: 'keep' | 'cut' | 'swap';
  transcript_context: string;
  reasoning: string;
  strength: number;
  graphic_type: string;
  start_sec: number;
  end_sec: number;
  search_query: string;
  selected_asset?: Record<string, any>;
  swap_details?: Record<string, any>;
  final_decision?: Record<string, any>;
  editor_notes?: string;
  created_at: string;
  updated_at?: string;
}

export interface FeedbackStats {
  total_decisions: number;
  kept: number;
  cut: number;
  swapped: number;
  keep_rate_pct: number;
  cut_rate_pct: number;
  swap_rate_pct: number;
  avg_strength: number;
  summary_text: string;
  by_graphic_type: Record<string, { total: number; keep: number; cut: number; swap: number }>;
}

export interface FewShotExportResponse {
  total_exported: number;
  positive_count: number;
  negative_count: number;
  modified_count: number;
  markdown: string;
}


