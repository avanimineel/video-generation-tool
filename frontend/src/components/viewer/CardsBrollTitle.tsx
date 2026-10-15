import React, { useEffect, useMemo, useRef } from 'react';
import { BACKEND_ORIGIN } from '../../services/api';
import { MotionGraphicItem } from '../../types';

function MiniVideo({ src, time, playing }: { src: string; time: number; playing: boolean }) {
  const ref = useRef<HTMLVideoElement>(null);
  const resolveUrl = (url: string) => {
    if (!url) return '';
    if (url.startsWith('http://') || url.startsWith('https://')) return url;
    if (url.startsWith('/api/')) return `${BACKEND_ORIGIN}${url}`;
    return url;
  };
  const sync = () => {
    const v = ref.current;
    if (!v || v.readyState < 1) return;
    const target = Number.isFinite(v.duration) && v.duration > 0 ? Math.max(0, time) % v.duration : Math.max(0, time);
    if (Math.abs(v.currentTime - target) > 0.2) v.currentTime = target;
    if (playing) void v.play().catch(() => {});
    else v.pause();
  };
  useEffect(sync, [src, time, playing]);
  return <video ref={ref} src={resolveUrl(src)} muted playsInline preload="auto" onLoadedMetadata={sync} className="w-full h-full object-cover" />;
}

interface CardsBrollTitleProps {
  graphic: MotionGraphicItem;
  time: number;
  width: number;
  height: number;
  isPlaying?: boolean;
}

export const CardsBrollTitle: React.FC<CardsBrollTitleProps> = ({
  graphic,
  time,
  width,
  height,
  isPlaying = false,
}) => {
  const p = graphic.parameters || {};
  const mask = p.subject_mask;

  // Preload subject mask frames for seamless playback
  useEffect(() => {
    if (!mask || !mask.count || !mask.prefix) return;
    const images = Array.from({ length: mask.count }, (_, i) => {
      const img = new Image();
      img.src = `${BACKEND_ORIGIN}${mask.prefix}${String(i).padStart(5, '0')}.png`;
      return img;
    });
    return () => {
      images.forEach((img) => {
        img.onload = null;
      });
    };
  }, [mask?.prefix, mask?.count]);

  const elapsedTotal = Math.max(0, time - graphic.start);
  const duration = Math.max(0.1, graphic.end - graphic.start);
  const exit = Math.min(1, Math.max(0, (graphic.end - time) / 0.25));
  const prog = Math.min(1, elapsedTotal / 0.35);

  // Compute mask URL if mask data exists
  let maskUrl: string | null = null;
  if (mask && mask.count && mask.prefix) {
    const frame = Math.min(mask.count - 1, Math.max(0, Math.floor((time - mask.start) * mask.fps)));
    maskUrl = `${BACKEND_ORIGIN}${mask.prefix}${String(frame).padStart(5, '0')}.png`;
  }

  // Cards data
  const userCards = useMemo(() => {
    if (Array.isArray(p.card_media) && p.card_media.length > 0) {
      return p.card_media;
    }
    return [];
  }, [p.card_media]);

  // Typography lines & independent font resolution
  const lines = Array.isArray(p.title_lines) ? p.title_lines : [{ text: p.headline || graphic.title, offset: 0 }];
  let topText = '';
  let midText = '';
  let scriptText = '';

  let topFont = '';
  let midFont = '';
  let scriptFont = '';

  let topColor = '';
  let midColor = '';
  let scriptColor = '';

  if (lines.length === 2) {
    // 2-line cards layout: Line 0 is subject headline, Line 1 is cursive script accent
    midText = lines[0]?.text || '';
    scriptText = lines[1]?.text || '';
    midFont = lines[0]?.font_family || p.font_family || '"Montserrat", "Arial Black", Arial, sans-serif';
    scriptFont = lines[1]?.font_family || p.script_font_family || p.secondary_font_family || '"Snell Roundhand", "Caveat", "Dancing Script", cursive';
    midColor = lines[0]?.color || p.primary_color || '#FFE600';
    scriptColor = lines[1]?.color || p.accent_color || '#027500';
  } else if (lines.length >= 3) {
    topText = lines[0]?.text || '';
    midText = lines[1]?.text || '';
    scriptText = lines[2]?.text || '';
    topFont = lines[0]?.font_family || p.font_family || '"Montserrat", "Arial Black", Arial, sans-serif';
    midFont = lines[1]?.font_family || p.font_family || '"Montserrat", "Arial Black", Arial, sans-serif';
    scriptFont = lines[2]?.font_family || p.script_font_family || p.secondary_font_family || '"Snell Roundhand", "Caveat", "Dancing Script", cursive';
    topColor = lines[0]?.color || '#F1F5F9';
    midColor = lines[1]?.color || p.primary_color || '#FFE600';
    scriptColor = lines[2]?.color || p.accent_color || '#027500';
  } else {
    // 1-line fallback
    midText = lines[0]?.text || p.headline || graphic.title || '';
    midFont = lines[0]?.font_family || p.font_family || '"Montserrat", "Arial Black", Arial, sans-serif';
    midColor = lines[0]?.color || p.primary_color || '#FFFFFF';
  }

  const customPrimaryColor = p.primary_color || '#FFFFFF';
  const customAccentColor = p.accent_color || '#FBBF24';
  const scale = graphic.scale ?? p.scale ?? 1.0;
  const posY = (graphic.pos_y ?? 0.5) * 100;
  const posX = (graphic.pos_x ?? 0.5) * 100;

  const resolveUrl = (url: string) => {
    if (!url) return '';
    if (url.startsWith('http://') || url.startsWith('https://')) return url;
    if (url.startsWith('/api/')) return `${BACKEND_ORIGIN}${url}`;
    return url;
  };

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        width,
        height,
        pointerEvents: 'none',
        zIndex: 15,
        opacity: exit,
      }}
    >
      {/* LAYER 1: MASKED BACKGROUND (Black band and floating mini cards rendered BEHIND speaker) */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          width,
          height,
          pointerEvents: 'none',
          ...(maskUrl
            ? {
                maskImage: `url("${maskUrl}")`,
                WebkitMaskImage: `url("${maskUrl}")`,
                maskSize: '100% 100%',
                WebkitMaskSize: '100% 100%',
                maskRepeat: 'no-repeat',
              }
            : {}),
        }}
      >
        {/* Semi-translucent dark band behind speaker */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: `${posY - 15}%`,
            height: `${height * 0.30}px`,
            backgroundColor: 'rgba(0, 0, 0, 0.58)',
            backdropFilter: 'blur(3px)',
            opacity: prog,
            boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
          }}
        />

        {/* Floating tilted Polaroid mini-cards in background */}
        <div
          style={{
            position: 'absolute',
            left: `${posX}%`,
            top: `${posY}%`,
            transform: `translate(-50%, -50%) scale(${scale})`,
            width: width * 0.95,
            height: height * 0.30,
            pointerEvents: 'none',
          }}
        >
          {userCards.slice(0, 3).map((card: any, i: number) => {
            const tilts = [-8, 7, -3];
            const lefts = ['2%', '68%', '34%'];
            const tops = [-45, -35, 75];
            const delayOffset = i * 0.08;
            const cardProg = Math.min(1, Math.max(0, (elapsedTotal - delayOffset) / 0.3));
            const yFloat = (1 - cardProg) * 16;

            return (
              <div
                key={card.url || i}
                style={{
                  position: 'absolute',
                  width: width * 0.30,
                  height: width * 0.22,
                  left: lefts[i],
                  top: tops[i],
                  transform: `rotate(${tilts[i]}deg) translateY(${yFloat}px)`,
                  boxShadow: '0 10px 28px rgba(0,0,0,0.85)',
                  border: '2.5px solid rgba(255,255,255,0.92)',
                  borderRadius: 6,
                  overflow: 'hidden',
                  opacity: cardProg,
                }}
              >
                {card.type === 'video' ? (
                  <MiniVideo src={card.url} time={elapsedTotal} playing={isPlaying} />
                ) : (
                  <img
                    src={resolveUrl(card.url)}
                    alt="Supporting visual"
                    className="w-full h-full object-cover"
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* LAYER 2: UNMASKED FOREGROUND TYPOGRAPHY (Stands cleanly in FRONT of speaker) */}
      <div
        style={{
          position: 'absolute',
          left: `${posX}%`,
          top: `${posY}%`,
          transform: `translate(-50%, -50%) scale(${scale})`,
          width: width * 0.95,
          zIndex: 25,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
          pointerEvents: 'none',
        }}
        className="drop-shadow-[0_4px_16px_rgba(0,0,0,0.9)]"
      >
        {topText && (
          <div
            style={{
              fontFamily: topFont,
              fontSize: width * 0.048,
              color: topColor,
              letterSpacing: '0.04em',
              textShadow: '0 2px 10px rgba(0,0,0,0.9), 0 1px 3px rgba(0,0,0,0.8)',
            }}
            className="font-semibold tracking-wide"
          >
            {topText}
          </div>
        )}

        {midText && (
          <div
            style={{
              fontFamily: midFont,
              fontSize: width * 0.086,
              color: midColor,
              letterSpacing: '-0.02em',
              textShadow: '0 3px 14px rgba(0,0,0,0.95), 0 1px 4px rgba(0,0,0,0.9)',
              marginTop: 2,
            }}
            className="font-black uppercase tracking-tight"
          >
            {midText}
          </div>
        )}

        {scriptText && (
          <div
            style={{
              fontFamily: scriptFont,
              fontSize: Math.min(width * 0.11, (width * 0.9) / Math.max(1, scriptText.length * 0.45)),
              color: scriptColor,
              marginTop: -width * 0.015,
              textShadow: '0 3px 12px rgba(0,0,0,0.9), 0 0 20px rgba(251,191,36,0.35)',
              transform: 'rotate(-2deg)',
              whiteSpace: 'nowrap',
            }}
            className="font-bold"
          >
            {scriptText}
          </div>
        )}
      </div>
    </div>
  );
};
