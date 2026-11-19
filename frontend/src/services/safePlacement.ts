import { CenterRect, DEAD_ZONES, AspectPreset } from "../types/editorial";

type Box = { x1: number; y1: number; x2: number; y2: number };

const toBox = ([cx, cy, w, h]: CenterRect): Box => ({ x1: cx - w / 2, y1: cy - h / 2, x2: cx + w / 2, y2: cy + h / 2 });

const intersects = (a: Box, b: Box) => a.x1 < b.x2 && a.x2 > b.x1 && a.y1 < b.y2 && a.y2 > b.y1;

const clamp = (value: number, low: number, high: number) => Math.max(low, Math.min(high, value));

/** Closest 3x3 cell whose edges stay inside the safe bounds and miss avoid rects. */
export function findNextFreeSlot(current: CenterRect, avoid: CenterRect[], preset: AspectPreset): CenterRect | null {
  const zone = DEAD_ZONES[preset];
  const [xMin, yMin, xMax, yMax] = zone.safe_bounds;
  const width = current[2];
  const height = current[3];
  if (width > xMax - xMin || height > yMax - yMin) return null;
  const blocked = [...avoid, ...zone.rects].map(toBox);
  const cellW = (xMax - xMin) / 3;
  const cellH = (yMax - yMin) / 3;
  const seen = new Set<string>();
  const candidates: { rect: CenterRect; dist: number }[] = [];
  for (let row = 0; row < 3; row++) {
    for (let col = 0; col < 3; col++) {
      const centerX = clamp(xMin + cellW * (col + 0.5), xMin + width / 2, xMax - width / 2);
      const centerY = clamp(yMin + cellH * (row + 0.5), yMin + height / 2, yMax - height / 2);
      const key = `${centerX.toFixed(4)},${centerY.toFixed(4)}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const rect: CenterRect = [centerX, centerY, width, height];
      if (blocked.some(box => intersects(toBox(rect), box))) continue;
      const dx = centerX - current[0];
      const dy = centerY - current[1];
      candidates.push({ rect, dist: dx * dx + dy * dy });
    }
  }
  candidates.sort((a, b) => a.dist - b.dist);
  return candidates[0]?.rect ?? null;
}

export function presetForAspect(aspect: string): AspectPreset {
  if (aspect === "9:16") return "reels";
  if (aspect === "16:9") return "youtube";
  return "none";
}
