import { BehindSpeakerTitle } from "./BehindSpeakerTitle";
import { CardsBrollTitle } from "./CardsBrollTitle";
import { StaircaseTitle } from "./StaircaseTitle";
import { BACKEND_ORIGIN } from "../../services/api";
import React, { useRef, useState, useEffect } from "react";
import { 
  CheckCircle2, Flame, Heart, Activity, Dna, Shield, Key, 
  BatteryCharging, Stethoscope, Award, Youtube, Instagram, 
  Share2, Sparkles, AlertTriangle, FileText, Check, ArrowRight,
  Film, Scissors
} from "lucide-react";
import { CaptionItem, MotionGraphicItem, ProjectSettings } from "../../types";

const MEDICAL_CONDITIONS = new Set([
  'cancer', 'diabetes', 'hypertension', 'stroke', 'tumor', 'inflammation',
  'alzheimer', "alzheimer's", 'arrhythmia', 'sepsis', 'infection', 'dementia',
  'cholesterol', 'sclerosis', 'syndrome', 'disease', 'chronic', 'acute',
  'myocardial', 'infarction', 'cardiovascular', 'osteoporosis', 'arthritis'
]);

const ORGANS = new Set([
  'heart', 'brain', 'gut', 'liver', 'kidney', 'kidneys', 'lungs', 'lung',
  'pancreas', 'artery', 'arteries', 'neurons', 'neuron', 'mitochondria',
  'spine', 'vessels', 'vessel', 'blood', 'cells', 'cell', 'microbiome'
]);

const EMOTIONAL_TRIGGERS = new Set([
  'fatal', 'lethal', 'danger', 'breakthrough', 'miracle', 'critical',
  'emergency', 'toxic', 'cure', 'alert', 'warning', 'deadly', 'shocking',
  'secret', 'destroy', 'boost', 'protect'
]);

const checkIsKeyword = (wordStr: string) => {
  const clean = wordStr.toLowerCase().replace(/[^a-z0-9%]/g, '');
  if (/\d+[%xXmgkK]?/.test(wordStr) || ['double', 'triple', 'half', 'percent', 'zero'].includes(clean)) {
    return { isKw: true, cat: 'metric', color: '#00F0FF' };
  }
  if (MEDICAL_CONDITIONS.has(clean) || ['cancer', 'diabet', 'inflam', 'hyperten', 'stroke', 'tumor'].some(c => clean.includes(c))) {
    return { isKw: true, cat: 'condition', color: '#FF4D4D' };
  }
  if (ORGANS.has(clean) || ['cardio', 'neuro', 'mitochondr'].some(o => clean.includes(o))) {
    return { isKw: true, cat: 'organ', color: '#CCFF00' };
  }
  if (EMOTIONAL_TRIGGERS.has(clean)) {
    return { isKw: true, cat: 'impact', color: '#FFB800' };
  }
  return { isKw: false, cat: null, color: null };
};

interface CanvasOverlayProps {
  captions: CaptionItem[];
  graphics: MotionGraphicItem[];
  currentTime: number;
  isPlaying?: boolean;
  settings: ProjectSettings;
  selectedCaptionId: string | null;
  onSelectCaption: (id: string) => void;
  onUpdateCaptionPosition: (id: string, posX: number, posY: number, duringGraphic?: boolean) => void;
  activeLanguageView?: 'english' | 'hindi';
}

function localMediaUrl(src:string) {
  return src.startsWith('/api/') ? `${BACKEND_ORIGIN}${src}` : src;
}

export function TimelineVideo({
  src,
  time,
  playing,
  style,
  className,
  rate = 1
}: {
  src: string;
  time: number;
  playing: boolean;
  style?: React.CSSProperties;
  className?: string;
  rate?: number;
}) {
  const ref = useRef<HTMLVideoElement>(null);
  const sync = () => {
    const v = ref.current;
    if (!v || v.readyState < 1) return;
    const target = Number.isFinite(v.duration) && v.duration > 0 ? Math.max(0, time) % v.duration : Math.max(0, time);
    if (Math.abs(v.currentTime - target) > .2) v.currentTime = target;
    if (v.playbackRate !== rate) v.playbackRate = rate;
    if (playing) void v.play().catch(() => {}); else v.pause();
  };
  useEffect(sync, [src, time, playing, rate]);
  return (
    <video
      ref={ref}
      src={localMediaUrl(src)}
      muted
      playsInline
      preload="auto"
      onLoadedMetadata={sync}
      style={style}
      className={className || "w-full h-full object-cover"}
    />
  );
}

function SoundEffectsTrack({src,time,playing}:{src:string,time:number,playing:boolean}){
  const ref=useRef<HTMLAudioElement>(null);
  useEffect(()=>{const audio=ref.current;if(!audio)return;
    if(Math.abs(audio.currentTime-time)>.2)audio.currentTime=time;
    if(playing)void audio.play().catch(()=>{});else audio.pause();
  },[time,playing,src]);
  return <audio ref={ref} src={localMediaUrl(src)} preload="auto" />;
}

export const CanvasOverlay: React.FC<CanvasOverlayProps> = ({
  captions,
  graphics,
  currentTime,
  isPlaying=false,
  settings,
  selectedCaptionId,
  onSelectCaption,
  onUpdateCaptionPosition,
  activeLanguageView = 'english'
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [canvasScale,setCanvasScale]=useState(1);
  const referenceWidth=380;
  const referenceHeight=settings.aspect_ratio==='9:16'?380*16/9:380*9/16;
  useEffect(()=>{const el=containerRef.current;if(!el)return;const observer=new ResizeObserver(()=>setCanvasScale(el.clientWidth/referenceWidth));observer.observe(el);setCanvasScale(el.clientWidth/referenceWidth);return ()=>observer.disconnect()},[]);
  const [isDragging, setIsDragging] = useState(false);
  const [activeDragId, setActiveDragId] = useState<string | null>(null);
  const [showCenterSnap, setShowCenterSnap] = useState(false);

  // Respect speech end times; do not carry captions through silence or the outro.
  const visibleCaptions = captions.filter(c => currentTime >= c.start && currentTime < c.end);

  // Find currently visible motion graphics
  const visibleGraphics = graphics.filter(
    (g) => g.template_id !== "source_reframe" && currentTime >= g.start && currentTime < g.end
  );

  const activeGraphic = visibleGraphics[0] ?? null;
  const isGraphicActive = visibleGraphics.length > 0;

  // Handle Dragging
  const handleMouseDown = (e: React.MouseEvent, captionId: string) => {
    e.stopPropagation();
    setIsDragging(true);
    setActiveDragId(captionId);
    onSelectCaption(captionId);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !activeDragId || !containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    let normX = (e.clientX - rect.left) / rect.width;
    let normY = (e.clientY - rect.top) / rect.height;

    // Constrain within bounds 0.05 to 0.95
    normX = Math.max(0.08, Math.min(0.92, normX));
    normY = Math.max(0.08, Math.min(0.92, normY));

    // Center snapping
    if (settings.center_snapping && Math.abs(normX - 0.5) < 0.035) {
      normX = 0.5;
      setShowCenterSnap(true);
    } else {
      setShowCenterSnap(false);
    }

    onUpdateCaptionPosition(activeDragId, round2(normX), round2(normY), isGraphicActive);
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setActiveDragId(null);
    setShowCenterSnap(false);
  };

  const round2 = (num: number) => Math.round(num * 100) / 100;

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      className="absolute inset-0 pointer-events-auto select-none overflow-hidden"
    >
      <div style={{position:"absolute",width:referenceWidth,height:referenceHeight,transform:`scale(${canvasScale})`,transformOrigin:"top left"}}>
      {graphics.find(g=>g.parameters.sfx_track_url&&!g.parameters.sfx_muted)&&<SoundEffectsTrack src={String(graphics.find(g=>g.parameters.sfx_track_url&&!g.parameters.sfx_muted)!.parameters.sfx_track_url)} time={currentTime} playing={isPlaying} />}
      {/* 1. Center Snapping Guide (Magenta vertical line) */}
      {showCenterSnap && (
        <div className="absolute top-0 bottom-0 left-1/2 w-0.5 -translate-x-1/2 bg-pink-500 z-30 pointer-events-none shadow-[0_0_8px_rgba(236,72,153,0.8)]" />
      )}

      {/* 2. Safe Area Guides (Only when explicitly enabled) */}
      {settings.safe_area_guide === true && settings.aspect_ratio === "9:16" && (
        <div className="absolute inset-x-8 top-16 bottom-24 border border-dashed border-white/15 rounded-xl pointer-events-none z-10" />
      )}

      {/* Ken Burns static image animation calculation */}
      {(() => null)()}

      {/* 3. Render Motion Graphics & B-Roll Layers */}
      {visibleGraphics.map((graphic) => {
        if (graphic.template_id === 'caption_cover') {
          const top=Number(graphic.parameters.top ?? .675);
          const height=Number(graphic.parameters.height ?? .05);
          return <div key={graphic.id} style={{position:'absolute',left:0,top:top*referenceHeight,width:referenceWidth,height:height*referenceHeight,background:graphic.parameters.color||'#111315',zIndex:15,pointerEvents:'none'}} />;
        }
        if (graphic.template_id === 'authored_title') return null;

        // Same camera maths as the export (burnin_renderer.camera_pose): scale, shift (fraction of frame), rotation.
        const cameraPose = (animation: string, p: number, seconds: number): [number, number, number, number] => {
          const e = p * p * (3 - 2 * p);
          switch (animation) {
            case "slow_zoom_in": return [1 + p * .15, 0, 0, 0];
            case "slow_zoom_out": return [1.15 - p * .15, 0, 0, 0];
            case "push_in": return [1 + .22 * (1 - Math.pow(1 - p, 3)), 0, 0, 0];
            case "pan_left": return [1.1, (.5 - p) * .08, 0, 0];
            case "pan_right": return [1.1, (p - .5) * .08, 0, 0];
            case "tilt_up": return [1.1, 0, (.5 - p) * .08, 0];
            case "tilt_down": return [1.1, 0, (p - .5) * .08, 0];
            case "crane_up": return [1.08 + .06 * e, 0, (.5 - e) * .07, 0];
            case "dutch": return [1.16, 0, 0, 2.5 + 2 * e];
            case "handheld": return [1.06, (Math.sin(seconds * 2.1) + .6 * Math.sin(seconds * 5.3 + 1.3)) * .004,
                                     (Math.sin(seconds * 1.7 + .4) + .5 * Math.sin(seconds * 4.7)) * .004, .25 * Math.sin(seconds * 1.3)];
            default: return [1, 0, 0, 0];
          }
        };
        const getKenBurnsTransform = (g: MotionGraphicItem) => {
          if (g.template_id==="split_screen_vertical" || g.split_layout==="split_50_50_vertical") return "scale(1)";
          const animation = String(g.parameters?.animation || g.animation || "none");
          if (animation === "none") return "scale(1.0)";
          const dur = Math.max(0.1, g.end - g.start);
          const progress = Math.max(0, Math.min(1, (currentTime - g.start) / dur));
          const [scale, dx, dy, rotate] = cameraPose(animation, progress, currentTime - g.start);
          // A positive shift moves the view right/down, so the picture moves the other way.
          return `scale(${scale}) translate(${-dx * 100}%, ${-dy * 100}%) rotate(${rotate}deg)`;
        };
        // Speed treatment of a video cutaway (burnin_renderer.cutaway_time): source time and playback rate.
        const cutawaySpeed = (g: MotionGraphicItem): [number, number] => {
          const local = currentTime - g.start, dur = Math.max(.1, g.end - g.start);
          switch (g.parameters?.speed) {
            case "slow_motion": return [local * .5, .5];
            case "speed_ramp": { const knee = dur * .4; return local < knee ? [local * 2, 2] : [knee * 2 + (local - knee) * .5, .5]; }
            case "freeze_end": return local < dur * .66 ? [local, 1] : [dur * .66, 0];
            default: return [local, 1];
          }
        };
        // Hand-over in and out of a cutaway (burnin_renderer.transition_mix).
        const TRANSITIONS: Record<string, number> = { dissolve: .3, whip: .22, wipe: .3, flash: .25 };
        const handOver = (g: MotionGraphicItem): { style: React.CSSProperties; flash: number } => {
          const into = String(g.parameters?.transition_in || 'cut'), out = String(g.parameters?.transition_out || 'cut');
          const local = currentTime - g.start, left = g.end - currentTime;
          let kind = '', p = 1;
          if (TRANSITIONS[into] && local < TRANSITIONS[into]) { kind = into; p = local / TRANSITIONS[into]; }
          else if (TRANSITIONS[out] && left < TRANSITIONS[out]) { kind = out; p = left / TRANSITIONS[out]; }
          const e = Math.max(0, Math.min(1, p * p * (3 - 2 * p)));
          if (kind === 'dissolve') return { style: { opacity: e }, flash: 0 };
          if (kind === 'wipe') return { style: { clipPath: `inset(0 ${(1 - e) * 100}% 0 0)` }, flash: 0 };
          if (kind === 'whip') return { style: { transform: `translateX(${(1 - e) * 100}%)`, filter: `blur(${Math.sin(Math.PI * e) * 8}px)` }, flash: 0 };
          if (kind === 'flash') return { style: {}, flash: .85 * (1 - e) };
          return { style: {}, flash: 0 };
        };

        // 1. FULL SCREEN CUTAWAY INSERT (Screenshot 3 & Architecture Pillar 3)
        if (graphic.placement_mode === "insert") {
          const hand = handOver(graphic);
          const [cutawayTime, cutawayRate] = cutawaySpeed(graphic);
          return (
            <div
              key={graphic.id}
              style={hand.style}
              className="absolute inset-0 z-20 pointer-events-none flex flex-col justify-between bg-black overflow-hidden select-none"
            >
              {hand.flash > 0 && <div className="absolute inset-0 z-30 bg-white" style={{ opacity: hand.flash }} />}
              {/* Media Content (Video or Animated Photo) */}
              <div className="absolute inset-0 overflow-hidden flex items-center justify-center">
                {graphic.media_url ? (() => {
                  const mediaScale = graphic.parameters?.media_scale ?? (graphic.scale ?? 1.0);
                  const mediaPosX = graphic.parameters?.media_pos_x ?? (graphic.pos_x ?? 0.5);
                  const mediaPosY = graphic.parameters?.media_pos_y ?? (graphic.pos_y ?? 0.5);
                  const objPos = `${mediaPosX * 100}% ${mediaPosY * 100}%`;
                  const isVid = graphic.media_type === "video" || graphic.media_url.match(/\.(mp4|webm|mov)(\?.*)?$/i);
                  const kbTransform = getKenBurnsTransform(graphic);
                  const finalTransform = kbTransform ? `${kbTransform} scale(${mediaScale})` : `scale(${mediaScale})`;

                  return isVid ? (
                    <div 
                      className="w-full h-full flex items-center justify-center overflow-hidden" 
                      style={{ 
                        transform: `scale(${mediaScale})`, 
                        transformOrigin: objPos 
                      }}
                    >
                      <TimelineVideo 
                        src={localMediaUrl(graphic.media_url)} 
                        time={cutawayTime} 
                        playing={isPlaying && cutawayRate > 0}
                        rate={cutawayRate || 1}
                        style={{ 
                          objectPosition: objPos,
                          transform: kbTransform || undefined,
                          transformOrigin: objPos,
                          transition: "object-position 0.1s linear, transform 0.1s linear"
                        }}
                      />
                    </div>
                  ) : (
                    <img
                      src={localMediaUrl(graphic.media_url)}
                      alt={graphic.title}
                      style={{ 
                        objectPosition: objPos,
                        transform: finalTransform, 
                        transformOrigin: objPos,
                        transition: "transform 0.1s linear" 
                      }}
                      className="w-full h-full object-cover"
                    />
                  );
                })() : (
                  <div className="w-full h-full bg-neutral-900 flex flex-col items-center justify-center text-neutral-400">
                    <Film className="w-12 h-12 mb-2 text-lime opacity-80" />
                    <span className="font-mono text-xs font-bold uppercase">{graphic.title}</span>
                  </div>
                )}
              </div>

              {/* CRT TV scanlines effect (Screenshot 3) */}
              {graphic.parameters?.scanlines !== false && (
                <div
                  className="absolute inset-0 pointer-events-none opacity-35 mix-blend-overlay"
                  style={{
                    backgroundImage: "linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.8) 50%)",
                    backgroundSize: "100% 4px"
                  }}
                />
              )}
              <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_80px_rgba(0,0,0,0.85)]" />

              {/* Clean minimal overlay without badges */}
              <div className="relative z-10 p-4 flex items-center justify-end">
                {graphic.parameters?.timestamp_label && (
                  <span className="px-2 py-0.5 rounded bg-black/70 text-neutral-300 font-mono text-[9px] border border-white/20">
                    {graphic.parameters.timestamp_label}
                  </span>
                )}
              </div>

              {/* Clean cutaway - no badges or image descriptions */}
            </div>
          );
        }

        // 2. 50/50 VERTICAL SPLIT SCREEN (Delegated cleanly to VideoViewer to prevent layout conflicts and film placeholders)
        if (graphic.split_layout === "split_50_50_vertical" || graphic.template_id === "split_screen_vertical") {
          return null;
        }

        // 3. PIP TOP RIGHT FLOATING WINDOW
        if (graphic.split_layout === "pip_top_right") {
          return (
            <div
              key={graphic.id}
              className="absolute top-4 right-4 w-44 h-28 z-20 pointer-events-none rounded-xl overflow-hidden shadow-2xl border-2 border-white/40 bg-black animate-in zoom-in-95 duration-200 select-none"
            >
              {graphic.media_url && (
                <img
                  src={localMediaUrl(graphic.media_url)}
                  alt={graphic.title}
                  style={{ transform: getKenBurnsTransform(graphic), transition: "transform 0.1s linear" }}
                  className="w-full h-full object-cover"
                />
              )}
            </div>
          );
        }

        // 4. ARTICLE RECONSTRUCTION (100% FULL SCREEN PURE WHITE REPORT)
        if (graphic.template_id === "article_reconstruction") {
          const rawMediaUrl = graphic.parameters?.media_url || graphic.media_url;
          const showFullPageImage = graphic.parameters?.show_full_page_image === true && Boolean(rawMediaUrl);
          
          const publisher = (graphic.parameters?.publisher ?? "").trim();
          const publisherLogo = graphic.parameters?.publisher_logo;
          const headline = graphic.parameters?.headline ?? graphic.title ?? "";
          const paragraph = graphic.parameters?.paragraph ?? "";
          const highlightQuote = (graphic.parameters?.highlight_quote || "").trim();
          const markerColor = graphic.parameters?.marker_color || "#00E5FF";
          const showHighlight = graphic.parameters?.show_highlight !== false;
          const headlineSize = graphic.parameters?.headline_size || 30;
          const paragraphSize = graphic.parameters?.paragraph_size || 18;

          const duration = Math.max(0.6, graphic.end - graphic.start);
          const elapsed = currentTime - graphic.start;
          const sweepProgress = Math.min(1, Math.max(0, (elapsed - 0.2) / Math.max(0.6, duration * 0.6)));

          // Positioning and Scale from sliders
          const scale = graphic.scale ?? 1.0;
          const offsetX = (graphic.pos_x ?? 0.5) * 60 - 30;
          const offsetY = (graphic.pos_y ?? 0.5) * 60 - 30;

          const resolveMediaUrl = (url?: string) => {
            if (!url) return '';
            if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('blob:') || url.startsWith('data:')) {
              return url;
            }
            return `${BACKEND_ORIGIN}${url.startsWith('/') ? '' : '/'}${url}`;
          };

          // 1. RESOLVE MEDIA URL HELPER (Figure image will render below text)

          // 2. HIGHLIGHT SEARCH LOGIC
          let highlightInPara = -1;
          let matchedParaQuote = "";
          if (showHighlight && highlightQuote && paragraph) {
            const pLower = paragraph.toLowerCase();
            const qLower = highlightQuote.toLowerCase();
            highlightInPara = pLower.indexOf(qLower);
            if (highlightInPara > -1) {
              matchedParaQuote = paragraph.slice(highlightInPara, highlightInPara + highlightQuote.length);
            }
          }

          let highlightInHead = -1;
          let matchedHeadQuote = "";
          if (showHighlight && highlightQuote && headline && highlightInPara === -1) {
            const hLower = headline.toLowerCase();
            const qLower = highlightQuote.toLowerCase();
            highlightInHead = hLower.indexOf(qLower);
            if (highlightInHead > -1) {
              matchedHeadQuote = headline.slice(highlightInHead, highlightInHead + highlightQuote.length);
            }
          }

          if (showHighlight && highlightInPara === -1 && highlightInHead === -1 && paragraph) {
            const sentenceMatch = paragraph.match(/^([^.!?]+[.!?]?)/);
            highlightInPara = 0;
            matchedParaQuote = sentenceMatch ? sentenceMatch[1] : paragraph.slice(0, Math.min(80, paragraph.length));
          }

          const preParaText = highlightInPara > -1 ? paragraph.slice(0, highlightInPara) : paragraph;
          const midParaText = highlightInPara > -1 ? matchedParaQuote : "";
          const postParaText = highlightInPara > -1 ? paragraph.slice(highlightInPara + matchedParaQuote.length) : "";

          const preHeadText = highlightInHead > -1 ? headline.slice(0, highlightInHead) : headline;
          const midHeadText = highlightInHead > -1 ? matchedHeadQuote : "";
          const postHeadText = highlightInHead > -1 ? headline.slice(highlightInHead + matchedHeadQuote.length) : "";

          // 3. FULL PAGE SOLID WHITE REPORT
          return (
            <div
              key={graphic.id}
              className="absolute inset-0 z-20 pointer-events-none flex flex-col justify-center p-8 bg-white overflow-hidden animate-in fade-in duration-200"
            >
              <div
                className="relative w-full h-full flex flex-col justify-center text-neutral-900 transition-all"
                style={{
                  transform: `translate(${offsetX}%, ${offsetY}%) scale(${scale})`,
                  transformOrigin: "center center",
                }}
              >
                {/* Publisher Masthead: Logo or Text */}
                {(publisherLogo || publisher) && (
                  <div className="pb-3 mb-4 flex items-center justify-between border-b border-neutral-200">
                    {publisherLogo ? (
                      <img 
                        src={resolveMediaUrl(publisherLogo)} 
                        alt={publisher || 'Publisher Logo'} 
                        className="h-8 max-w-[220px] object-contain"
                        style={{
                          filter: (publisherLogo.toLowerCase().includes('white') || publisherLogo.toLowerCase().includes('light')) 
                            ? 'brightness(0) saturate(100%) invert(10%)' 
                            : 'none'
                        }}
                      />
                    ) : (
                      <span className="text-xl font-serif font-black tracking-tight text-neutral-900 uppercase">
                        {publisher}
                      </span>
                    )}
                  </div>
                )}

                {/* Headline (with optional kinetic highlight sweep) */}
                {headline && (
                  <h3
                    style={{ fontSize: `${headlineSize}px` }}
                    className="font-serif font-bold leading-snug tracking-tight text-neutral-900 mb-4"
                  >
                    {preHeadText && <span>{preHeadText}</span>}
                    {midHeadText && (
                      <span className="relative inline-block px-1 mx-0.5">
                        <span
                          className="absolute inset-0 rounded-[2px] pointer-events-none -rotate-[0.3deg] transition-all duration-75"
                          style={{
                            backgroundColor: markerColor,
                            opacity: 0.65,
                            clipPath: `inset(0 ${(1 - sweepProgress) * 100}% 0 0)`,
                            boxShadow: `0 0 12px ${markerColor}66`
                          }}
                        />
                        <span className="relative z-10 text-neutral-950 font-bold">
                          {midHeadText}
                        </span>
                      </span>
                    )}
                    {postHeadText && <span>{postHeadText}</span>}
                  </h3>
                )}

                {/* Body Paragraph with Kinetic Highlighter Sweep */}
                {paragraph && (
                  <div
                    style={{ fontSize: `${paragraphSize}px` }}
                    className="font-serif leading-relaxed text-neutral-800 relative mb-3"
                  >
                    {preParaText && <span>{preParaText}</span>}

                    {midParaText && (
                      <span className="relative inline-block font-semibold text-neutral-950 px-1 mx-0.5">
                        <span
                          className="absolute inset-0 rounded-[2px] pointer-events-none -rotate-[0.3deg] transition-all duration-75"
                          style={{
                            backgroundColor: markerColor,
                            opacity: 0.65,
                            clipPath: `inset(0 ${(1 - sweepProgress) * 100}% 0 0)`,
                            boxShadow: `0 0 14px ${markerColor}80`
                          }}
                        />
                        <span className="relative z-10 text-neutral-950 font-bold">
                          {midParaText}
                        </span>
                      </span>
                    )}

                    {postParaText && <span>{postParaText}</span>}
                  </div>
                )}

                {/* Attached Figure / Image UNDER THE TEXT */}
                {rawMediaUrl && graphic.parameters?.show_image !== false && (
                  <div className="mt-2 flex items-center justify-center w-full overflow-hidden">
                    <img
                      src={resolveMediaUrl(rawMediaUrl)}
                      alt="Article figure"
                      className="max-h-[220px] max-w-full rounded-lg border border-neutral-200 object-contain shadow-sm bg-neutral-50"
                    />
                  </div>
                )}
              </div>
            </div>
          );
        }

        if ((graphic.parameters?.title_style === 'behind_subject' || graphic.parameters?.behind_subject) && graphic.parameters?.subject_mask) {
          return <BehindSpeakerTitle key={graphic.id} graphic={graphic} time={currentTime} width={referenceWidth} height={referenceHeight}/>;
        }

        if (graphic.parameters?.title_style === 'cards_broll') {
          return (
            <CardsBrollTitle
              key={graphic.id}
              graphic={graphic}
              time={currentTime}
              width={referenceWidth}
              height={referenceHeight}
              isPlaying={isPlaying}
            />
          );
        }

        if (graphic.parameters?.title_style === 'staircase' || graphic.parameters?.title_style === 'silhouette_curve') {
          return (
            <StaircaseTitle
              key={graphic.id}
              graphic={graphic}
              time={currentTime}
              width={referenceWidth}
              height={referenceHeight}
              captions={captions}
            />
          );
        }

        // Draggable / Scalable overlay block for all graphics and title styles
        const tStyle = graphic.parameters?.title_style;
        const scale = graphic.scale ?? graphic.parameters?.scale ?? 1.0;
        const posX = (graphic.pos_x ?? 0.5) * 100;
        const defaultPosY = tStyle === 'behind_subject' ? 0.24 : (tStyle === 'flame_subject' ? 0.45 : 0.5);
        const posY = (graphic.pos_y ?? defaultPosY) * 100;

        return (
          <div
            key={graphic.id}
            style={{
              left: `${posX}%`,
              top: `${posY}%`,
              transform: `translate(-50%, -50%) scale(${scale})`,
              transformOrigin: "center center",
              width: "100%",
              maxWidth: referenceWidth,
              display: "flex",
              alignItems: "center",
              justifyContent: "center"
            }}
            className="absolute z-15 pointer-events-none"
          >
            {/* A. 50/50 Split Walking Silhouette with Curved Text (Frame 4 Screenshot) */}
            {(graphic.template_id === "split_silhouette_walking" ||
              graphic.template_id === "silhouette_curve") && (
            <div className="relative w-72 h-96 rounded-2xl bg-[#B4F000] p-4 flex flex-col items-center justify-between text-black shadow-2xl border-2 border-black overflow-hidden animate-in fade-in zoom-in-95 duration-200">
              <svg viewBox="0 0 240 320" className="w-full h-full select-none pointer-events-none">
                <defs>
                  <path id={`arcTop_${graphic.id}`} d="M 20 80 Q 120 18 220 80" fill="none" />
                  <path id={`arcBot_${graphic.id}`} d="M 20 285 Q 120 320 220 285" fill="none" />
                </defs>
                {/* Curved Text Arc Over Head */}
                <text className="fill-black font-black text-[22px] tracking-tight uppercase" style={{ fontFamily: "Montserrat, sans-serif" }}>
                  <textPath href={`#arcTop_${graphic.id}`} startOffset="50%" textAnchor="middle">
                    {graphic.parameters.arc_text_top || "It felt like"}
                  </textPath>
                </text>

                {/* High-Definition Solid Black Walking Silhouette (Frame 4) */}
                <g fill="#000000">
                  {/* Head */}
                  <circle cx="120" cy="98" r="14" />
                  {/* Collar & Neck */}
                  <path d="M 113 112 L 127 112 L 131 119 L 109 119 Z" />
                  {/* Tailored Jacket Torso */}
                  <path d="M 96 120 C 96 116, 144 116, 144 120 L 148 196 C 136 200, 104 200, 92 196 Z" />
                  {/* Left Arm Swinging Back */}
                  <path d="M 96 122 C 90 135, 85 162, 86 182 C 86 188, 91 188, 92 182 C 94 164, 98 140, 102 128 Z" />
                  {/* Right Arm Swinging Forward */}
                  <path d="M 144 122 C 150 135, 155 162, 154 182 C 154 188, 149 188, 148 182 C 146 164, 142 140, 138 128 Z" />
                  {/* Left Leg Stepping Forward */}
                  <path d="M 101 196 L 93 268 L 86 272 L 84 278 L 104 280 L 109 268 L 117 197 Z" />
                  {/* Right Leg Stepping Back */}
                  <path d="M 123 197 L 131 268 L 136 272 L 134 278 L 153 277 L 145 266 L 139 196 Z" />
                </g>

                {/* Curved Text Arc Under Feet */}
                <text className="fill-black font-black text-[18px] tracking-wide uppercase font-serif italic">
                  <textPath href={`#arcBot_${graphic.id}`} startOffset="50%" textAnchor="middle">
                    {graphic.parameters.arc_text_bottom || "walking away"}
                  </textPath>
                </text>
              </svg>
            </div>
          )}

          {/* B. 50/50 Split Falling / Leaping Silhouette (Frame 5 Screenshot) */}
          {graphic.template_id === "split_silhouette_falling" && (
            <div className="relative w-72 h-96 rounded-2xl bg-[#B4F000] p-4 flex flex-col items-center justify-between text-black shadow-2xl border-2 border-black overflow-hidden animate-in fade-in zoom-in-95 duration-200">
              <svg viewBox="0 0 240 320" className="w-full h-full select-none pointer-events-none">
                <defs>
                  <path id={`arcFallTop_${graphic.id}`} d="M 25 75 Q 120 22 215 75" fill="none" />
                  <path id={`arcFallBot_${graphic.id}`} d="M 25 280 Q 120 325 215 280" fill="none" />
                </defs>
                {/* Curved Text Arc Over Head */}
                <text className="fill-black font-black text-[24px] tracking-tighter uppercase font-montserrat">
                  <textPath href={`#arcFallTop_${graphic.id}`} startOffset="50%" textAnchor="middle">
                    {graphic.parameters.arc_text_top || "under"}
                  </textPath>
                </text>

                {/* Dynamic Athletic Airborne Silhouette in Mid-Flight */}
                <g fill="#000000" transform="translate(120, 160) rotate(-14) translate(-120, -160)">
                  {/* Head */}
                  <circle cx="100" cy="115" r="14" />
                  {/* Torso Angled */}
                  <path d="M 97 129 L 142 140 L 132 188 L 88 177 Z" />
                  {/* Extended Arm */}
                  <path d="M 95 133 C 72 142, 54 158, 46 172 C 44 176, 50 179, 54 175 C 62 164, 81 150, 99 144 Z" />
                  {/* Trailing Arm */}
                  <path d="M 140 140 C 158 126, 174 109, 188 96 C 192 92, 187 87, 182 90 C 169 101, 151 118, 135 131 Z" />
                  {/* Trailing Legs in Mid-Air Kick */}
                  <path d="M 94 180 L 76 242 L 58 256 L 65 263 L 90 250 L 105 184 Z" />
                  <path d="M 124 187 L 160 236 L 176 247 L 182 241 L 162 224 L 133 184 Z" />
                </g>

                {/* Inverted Curved Text Arc Beneath Feet */}
                <text className="fill-black font-black text-[24px] tracking-tighter uppercase font-montserrat">
                  <textPath href={`#arcFallBot_${graphic.id}`} startOffset="50%" textAnchor="middle">
                    {graphic.parameters.arc_text_bottom || "my feet"}
                  </textPath>
                </text>
              </svg>
            </div>
          )}

          {/* C. Giant 3D Compressed Block Kinetic Typography (Frames 2 & 3: WHAT TO DO) */}
          {graphic.template_id === "kinetic_3d_block" && (
            <div className="flex flex-col items-center justify-center select-none drop-shadow-2xl animate-in zoom-in-95 duration-200">
              <div
                style={{
                  fontFamily: "'Impact', 'Montserrat', 'Arial Black', sans-serif",
                  textShadow:
                    "3px 3px 0px #000000, 6px 6px 0px #000000, 9px 9px 0px #B4F000, 12px 12px 0px #000000",
                  letterSpacing: "-0.04em",
                  lineHeight: 0.88
                }}
                className="text-white text-6xl md:text-7xl font-black uppercase text-center"
              >
                {graphic.parameters.line_1 || "WHAT"}
              </div>
              <div
                style={{
                  fontFamily: "'Impact', 'Montserrat', 'Arial Black', sans-serif",
                  textShadow:
                    "3px 3px 0px #000000, 6px 6px 0px #000000, 9px 9px 0px #000000",
                  letterSpacing: "-0.04em",
                  lineHeight: 0.88
                }}
                className="text-white text-6xl md:text-7xl font-black uppercase text-center mt-1"
              >
                <span>{graphic.parameters.line_2_word_1 || "TO"} </span>
                <span style={{ color: graphic.parameters.accent_color || "#B4F000" }}>
                  {graphic.parameters.line_2_word_2 || "DO"}
                </span>
              </div>
            </div>
          )}

          {/* D. Editorial Dual-Font Typography */}
          {graphic.template_id === "editorial_dual_font" && (
            <div className="flex flex-col items-center justify-center text-center px-4 py-2 drop-shadow-2xl animate-in fade-in duration-200">
              <div className="text-white text-3xl font-black tracking-widest font-montserrat uppercase drop-shadow-[0_4px_8px_rgba(0,0,0,0.9)]">
                {graphic.parameters.headline || graphic.title}
              </div>
              {(graphic.parameters.accent_word || graphic.parameters.punchline) && (
                <div className="text-[#B4F000] text-4xl italic font-serif mt-1.5 drop-shadow-[0_4px_8px_rgba(0,0,0,0.9)]">
                  {graphic.parameters.accent_word && (
                    <span className="text-white/90 text-2xl mr-2 font-sans font-medium uppercase tracking-wider not-italic">
                      {graphic.parameters.accent_word}
                    </span>
                  )}
                  {graphic.parameters.punchline && (
                    <span className="font-bold underline decoration-[#B4F000] decoration-2 underline-offset-4">
                      {graphic.parameters.punchline}
                    </span>
                  )}
                </div>
              )}
            </div>
          )}

          {(graphic.template_id === 'kinetic_typography' || graphic.template_id === 'mixed_typography_title') && (() => {
            const style = String(graphic.parameters.title_style || 'rise');
            const duration = Number(graphic.parameters.title_reveal_seconds) || 0.45;
            const lines = Array.isArray(graphic.parameters.title_lines) ? graphic.parameters.title_lines : [{ text: graphic.parameters.headline || graphic.title || '', offset: 0 }];
            
            // Custom font and color parameters
            const customFont = graphic.parameters?.font_family;
            const customPrimaryColor = graphic.parameters?.primary_color;
            const customAccentColor = graphic.parameters?.accent_color;

            // Extract exact word timings from captions if not explicitly defined in graphic parameters
            const timedWords: any[] = (Array.isArray(graphic.parameters.timed_words) && graphic.parameters.timed_words.length > 0)
              ? graphic.parameters.timed_words
              : (() => {
                  const wordsInSpan: any[] = [];
                  for (const c of captions) {
                    if (c.end >= graphic.start - 0.25 && c.start <= graphic.end + 0.25) {
                      if (Array.isArray(c.words) && c.words.length > 0) {
                        for (const w of c.words) {
                          if (w.end >= graphic.start - 0.1 && w.start <= graphic.end + 0.1) {
                            wordsInSpan.push({
                              text: w.word.trim(),
                              start: w.start,
                              end: w.end,
                              offset: Math.max(0, w.start - graphic.start),
                              duration: Math.max(0.12, w.end - w.start)
                            });
                          }
                        }
                      }
                    }
                  }
                  return wordsInSpan;
                })();

            const exit = Math.min(1, Math.max(0, (graphic.end - currentTime) / 0.2));
            const elapsedTotal = Math.max(0, currentTime - graphic.start);

            // Progressive word visibility helper based on exact audio timing
            const getWordState = (wText: string, wOffset: number, wDur: number = 0.25) => {
              const rel = currentTime - graphic.start - wOffset;
              const isSpoken = rel >= 0;
              const progress = Math.min(1, Math.max(0, rel / Math.max(0.08, wDur)));
              return { isSpoken, progress, rel };
            };

            // Renders line text word-by-word according to audio pace, highlighting each word in real time
            const renderTimedLine = (fullLineText: string, baseFontFamily: string, baseFontSize: number, defaultColor: string, extraClasses: string = '', startWordOffset: number = 0, justifyClass: string = 'justify-center') => {
              const lineWords = String(fullLineText).split(' ');
              const matchLine = lines.findIndex((line: any) => line.text === fullLineText);
              if (matchLine >= 0) startWordOffset = lines.slice(0, matchLine).reduce((n: number, line: any) => n + String(line.text).split(/\s+/).length, 0);
              const effectiveFont = customFont || baseFontFamily;
              const effectiveColor = customPrimaryColor || defaultColor;

              return (
                <div className={`flex flex-wrap items-center ${justifyClass} gap-x-[0.24em] gap-y-0 leading-[1.08] ${extraClasses}`}>
                  {lineWords.map((word, wIdx) => {
                    const globalIdx = startWordOffset + wIdx;
                    const clean = word.toLowerCase().replace(/[^a-z0-9]/g, '');
                    // Priority 1: exact index in timedWords if text matches
                    let tw = (globalIdx < timedWords.length && timedWords[globalIdx].text?.toLowerCase().replace(/[^a-z0-9]/g, '') === clean)
                      ? timedWords[globalIdx]
                      : undefined;
                    // Priority 2: find by clean text starting from globalIdx
                    if (!tw) {
                      tw = timedWords.slice(globalIdx).find(t => (t.text || '').toLowerCase().replace(/[^a-z0-9]/g, '') === clean)
                        || timedWords.find(t => (t.text || '').toLowerCase().replace(/[^a-z0-9]/g, '') === clean);
                    }
                    const offset = tw ? Number(tw.offset || 0) : (globalIdx * 0.18);
                    const dur = tw ? Number(tw.duration || 0.25) : 0.25;
                    const { isSpoken, progress } = getWordState(word, offset, dur);
                    const isCurrentWord = tw ? (currentTime >= tw.start && currentTime <= tw.end) : (isSpoken && progress < 1.0);
                    const eased = 1 - Math.pow(1 - progress, 3);
                    const wordColor = isCurrentWord ? (customAccentColor || '#FBBF24') : effectiveColor;

                    return (
                      <span
                        key={wIdx}
                        style={{
                          fontFamily: effectiveFont,
                          fontSize: Math.min(baseFontSize, referenceWidth * .84 / Math.max(1, fullLineText.length * .45)),
                          color: wordColor,
                          opacity: isSpoken ? Math.min(progress, exit) : 0,
                          transform: isSpoken 
                            ? (isCurrentWord ? 'scale(1.12) translateY(-2px)' : `scale(${0.85 + 0.15 * eased}) translateY(${(1 - eased) * 8}px)`) 
                            : 'scale(0.8) translateY(10px)',
                          textShadow: isCurrentWord ? '0 0 16px rgba(251,191,36,0.6)' : undefined,
                          transition: 'color 0.1s ease, transform 0.1s ease'
                        }}
                        className="inline-block"
                      >
                        {word}
                      </span>
                    );
                  })}
                </div>
              );
            };

            if (style === 'stat_pair' && Array.isArray(graphic.parameters.stat_cards)) {
              return <div style={{width:referenceWidth*.86,opacity:exit,padding:18,background:'rgba(17,25,28,.88)',borderRadius:6,color:'#faf7ee'}}>
                <div style={{fontFamily:'Arial, sans-serif',fontSize:10,letterSpacing:'.16em',marginBottom:18}}>INDIA · EACH YEAR</div>
                <div style={{display:'flex',gap:20}}>{graphic.parameters.stat_cards.map((stat:any,i:number)=>{
                  const progress=Math.min(1,Math.max(0,(elapsedTotal-Number(stat.offset||0))/.3));
                  return <div key={i} style={{flex:1,borderLeft:i?'1px solid #ffffff40':undefined,paddingLeft:i?16:0,opacity:progress,transform:`translateY(${(1-progress)*8}px)`}}>
                    <div style={{fontFamily:'Arial, sans-serif',fontWeight:800,fontSize:referenceWidth*.075,letterSpacing:'-.04em',color:i?'#eed29b':'#fff'}}>{stat.value}</div>
                    <div style={{fontFamily:'Arial, sans-serif',fontSize:10,lineHeight:1.4,marginTop:6,textTransform:'uppercase',letterSpacing:'.07em'}}>{stat.label}</div>
                  </div>;
                })}</div>
              </div>;
            }

            // 1. DUAL (Bold sans-serif + flowing vibrant red cursive script - Image 1 Panel 1)
            // 0. EDITORIAL (lowercase grotesque, key word in gold italic serif, soft shadow, no box)
            if (style === 'editorial') {
              const accents = new Set((Array.isArray(graphic.parameters.accent_words) ? graphic.parameters.accent_words : []).map((w: string) => String(w).toLowerCase().replace(/[^a-z0-9]/g, '')));
              const longest = Math.max(1, ...lines.map((line: any) => String(line.text || '').length));
              const size = Math.max(14, Math.min(referenceWidth * 0.092, referenceWidth * 0.88 / (longest * 0.5)));
              const wordCount = lines.reduce((n: number, line: any) => n + String(line.text || '').split(/\s+/).filter(Boolean).length, 0);
              let wordIndex = 0;
              return (
                <div style={{ opacity: exit, width: referenceWidth * 0.94 }} className="flex flex-col items-center text-center select-none pointer-events-none">
                  {lines.map((line: any, row: number) => (
                    <div key={row} style={{ height: size * 1.1, columnGap: size * 0.24 }} className="flex items-center justify-center whitespace-nowrap">
                      {String(line.text || '').toLowerCase().split(/\s+/).filter(Boolean).map((word: string, column: number) => {
                        const timed = wordCount === timedWords.length ? timedWords[wordIndex] : undefined;
                        wordIndex += 1;
                        const offset = timed ? Number(timed.offset || 0) : Number(line.offset || 0);
                        const progress = Math.min(1, Math.max(0, (elapsedTotal - offset) / 0.14));
                        const eased = 1 - Math.pow(1 - progress, 3);
                        const accent = accents.has(word.replace(/[^a-z0-9]/g, ''));
                        // Spoken figures count up as they land, matching the export; years stay fixed.
                        const figure = word.match(/^(\D*?)(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(\D*)$/);
                        const digits = figure ? figure[2].replace(/,/g, '') : '';
                        const counts = figure && !/^(19|20)\d\d$/.test(digits) && Number(digits) >= 2;
                        const countProgress = Math.min(1, Math.max(0, (elapsedTotal - offset) / 0.55));
                        const decimals = digits.includes('.') ? digits.split('.')[1].length : 0;
                        const counted = counts ? Number(digits) * (1 - Math.pow(1 - countProgress, 3)) : 0;
                        const shown = counts && figure
                          ? figure[1] + (figure[2].includes(',') ? counted.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) : counted.toFixed(decimals)) + figure[3]
                          : word;
                        return (
                          <span
                            key={column}
                            style={{
                              fontFamily: accent ? 'Baskerville, "Playfair Display", Georgia, serif' : '"Helvetica Neue", Helvetica, Arial, sans-serif',
                              fontStyle: accent ? 'italic' : 'normal',
                              fontWeight: accent ? 600 : 500,
                              fontSize: accent ? size * 1.2 : size,
                              color: accent ? '#FFD65C' : '#FFFFFF',
                              opacity: progress,
                              lineHeight: 1,
                              transform: `translateY(${(1 - eased) * size * 0.18}px)`,
                              textShadow: `0 ${size * 0.04}px ${size * 0.14}px rgba(0,0,0,0.85), 0 0 ${size * 0.3}px rgba(0,0,0,0.55)`
                            }}
                          >
                            {shown}
                          </span>
                        );
                      })}
                    </div>
                  ))}
                </div>
              );
            }

            // 0B. MIXED_TYPOGRAPHY (Geometric Sans-Serif Bold setup + 1.25x Italic Serif/Script punchword in transform wireframe box)
            if (style === 'mixed_typography') {
              const setupText = String(graphic.parameters.setup_text || (lines[0]?.text && lines.length > 1 ? lines[0]?.text : '') || '').toUpperCase();
              const accentText = String(graphic.parameters.accent_text || (lines.length > 1 ? lines[1]?.text : lines[0]?.text) || '');
              const accentColor = graphic.parameters.accent_color || '#E04F26';
              const setupColor = graphic.parameters.setup_color || '#FFFFFF';
              const boxRotation = Number(graphic.parameters.box_rotation ?? -3);
              const showBox = graphic.parameters.bounding_box_highlight !== false;
              const baseSize = Math.min(referenceWidth * 0.088, referenceWidth * 0.9 / Math.max(1, setupText.length * 0.5));
              const accentSize = baseSize * 1.25;

              return (
                <div
                  style={{
                    opacity: exit,
                    width: referenceWidth * 0.94,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    userSelect: 'none',
                    pointerEvents: 'none'
                  }}
                >
                  {setupText && (
                    <div
                      style={{
                        fontFamily: '"Arial Black", Impact, Inter, sans-serif',
                        fontWeight: 900,
                        fontSize: baseSize,
                        color: setupColor,
                        letterSpacing: '-0.035em',
                        lineHeight: 1.05,
                        textTransform: 'uppercase',
                        textShadow: '0 2px 8px rgba(0,0,0,0.85)'
                      }}
                    >
                      {setupText}
                    </div>
                  )}
                  {accentText && (
                    <div style={{ marginTop: setupText ? -baseSize * 0.18 : 0 }}>
                      {showBox ? (
                        <div
                          style={{
                            position: 'relative',
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            border: `2px solid ${accentColor}`,
                            transform: `rotate(${boxRotation}deg)`,
                            padding: '4px 12px'
                          }}
                        >
                          <span style={{ position: 'absolute', top: -4, left: -4, width: 8, height: 8, backgroundColor: accentColor }} />
                          <span style={{ position: 'absolute', top: -4, right: -4, width: 8, height: 8, backgroundColor: accentColor }} />
                          <span style={{ position: 'absolute', bottom: -4, left: -4, width: 8, height: 8, backgroundColor: accentColor }} />
                          <span style={{ position: 'absolute', bottom: -4, right: -4, width: 8, height: 8, backgroundColor: accentColor }} />
                          <span
                            style={{
                              fontFamily: '"Georgia", Baskerville, "Playfair Display", serif',
                              fontStyle: 'italic',
                              fontWeight: 700,
                              fontSize: accentSize,
                              color: accentColor,
                              whiteSpace: 'nowrap',
                              lineHeight: 1.05,
                              textShadow: '0 2px 8px rgba(0,0,0,0.6)'
                            }}
                          >
                            {accentText}
                          </span>
                        </div>
                      ) : (
                        <span
                          style={{
                            fontFamily: '"Georgia", Baskerville, "Playfair Display", serif',
                            fontStyle: 'italic',
                            fontWeight: 700,
                            fontSize: accentSize,
                            color: accentColor,
                            transform: `rotate(${boxRotation}deg)`,
                            display: 'inline-block',
                            lineHeight: 1.05
                          }}
                        >
                          {accentText}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              );
            }

            if (style === 'dual') {
              let topText = lines[0]?.text || graphic.parameters.headline || "";
              let bottomText = lines[1]?.text || "";
              if (!bottomText) {
                const parts = topText.split(/\s+/).filter(Boolean);
                if (parts.length > 1) {
                  const half = Math.ceil(parts.length / 2);
                  topText = parts.slice(0, half).join(' ');
                  bottomText = parts.slice(half).join(' ');
                }
              }
              const font1 = lines[0]?.font_family || graphic.parameters.font_family || '"Montserrat", "Arial Black", Arial, sans-serif';
              const font2 = lines[1]?.font_family || graphic.parameters.script_font_family || graphic.parameters.secondary_font_family || '"Snell Roundhand", "Caveat", "Dancing Script", "Brush Script MT", cursive';
              const color1 = lines[0]?.color || graphic.parameters.primary_color || '#FFFFFF';
              const color2 = lines[1]?.color || graphic.parameters.accent_color || '#EF4444';

              return (
                <div style={{ opacity: exit, width: referenceWidth * 0.92 }} className="flex flex-col items-center justify-center text-center select-none pointer-events-none">
                  <div style={{ letterSpacing: '0.06em' }} className="font-black uppercase drop-shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
                    {renderTimedLine(topText, font1, referenceWidth * 0.082, color1, 'font-black tracking-wider')}
                  </div>
                  <div style={{ marginTop: -referenceWidth * 0.02, transform: 'rotate(-3deg)' }} className="drop-shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
                    {renderTimedLine(bottomText, font2, referenceWidth * 0.13, color2, 'font-bold')}
                  </div>
                </div>
              );
            }

            // 2. FLAME_SUBJECT (Cinematic noir vignette + fiery burn aura + handwriting script "burnt out." - Image 1 Panel 2)
            if (style === 'flame_subject') {
              const text = lines[0]?.text || graphic.parameters.headline || "burnt out.";
              const prog = Math.min(1, Math.max(0, elapsedTotal / duration));
              const pulse = 1 + 0.04 * Math.sin(elapsedTotal * 10);
              return (
                <div style={{ opacity: exit, width: referenceWidth }} className="relative flex flex-col items-center justify-center select-none pointer-events-none">
                  {/* Radiant leaping fire aura */}
                  <div style={{ position: 'absolute', transform: `scale(${pulse})`, opacity: 0.85 * prog }} className="flex items-center justify-center">
                    <svg viewBox="0 0 240 260" style={{ width: referenceWidth * 0.65, height: referenceWidth * 0.75, filter: 'drop-shadow(0 0 24px #ea580c)' }}>
                      <defs>
                        <radialGradient id={`flameCore-${graphic.id}`} cx="50%" cy="60%" r="50%">
                          <stop offset="0%" stopColor="#fff8db" stopOpacity="0.95" />
                          <stop offset="30%" stopColor="#f59e0b" stopOpacity="0.9" />
                          <stop offset="65%" stopColor="#ea580c" stopOpacity="0.75" />
                          <stop offset="100%" stopColor="#dc2626" stopOpacity="0" />
                        </radialGradient>
                      </defs>
                      <path d="M120 10 C145 60 195 80 180 140 C210 110 205 85 195 70 C245 150 215 230 120 245 C25 235 15 150 65 85 C55 120 80 145 95 150 C70 90 120 70 120 10 Z" fill={`url(#flameCore-${graphic.id})`} />
                    </svg>
                  </div>

                  {/* Large pure white handwriting script stretching across the burning subject */}
                  <div style={{ transform: 'rotate(-2.5deg)', zIndex: 10 }} className="relative drop-shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
                    {renderTimedLine(text, '"Caveat", "Snell Roundhand", "Apple Chancery", cursive', referenceWidth * 0.135, '#FFFFFF', 'font-normal tracking-wide')}
                  </div>
                </div>
              );
            }

            // 3. SCRIPT (Pure white elegant cursive script across frame with ghosted editorial depth - Image 1 Panel 3)
            if (style === 'script') {
              const text = lines[0]?.text || graphic.parameters.headline || "";
              return (
                <div style={{ opacity: exit, maxWidth: referenceWidth * 0.94 }} className="relative flex items-center justify-center text-center px-4 select-none pointer-events-none">
                  {/* Subtle ethereal ghosted layer behind for cinematic depth */}
                  <div style={{ position: 'absolute', transform: 'scale(1.08) translateY(-4px)', opacity: 0.18, filter: 'blur(1.5px)' }} aria-hidden="true" className="select-none pointer-events-none">
                    <span style={{ fontFamily: '"Snell Roundhand", "Caveat", "Dancing Script", cursive', fontSize: referenceWidth * 0.13, color: '#FFFFFF' }}>
                      {text}
                    </span>
                  </div>
                  {/* Foreground pure white elegant cursive calligraphy */}
                  <div className="relative z-10 drop-shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
                    {renderTimedLine(text, '"Snell Roundhand", "Caveat", "Dancing Script", cursive', referenceWidth * 0.125, '#FFFFFF', 'font-normal tracking-wide')}
                  </div>
                </div>
              );
            }

            // 4. CARDS_BROLL (Title with floating B-roll mini-cards in background - Image 1 Panel 4)
            if (style === 'cards_broll') {
              let topText = lines[0]?.text || "";
              let midText = lines[1]?.text || "";
              let scriptText = lines[2]?.text || "";
              if (!midText && !scriptText) {
                const parts = (lines[0]?.text || graphic.parameters.headline || "").split(/\s+/).filter(Boolean);
                if (parts.length >= 3) {
                  topText = parts[0];
                  midText = parts.slice(1, -1).join(' ');
                  scriptText = parts[parts.length - 1];
                } else if (parts.length === 2) {
                  topText = parts[0];
                  midText = parts[1];
                } else {
                  midText = parts.join(' ');
                }
              }
              const userCards = Array.isArray(graphic.parameters.card_media) && graphic.parameters.card_media.length > 0 
                ? graphic.parameters.card_media 
                : graphics.filter(g => g.media_url && g.id !== graphic.id).slice(0, 3).map(g => ({ url: g.media_url, type: g.media_type || 'image' }));
              return (
                <div style={{ opacity: exit, width: referenceWidth * 0.95 }} className="relative flex flex-col items-center justify-center py-6 select-none pointer-events-none">
                  {/* Dimmed backdrop for card contrast */}
                  <div className="absolute -inset-10 bg-black/45 rounded-xl pointer-events-none" />

                  {/* Floating tilted Polaroid mini-cards in background */}
                  <div className="absolute inset-0 pointer-events-none">
                    {userCards.slice(0, 3).map((card: any, i: number) => {
                      const tilts = [-8, 7, -3];
                      const lefts = ['2%', '68%', '34%'];
                      const tops = [-55, -40, 85];
                      return (
                        <div
                          key={card.url || i}
                          style={{
                            position: 'absolute',
                            width: referenceWidth * 0.30,
                            height: referenceWidth * 0.22,
                            left: lefts[i],
                            top: tops[i],
                            transform: `rotate(${tilts[i]}deg) translateY(${(1 - Math.min(1, elapsedTotal / 0.35)) * 12}px)`,
                            boxShadow: '0 8px 24px rgba(0,0,0,0.7)',
                            border: '2px solid rgba(255,255,255,0.85)',
                            borderRadius: 5,
                            overflow: 'hidden'
                          }}
                        >
                          {card.type === 'video' ? (
                            <TimelineVideo src={card.url} time={elapsedTotal} playing={isPlaying} />
                          ) : (
                            <img src={localMediaUrl(card.url)} alt="Supporting visual" className="w-full h-full object-cover" />
                          )}
                        </div>
                      );
                    })}
                  </div>

                  {/* Center Typography: Clean sans top + Bold uppercase mid + Golden amber script bottom */}
                  <div className="relative z-10 flex flex-col items-center text-center drop-shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
                    {topText && renderTimedLine(topText, '"Inter", "Arial", sans-serif', referenceWidth * 0.048, '#E2E8F0', 'tracking-normal')}
                    {midText && renderTimedLine(midText, '"Montserrat", "Arial Black", Arial, sans-serif', referenceWidth * 0.082, '#FFFFFF', 'font-black uppercase tracking-tight')}
                    {scriptText && (
                      <div style={{ marginTop: -referenceWidth * 0.018 }}>
                        {renderTimedLine(scriptText, '"Snell Roundhand", "Caveat", "Dancing Script", cursive', referenceWidth * 0.11, '#FBBF24', 'font-bold')}
                      </div>
                    )}
                  </div>
                </div>
              );
            }

            // 5. BEHIND_SUBJECT (Massive uppercase block typography behind speaker + golden cursive accent in front - Image 1 Panel 5)
            if (style === 'behind_subject') {
              let bgText = lines[0]?.text || "";
              let accentText = lines[1]?.text || "";
              let scriptSub = lines[2]?.text || "";
              if (!accentText && !scriptSub) {
                const parts = bgText.split(/\s+/).filter(Boolean);
                if (parts.length > 1) {
                  const half = Math.ceil(parts.length / 2);
                  bgText = parts.slice(0, half).join(' ');
                  accentText = parts.slice(half).join(' ');
                }
              }
              const font1 = lines[0]?.font_family || graphic.parameters.font_family || '"Anton", "Impact", "Montserrat Black", Arial, sans-serif';
              const font2 = lines[1]?.font_family || graphic.parameters.font_family || font1;
              const font3 = lines[2]?.font_family || graphic.parameters.script_font_family || graphic.parameters.secondary_font_family || '"Snell Roundhand", "Caveat", "Dancing Script", cursive';
              const color1 = lines[0]?.color || graphic.parameters.primary_color || '#F1F5F9';
              const color2 = lines[1]?.color || graphic.parameters.primary_color || '#FFFFFF';
              const color3 = lines[2]?.color || graphic.parameters.accent_color || '#FDE047';

              return (
                <div style={{ opacity: exit, width: referenceWidth * 0.94 }} className="relative flex flex-col items-center justify-center select-none pointer-events-none">
                  {/* Giant massive uppercase bold white letters in upper backdrop */}
                  <div style={{ width: referenceWidth * 0.94 }} className="flex flex-col items-center text-center drop-shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
                    {bgText && renderTimedLine(bgText, font1, referenceWidth * 0.13, color1, 'font-black uppercase tracking-tighter leading-[0.88]')}
                    {accentText && renderTimedLine(accentText, font2, referenceWidth * 0.13, color2, 'font-black uppercase tracking-tighter leading-[0.88]')}
                  </div>

                  {/* Flowing golden cursive script accent across bottom foreground */}
                  {scriptSub && (
                    <div style={{ transform: 'rotate(-3.5deg)', marginTop: referenceWidth * 0.04 }} className="relative z-20 drop-shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
                      {renderTimedLine(scriptSub, font3, referenceWidth * 0.09, color3, 'font-bold')}
                    </div>
                  )}
                </div>
              );
            }

            // 6. RISE / CORNER_PILL (Clean minimalist stacked sans-serif, left-aligned - Image 1 Panel 6)
            if (style === 'rise' || style === 'corner_pill') {
              let head1 = lines[0]?.text || "";
              let head2 = lines[1]?.text || "";
              if (!head2) {
                const parts = head1.split(/\s+/).filter(Boolean);
                if (parts.length > 1) {
                  const half = Math.ceil(parts.length / 2);
                  head1 = parts.slice(0, half).join(' ');
                  head2 = parts.slice(half).join(' ');
                }
              }
              const rFont1 = lines[0]?.font_family || graphic.parameters.font_family || '"Montserrat", "Arial Black", Arial, sans-serif';
              const rFont2 = lines[1]?.font_family || graphic.parameters.secondary_font_family || graphic.parameters.font_family || '"Montserrat", "Arial Black", Arial, sans-serif';
              const rColor1 = lines[0]?.color || graphic.parameters.primary_color || '#FFFFFF';
              const rColor2 = lines[1]?.color || graphic.parameters.secondary_color || '#F1F5F9';

              return (
                <div style={{ opacity: exit, width: referenceWidth * 0.88 }} className="flex flex-col items-start text-left select-none pointer-events-none px-4 drop-shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
                  <div style={{ letterSpacing: '-0.035em' }} className="font-black uppercase text-left w-full">
                    {renderTimedLine(head1, rFont1, referenceWidth * 0.082, rColor1, 'font-black uppercase text-left', 0, 'justify-start')}
                  </div>
                  {head2 && (
                    <div style={{ letterSpacing: '-0.035em', marginTop: -referenceWidth * 0.01 }} className="font-black uppercase text-left w-full">
                      {renderTimedLine(head2, rFont2, referenceWidth * 0.082, rColor2, 'font-black uppercase text-left', 0, 'justify-start')}
                    </div>
                  )}
                </div>
              );
            }

            // 7. PAPER / TORN_PAPER (Realistic torn paper banner background + dark serif font - Image 1 Panel 7)
            if (style === 'paper' || style === 'torn_paper') {
              const mainText = lines[0]?.text || graphic.parameters.headline || "";
              const badgeText = graphic.parameters.badge || (lines.length > 1 ? lines[1]?.text : null);
              const customFont = lines[0]?.font_family || graphic.parameters.font_family || '"Playfair Display", "Georgia", "Times New Roman", serif';
              const badgeFont = lines[1]?.font_family || graphic.parameters.secondary_font_family || '"Montserrat", Arial, sans-serif';
              const customTextColor = lines[0]?.color || graphic.parameters.primary_color || '#18181B';
              const customBadgeColor = lines[1]?.color || graphic.parameters.accent_color || '#0284C7';
              return (
                <div style={{ opacity: exit, transform: 'rotate(-2deg)' }} className="relative inline-flex items-center select-none pointer-events-none drop-shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
                  {/* Torn Ripped Paper Texture Container with realistic jagged fibrous edges */}
                  <div className="relative bg-[#FAF6EE] text-neutral-900 px-6 py-3 rounded-xs shadow-2xl flex items-center gap-3 border-y border-stone-300/80">
                    {/* Left torn edge */}
                    <svg className="absolute -left-3.5 top-0 bottom-0 h-full w-4 text-[#FAF6EE] fill-current" viewBox="0 0 12 100" preserveAspectRatio="none">
                      <polygon points="12,0 3,7 11,15 1,24 10,34 2,46 12,56 0,67 11,78 3,89 12,100" />
                    </svg>
                    {/* Right torn edge */}
                    <svg className="absolute -right-3.5 top-0 bottom-0 h-full w-4 text-[#FAF6EE] fill-current" viewBox="0 0 12 100" preserveAspectRatio="none">
                      <polygon points="0,0 9,9 1,18 11,30 2,42 12,54 1,65 10,77 2,88 0,100" />
                    </svg>
                    {/* Main Dark Headline */}
                    <div className="font-serif font-black uppercase tracking-tight text-neutral-900">
                      {renderTimedLine(mainText, customFont, referenceWidth * 0.054, customTextColor, 'font-black')}
                    </div>
                    {/* Optional Accent Punch Badge - only if explicitly provided */}
                    {badgeText && (
                      <div style={{ fontFamily: badgeFont, fontSize: referenceWidth * 0.046, backgroundColor: customBadgeColor }} className="text-white font-black px-3 py-0.5 rounded-xs uppercase tracking-wider shadow-md">
                        {badgeText}
                      </div>
                    )}
                  </div>
                </div>
              );
            }

            // 8. TYPEWRITER (Clean parchment substrate + retro monospace font + blinking cursor - Image 1 Panel 8)
            if (style === 'typewriter') {
              const fullText = lines[0]?.text || graphic.parameters.headline || "That's what I've |";
              const cleanText = fullText.replace(/\|+$/, '').replace(/ \| /g, '\n');
              const charCount = Math.ceil(cleanText.length * Math.min(1, elapsedTotal / Math.max(0.4, (graphic.end - graphic.start) * 0.65)));
              const typed = cleanText.slice(0, charCount);
              const showCursor = Math.floor(currentTime * 3) % 2 === 0;
              return (
                <div style={{ opacity: exit, width: referenceWidth * 0.92 }} className="relative select-none pointer-events-none drop-shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
                  <div className="bg-[#FAF8F5] border border-neutral-300/50 px-6 py-4 rounded-sm flex items-center justify-center shadow-lg">
                    <span style={{ 
                      fontFamily: '"Courier Prime", "Special Elite", "Courier New", monospace', 
                      fontSize: referenceWidth * 0.058,
                      letterSpacing: '0.02em', whiteSpace:'pre-wrap', minHeight:Math.ceil(cleanText.length/23)*referenceWidth*.074, width:'100%'
                    }} className="text-neutral-900 font-bold">
                      {typed}
                      <span className="text-neutral-800 font-black ml-0.5" style={{ opacity: showCursor ? 1 : 0 }}>|</span>
                    </span>
                  </div>
                </div>
              );
            }

            // 9. BOLD_POP / TECH_GRID / LAUNCH_BADGE (Dark cyber-grid container + massive block typography + circular upward arrow badge - Image 1 Panel 9)
            if (style === 'bold_pop' || style === 'tech_grid' || style === 'launch_badge') {
              const fullText = lines[0]?.text || graphic.parameters.headline || "LAUNCH";
              const prog = Math.min(1, elapsedTotal / 0.25);
              const badgeScale = 1 + 0.12 * Math.sin(prog * Math.PI);
              const bpFont = lines[0]?.font_family || graphic.parameters.font_family || '"Montserrat Black", "Arial Black", Arial, sans-serif';
              const bpColor = lines[0]?.color || graphic.parameters.primary_color || '#FFFFFF';
              return (
                <div style={{
                  opacity: exit,
                  width: referenceWidth * 0.88,
                  padding: '16px 14px',
                  borderRadius: 6,
                  background: '#0F1015',
                  backgroundImage: 'linear-gradient(rgba(0,255,255,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,255,0.06) 1px, transparent 1px)',
                  backgroundSize: '20px 20px',
                  textAlign: 'center',
                  transform: `scale(${0.94 + 0.06 * prog})`,
                  boxShadow: '0 12px 32px rgba(0,0,0,0.85)'
                }} className="relative select-none pointer-events-none flex items-center justify-center">
                  {/* Ultra-bold typography */}
                  <div className="relative z-10 flex items-center justify-center gap-2">
                    {renderTimedLine(fullText, bpFont, referenceWidth * 0.11, bpColor, 'font-black uppercase tracking-tighter')}
                  </div>

                  {/* Circular Pop-out Upward Arrow Badge in light peach/pink */}
                  <div
                    style={{
                      transform: `scale(${badgeScale})`,
                      boxShadow: '0 4px 16px rgba(244,63,94,0.45)',
                      border: '2px solid #FB7185'
                    }}
                    className="absolute -top-3.5 right-6 w-9 h-9 rounded-full bg-[#FFE4E6] flex items-center justify-center text-neutral-950 font-black shadow-xl z-20"
                  >
                    <span className="text-base font-black leading-none">↑</span>
                  </div>
                </div>
              );
            }

            // 10. STAIRCASE / SILHOUETTE_CURVE (Words stepping in a horseshoe arch framing the protagonist - Image 1 Panel 10)
            if (style === 'staircase' || style === 'silhouette_curve') {
              const words = lines.length > 1
                ? lines.map((l: any) => String(l.text))
                : String(lines[0]?.text || graphic.parameters.headline || "").split(/\s+/).filter(Boolean);
              const total = words.length;
              const scFont = lines[0]?.font_family || graphic.parameters.font_family || '"Montserrat", "Arial Black", Arial, sans-serif';
              const scColor = lines[0]?.color || graphic.parameters.primary_color || '#FFFFFF';
              return (
                <div style={{ opacity: exit }} className="absolute inset-0 w-full h-full select-none pointer-events-none">
                  {words.map((word: string, idx: number) => {
                    const tw = timedWords.find(t => t.text.toLowerCase().replace(/[^a-z0-9]/g, '') === word.toLowerCase().replace(/[^a-z0-9]/g, ''));
                    const offset = tw ? Number(tw.offset || 0) : (idx * 0.18);
                    const dur = tw ? Number(tw.duration || 0.25) : 0.25;
                    const { isSpoken, progress } = getWordState(word, offset, dur);
                    const eased = 1 - Math.pow(1 - progress, 3);

                    // Horseshoe body arch formula: flanks -> crown -> flanks
                    const t = idx / Math.max(1, total - 1);
                    const posX = referenceWidth * (0.50 - 0.34 * Math.cos(Math.PI * t));
                    const posY = referenceHeight * (0.44 - 0.28 * Math.sin(Math.PI * t));
                    const fontSize = Math.min(referenceWidth * 0.08, Math.max(16, referenceWidth * (total > 8 ? 0.056 : 0.068)));

                    return (
                      <div 
                        key={idx} 
                        style={{ 
                          position: 'absolute',
                          left: `${posX}px`,
                          top: `${posY}px`,
                          opacity: isSpoken ? Math.min(progress, exit) : 0,
                          transform: isSpoken 
                            ? `translate(-50%, -50%) scale(${0.88 + 0.12 * eased})` 
                            : 'translate(-50%, -50%) scale(0.75)',
                          fontFamily: scFont,
                          fontSize,
                          color: scColor,
                          transition: 'none'
                        }}
                        className="font-black uppercase tracking-tight drop-shadow-[0_1px_3px_rgba(0,0,0,0.3)] whitespace-nowrap"
                      >
                        {word}
                      </div>
                    );
                  })}
                </div>
              );
            }

            // 11. COOKED_BADGE / COOKED_RED (Massive expressive red cursive script + solid dark pill badges - Image 1 Panel 11)
            if (style === 'cooked_badge' || style === 'cooked_red') {
              let scriptHeader = lines[0]?.text || graphic.parameters.headline || "Cooked";
              let bottomWords = (lines[1]?.text || "").split(' ').filter(Boolean);
              if (lines.length <= 1 && bottomWords.length === 0) {
                const parts = scriptHeader.split(/\s+/).filter(Boolean);
                if (parts.length > 1) {
                  scriptHeader = parts[0];
                  bottomWords = parts.slice(1);
                }
              }
              const scriptFont = lines[0]?.font_family || graphic.parameters.script_font_family || graphic.parameters.secondary_font_family || '"Snell Roundhand", "Caveat", "Dancing Script", cursive';
              const pillFont = lines[1]?.font_family || graphic.parameters.font_family || '"Montserrat", "Arial Black", Arial, sans-serif';
              const scriptColor = lines[0]?.color || graphic.parameters.accent_color || '#DC2626';
              const pillTextColor = lines[1]?.color || graphic.parameters.primary_color || '#FFFFFF';

              return (
                <div style={{ opacity: exit, width: referenceWidth * 0.95 }} className="relative flex flex-col items-center justify-center select-none pointer-events-none">
                  {/* Giant expressive bright RED cursive script */}
                  <div style={{ 
                    fontFamily: scriptFont, 
                    fontSize: referenceWidth * 0.17,
                    lineHeight: 0.92,
                    transform: 'rotate(-4deg)',
                    color: scriptColor,
                  }} className="font-bold drop-shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
                    {renderTimedLine(scriptHeader, scriptFont, referenceWidth * 0.16, scriptColor, 'font-bold')}
                  </div>

                  {/* Separate solid dark pill badges with crisp text appearing word-by-word */}
                  <div className="flex flex-wrap items-center justify-center gap-2 mt-2">
                    {bottomWords.map((w: string, idx: number) => {
                      if (!w.trim()) return null;
                      const tw = timedWords.find(t => t.text.toLowerCase().replace(/[^a-z0-9]/g, '') === w.toLowerCase().replace(/[^a-z0-9]/g, ''));
                      const offset = tw ? Number(tw.offset || 0) : ((idx + 1) * 0.2);
                      const dur = tw ? Number(tw.duration || 0.25) : 0.25;
                      const { isSpoken, progress } = getWordState(w, offset, dur);
                      const eased = 1 - Math.pow(1 - progress, 3);
                      return (
                        <div 
                          key={idx} 
                          style={{ 
                            opacity: isSpoken ? Math.min(progress, exit) : 0,
                            fontFamily: pillFont, 
                            fontSize: referenceWidth * 0.046,
                            color: pillTextColor,
                            transform: isSpoken ? `translateY(${(1 - eased) * 12}px) scale(${0.85 + 0.15 * eased})` : 'translateY(16px) scale(0.8)'
                          }}
                          className="bg-[#18181B]/95 border border-white/20 font-black px-3.5 py-1.5 rounded-full uppercase tracking-wider shadow-lg"
                        >
                          {w}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            }

            // Default fallback
            return (
              <div style={{ color: graphic.parameters.text_color || '#FFFFFF', fontSize: referenceWidth * 0.065 }} className="font-black text-center drop-shadow-[0_2px_4px_black]">
                {graphic.parameters.headline || graphic.title}
              </div>
            );
          })()}

          {/* E. Stat & Growth Counter */}
          {graphic.template_id === "stat_counter" && (
            <div className="bg-black/90 border-2 border-[#B4F000] rounded-2xl p-4 text-center shadow-2xl animate-in zoom-in-95 duration-200">
              <div className="text-3xl font-black text-white font-montserrat">
                {graphic.parameters.start_value || "$2M"} →{" "}
                <span className="text-[#B4F000]">{graphic.parameters.end_value || "$12M"}</span>
              </div>
              <div className="mt-1 inline-block bg-[#B4F000] text-black font-black text-xs px-2.5 py-0.5 rounded-full uppercase">
                {graphic.parameters.sub_badge || "+500% Revenue"}
              </div>
            </div>
          )}

          {/* F. Thematic Medical Canvas (Cellular / Neuro / ECG / Genomics) */}
          {graphic.template_id === "thematic_canvas" && (() => {
            const field = graphic.parameters.field_type || "cardiology";
            return (
              <div className="relative w-80 h-96 rounded-2xl bg-neutral-950 border-2 border-cyan-500/60 p-4 flex flex-col justify-between text-white shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                {/* Background Grid & Vector Visualizer */}
                <div className="absolute inset-0 opacity-25 bg-[radial-gradient(#00F0FF_1px,transparent_1px)] [background-size:16px_16px] pointer-events-none" />
                
                {/* Animated Visual Vector based on field */}
                <div className="relative z-10 flex-1 flex items-center justify-center">
                  {field === "cardiology" && (
                    <div className="w-full flex flex-col items-center">
                      <svg viewBox="0 0 260 100" className="w-full h-24 stroke-cyan-400 fill-none stroke-[3]">
                        <path d="M 10 50 L 70 50 L 85 20 L 100 85 L 115 10 L 130 65 L 140 50 L 250 50" />
                      </svg>
                      <div className="flex items-center gap-1.5 text-cyan-400 font-mono text-xs mt-1 animate-pulse">
                        <Activity className="w-3.5 h-3.5" />
                        <span>ECG NORMAL SINUS RHYTHM • 72 BPM</span>
                      </div>
                    </div>
                  )}

                  {field === "cellular" && (
                    <div className="relative w-44 h-44 flex items-center justify-center">
                      <div className="absolute inset-0 rounded-full border-2 border-dashed border-cyan-400/50 animate-spin" style={{ animationDuration: "12s" }} />
                      <div className="w-28 h-28 rounded-full bg-cyan-950/60 border-2 border-cyan-400 flex items-center justify-center shadow-[0_0_20px_rgba(0,240,255,0.4)]">
                        <div className="w-10 h-10 rounded-full bg-cyan-400/80 animate-ping" />
                      </div>
                      <span className="absolute bottom-1 text-[9px] font-mono text-cyan-300">CELLULAR MITOSIS MESH</span>
                    </div>
                  )}

                  {field === "neurology" && (
                    <div className="w-full flex flex-col items-center gap-2">
                      <svg viewBox="0 0 200 120" className="w-full h-28 stroke-cyan-400 fill-cyan-400/30">
                        <circle cx="50" cy="60" r="10" />
                        <circle cx="150" cy="30" r="8" />
                        <circle cx="140" cy="95" r="12" />
                        <line x1="50" y1="60" x2="150" y2="30" strokeWidth="2" strokeDasharray="4 4" />
                        <line x1="50" y1="60" x2="140" y2="95" strokeWidth="2" strokeDasharray="4 4" />
                        <line x1="150" y1="30" x2="140" y2="95" strokeWidth="2" strokeDasharray="4 4" />
                      </svg>
                      <span className="text-[10px] font-mono text-cyan-300 tracking-wider">NEURAL SYNAPSE OSCILLATION</span>
                    </div>
                  )}

                  {field === "genomics" && (
                    <div className="flex flex-col items-center">
                      <Dna className="w-20 h-20 text-cyan-400 animate-pulse" />
                      <span className="text-[10px] font-mono text-cyan-300 mt-2">GENOMIC BASE-PAIR SEQUENCING</span>
                    </div>
                  )}
                </div>

                {/* Footer Header Info */}
                <div className="relative z-10 border-t border-cyan-500/40 pt-2.5">
                  <div className="text-[11px] font-black uppercase text-cyan-400 tracking-wide">
                    {graphic.parameters.headline || "CLINICAL EVIDENCE"}
                  </div>
                  <div className="text-[9px] font-mono text-neutral-400">
                    {graphic.parameters.subtext || "Phase III Human Trial Synthesis"}
                  </div>
                </div>
              </div>
            );
          })()}

          {/* G. Digital Highlighter Effect (Medical Journal) */}
          {graphic.template_id === "digital_highlighter" && (() => {
            const markerColor = graphic.parameters.marker_color || "#FFE600";
            const duration = Math.max(0.6, graphic.end - graphic.start);
            const elapsed = currentTime - graphic.start;
            const sweepProgress = Math.min(1, Math.max(0, (elapsed - 0.2) / Math.max(0.6, duration * 0.6)));

            return (
              <div className="relative w-84 bg-[#FAF9F5] text-neutral-900 rounded-xl p-4 shadow-2xl border border-neutral-300 font-serif animate-in fade-in zoom-in-95 duration-200">
                {/* Journal Header */}
                <div className="border-b-2 border-neutral-800 pb-2 mb-2.5 flex items-center justify-between">
                  <div>
                    <div className="text-xs font-black tracking-tight text-neutral-900 uppercase font-sans">
                      {graphic.parameters.journal_title || "The New England Journal of Medicine"}
                    </div>
                    <div className="text-[9px] font-mono text-neutral-500">
                      {graphic.parameters.citation_doi || "ORIGINAL CLINICAL INVESTIGATION"}
                    </div>
                  </div>
                  <FileText className="w-4 h-4 text-neutral-700" />
                </div>

                {/* Dense Scientific Passage */}
                <div className="text-xs leading-relaxed text-neutral-800 relative">
                  <p className="mb-2">
                    {graphic.parameters.dense_passage || "In a randomized trial, subjects administering the intervention exhibited a 42% reduction in systemic inflammatory biomarkers compared to baseline control."}
                  </p>

                  {/* Animated Translucent Highlighter Stroke over specific sentence */}
                  <div className="relative inline-block bg-transparent px-1 mt-1 rounded font-bold text-neutral-950">
                    <span
                      style={{
                        backgroundColor: markerColor,
                        opacity: 0.6,
                        clipPath: `inset(0 ${(1 - sweepProgress) * 100}% 0 0)`,
                        boxShadow: `0 0 12px ${markerColor}`
                      }}
                      className="absolute inset-0 rounded -rotate-0.5 transition-all duration-75"
                    />
                    <span className="relative z-10">
                      "{graphic.parameters.highlight_sentence || "exhibited a 42% reduction in systemic inflammatory biomarkers"}"
                    </span>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* G2. Reconstructed News / Medical Article (Screenshot 5) */}
          {false && graphic.template_id === "article_reconstruction" && (() => {
            const publisher = graphic.parameters.publisher || "Scroll.in";
            const headline = graphic.parameters.headline || "Dombivli hospital assault: Doctor resigns after attack by Shinde Sena corporator, fearing for safety";
            const dateStr = graphic.parameters.date || "May 14, 2024";
            const paragraph = graphic.parameters.paragraph || "The 26-year-old resident medical officer at the Kalyan-Dombivli Municipal Corporation's Shastri Nagar Hospital said he had left the city after receiving threats and would 'never go back'.";
            const highlightQuote = graphic.parameters.highlight_quote || "he had left the city after receiving threats and would 'never go back'";
            const markerColor = graphic.parameters.marker_color || "#00E5FF";
            const paperTheme = graphic.parameters.paper_theme || "editorial_clean";

            const duration = Math.max(0.6, graphic.end - graphic.start);
            const elapsed = currentTime - graphic.start;
            const sweepProgress = Math.min(1, Math.max(0, (elapsed - 0.25) / Math.max(0.6, duration * 0.6)));

            const isDark = paperTheme === "dark_archival";
            const isScrollIn = publisher.toLowerCase().includes("scroll.in");

            const highlightIndex = paragraph.indexOf(highlightQuote);
            const preText = highlightIndex > -1 ? paragraph.slice(0, highlightIndex) : "";
            const midText = highlightIndex > -1 ? highlightQuote : paragraph;
            const postText = highlightIndex > -1 ? paragraph.slice(highlightIndex + highlightQuote.length) : "";

            return (
              <div className="relative flex flex-col items-center animate-in fade-in zoom-in-95 duration-200">
                <div
                  className={`relative w-[330px] rounded-xl p-4 shadow-2xl border transition-all ${
                    isDark
                      ? "bg-slate-900/95 text-slate-100 border-slate-700 shadow-cyan-950/40"
                      : "bg-[#FCFAF6] text-neutral-900 border-neutral-300/80 shadow-2xl"
                  }`}
                  style={{
                    boxShadow: "0 20px 45px -10px rgba(0, 0, 0, 0.45), 0 0 1px rgba(0,0,0,0.2)"
                  }}
                >
                  {/* Newspaper Masthead */}
                  <div className={`pb-2 mb-2.5 flex items-center justify-between border-b ${
                    isDark ? "border-slate-800" : "border-neutral-200"
                  }`}>
                    {isScrollIn ? (
                      <div className="flex items-center gap-1.5">
                        <span className="font-serif italic font-black text-2xl tracking-tight text-neutral-950 flex items-center">
                          Scroll<span className="text-red-600 font-sans font-black">.</span>in
                        </span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5">
                        <FileText className={`w-3.5 h-3.5 ${isDark ? "text-cyan-400" : "text-neutral-700"}`} />
                        <span className="text-xs font-serif font-black tracking-tight uppercase">
                          {publisher}
                        </span>
                      </div>
                    )}

                    <div className="text-xs font-mono text-neutral-500 uppercase tracking-wider">
                      {dateStr}
                    </div>
                  </div>

                  {/* Headline */}
                  <h3 className={`text-xs font-serif font-bold leading-snug tracking-tight mb-2.5 ${
                    isDark ? "text-slate-100" : "text-neutral-900"
                  }`}>
                    {headline}
                  </h3>

                  {/* Body Paragraph with Kinetic Highlighter Sweep */}
                  <div className={`text-[11px] font-serif leading-relaxed relative ${
                    isDark ? "text-slate-300" : "text-neutral-800"
                  }`}>
                    {preText && <span>{preText}</span>}

                    <span className="relative inline-block font-semibold text-neutral-950 px-0.5 mx-0.5">
                      <span
                        className="absolute inset-0 rounded-[2px] pointer-events-none -rotate-[0.3deg] transition-all duration-75"
                        style={{
                          backgroundColor: markerColor,
                          opacity: 0.62,
                          clipPath: `inset(0 ${(1 - sweepProgress) * 100}% 0 0)`,
                          boxShadow: `0 0 10px ${markerColor}66`
                        }}
                      />
                      <span className="relative z-10 text-neutral-950 font-bold">
                        {midText}
                      </span>
                    </span>

                    {postText && <span>{postText}</span>}
                  </div>

                  {/* Archival Source Link */}
                  {graphic.parameters.source_url && (
                    <div className={`mt-2.5 pt-1.5 border-t text-[8px] font-mono flex items-center justify-between ${
                      isDark ? "border-slate-800 text-slate-500" : "border-neutral-200 text-neutral-400"
                    }`}>
                      <span className="truncate max-w-[200px]">{graphic.parameters.source_url}</span>
                      
                    </div>
                  )}
                </div>

                
              </div>
            );
          })()}

          {/* H. Jargon-to-Plain English Pop-Up */}
          {graphic.template_id === "jargon_translation" && (
            <div className="w-80 bg-neutral-950/95 border-2 border-lime rounded-2xl p-4 shadow-2xl text-white space-y-3 animate-in zoom-in-95 duration-200">
              {/* Complex Clinical Finding */}
              <div className="bg-neutral-900 p-2.5 rounded-xl border border-neutral-800 text-[11px] text-neutral-300 space-y-1">
                <div className="flex items-center gap-1 font-mono text-[9px] text-neutral-400 uppercase">
                  <FileText className="w-3 h-3 text-neutral-400" />
                  <span>Clinical Study Text</span>
                </div>
                <div className="italic font-serif">
                  "{graphic.parameters.clinical_finding || "Significant downregulation of serum C-reactive protein (CRP) & pro-inflammatory cytokines."}"
                </div>
              </div>

              {/* Floating Plain English Pop-Up Callout */}
              <div className="bg-gradient-to-r from-lime/20 to-lime/10 border-2 border-lime rounded-xl p-3 text-black text-left shadow-lg">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] font-mono font-black uppercase text-lime flex items-center gap-1">
                    <Sparkles className="w-3 h-3" />
                    <span>Plain English Translation</span>
                  </span>
                  <span className="text-[10px] font-mono font-bold bg-lime text-black px-1.5 py-0.2 rounded-full">
                    {graphic.parameters.takeaway_badge || "↓ 45% Inflammation"}
                  </span>
                </div>
                <div className="text-sm font-black text-white leading-snug">
                  {graphic.parameters.plain_english || "Body inflammation dropped dramatically in just 14 days!"}
                </div>
              </div>
            </div>
          )}

          {/* I. Metaphorical Physiological Sequence */}
          {graphic.template_id === "metaphor_sequence" && (() => {
            const mType = graphic.parameters.metaphor_type || "lock_and_key";
            return (
              <div className="w-76 bg-black/95 border-2 border-lime rounded-2xl p-4 text-center shadow-2xl text-white space-y-2 animate-in zoom-in-95 duration-200">
                <div className="text-[10px] font-mono text-lime font-bold uppercase tracking-wider">
                  {graphic.parameters.headline || "PHYSIOLOGICAL METAPHOR"}
                </div>

                {/* Animated Metaphor Icon / Mechanism */}
                <div className="py-2 flex items-center justify-center">
                  {mType === "lock_and_key" && (
                    <div className="flex items-center gap-2">
                      <Key className="w-10 h-10 text-lime animate-bounce" />
                      <ArrowRight className="w-5 h-5 text-neutral-500" />
                      <Shield className="w-10 h-10 text-cyan-400" />
                    </div>
                  )}
                  {mType === "immune_shield" && (
                    <div className="relative">
                      <Shield className="w-12 h-12 text-lime mx-auto shadow-[0_0_15px_rgba(180,240,0,0.5)]" />
                      <div className="text-[9px] font-mono text-lime mt-1 font-bold">ANTIBODY DEFENSE</div>
                    </div>
                  )}
                  {mType === "battery_recharge" && (
                    <div className="flex flex-col items-center">
                      <BatteryCharging className="w-12 h-12 text-lime animate-pulse" />
                      <div className="text-[10px] font-mono text-lime font-black mt-1">ATP CELL ENERGY 100%</div>
                    </div>
                  )}
                  {mType === "clogged_pipe" && (
                    <div className="flex items-center gap-2">
                      <Activity className="w-10 h-10 text-lime" />
                      <span className="text-xs font-mono text-neutral-300">CLEAR ARTERIAL FLOW</span>
                    </div>
                  )}
                </div>

                <div className="text-xs font-semibold text-neutral-200">
                  {graphic.parameters.caption || "The hormone acts like a custom key unlocking cellular receptors."}
                </div>
              </div>
            );
          })()}

          {/* J. Contextual Stock B-Roll Overlay with Edge Feathering */}
          {graphic.template_id === "contextual_broll" && (
            <div className="w-80 h-52 rounded-2xl border-2 border-cyan-400/80 bg-neutral-900 shadow-2xl overflow-hidden relative flex flex-col justify-between p-3 animate-in zoom-in-95 duration-200">
              {/* Feathered vignette overlay */}
              <div className="absolute inset-0 bg-gradient-to-t from-black via-black/30 to-transparent pointer-events-none" />
              <div className="relative z-10 flex items-center justify-between">
                <span className="px-2 py-0.5 rounded-full bg-cyan-400 text-black font-mono font-black text-[9px] uppercase">
                  B-ROLL: {graphic.parameters.broll_topic || "Clinical Context"}
                </span>
                <Sparkles className="w-3.5 h-3.5 text-cyan-300" />
              </div>

              <div className="relative z-10">
                <div className="text-sm font-black text-white">
                  {graphic.parameters.headline || "HEALTHY LIFESTYLE HABITS"}
                </div>
                <div className="text-[10px] text-neutral-300 font-mono">
                  Seamless edge feathered overlay
                </div>
              </div>
            </div>
          )}

          {/* K. Subject Extraction (Die-Cut Sticker Effect) */}
          {graphic.template_id === "sticker_cutout" && (
            <div className="flex flex-col items-center animate-in zoom-in-90 duration-300">
              <div className="p-4 rounded-3xl bg-neutral-900/90 border-4 border-white shadow-[0_15px_35px_rgba(0,0,0,0.8)] relative hover:scale-105 transition-transform">
                <Stethoscope className="w-16 h-16 text-lime stroke-[2.5]" />
                <div className="absolute -bottom-2.5 left-1/2 -translate-x-1/2 bg-white text-black font-black text-[10px] px-2.5 py-0.5 rounded-full uppercase shadow">
                  {graphic.parameters.label || "CLINICAL GRADE"}
                </div>
              </div>
            </div>
          )}

          {/* L. Persistent Authority Watermark Nameplate */}
          {graphic.template_id === "authority_watermark" && (
            <div className="bg-black/85 backdrop-blur-md border border-white/20 rounded-xl px-3 py-1.5 flex items-center gap-2 shadow-2xl animate-in fade-in duration-300">
              <div className="w-7 h-7 rounded-full bg-cyan-500/20 border border-cyan-400 flex items-center justify-center text-cyan-300">
                <Stethoscope className="w-4 h-4" />
              </div>
              <div className="text-left">
                <div className="text-xs font-black text-white flex items-center gap-1">
                  <span>{graphic.parameters.doctor_name || "Dr. Priya Sharma, MD"}</span>
                  <CheckCircle2 className="w-3 h-3 text-cyan-400 fill-cyan-400 text-black" />
                </div>
                <div className="text-[9px] font-mono text-neutral-400">
                  {graphic.parameters.credentials || "Cardiologist • AIIMS Heart Institute"}
                </div>
              </div>
            </div>
          )}

          {/* M. Medical Outro End Card */}
          {graphic.template_id === "medical_endcard" && (
            <div className="w-80 bg-neutral-950 border-2 border-lime rounded-2xl p-5 text-center shadow-2xl text-white space-y-3 animate-in zoom-in-95 duration-300">
              {/* Circular Portrait Cutout with Glowing Ring */}
              <div className="w-20 h-20 rounded-full border-2 border-lime mx-auto p-1 shadow-[0_0_20px_rgba(180,240,0,0.5)]">
                <div className="w-full h-full rounded-full bg-neutral-800 flex items-center justify-center font-bold text-lime text-xl">
                  👨‍⚕️
                </div>
              </div>

              <div>
                <div className="font-black text-sm text-white flex items-center justify-center gap-1">
                  <span>{graphic.parameters.doctor_name || "Dr. Priya Sharma, MD"}</span>
                  <CheckCircle2 className="w-3.5 h-3.5 text-lime fill-lime text-black" />
                </div>
                <div className="text-[10px] text-neutral-400 font-mono">
                  {graphic.parameters.tagline || "Evidence-Based Medicine • Weekly Insights"}
                </div>
              </div>

              {/* Social Handles */}
              <div className="flex justify-center gap-3 text-[10px] font-mono text-neutral-300">
                <span className="flex items-center gap-1">
                  <Youtube className="w-3 h-3 text-red-500" />
                  {graphic.parameters.social_yt || "@DrPriyaHealth"}
                </span>
                <span className="flex items-center gap-1">
                  <Instagram className="w-3 h-3 text-pink-500" />
                  {graphic.parameters.social_ig || "@dr.priya"}
                </span>
              </div>

              {/* Call to Action Button */}
              <button className="w-full py-2 bg-lime hover:bg-lime-400 text-black font-black text-xs rounded-xl shadow-[0_0_15px_rgba(180,240,0,0.4)] transition">
                {graphic.parameters.cta_text || "Subscribe for Evidence-Based Health Tips"}
              </button>
            </div>
          )}

          {/* N. Architectural Dimension Line & Callout */}
          {graphic.template_id === "dimension_callout" && (
            <div className="w-full max-w-[320px] flex flex-col items-center select-none pointer-events-none animate-in fade-in zoom-in-95 duration-200">
              <div className="relative w-full flex items-center justify-center my-2">
                <svg viewBox="0 0 300 40" className="w-full h-10 overflow-visible">
                  {/* Left Tick End-Cap */}
                  <line x1="12" y1="6" x2="12" y2="34" stroke={graphic.parameters.color || "#00F0FF"} strokeWidth="2.5" />
                  {/* Right Tick End-Cap */}
                  <line x1="288" y1="6" x2="288" y2="34" stroke={graphic.parameters.color || "#00F0FF"} strokeWidth="2.5" />
                  {/* Left Segment Line */}
                  <line x1="12" y1="20" x2="80" y2="20" stroke={graphic.parameters.color || "#00F0FF"} strokeWidth="2" strokeDasharray="3 3" />
                  {/* Left Arrow Head */}
                  <polygon points="14,20 24,15 24,25" fill={graphic.parameters.color || "#00F0FF"} />
                  {/* Right Segment Line */}
                  <line x1="220" y1="20" x2="288" y2="20" stroke={graphic.parameters.color || "#00F0FF"} strokeWidth="2" strokeDasharray="3 3" />
                  {/* Right Arrow Head */}
                  <polygon points="286,20 276,15 276,25" fill={graphic.parameters.color || "#00F0FF"} />
                </svg>

                {/* Center Measurement Pill */}
                <div
                  className="absolute px-3 py-1 rounded-full bg-black/95 border-2 text-xs font-mono font-black tracking-wider shadow-[0_0_15px_rgba(0,240,255,0.4)] flex items-center gap-1.5"
                  style={{
                    borderColor: graphic.parameters.color || "#00F0FF",
                    color: graphic.parameters.color || "#00F0FF"
                  }}
                >
                  <span
                    className="w-1.5 h-1.5 rounded-full animate-ping"
                    style={{ backgroundColor: graphic.parameters.color || "#00F0FF" }}
                  />
                  <span>{graphic.parameters.measurement_text || "14 FEET LONG"}</span>
                </div>
              </div>
              {graphic.parameters.subtext && (
                <span className="text-[10px] font-mono uppercase tracking-widest text-neutral-300 bg-black/80 px-2 py-0.5 rounded border border-neutral-700 shadow-md">
                  {graphic.parameters.subtext}
                </span>
              )}
            </div>
          )}

          {/* O. Automated Source Citation Overlay */}
          {graphic.template_id === "source_citation" && (
            <div className="absolute top-2 left-2 flex items-center gap-2 bg-black/85 backdrop-blur-md px-3 py-1.5 rounded-md border border-neutral-700 shadow-xl pointer-events-none">
              <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <div className="flex flex-col text-left">
                <span className="text-[11px] font-mono font-bold tracking-wider text-white uppercase">
                  {graphic.parameters.source_name || "Source: National Archives (1969)"}
                </span>
                {graphic.parameters.doc_type && (
                  <span className="text-[9px] font-mono text-cyan-400">
                    {graphic.parameters.doc_type}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* P. 3D Rotating Globe Outro & Teaser Carousel */}
          {graphic.template_id === "documentary_outro" && (
            <div className="w-80 bg-neutral-950/95 border-2 border-cyan-400/80 rounded-2xl p-4 text-center shadow-2xl text-white space-y-3 animate-in zoom-in-95 duration-300 backdrop-blur-md">
              {/* Animated 3D Rotating Wireframe Globe */}
              <div className="relative w-24 h-24 mx-auto flex items-center justify-center">
                <svg viewBox="0 0 100 100" className="w-full h-full animate-spin [animation-duration:12s]">
                  <circle cx="50" cy="50" r="44" fill="none" stroke="#00F0FF" strokeWidth="1.5" strokeDasharray="4 2" opacity="0.6" />
                  <ellipse cx="50" cy="50" rx="44" ry="18" fill="none" stroke="#00F0FF" strokeWidth="1.5" opacity="0.7" />
                  <ellipse cx="50" cy="50" rx="18" ry="44" fill="none" stroke="#00F0FF" strokeWidth="1.5" opacity="0.7" />
                  <line x1="6" y1="50" x2="94" y2="50" stroke="#00F0FF" strokeWidth="1.2" opacity="0.5" />
                  <line x1="50" y1="6" x2="50" y2="94" stroke="#00F0FF" strokeWidth="1.2" opacity="0.5" />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center font-black text-xs text-cyan-300 font-mono tracking-tighter">
                  ARCHIVE
                </div>
              </div>

              <div>
                <div className="font-black text-sm text-white tracking-wider font-montserrat uppercase">
                  {graphic.parameters.globe_headline || "MISSION LOG COMPLETE"}
                </div>
                <div className="text-[10px] text-cyan-400/80 font-mono uppercase tracking-widest mt-0.5">
                  HISTORICAL RECONSTRUCTION
                </div>
              </div>

              {/* Episode Teaser Carousel */}
              <div className="space-y-1.5 text-left">
                <div className="text-[9px] font-mono text-neutral-400 uppercase tracking-wider">UP NEXT IN SERIES:</div>
                <div className="grid grid-cols-2 gap-1.5">
                  <div className="bg-neutral-900 border border-neutral-700 rounded-lg p-1.5 hover:border-cyan-400 transition">
                    <div className="text-[8px] text-cyan-400 font-mono font-bold">EPISODE 02</div>
                    <div className="text-[10px] font-semibold text-neutral-200 line-clamp-1">
                      {graphic.parameters.teaser_1 || "Part II: The Stratosphere"}
                    </div>
                  </div>
                  <div className="bg-neutral-900 border border-neutral-700 rounded-lg p-1.5 hover:border-cyan-400 transition">
                    <div className="text-[8px] text-cyan-400 font-mono font-bold">EPISODE 03</div>
                    <div className="text-[10px] font-semibold text-neutral-200 line-clamp-1">
                      {graphic.parameters.teaser_2 || "Part III: Deep Oceanic Trench"}
                    </div>
                  </div>
                </div>
              </div>

              {/* Urgency CTA Button */}
              <button className="w-full py-2 bg-gradient-to-r from-cyan-400 to-blue-500 hover:from-cyan-300 hover:to-blue-400 text-black font-black text-xs rounded-xl shadow-[0_0_15px_rgba(0,240,255,0.4)] tracking-wider uppercase transition">
                {graphic.parameters.cta_text || "SUBSCRIBE FOR NEXT EPISODE"}
              </button>
            </div>
          )}

          {/* Q. Static Top-Right Corner Bug Watermark */}
          {graphic.template_id === "corner_bug" && (
            <div className="absolute top-2 right-2 flex items-center gap-1.5 px-2.5 py-1 rounded bg-black/80 border border-white/20 backdrop-blur-sm pointer-events-none shadow-md">
              <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
              <span className="text-[10px] font-mono font-black tracking-widest text-white uppercase">
                {graphic.parameters.bug_text || "CHRONICLES"}
              </span>
            </div>
          )}
        </div>
      );
    })}

      {/* 4. Render Active Captions with Click-and-Drag (only suppress when a title explicitly requests it) */}
      {visibleCaptions.filter(() => {
        const isTitleActive = graphics.some(
          g => g.start <= currentTime && currentTime < g.end && (
            g.parameters?.suppress_subtitles === true ||
            (g.template_id === 'kinetic_typography' && g.parameters?.suppress_subtitles !== false && g.placement_mode === 'insert')
          )
        );
        return !isTitleActive;
      }).map((caption) => {
        const isSelected = caption.id === selectedCaptionId;
        const style = caption.style;
        // Check background strictly based on user's style toggle, not preset name override
        const isDocMinimalist = !style.has_background;
        const textToDisplay =
          activeLanguageView === 'hindi'
            ? caption.text
            : (caption.translated_text || caption.text);

        // Automatic layout can store 8–24px sizes meant for burn-in; keep a readable floor in the studio preview.
        const displayFontSize = Math.max(28, Number(style.font_size) || 32);

        // Check if a graphic / split-screen is active at this moment
        const activeGraphic = graphics.find(g => currentTime >= g.start && currentTime <= g.end);
        const isSplitActive = Boolean(
          activeGraphic?.template_id === 'split_screen_vertical' ||
          activeGraphic?.template_id === 'split_silhouette_walking' ||
          activeGraphic?.template_id === 'split_silhouette_falling' ||
          activeGraphic?.parameters?.split_mode
        );

        // Effective position: if during graphic/split, use dedicated override, or default to 0.90 for split-screen to keep off the speaker's face!
        const effectivePosY = activeGraphic
          ? (caption.pos_y_during_graphic ?? (isSplitActive ? 0.90 : caption.pos_y))
          : caption.pos_y;
        const effectivePosX = activeGraphic
          ? (caption.pos_x_during_graphic ?? caption.pos_x)
          : caption.pos_x;

        // Contrast block modes: pill, per_word, solid_box
        const contrastMode = style.contrast_block_mode || 'solid_box';
        const isPerWord = style.has_background && contrastMode === 'per_word' && !isDocMinimalist;
        const isPill = style.has_background && contrastMode === 'pill' && !isDocMinimalist;

        // Apply background alpha on the color only — never set opacity on the caption node
        // (CSS opacity on the parent would fade the glyph text and make subtitles look "missing").
        const bgAlpha = Math.max(0, Math.min(1, style.background_opacity ?? 0.75));
        const containerBg = isDocMinimalist || isPerWord || !style.has_background
          ? "transparent"
          : (() => {
              const raw = style.background_color || "#000000";
              if (raw.startsWith("rgba") || raw.startsWith("rgb")) return raw;
              const hex = raw.replace("#", "");
              const full = hex.length === 3 ? hex.split("").map((c) => c + c).join("") : hex;
              if (full.length !== 6) return `rgba(0,0,0,${bgAlpha})`;
              const r = parseInt(full.slice(0, 2), 16);
              const g = parseInt(full.slice(2, 4), 16);
              const b = parseInt(full.slice(4, 6), 16);
              return `rgba(${r},${g},${b},${bgAlpha})`;
            })();
        const containerRadius = isPill
          ? "9999px"
          : `${style.corner_radius ?? 12}px`;

        return (
          <div
            key={caption.id}
            onMouseDown={(e) => handleMouseDown(e, caption.id)}
            style={{
              left: `${effectivePosX * 100}%`,
              top: `${effectivePosY * 100}%`,
              transform: "translate(-50%, -50%)",
              cursor: isDragging ? "grabbing" : "grab"
            }}
            className={`absolute z-40 group transition-shadow select-none max-w-[90%] text-center pointer-events-auto ${
              isSelected ? "ring-2 ring-lime ring-offset-2 ring-offset-black" : ""
            }`}
          >
            {/* Draggable Bounding Handle */}
            {isSelected && (
              <div className="absolute -top-5 left-1/2 -translate-x-1/2 bg-lime text-black text-[9px] font-mono font-black px-1.5 py-0.2 rounded shadow whitespace-nowrap">
                Drag caption
              </div>
            )}

            {/* Rounded Background Box & Styled Words */}
            <div
              style={{
                backgroundColor: containerBg,
                borderRadius: containerRadius,
                padding: isDocMinimalist || isPerWord ? "2px 4px" : `${style.padding_y ?? 10}px ${style.padding_x ?? 18}px`,
                boxShadow: !isDocMinimalist && !isPerWord && style.has_background && style.shadow_blur
                  ? `${style.shadow_offset_x}px ${style.shadow_offset_y}px ${style.shadow_blur}px ${style.shadow_color}`
                  : "0 2px 8px rgba(0,0,0,0.45)"
              }}
              className={`inline-block transition-all ${isDocMinimalist || isPerWord ? "" : "backdrop-blur-sm"}`}
            >
              {/* Word-Level Dynamic Text Engine: Pacing, Cadence & Keyword Emphasis */}
              {caption.words && caption.words.length > 0 ? (() => {
                const pacingMode = style.pacing_mode || "full_line";

                // Filter or slice words based on pacing mode
                let wordsToProcess = caption.words;

                if (pacingMode === "phrase_chunk") {
                  const activeIdx = caption.words.findIndex(
                    (w) => currentTime >= w.start && currentTime <= w.end
                  );
                  const validIdx = activeIdx >= 0 ? activeIdx : 0;
                  const chunkSize = 3;
                  const startIdx = Math.floor(validIdx / chunkSize) * chunkSize;
                  wordsToProcess = caption.words.slice(startIdx, startIdx + chunkSize);
                }

                const renderWordSpans = (wordsSlice: typeof caption.words, offsetKey: number = 0) =>
                  wordsSlice.map((w, wIdx) => {
                    const isHighlightEnabled = style.has_highlight !== false;
                    const isShadowEnabled = style.has_shadow !== false;

                    const isWordActive = currentTime >= w.start && currentTime <= w.end;
                    const isWordPast = currentTime > w.end;
                    const isWordFuture = currentTime < w.start;

                    // Pacing Mode: Word Reveal (words only appear as they are spoken)
                    if (pacingMode === "word_reveal" && isWordFuture) {
                      return (
                        <span
                          key={offsetKey + wIdx}
                          className="inline-block opacity-0 select-none pointer-events-none w-0 overflow-hidden"
                        >
                          {w.word}
                        </span>
                      );
                    }

                    // Clean static subtitles: zero word bouncing or distracting karaoke shifts
                    const wordColor = style.text_color || "#FFFFFF";
                    const transform = "none";

                    let textShadow = "none";
                    if (isDocMinimalist) {
                      textShadow = "0px 2px 4px rgba(0,0,0,0.9), 0px 1px 2px rgba(0,0,0,0.95)";
                    } else if (isShadowEnabled) {
                      const shadowParts: string[] = [];
                      if (style.outline_width > 0) {
                        shadowParts.push(
                          `-${style.outline_width}px -${style.outline_width}px 0 ${style.outline_color}`,
                          `${style.outline_width}px -${style.outline_width}px 0 ${style.outline_color}`,
                          `-${style.outline_width}px ${style.outline_width}px 0 ${style.outline_color}`,
                          `${style.outline_width}px ${style.outline_width}px 0 ${style.outline_color}`
                        );
                      }
                      if (style.shadow_blur > 0) {
                        shadowParts.push(
                          `${style.shadow_offset_x || 0}px ${style.shadow_offset_y || 2}px ${style.shadow_blur}px ${style.shadow_color || "rgba(0,0,0,0.8)"}`
                        );
                      }
                      if (shadowParts.length > 0) {
                        textShadow = shadowParts.join(", ");
                      }
                    }

                    const wordElement = (
                      <span
                        key={offsetKey + wIdx}
                        style={{
                          fontSize: `${displayFontSize}px`,
                          color: wordColor || "#FFFFFF",
                          transform,
                          textShadow: textShadow === "none"
                            ? "0 2px 4px rgba(0,0,0,0.9), 0 1px 2px rgba(0,0,0,0.95)"
                            : textShadow,
                          fontFamily: style.font_family || "Montserrat, sans-serif",
                          fontStyle: "normal",
                          fontWeight: style.font_weight || "700",
                          backgroundColor: isPerWord ? style.background_color : undefined,
                          borderRadius: isPerWord ? `${Math.min(style.corner_radius ?? 6, 16)}px` : undefined,
                          padding: isPerWord ? `${Math.max(2, style.padding_y)}px ${Math.max(4, style.padding_x)}px` : undefined,
                          margin: isPerWord ? "0 2px" : undefined
                        }}
                        className="inline-block"
                      >
                        {w.word}
                      </span>
                    );

                    return wordElement;
                  });

                // Check lines configuration
                const maxLines = style.max_lines ?? 1;

                if (maxLines === 1 || pacingMode === "phrase_chunk") {
                  // Strict Single Line
                  return (
                    <div
                      style={{
                        fontFamily: style.font_family,
                        fontWeight: style.font_weight,
                        fontSize: `${displayFontSize}px`,
                        lineHeight: style.line_height || 1.2,
                        letterSpacing: `${style.letter_spacing ?? 0}px`,
                        textTransform: style.is_uppercase ? "uppercase" : "none"
                      }}
                      className="flex flex-nowrap items-center justify-center gap-x-2 whitespace-nowrap"
                    >
                      {renderWordSpans(wordsToProcess)}
                    </div>
                  );
                }

                // Dual-Line (2 Lines) mode — prefer active language text for line breaks
                const rawText = textToDisplay || caption.translated_text || caption.text;
                let line1: typeof caption.words = [];
                let line2: typeof caption.words = [];

                if (rawText.includes("\n")) {
                  const parts = rawText.split("\n");
                  const p1Count = parts[0].trim().split(/\s+/).filter(Boolean).length;
                  line1 = wordsToProcess.slice(0, p1Count);
                  line2 = wordsToProcess.slice(p1Count);
                } else if (wordsToProcess.length >= 3) {
                  const mid = Math.ceil(wordsToProcess.length / 2);
                  line1 = wordsToProcess.slice(0, mid);
                  line2 = wordsToProcess.slice(mid);
                } else {
                  line1 = wordsToProcess;
                }

                return (
                  <div
                    style={{
                      fontFamily: style.font_family,
                      fontWeight: style.font_weight,
                      fontSize: `${displayFontSize}px`,
                      lineHeight: style.line_height || 1.2,
                      letterSpacing: `${style.letter_spacing ?? 0}px`,
                      textTransform: style.is_uppercase ? "uppercase" : "none"
                    }}
                    className="flex flex-col items-center justify-center gap-y-1"
                  >
                    <div className="flex flex-nowrap items-center justify-center gap-x-2 whitespace-nowrap">
                      {renderWordSpans(line1, 0)}
                    </div>
                    {line2.length > 0 && (
                      <div className="flex flex-nowrap items-center justify-center gap-x-2 whitespace-nowrap">
                        {renderWordSpans(line2, line1.length)}
                      </div>
                    )}
                  </div>
                );
              })() : (
                /* Fallback if words array is not yet split */
                <span
                  style={{
                    fontFamily: style.font_family || "Montserrat, sans-serif",
                    fontWeight: style.font_weight || "700",
                    fontSize: `${displayFontSize}px`,
                    color: style.text_color || "#FFFFFF",
                    lineHeight: style.line_height || 1.2,
                    letterSpacing: `${style.letter_spacing ?? 0}px`,
                    textTransform: style.is_uppercase ? "uppercase" : "none",
                    whiteSpace: style.max_lines === 1 ? "nowrap" : "pre-line",
                    textShadow: "0 2px 4px rgba(0,0,0,0.9), 0 1px 2px rgba(0,0,0,0.95)"
                  }}
                  className="font-extrabold"
                >
                  {style.max_lines === 1 ? textToDisplay.replace(/\n/g, " ") : textToDisplay}
                </span>
              )}
            </div>
          </div>
        );
      })}
      </div>
    </div>
  );
};
