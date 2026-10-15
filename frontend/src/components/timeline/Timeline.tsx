import React, { useRef, useState } from "react";
import { 
  Scissors, Plus, ZoomIn, ZoomOut, Volume2, 
  Sparkles, Video as VideoIcon, Type, Trash2, Globe, Film, Music
} from "lucide-react";
import { ProjectState, CaptionItem, MotionGraphicItem, AudioTrackItem } from "../../types";

interface TimelineProps {
  project: ProjectState;
  currentTime: number;
  selectedCaptionId: string | null;
  onTimeUpdate: (time: number) => void;
  onSelectCaption: (id: string) => void;
  onSplitCaption: (captionId: string, splitTime: number) => void;
  onMergeCaptions?: (capId1: string, capId2: string) => void;
  onUpdateCaptionTiming: (id: string, newStart: number, newEnd: number) => void;
  onAddCaption: () => void;
  onDeleteCaption?: (id: string) => void;
  selectedGraphicId?: string | null;
  onSelectGraphic?: (id: string) => void;
  onDeleteGraphic?: (id: string) => void;
  onClearAllGraphics?: () => void;
  onUpdateGraphicTiming?: (id: string, newStart: number, newEnd: number) => void;
  onDeleteAudioTrack?: (id: string) => void;
}

export const Timeline: React.FC<TimelineProps> = ({
  project,
  currentTime,
  selectedCaptionId,
  onTimeUpdate,
  onSelectCaption,
  onSplitCaption,
  onUpdateCaptionTiming,
  onAddCaption,
  onDeleteCaption,
  selectedGraphicId,
  onSelectGraphic,
  onDeleteGraphic,
  onClearAllGraphics,
  onUpdateGraphicTiming,
  onDeleteAudioTrack
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState<number>(60); // pixels per second
  const [isScrubbing, setIsScrubbing] = useState(false);

  // Unified Trimming / Dragging state for captions and graphics
  const [activeTrim, setActiveTrim] = useState<{
    id: string;
    targetType: "caption" | "graphic";
    type: "start" | "end" | "move";
    initialX: number;
    initialStart: number;
    initialEnd: number;
  } | null>(null);

  const duration = Math.max(15, project.duration_seconds || 15);
  const totalWidth = duration * zoom;

  // Timeline Click / Scrub
  const handleTimelineMouseDown = (e: React.MouseEvent) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left + containerRef.current.scrollLeft;
    const time = Math.max(0, Math.min(duration, clickX / zoom));
    onTimeUpdate(round2(time));
    setIsScrubbing(true);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isScrubbing && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const clickX = e.clientX - rect.left + containerRef.current.scrollLeft;
      const time = Math.max(0, Math.min(duration, clickX / zoom));
      onTimeUpdate(round2(time));
    } else if (activeTrim) {
      const deltaX = e.clientX - activeTrim.initialX;
      const deltaTime = deltaX / zoom;

      if (activeTrim.targetType === "caption") {
        if (activeTrim.type === "start") {
          const newStart = Math.max(0, Math.min(activeTrim.initialEnd - 0.2, activeTrim.initialStart + deltaTime));
          onUpdateCaptionTiming(activeTrim.id, round2(newStart), activeTrim.initialEnd);
        } else if (activeTrim.type === "end") {
          const newEnd = Math.max(activeTrim.initialStart + 0.2, Math.min(duration, activeTrim.initialEnd + deltaTime));
          onUpdateCaptionTiming(activeTrim.id, activeTrim.initialStart, round2(newEnd));
        } else if (activeTrim.type === "move") {
          const capDur = activeTrim.initialEnd - activeTrim.initialStart;
          const newStart = Math.max(0, Math.min(duration - capDur, activeTrim.initialStart + deltaTime));
          onUpdateCaptionTiming(activeTrim.id, round2(newStart), round2(newStart + capDur));
        }
      } else if (activeTrim.targetType === "graphic" && onUpdateGraphicTiming) {
        if (activeTrim.type === "start") {
          const newStart = Math.max(0, Math.min(activeTrim.initialEnd - 0.2, activeTrim.initialStart + deltaTime));
          onUpdateGraphicTiming(activeTrim.id, round2(newStart), activeTrim.initialEnd);
        } else if (activeTrim.type === "end") {
          const newEnd = Math.max(activeTrim.initialStart + 0.2, Math.min(duration, activeTrim.initialEnd + deltaTime));
          onUpdateGraphicTiming(activeTrim.id, activeTrim.initialStart, round2(newEnd));
        } else if (activeTrim.type === "move") {
          const gDur = activeTrim.initialEnd - activeTrim.initialStart;
          const newStart = Math.max(0, Math.min(duration - gDur, activeTrim.initialStart + deltaTime));
          onUpdateGraphicTiming(activeTrim.id, round2(newStart), round2(newStart + gDur));
        }
      }
    }
  };

  const handleMouseUp = () => {
    setIsScrubbing(false);
    setActiveTrim(null);
  };

  const round2 = (n: number) => Math.round(n * 100) / 100;

  // Find caption at playhead for blade/split
  const captionAtPlayhead = project.captions.find(
    (c) => currentTime > c.start + 0.05 && currentTime < c.end - 0.05
  );

  // Multi-Track Item Filters
  const v5Graphics = project.graphics.filter(
    (g) =>
      g.track === "V5" ||
      g.template_id === "hook_typography" ||
      g.template_id === "kinetic_typography" ||
      g.template_id === "kinetic_3d_block" ||
      g.template_id === "stat_counter"
  );

  const v4Graphics = project.graphics.filter(
    (g) =>
      (g.track === "V4" ||
        g.template_id === "digital_highlighter" ||
        g.template_id === "source_citation" ||
        g.template_id?.includes("article") ||
        g.template_id?.includes("youtube") ||
        g.template_id?.includes("citation")) &&
      !v5Graphics.some((vg) => vg.id === g.id)
  );

  const v3Graphics = project.graphics.filter(
    (g) =>
      !v5Graphics.some((vg) => vg.id === g.id) &&
      !v4Graphics.some((vg) => vg.id === g.id)
  );

  const insertCutaways = project.graphics.filter((g) => g.placement_mode === "insert");
  const sfx=project.graphics.find(g=>g.parameters.sfx_track_url);
  const audioTracks = [...(project.audio_tracks || []),...(sfx?[{id:'automatic-sfx',start:0,duration:project.duration_seconds,title:sfx.parameters.sfx_muted?'Automatic SFX (muted)':'Automatic SFX'}]:[])];

  const renderGraphicClip = (
    g: MotionGraphicItem,
    colorClasses: { active: string; idle: string; iconColor: string }
  ) => {
    const isSelected = g.id === selectedGraphicId;
    const left = g.start * zoom;
    const width = Math.max(24, (g.end - g.start) * zoom);
    const isInsert = g.placement_mode === "insert";

    return (
      <div
        key={g.id}
        onClick={(e) => {
          e.stopPropagation();
          onSelectGraphic?.(g.id);
        }}
        onMouseDown={(e) => {
          e.stopPropagation();
          onSelectGraphic?.(g.id);
          setActiveTrim({
            id: g.id,
            targetType: "graphic",
            type: "move",
            initialX: e.clientX,
            initialStart: g.start,
            initialEnd: g.end
          });
        }}
        style={{ left: `${left}px`, width: `${width}px` }}
        className={`group absolute top-1 bottom-1 rounded border px-2 flex items-center justify-between text-xs font-medium truncate shadow-sm cursor-grab transition-all select-none ${
          isSelected ? colorClasses.active : colorClasses.idle
        }`}
      >
        {/* Left Trim Handle */}
        <div
          onMouseDown={(e) => {
            e.stopPropagation();
            setActiveTrim({
              id: g.id,
              targetType: "graphic",
              type: "start",
              initialX: e.clientX,
              initialStart: g.start,
              initialEnd: g.end
            });
          }}
          className="absolute left-0 top-0 bottom-0 w-2 hover:bg-black/10 cursor-ew-resize rounded-l"
        />

        {/* Clip Content & Mode Badge */}
        <div className="flex items-center gap-1.5 min-w-0 truncate">
          <span className={colorClasses.iconColor}>
            {g.track === "V5" ? <Sparkles className="h-3 w-3" /> : g.track === "V4" ? <Globe className="h-3 w-3" /> : <Film className="h-3 w-3" />}
          </span>
          <span className="truncate text-[11px] font-medium">{g.title}</span>
          {isInsert ? (
            <span className="text-[8px] bg-amber-500 text-white px-1 rounded font-mono uppercase font-bold shrink-0">
              Cutaway
            </span>
          ) : (
            <span className="text-[8px] bg-neutral-200 text-neutral-700 px-1 rounded font-mono uppercase shrink-0">
              Overlay
            </span>
          )}
        </div>

        {/* Delete Handle */}
        {onDeleteGraphic && (
          <button
            onMouseDown={(e) => e.stopPropagation()}
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation();
              onDeleteGraphic(g.id);
            }}
            title="Delete clip"
            className="opacity-40 group-hover:opacity-100 hover:bg-neutral-300 p-0.5 rounded transition ml-1 shrink-0 text-neutral-700 cursor-pointer"
          >
            <Trash2 className="w-2.5 h-2.5" />
          </button>
        )}

        {/* Right Trim Handle */}
        <div
          onMouseDown={(e) => {
            e.stopPropagation();
            setActiveTrim({
              id: g.id,
              targetType: "graphic",
              type: "end",
              initialX: e.clientX,
              initialStart: g.start,
              initialEnd: g.end
            });
          }}
          className="absolute right-0 top-0 bottom-0 w-2 hover:bg-black/10 cursor-ew-resize rounded-r"
        />
      </div>
    );
  };

  return (
    <div 
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      className="h-[310px] bg-white border-t border-neutral-200 flex flex-col select-none relative z-10"
    >
      {/* Timeline Controls & Quick Tools */}
      <div className="h-8 bg-neutral-50 border-b border-neutral-200 px-3 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          {/* Blade / Split Tool */}
          <button
            onClick={() => captionAtPlayhead && onSplitCaption(captionAtPlayhead.id, currentTime)}
            disabled={!captionAtPlayhead}
            className="flex items-center gap-1 px-2 py-0.5 rounded bg-white hover:bg-neutral-100 border border-neutral-200 text-neutral-800 disabled:opacity-30 transition shadow-xs"
            title="Split caption at playhead"
          >
            <Scissors className="h-3 w-3 text-neutral-700" />
            <span className="text-[11px] font-medium">Split</span>
          </button>

          {/* Add Caption */}
          <button
            onClick={onAddCaption}
            className="flex items-center gap-1 px-2 py-0.5 rounded bg-white hover:bg-neutral-100 border border-neutral-200 text-neutral-800 transition shadow-xs"
            title="Add new caption block at playhead"
          >
            <Plus className="h-3 w-3 text-neutral-700" />
            <span className="text-[11px] font-medium">Add Caption</span>
          </button>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center gap-2 text-neutral-500">
          <ZoomOut className="h-3 w-3" />
          <input
            type="range"
            min={25}
            max={180}
            value={zoom}
            onChange={(e) => setZoom(Number(e.target.value))}
            className="w-20 h-1.5 accent-neutral-800 bg-neutral-200 rounded cursor-pointer"
          />
          <ZoomIn className="h-3 w-3" />
          <span className="text-[10px] font-mono w-10 text-right">{zoom}px/s</span>
        </div>
      </div>

      {/* Main Multi-Track Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Track Headers */}
        <div className="w-36 bg-neutral-50 border-r border-neutral-200 flex flex-col text-[10px] font-medium text-neutral-600 z-10 select-none shrink-0">
          {/* Header spacer */}
          <div className="h-6 border-b border-neutral-200 px-2 flex items-center text-[9px] uppercase tracking-wider text-neutral-400 font-semibold">
            Tracks
          </div>

          {/* Track V5 */}
          <div className="h-8 border-b border-neutral-200 px-2 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-amber-700">
              <Sparkles className="h-3 w-3 text-amber-600" />
              <span>V5: Hook / Title</span>
            </div>
            <span className="text-[8px] px-1 bg-neutral-200/80 rounded font-mono text-neutral-600">
              {v5Graphics.length}
            </span>
          </div>

          {/* Track V4 */}
          <div className="h-8 border-b border-neutral-200 px-2 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-cyan-700">
              <Globe className="h-3 w-3 text-cyan-600" />
              <span>V4: Article/Web</span>
            </div>
            <span className="text-[8px] px-1 bg-neutral-200/80 rounded font-mono text-neutral-600">
              {v4Graphics.length}
            </span>
          </div>

          {/* Track V3 */}
          <div className="h-8 border-b border-neutral-200 px-2 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-violet-700">
              <Film className="h-3 w-3 text-violet-600" />
              <span>V3: B-Roll/Cut</span>
            </div>
            <div className="flex items-center gap-1">
              {project.graphics.length > 0 && onClearAllGraphics && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm("Clear all graphics layers?")) onClearAllGraphics();
                  }}
                  title="Clear all graphics"
                  className="px-1 text-[8px] bg-red-100 hover:bg-red-200 border border-red-200 text-red-700 rounded"
                >
                  Clear
                </button>
              )}
              <span className="text-[8px] px-1 bg-neutral-200/80 rounded font-mono text-neutral-600">
                {v3Graphics.length}
              </span>
            </div>
          </div>

          {/* Track V2 */}
          <div className="h-9 border-b border-neutral-200 px-2 flex items-center justify-between bg-neutral-100/60">
            <div className="flex items-center gap-1.5 text-neutral-900 font-semibold">
              <Type className="h-3 w-3 text-neutral-800" />
              <span>V2: Subtitles</span>
            </div>
            <span className="text-[8px] px-1 bg-neutral-200 rounded font-mono text-neutral-700">
              {project.captions.length}
            </span>
          </div>

          {/* Track V1 */}
          <div className="h-8 border-b border-neutral-200 px-2 flex items-center gap-1.5 text-slate-700">
            <VideoIcon className="h-3 w-3 text-slate-600" />
            <span>V1: Video</span>
          </div>

          {/* Track A1 */}
          <div className="h-7 border-b border-neutral-200 px-2 flex items-center gap-1.5 text-emerald-700">
            <Volume2 className="h-3 w-3 text-emerald-600" />
            <span>A1: Dialogue</span>
          </div>

          {/* Track A2 */}
          <div className="h-7 px-2 flex items-center gap-1.5 text-indigo-700">
            <Music className="h-3 w-3 text-indigo-600" />
            <span>A2: Music / SFX</span>
          </div>
        </div>

        {/* Interactive Track Canvas */}
        <div
          ref={containerRef}
          onMouseDown={handleTimelineMouseDown}
          className="flex-1 overflow-x-auto overflow-y-hidden relative bg-neutral-50/70 cursor-pointer"
        >
          <div
            style={{ width: `${totalWidth}px` }}
            className="h-full relative select-none"
          >
            {/* Timecode Ruler */}
            <div className="h-6 border-b border-neutral-200 bg-white flex items-end text-[9px] font-mono text-neutral-500 px-1 relative">
              {Array.from({ length: Math.ceil(duration) + 1 }).map((_, sec) => (
                <div
                  key={sec}
                  style={{ left: `${sec * zoom}px` }}
                  className="absolute bottom-0 h-3 border-l border-neutral-300 pl-1"
                >
                  {sec % 2 === 0 && `00:${sec.toString().padStart(2, "0")}`}
                </div>
              ))}
            </div>

            {/* Red Scrubbing Playhead Line */}
            <div
              style={{ left: `${currentTime * zoom}px` }}
              className="absolute top-0 bottom-0 w-0.5 bg-red-600 z-30 pointer-events-none"
            >
              <div className="w-2.5 h-2.5 bg-red-600 rounded-xs -translate-x-[4px] rotate-45 shadow-xs" />
            </div>

            {/* TRACK V5 */}
            <div className="h-8 border-b border-neutral-200/80 relative bg-amber-50/20">
              {v5Graphics.map((g) =>
                renderGraphicClip(g, {
                  active: "bg-amber-600 border-amber-700 text-white z-20 shadow",
                  idle: "bg-amber-100 hover:bg-amber-200 border-amber-300 text-amber-900",
                  iconColor: "text-amber-600"
                })
              )}
            </div>

            {/* TRACK V4 */}
            <div className="h-8 border-b border-neutral-200/80 relative bg-cyan-50/20">
              {v4Graphics.map((g) =>
                renderGraphicClip(g, {
                  active: "bg-cyan-600 border-cyan-700 text-white z-20 shadow",
                  idle: "bg-cyan-100 hover:bg-cyan-200 border-cyan-300 text-cyan-900",
                  iconColor: "text-cyan-600"
                })
              )}
            </div>

            {/* TRACK V3 */}
            <div className="h-8 border-b border-neutral-200/80 relative bg-violet-50/20">
              {v3Graphics.map((g) =>
                renderGraphicClip(g, {
                  active: "bg-violet-600 border-violet-700 text-white z-20 shadow",
                  idle: "bg-violet-100 hover:bg-violet-200 border-violet-300 text-violet-900",
                  iconColor: "text-violet-600"
                })
              )}
            </div>

            {/* TRACK V2: Captions */}
            <div className="h-9 border-b border-neutral-200/80 relative bg-neutral-100/40">
              {project.captions.map((cap) => {
                const isSelected = cap.id === selectedCaptionId;
                const left = cap.start * zoom;
                const width = Math.max(20, (cap.end - cap.start) * zoom);

                return (
                  <div
                    key={cap.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      onSelectCaption(cap.id);
                    }}
                    onMouseDown={(e) => {
                      e.stopPropagation();
                      onSelectCaption(cap.id);
                      setActiveTrim({
                        id: cap.id,
                        targetType: "caption",
                        type: "move",
                        initialX: e.clientX,
                        initialStart: cap.start,
                        initialEnd: cap.end
                      });
                    }}
                    style={{ left: `${left}px`, width: `${width}px` }}
                    className={`group absolute top-1 bottom-1 rounded flex items-center justify-between px-2 text-xs font-medium overflow-hidden transition-all cursor-grab ${
                      isSelected
                        ? "bg-neutral-900 text-white shadow z-20 ring-1 ring-neutral-900"
                        : "bg-white hover:bg-neutral-50 text-neutral-900 border border-neutral-300 shadow-2xs"
                    }`}
                  >
                    <div
                      onMouseDown={(e) => {
                        e.stopPropagation();
                        setActiveTrim({
                          id: cap.id,
                          targetType: "caption",
                          type: "start",
                          initialX: e.clientX,
                          initialStart: cap.start,
                          initialEnd: cap.end
                        });
                      }}
                      className="absolute left-0 top-0 bottom-0 w-2 hover:bg-neutral-300/60 cursor-ew-resize rounded-l"
                    />

                    <span className="truncate pr-1 text-[11px] flex-1">
                      {cap.translated_text || cap.text}
                    </span>

                    {onDeleteCaption && (
                      <button
                        onMouseDown={(e) => e.stopPropagation()}
                        onPointerDown={(e) => e.stopPropagation()}
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteCaption(cap.id);
                        }}
                        className={`p-0.5 rounded transition shrink-0 cursor-pointer ${
                          isSelected
                            ? "hover:bg-neutral-700 text-neutral-300"
                            : "hover:bg-red-50 text-neutral-400 hover:text-red-600 opacity-0 group-hover:opacity-100"
                        }`}
                        title="Delete caption"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}

                    <div
                      onMouseDown={(e) => {
                        e.stopPropagation();
                        setActiveTrim({
                          id: cap.id,
                          targetType: "caption",
                          type: "end",
                          initialX: e.clientX,
                          initialStart: cap.start,
                          initialEnd: cap.end
                        });
                      }}
                      className="absolute right-0 top-0 bottom-0 w-2 hover:bg-neutral-300/60 cursor-ew-resize rounded-r"
                    />
                  </div>
                );
              })}
            </div>

            {/* TRACK V1: Raw Video */}
            <div className="h-8 border-b border-neutral-200/80 relative flex items-center">
              <div
                style={{ width: `${duration * zoom}px` }}
                className="h-6 mx-1 rounded bg-slate-100 border border-slate-300 text-slate-700 px-2 flex items-center gap-2 text-xs font-mono"
              >
                <VideoIcon className="h-3 w-3 text-slate-600 shrink-0" />
                <span className="truncate text-[10px]">
                  {project.source_media_path ? project.source_media_path.split("/").pop() : "Source_Video.mp4"}
                </span>
                <span className="text-[9px] text-slate-500 ml-auto font-mono">
                  {project.fps} FPS
                </span>
              </div>

              {/* Insert Cutaway Overlay Markers */}
              {insertCutaways.map((cut) => {
                const cutLeft = cut.start * zoom;
                const cutWidth = Math.max(16, (cut.end - cut.start) * zoom);
                return (
                  <div
                    key={`cut_${cut.id}`}
                    style={{ left: `${cutLeft}px`, width: `${cutWidth}px` }}
                    className="absolute top-1 bottom-1 bg-amber-500 text-white rounded px-1.5 flex items-center gap-1 text-[9px] font-mono font-bold z-10 shadow overflow-hidden"
                    title={`Cutaway Insert: ${cut.title}`}
                  >
                    <Scissors className="w-2.5 h-2.5 shrink-0" />
                    <span className="truncate">Cutaway: {cut.title}</span>
                  </div>
                );
              })}
            </div>

            {/* TRACK A1: Dialogue Waveform */}
            <div className="h-7 border-b border-neutral-200/80 relative flex items-center px-1">
              <div 
                style={{ width: `${duration * zoom}px` }}
                className="h-5 w-full bg-emerald-50 border border-emerald-200 rounded flex items-center justify-between px-2 overflow-hidden"
              >
                <div className="flex items-center gap-0.5 w-full h-full">
                  {(project.waveform_data && project.waveform_data.length > 0
                    ? project.waveform_data
                    : Array.from({ length: 80 }).map((_, i) => Math.sin(i * 0.3) * 0.4 + 0.5)
                  ).map((amp, idx) => (
                    <div
                      key={idx}
                      style={{ height: `${Math.max(15, amp * 90)}%` }}
                      className="w-1 bg-emerald-400 rounded-full"
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* TRACK A2: Music / SFX */}
            <div className="h-7 relative flex items-center px-1 bg-indigo-50/10">
              {audioTracks.length === 0 ? (
                <div className="text-[9px] text-neutral-400 italic px-2 font-mono">
                  No background music or SFX added
                </div>
              ) : (
                audioTracks.map((trk) => {
                  const trkLeft = trk.start * zoom;
                  const trkWidth = Math.max(20, trk.duration * zoom);
                  return (
                    <div
                      key={trk.id}
                      style={{ left: `${trkLeft}px`, width: `${trkWidth}px` }}
                      className="absolute top-1 bottom-1 bg-indigo-100 border border-indigo-300 text-indigo-900 rounded px-1.5 flex items-center justify-between text-[9px] font-medium shadow-2xs group"
                    >
                      <span className="truncate">{trk.title}</span>
                      {onDeleteAudioTrack && trk.id!=='automatic-sfx' && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteAudioTrack(trk.id);
                          }}
                          className="opacity-0 group-hover:opacity-100 hover:text-red-600 transition ml-1"
                        >
                          <Trash2 className="w-2.5 h-2.5" />
                        </button>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
