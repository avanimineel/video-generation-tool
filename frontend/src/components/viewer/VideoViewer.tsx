import React, { useRef, useEffect, useState } from "react";
import { Play, Pause, RotateCcw, Volume2, Maximize2 } from "lucide-react";
import { CanvasOverlay, TimelineVideo } from "./CanvasOverlay";
import { ProjectState, ProjectSettings, MotionGraphicItem, AudioTrackItem } from "../../types";
import { api, BACKEND_ORIGIN } from "../../services/api";

interface VideoViewerProps {
  project: ProjectState;
  currentTime: number;
  isPlaying: boolean;
  selectedCaptionId: string | null;
  onTimeUpdate: (time: number) => void;
  onTogglePlay: () => void;
  onSelectCaption: (id: string) => void;
  onUpdateCaptionPosition: (id: string, posX: number, posY: number, duringGraphic?: boolean) => void;
  activeLanguageView?: 'english' | 'hindi';
  onUpdateSettings?: (settings: ProjectSettings) => void;
  onUpdateGraphic?: (graphic: MotionGraphicItem) => void;
}

// The project's licensed music bed, kept in step with the playhead. While a caption is on screen the
// bed is lowered, a preview of the export's ducking under speech.
function MusicBed({ track, time, playing, speaking }: { track: AudioTrackItem; time: number; playing: boolean; speaking: boolean }) {
  const ref = useRef<HTMLAudioElement>(null);
  const local = time - (track.start || 0);
  const inside = local >= 0 && local < (track.duration || 0);
  useEffect(() => {
    const audio = ref.current; if (!audio) return;
    const fadeIn = Math.min(1, local / 0.6), fadeOut = Math.min(1, ((track.duration || 0) - local) / 1.5);
    audio.volume = Math.max(0, Math.min(1, (track.volume ?? 0.35) * (speaking && track.duck_under_speech !== false ? 0.3 : 1) * Math.max(0, Math.min(fadeIn, fadeOut))));
    if (!inside) { audio.pause(); return; }
    if (Math.abs(audio.currentTime - local) > 0.25) audio.currentTime = local;
    if (playing) void audio.play().catch(() => {}); else audio.pause();
  }, [local, playing, speaking, inside, track]);
  return <audio ref={ref} src={`${BACKEND_ORIGIN}${track.url}`} preload="auto" />;
}

export const VideoViewer: React.FC<VideoViewerProps> = ({
  project,
  currentTime,
  isPlaying,
  selectedCaptionId,
  onTimeUpdate,
  onTogglePlay,
  onSelectCaption,
  onUpdateCaptionPosition,
  activeLanguageView = 'english',
  onUpdateSettings,
  onUpdateGraphic
}) => {
  const [playbackError,setPlaybackError]=useState('');
  const playbackUrl=project.source_media_path ? `${api.getProxyUrl(project.id)}?preview=2&source=${encodeURIComponent(project.source_media_path)}` : project.video_url;
  useEffect(()=>setPlaybackError(''),[playbackUrl]);
  const videoRef = useRef<HTMLVideoElement>(null);
  const is916 = (project?.settings?.aspect_ratio ?? "9:16") === "9:16";
  const graphics = project?.graphics ?? [];
  const reframe = graphics.find(g=>g.template_id==='source_reframe' && currentTime>=g.start && currentTime<g.end);
  const reframeProgress = reframe ? Math.min(1,Math.max(0,(currentTime-reframe.start)/(reframe.end-reframe.start))) : 0;
  const motionProgress = reframe?.parameters.motion_curve === 'pulse' ? Math.sin(Math.PI * reframeProgress) ** 2 : reframe?.parameters.motion_curve === 'smoothstep' ? reframeProgress * reframeProgress * (3 - 2 * reframeProgress) : reframeProgress;
  const targetScale = reframe?.parameters.motion_curve === 'pulse' ? 1.08 : Number(reframe?.parameters.end_scale ?? 1.13);
  const reframeScale = reframe ? Number(reframe.parameters.start_scale ?? 1)+(targetScale-Number(reframe.parameters.start_scale ?? 1))*motionProgress : 1;
  const captions = project?.captions ?? [];

  // Sync HTML5 video play/pause & currentTime
  useEffect(() => {
    if (videoRef.current) {
      if (isPlaying && videoRef.current.paused) {
        videoRef.current.play().catch((error) => {setPlaybackError('Playback could not start: '+error.message);onTogglePlay();});
      } else if (!isPlaying && !videoRef.current.paused) {
        videoRef.current.pause();
      }
    }
  }, [isPlaying, playbackUrl]);

  useEffect(() => {
    if (videoRef.current && Math.abs(videoRef.current.currentTime - currentTime) > 0.25) {
      videoRef.current.currentTime = currentTime;
    }
  }, [currentTime]);

  const handleLoadedMetadata = () => {
    if (videoRef.current && Math.abs(videoRef.current.currentTime - currentTime) > 0.1) {
      videoRef.current.currentTime = currentTime;
    }
  };

  const handleCanPlay = () => {
    setPlaybackError('');
    if (videoRef.current && Math.abs(videoRef.current.currentTime - currentTime) > 0.1) {
      videoRef.current.currentTime = currentTime;
    }
  };

  const handleVideoTimeUpdate = () => {
    if (videoRef.current && isPlaying) {
      onTimeUpdate(videoRef.current.currentTime);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 100);
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}.${ms.toString().padStart(2, "0")}`;
  };

  // Check if current time has an active 50/50 horizontal split-screen graphic
  const activeSplitGraphic = graphics.find(
    (g) =>
      currentTime >= g.start &&
      currentTime <= g.end &&
      (g.template_id === "split_silhouette_walking" ||
        g.template_id === "split_silhouette_falling" ||
        Boolean(g.parameters?.split_mode))
  );

  // Check if current time has an active 50/50 vertical split-screen (B-roll top, Speaker bottom)
  const activeVerticalSplit = graphics.find(
    (g) =>
      currentTime >= g.start &&
      currentTime <= g.end &&
      (g.template_id === "split_screen_vertical" ||
       g.split_layout === "split_50_50_vertical" ||
       g.parameters?.split_layout === "split_50_50_vertical")
  );

  // Check if current time has an archival filter applied
  const activeArchivalFilter = graphics.find(
    (g) =>
      currentTime >= g.start &&
      currentTime <= g.end &&
      g.template_id === "archival_filter"
  );

  const isArchivalGraded = Boolean(
    activeArchivalFilter || project?.settings?.brand_preset === "documentary_minimalist"
  );

  return (
    <div className="flex-1 bg-neutral-100 flex flex-col items-center justify-center p-4 relative overflow-hidden select-none">
      {(project?.audio_tracks || []).filter(t => t.type === "music" && t.music_id).map(t => (
        <MusicBed key={t.id} track={t} time={currentTime} playing={isPlaying} speaking={captions.some(c => currentTime >= c.start && currentTime < c.end)} />
      ))}
      {playbackError&&<p role="alert" className="absolute top-2 z-50 bg-red-50 text-red-800 p-3 rounded text-sm">{playbackError}</p>}
      {/* Aspect Ratio Video Container */}
      <div
        className={`relative bg-neutral-900 rounded-2xl overflow-hidden shadow-xl border border-neutral-300 flex items-center justify-center mb-16 ${
          is916
            ? "aspect-[9/16] h-[85%] max-h-[calc(100%-80px)] max-w-[420px]"
            : "aspect-[16/9] w-[90%] max-h-[calc(100%-80px)] max-w-[800px]"
        }`}
      >
        {/* Top 50% Archival B-Roll Container (when 50/50 Vertical Split is active) */}
        {activeVerticalSplit && (() => {
          const rawMediaUrl = activeVerticalSplit.parameters?.media_url || activeVerticalSplit.media_url;
          // Direct backend port resolution to bypass any dev-server proxy restrictions
          const mediaUrl = rawMediaUrl?.startsWith('/api') 
            ? `${BACKEND_ORIGIN}${rawMediaUrl}`
            : rawMediaUrl;

          const isExplicitImage = Boolean(mediaUrl?.match(/\.(jpg|jpeg|png|webp|gif|svg)(\?.*)?$/i)) || Boolean(mediaUrl?.includes('images.unsplash.com'));
          const isVideo = !isExplicitImage && (
            Boolean(mediaUrl?.match(/\.(mp4|webm|ogv|mov)(\?.*)?$/i)) ||
            (activeVerticalSplit.parameters?.media_type || activeVerticalSplit.media_type) === "video"
          );
          const brollTitle = activeVerticalSplit.parameters?.broll_topic || activeVerticalSplit.parameters?.broll_title || activeVerticalSplit.title;
          const sourceCitation = activeVerticalSplit.parameters?.source_citation || activeVerticalSplit.source_name;
          const showSourceBadge = activeVerticalSplit.parameters?.show_source_badge !== false && (activeVerticalSplit as any).show_source_badge !== false;
          const showTitleBadge = activeVerticalSplit.parameters?.show_title_badge !== false && (activeVerticalSplit as any).show_title_badge !== false;
          const splitRatio = activeVerticalSplit.parameters?.split_ratio ?? 0.5;
          const speakerFocusY = activeVerticalSplit.parameters?.speaker_focus_y ?? 0.28;
          const progress = Math.max(0, Math.min(1, (currentTime - activeVerticalSplit.start) / Math.max(0.1, activeVerticalSplit.end - activeVerticalSplit.start)));

          return (
            <div 
              style={{ height: `${splitRatio * 100}%` }}
              className="absolute top-0 left-0 right-0 bg-neutral-950 overflow-hidden z-10 border-b-2 border-white/50 flex flex-col justify-between p-3 shadow-2xl"
            >
              {/* Media Display: Real Video, Real Image, or Contextual Canvas Fallback */}
              {mediaUrl ? (() => {
                const mediaScale = activeVerticalSplit.parameters?.media_scale ?? (activeVerticalSplit.scale ?? 1.0);
                const mediaPosX = activeVerticalSplit.parameters?.media_pos_x ?? (activeVerticalSplit.pos_x ?? 0.5);
                const mediaPosY = activeVerticalSplit.parameters?.media_pos_y ?? (activeVerticalSplit.pos_y ?? 0.5);
                const objPos = `${mediaPosX * 100}% ${mediaPosY * 100}%`;
                const transform = `scale(${mediaScale})`;

                return (
                  <div className="absolute inset-0 overflow-hidden flex items-center justify-center">
                    {isVideo ? (
                      <div 
                        className="w-full h-full flex items-center justify-center"
                        style={{
                          transform,
                          transformOrigin: objPos
                        }}
                      >
                        <TimelineVideo 
                          key={mediaUrl} 
                          src={mediaUrl}
                          time={currentTime - activeVerticalSplit.start} 
                          playing={isPlaying}
                          style={{ objectPosition: objPos }}
                        />
                      </div>
                    ) : (
                      <img
                        key={mediaUrl}
                        src={mediaUrl}
                        alt={brollTitle}
                        className="w-full h-full object-cover"
                        style={{
                          objectPosition: objPos,
                          transform,
                          transformOrigin: objPos
                        }}
                      />
                    )}
                    {/* Subtle filmic shading so text overlays pop */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/50 pointer-events-none" />
                  </div>
                );
              })() : (
                /* Topic-Agnostic Contextual Motion Canvas */
                <div className="absolute inset-0 bg-gradient-to-b from-neutral-800 via-neutral-900 to-black flex items-center justify-center opacity-95">
                  <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff0c_1px,transparent_1px),linear-gradient(to_bottom,#ffffff0c_1px,transparent_1px)] bg-[size:20px_20px]" />
                  <div className="relative flex flex-col items-center justify-center text-center p-3">
                    <div className="text-xs font-semibold text-neutral-300">
                      {brollTitle}
                    </div>
                    
                  </div>
                </div>
              )}

              {/* Clean media - no badge pills or description overlays */}
            </div>
          );
        })()}

        {/* Talking Head / Speaker Container */}
        <div
          style={{
            height: activeVerticalSplit ? `${(1 - (activeVerticalSplit.parameters?.split_ratio ?? 0.5)) * 100}%` : undefined
          }}
          className={`overflow-hidden absolute ${
            activeVerticalSplit
              ? "bottom-0 left-0 right-0"
              : activeSplitGraphic
              ? "left-0 top-0 bottom-0 w-1/2 border-r border-black/30 h-full"
              : "inset-0 w-full h-full"
          } ${isArchivalGraded ? "contrast-115 grayscale-[0.3]" : ""}`}
        >
          {project.video_url || project.proxy_media_path ? (
            <video
              ref={videoRef}
              key={playbackUrl}
              src={playbackUrl}
              onTimeUpdate={handleVideoTimeUpdate}
              onEnded={() => onTogglePlay()}
              onError={() => {setPlaybackError('The preview could not be decoded. Check that video preparation has finished and reload.');if(isPlaying)onTogglePlay();}}
              style={{
                transform: `scale(${reframeScale})`,
                transformOrigin: `${Number(reframe?.parameters.focus_x ?? 0.5) * 100}% ${Number(reframe?.parameters.focus_y ?? 0.5) * 100}%`,
                objectPosition: activeVerticalSplit 
                  ? `center ${(activeVerticalSplit.parameters?.speaker_focus_y ?? 0.28) * 100}%` 
                  : "center center"
              }}
              className="w-full h-full object-cover"
              playsInline
              preload="auto"
              onLoadedMetadata={handleLoadedMetadata}
              onLoadedData={handleLoadedMetadata}
              onCanPlay={handleCanPlay}
              crossOrigin="anonymous"
            />
          ) : (
            /* Clean Minimal Video Canvas Backdrop */
            <div className="w-full h-full bg-neutral-900 flex flex-col items-center justify-center relative overflow-hidden">
              <div className="relative z-0 flex flex-col items-center mt-6">
                <div className="h-20 w-20 rounded-full bg-neutral-800 border border-neutral-700 shadow-md flex items-center justify-center text-neutral-400">
                  <Play className="h-8 w-8 ml-1" />
                </div>
                <div className="text-[11px] font-mono font-semibold text-neutral-400 mt-4">
                  {activeVerticalSplit ? "PRIMARY SPEAKER (BOTTOM 50%)" : "9:16 VIDEO CANVAS"}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Side: 50/50 Split Screen Graphic Pillar (Frames 4 & 5 Screenshot) */}
        {activeSplitGraphic && (
          <div className="absolute right-0 top-0 bottom-0 w-1/2 bg-[#B4F000] overflow-hidden flex items-center justify-center z-10 animate-in fade-in slide-in-from-right-4 duration-300 shadow-[-8px_0_24px_rgba(0,0,0,0.5)]">
            {activeSplitGraphic.template_id === "split_silhouette_falling" ? (
              /* Jumping / Falling Silhouette */
              <svg viewBox="0 0 200 320" className="w-full h-full max-h-[360px] p-2 select-none pointer-events-none">
                <defs>
                  <path id="splitFallTop" d="M 20 70 Q 100 18 180 70" fill="none" />
                  <path id="splitFallBot" d="M 20 280 Q 100 325 180 280" fill="none" />
                </defs>
                <text className="fill-black font-black text-[22px] tracking-tighter uppercase font-montserrat">
                  <textPath href="#splitFallTop" startOffset="50%" textAnchor="middle">
                    {activeSplitGraphic.parameters.arc_text_top || "under"}
                  </textPath>
                </text>
                <g fill="#000000" transform="translate(100, 160) rotate(-14) translate(-100, -160)">
                  <circle cx="85" cy="115" r="13" />
                  <path d="M 82 128 L 122 138 L 114 185 L 75 175 Z" />
                  <path d="M 80 132 C 60 140, 45 155, 38 168 C 36 172, 41 175, 45 171 C 52 161, 68 148, 84 142 Z" />
                  <path d="M 120 138 C 135 125, 150 110, 162 98 C 166 94, 162 89, 158 92 C 146 102, 130 118, 116 130 Z" />
                  <path d="M 80 178 L 65 235 L 50 248 L 56 254 L 78 242 L 90 182 Z" />
                  <path d="M 108 184 L 140 230 L 155 240 L 160 235 L 142 220 L 116 182 Z" />
                </g>
                <text className="fill-black font-black text-[22px] tracking-tighter uppercase font-montserrat">
                  <textPath href="#splitFallBot" startOffset="50%" textAnchor="middle">
                    {activeSplitGraphic.parameters.arc_text_bottom || "my feet"}
                  </textPath>
                </text>
              </svg>
            ) : (
              /* Walking Silhouette (Default Frame 4) */
              <svg viewBox="0 0 200 320" className="w-full h-full max-h-[360px] p-2 select-none pointer-events-none">
                <defs>
                  <path id="splitWalkTop" d="M 15 80 Q 100 16 185 80" fill="none" />
                  <path id="splitWalkBot" d="M 15 285 Q 100 322 185 285" fill="none" />
                </defs>
                <text className="fill-black font-black text-[20px] tracking-tight uppercase" style={{ fontFamily: "Montserrat, sans-serif" }}>
                  <textPath href="#splitWalkTop" startOffset="50%" textAnchor="middle">
                    {activeSplitGraphic.parameters.arc_text_top || "It felt like"}
                  </textPath>
                </text>
                <g fill="#000000">
                  <circle cx="100" cy="98" r="14" />
                  <path d="M 93 112 L 107 112 L 111 119 L 89 119 Z" />
                  <path d="M 78 120 C 78 116, 122 116, 122 120 L 126 196 C 114 200, 86 200, 74 196 Z" />
                  <path d="M 78 122 C 72 135, 68 162, 69 182 C 69 188, 74 188, 75 182 C 77 164, 81 140, 84 128 Z" />
                  <path d="M 122 122 C 128 135, 132 162, 131 182 C 131 188, 126 188, 125 182 C 123 164, 119 140, 116 128 Z" />
                  <path d="M 83 196 L 75 268 L 68 272 L 66 278 L 86 280 L 91 268 L 99 197 Z" />
                  <path d="M 103 197 L 111 268 L 116 272 L 114 278 L 133 277 L 125 266 L 119 196 Z" />
                </g>
                <text className="fill-black font-serif italic font-bold text-[18px] tracking-wide">
                  <textPath href="#splitWalkBot" startOffset="50%" textAnchor="middle">
                    {activeSplitGraphic.parameters.arc_text_bottom || "walking away"}
                  </textPath>
                </text>
              </svg>
            )}
          </div>
        )}

        {/* 16mm Film Grain Noise & Vignette Overlays (Mixed-Media Compositing) */}
        {isArchivalGraded && (
          <>
            <div className="absolute inset-0 pointer-events-none z-15 mix-blend-overlay opacity-30 overflow-hidden">
              <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
                <filter id="archivalGrain">
                  <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="3" stitchTiles="stitch" />
                  <feColorMatrix type="saturate" values="0" />
                </filter>
                <rect width="100%" height="100%" filter="url(#archivalGrain)" />
              </svg>
            </div>
            <div className="absolute inset-0 pointer-events-none z-15 bg-[radial-gradient(circle_at_center,transparent_55%,rgba(0,0,0,0.8)_100%)]" />
          </>
        )}

        

        {/* Interactive Canvas Overlay (Click & Drag Subtitles, Rounded Backgrounds, Word Highlight) */}
        <CanvasOverlay
          captions={captions}
          graphics={graphics}
          currentTime={currentTime}
          isPlaying={isPlaying}
          settings={project?.settings ?? { aspect_ratio: '9:16', safe_area_guide: false, center_snapping: true, default_brand_preset: 'podcast_lime' }}
          selectedCaptionId={selectedCaptionId}
          onSelectCaption={onSelectCaption}
          onUpdateCaptionPosition={onUpdateCaptionPosition}
          activeLanguageView={activeLanguageView}
        />
      </div>

      {/* Floating Transport Bar under Video */}
      <div className="absolute bottom-6 flex items-center gap-3 bg-white/95 backdrop-blur-md px-4 py-2 rounded-full border border-neutral-300 shadow-xl z-25 text-neutral-900">
        <button
          onClick={() => onTimeUpdate(0)}
          className="p-1.5 rounded-full text-neutral-500 hover:text-neutral-900 hover:bg-neutral-100 transition cursor-pointer"
          title="Return to start"
        >
          <RotateCcw className="h-4 w-4" />
        </button>

        <button
          aria-label={isPlaying ? "Pause" : "Play"}
          onClick={onTogglePlay}
          className="h-8 w-8 rounded-full bg-neutral-900 flex items-center justify-center text-white font-semibold hover:bg-neutral-800 shadow-md transition cursor-pointer"
        >
          {isPlaying ? <Pause className="h-4 w-4 fill-white" /> : <Play className="h-4 w-4 fill-white ml-0.5" />}
        </button>

        {/* Timecode Readout */}
        <div className="text-xs font-mono font-bold text-neutral-900 tracking-wider px-2">
          {formatTime(currentTime)} / {formatTime(project?.duration_seconds || 15.0)}
        </div>

        <div className="h-4 w-px bg-neutral-300 mx-1" />

        <div className="text-[10px] font-mono font-bold text-neutral-500 uppercase">
          {project?.settings?.aspect_ratio ?? "9:16"}
        </div>

        
      </div>
    </div>
  );
};
