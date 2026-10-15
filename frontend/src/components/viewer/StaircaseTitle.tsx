import React, { useMemo } from 'react';
import { MotionGraphicItem } from '../../types';

interface StaircaseTitleProps {
  graphic: MotionGraphicItem;
  time: number;
  width: number;
  height: number;
  captions?: any[];
}

export const StaircaseTitle: React.FC<StaircaseTitleProps> = ({
  graphic,
  time,
  width,
  height,
  captions = [],
}) => {
  const p = graphic.parameters || {};
  const exit = Math.min(1, Math.max(0, (graphic.end - time) / 0.25));

  // Extract words
  const words = useMemo(() => {
    if (Array.isArray(p.title_lines) && p.title_lines.length > 1) {
      return p.title_lines.map((l: any) => String(l.text || '').trim()).filter(Boolean);
    }
    const raw = String(p.headline || graphic.title || '').trim();
    return raw.split(/\s+/).filter(Boolean);
  }, [p.title_lines, p.headline, graphic.title]);

  const total = words.length;

  // Extract or build timed_words
  const timedWords = useMemo(() => {
    if (Array.isArray(p.timed_words) && p.timed_words.length > 0) {
      return p.timed_words;
    }
    // Auto-extract from captions if available
    const extracted: Array<{ text: string; start: number; end: number; offset: number; duration: number }> = [];
    if (captions && captions.length > 0) {
      captions.forEach((cap) => {
        if (cap.words && Array.isArray(cap.words)) {
          cap.words.forEach((w: any) => {
            if (w.start >= graphic.start - 0.2 && w.end <= graphic.end + 0.3) {
              extracted.push({
                text: String(w.word || '').trim(),
                start: w.start,
                end: w.end,
                offset: Math.max(0, w.start - graphic.start),
                duration: Math.max(0.15, w.end - w.start),
              });
            }
          });
        }
      });
    }
    return extracted;
  }, [p.timed_words, captions, graphic.start, graphic.end]);

  const customFont = p.font_family || '"Montserrat Black", "Arial Black", Arial, sans-serif';
  const customPrimaryColor = p.primary_color || '#FFFFFF';
  const customAccentColor = p.accent_color || '#FFE600';

  const baseFontSize = Math.min(
    width * 0.082,
    Math.max(16, width * (total > 8 ? 0.054 : total > 5 ? 0.065 : 0.078))
  );

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        width,
        height,
        pointerEvents: 'none',
        zIndex: 22,
        opacity: exit,
      }}
    >
      {words.map((word: string, idx: number) => {
        // Find matching timed word
        const cleanWord = word.toLowerCase().replace(/[^a-z0-9]/g, '');
        const tw = timedWords.find(
          (t) => t.text.toLowerCase().replace(/[^a-z0-9]/g, '') === cleanWord
        );

        const offset = tw ? Number(tw.offset || 0) : idx * 0.26;
        const dur = tw ? Number(tw.duration || 0.28) : 0.28;
        const wordStart = graphic.start + offset;
        const wordEnd = wordStart + dur;

        const isCurrentWord = time >= wordStart && time <= wordEnd;
        const hasBeenSpoken = time >= wordStart;
        const wordProg = Math.min(1, Math.max(0, (time - wordStart) / Math.max(0.1, dur)));
        const eased = 1 - Math.pow(1 - wordProg, 3);

        // Halo Body Arch Formula framing head & shoulders
        // idx 0 (left shoulder/ear) -> middle (crown over head) -> last (right shoulder/ear)
        const t = total > 1 ? idx / (total - 1) : 0.5;
        const archAngle = (t - 0.5) * Math.PI * 0.65; // -58.5 deg to +58.5 deg
        const radiusX = width * 0.38;
        const radiusY = height * 0.15;
        const posX = width * 0.50 + radiusX * Math.sin(archAngle);
        const posY = height * 0.22 - radiusY * (Math.cos(archAngle) - 1);
        const tiltDeg = (t - 0.5) * 28;

        const scale = isCurrentWord
          ? 1.15
          : hasBeenSpoken
          ? 0.92 + 0.08 * eased
          : 0.75;

        const color = isCurrentWord ? customAccentColor : customPrimaryColor;
        const opacity = hasBeenSpoken ? Math.min(1, wordProg * 2) * exit : 0;

        return (
          <div
            key={idx}
            style={{
              position: 'absolute',
              left: `${posX}px`,
              top: `${posY}px`,
              opacity,
              transform: `translate(-50%, -50%) rotate(${tiltDeg}deg) scale(${scale})`,
              fontFamily: customFont,
              fontSize: `${baseFontSize}px`,
              color,
              lineHeight: 1,
              letterSpacing: '-0.02em',
              textShadow: isCurrentWord
                ? `0 0 20px ${customAccentColor}, 0 2px 10px rgba(0,0,0,0.95), 0 0 35px ${customAccentColor}88`
                : '0 2px 10px rgba(0,0,0,0.95), 0 1px 3px rgba(0,0,0,0.9)',
              WebkitTextStroke: isCurrentWord ? '0.5px rgba(0,0,0,0.4)' : 'none',
              transition: 'color 0.15s ease, transform 0.15s cubic-bezier(0.34, 1.56, 0.64, 1)',
            }}
            className="font-black uppercase whitespace-nowrap"
          >
            {word}
          </div>
        );
      })}
    </div>
  );
};
