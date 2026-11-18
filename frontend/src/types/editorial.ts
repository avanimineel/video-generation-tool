/** Center-anchored normalized rectangle in 0–1 preview frame space. */
export type CenterRect = [center_x: number, center_y: number, w: number, h: number];

export type AspectPreset = "reels" | "youtube" | "none";
export type DomainProfile = "general" | "medical" | "sports";
export type TemplateFamily = "text_title" | "callout" | "split_broll" | "article_card";

export interface PlatformDeadZones {
  preset: AspectPreset;
  rects: CenterRect[];
  safe_bounds: [x_min: number, y_min: number, x_max: number, y_max: number];
}

export const DEAD_ZONES: Record<AspectPreset, { rects: CenterRect[]; safe_bounds: PlatformDeadZones["safe_bounds"] }> = {
  reels: {
    rects: [[0.5, 0.06, 1, 0.12], [0.5, 0.91, 1, 0.18], [0.93, 0.5, 0.14, 1]],
    safe_bounds: [0.04, 0.12, 0.86, 0.82],
  },
  youtube: {
    rects: [[0.5, 0.05, 1, 0.1], [0.5, 0.94, 1, 0.12]],
    safe_bounds: [0.04, 0.1, 0.96, 0.88],
  },
  none: { rects: [], safe_bounds: [0, 0, 1, 1] },
};

export type RectDelta = [dx: number, dy: number, dw: number, dh: number];
export type BoundarySnapType = "shot_cut_next_frame" | "whisper_gap" | "word_start" | "none";

export interface CameraTransform {
  crop: [x_min: number, y_min: number, x_max: number, y_max: number];
  zoom: number;
  pan_x: number;
  pan_y: number;
}

export interface PlacementRecord {
  segment_id: string;
  raw_start_sec: number;
  raw_end_sec: number;
  start_sec: number;
  end_sec: number;
  start_snap: BoundarySnapType;
  end_snap: BoundarySnapType;
  crosses_cut: boolean;
  intervene: boolean;
  template_id: string;
  template_family: TemplateFamily | null;
  screen_rect: CenterRect;
  pos_x: number;
  pos_y: number;
  user_scale: number;
  effective_scale: number;
  avoid_rects: CenterRect[];
}

export type EditEvent =
  | { type: "move"; timestamp: string; delta: RectDelta; old_rect: CenterRect; new_rect: CenterRect; old_rect_hit_avoid: boolean }
  | { type: "retime"; timestamp: string; delta_start: number; delta_end: number }
  | { type: "swap_template"; timestamp: string; from_template: string; to_template: string; same_family: boolean }
  | { type: "cut"; timestamp: string; refused_rect: CenterRect; geometric_hint: "overlapping_cue" | "too_dense" | "false_positive" | "none" };

export interface DecisionFeedbackRow {
  cue_id: string;
  project_id: string;
  source: "live_editor" | "fcpxml_import";
  final_decision: "keep" | "cut" | "swap" | "manual_add";
  edits: EditEvent[];
  editor_notes?: string;
}
