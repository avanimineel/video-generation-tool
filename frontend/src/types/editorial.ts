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

export interface EditEvent {
  type: "move" | "retime" | "swap_template" | "cut";
  timestamp: string;
  delta_center?: [number, number, number, number];
  old_rect?: CenterRect;
  new_rect?: CenterRect;
  old_rect_hit_avoid?: boolean;
  delta_start?: number;
  delta_end?: number;
  from_template?: string;
  to_template?: string;
  same_family?: boolean;
  refused_rect?: CenterRect;
  geometric_hint?: "overlapping_cue" | "too_dense" | "false_positive" | "none";
}
