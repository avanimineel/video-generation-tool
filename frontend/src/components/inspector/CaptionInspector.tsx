import React, { useState } from "react";
import { 
  Type, Move, Palette, Sparkles, Sliders, Trash2, 
  Copy, Scissors, Layers, CheckSquare, Square, CheckCircle2, RefreshCw
} from "lucide-react";
import { CaptionItem } from "../../types";

interface CaptionInspectorProps {
  caption: CaptionItem | null;
  onUpdateCaption: (updated: CaptionItem) => void;
  onDeleteCaption: (id: string) => void;
  onDuplicateCaption: (id: string) => void;
  syncStylesToAll?: boolean;
  onToggleSyncStylesToAll?: () => void;
  onApplyStyleToAll?: () => void;
  captionsCount?: number;
}

export const CaptionInspector: React.FC<CaptionInspectorProps> = ({
  caption,
  onUpdateCaption,
  onDeleteCaption,
  onDuplicateCaption,
  syncStylesToAll = true,
  onToggleSyncStylesToAll,
  onApplyStyleToAll,
  captionsCount = 151
}) => {
  const [showAppliedNotice, setShowAppliedNotice] = useState(false);

  if (!caption) {
    return (
      <div className="p-6 text-center text-xs font-mono text-neutral-500">
        Select a caption clip on the timeline or video player to edit its text, position, rounded background, and karaoke styling.
      </div>
    );
  }

  const style = caption.style;

  const updateStyle = (key: string, value: any) => {
    onUpdateCaption({
      ...caption,
      style: {
        ...caption.style,
        [key]: value
      }
    });
  };

  const applyPreset = (presetName: 'documentary' | 'podcast' | 'medical') => {
    let newStyle = { ...caption.style };
    if (presetName === 'documentary') {
      newStyle = {
        ...newStyle,
        font_family: "Inter",
        font_weight: "medium",
        font_size: Math.min(newStyle.font_size, 26),
        text_color: "#FFFFFF",
        has_background: false,
        background_opacity: 0,
        has_shadow: true,
        shadow_blur: 4,
        shadow_color: "rgba(0,0,0,0.9)",
        text_align: "center",
        has_highlight: true,
        highlight_active_color: "#00F0FF",
        keyword_contrast_badge: false
      };
    } else if (presetName === 'podcast') {
      newStyle = {
        ...newStyle,
        font_family: "Montserrat",
        font_weight: "bold",
        font_size: 40,
        text_color: "#FFFFFF",
        has_background: true,
        background_color: "#000000",
        background_opacity: 0.8,
        corner_radius: 16,
        has_highlight: true,
        highlight_active_color: "#CCFF00",
        keyword_contrast_badge: true
      };
    } else if (presetName === 'medical') {
      newStyle = {
        ...newStyle,
        font_family: "Montserrat",
        font_weight: "bold",
        font_size: 38,
        text_color: "#FFFFFF",
        has_background: true,
        background_color: "#0B192C",
        background_opacity: 0.85,
        corner_radius: 14,
        has_highlight: true,
        highlight_active_color: "#00F0FF",
        keyword_contrast_badge: true
      };
    }
    onUpdateCaption({
      ...caption,
      style: newStyle
    });
    if (onApplyStyleToAll && syncStylesToAll) {
      setTimeout(() => onApplyStyleToAll(), 50);
    }
  };

  const handleApplyToAllClick = () => {
    if (onApplyStyleToAll) {
      onApplyStyleToAll();
      setShowAppliedNotice(true);
      setTimeout(() => setShowAppliedNotice(false), 2200);
    }
  };

  return (
    <div className="p-4 space-y-4 text-xs text-neutral-200 select-none overflow-y-auto max-h-full">
      {/* 1. Header & Actions */}
      <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
        <div className="font-bold text-sm text-white flex items-center gap-1.5">
          <Type className="h-4 w-4 text-lime" />
          <span>Caption Inspector</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => onDuplicateCaption(caption.id)}
            className="p-1 rounded hover:bg-neutral-800 text-neutral-400 hover:text-white"
            title="Duplicate caption"
          >
            <Copy className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => onDeleteCaption(caption.id)}
            className="p-1 rounded hover:bg-red-950/60 text-neutral-400 hover:text-red-400"
            title="Delete caption"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* 2. Global Sync Banner & Apply to All Button */}
      <div className="bg-neutral-900/90 border border-neutral-800 rounded-xl p-3 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Sparkles className="h-4 w-4 text-lime shrink-0" />
            <div>
              <div className="text-xs font-bold text-white">Auto-Sync Style & Position</div>
              <div className="text-[10px] text-neutral-400">Apply edits to all {captionsCount} subtitles</div>
            </div>
          </div>
          {onToggleSyncStylesToAll && (
            <button
              onClick={onToggleSyncStylesToAll}
              className={`px-2.5 py-1 rounded text-[10px] font-mono font-black transition ${
                syncStylesToAll
                  ? "bg-lime text-black shadow-[0_0_12px_rgba(180,240,0,0.3)]"
                  : "bg-neutral-800 text-neutral-400 hover:text-white"
              }`}
            >
              {syncStylesToAll ? "SYNC ON" : "SYNC OFF"}
            </button>
          )}
        </div>

        {onApplyStyleToAll && (
          <button
            onClick={handleApplyToAllClick}
            className={`w-full py-2 px-3 rounded-lg font-mono font-bold text-xs flex items-center justify-center gap-1.5 border transition active:scale-98 shadow ${
              showAppliedNotice
                ? "bg-lime text-black border-lime font-black"
                : "bg-neutral-800 hover:bg-neutral-700 text-lime border-neutral-700 hover:border-lime"
            }`}
          >
            {showAppliedNotice ? (
              <>
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Applied to all {captionsCount} captions!</span>
              </>
            ) : (
              <>
                <Layers className="h-3.5 w-3.5" />
                <span>Apply Style & Position to All Captions</span>
              </>
            )}
          </button>
        )}
      </div>

      {/* 2B. 1-Click Aesthetic Presets */}
      <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 space-y-2">
        <div className="flex items-center justify-between">
          <span className="font-bold text-xs text-white flex items-center gap-1.5">
            <Palette className="h-3.5 w-3.5 text-lime" />
            <span>Aesthetic Preset</span>
          </span>
          <span className="text-[9px] font-mono text-neutral-400">1-CLICK STYLING</span>
        </div>
        <div className="grid grid-cols-3 gap-1.5">
          <button
            onClick={() => applyPreset('documentary')}
            className={`p-2 rounded-lg text-left border transition flex flex-col justify-between ${
              !style.has_background
                ? "bg-cyan-950/40 border-cyan-400 text-white"
                : "bg-neutral-800/80 border-neutral-700 text-neutral-300 hover:border-neutral-500"
            }`}
          >
            <span className="text-[10px] font-bold text-cyan-400">📜 Minimalist</span>
            <span className="text-[8px] text-neutral-400 font-mono mt-1">Doc Clean (No Box)</span>
          </button>

          <button
            onClick={() => applyPreset('podcast')}
            className={`p-2 rounded-lg text-left border transition flex flex-col justify-between ${
              style.has_background && style.highlight_active_color === '#CCFF00'
                ? "bg-lime/10 border-lime text-white"
                : "bg-neutral-800/80 border-neutral-700 text-neutral-300 hover:border-neutral-500"
            }`}
          >
            <span className="text-[10px] font-bold text-lime">⚡ Lime Pop</span>
            <span className="text-[8px] text-neutral-400 font-mono mt-1">Podcast Reel</span>
          </button>

          <button
            onClick={() => applyPreset('medical')}
            className={`p-2 rounded-lg text-left border transition flex flex-col justify-between ${
              style.has_background && style.background_color === '#0B192C'
                ? "bg-blue-950/40 border-blue-400 text-white"
                : "bg-neutral-800/80 border-neutral-700 text-neutral-300 hover:border-neutral-500"
            }`}
          >
            <span className="text-[10px] font-bold text-blue-400">🩺 Evidence</span>
            <span className="text-[8px] text-neutral-400 font-mono mt-1">Clinical Blue</span>
          </button>
        </div>
      </div>

      {/* 3. Subtitle Lines Control (1 Line vs 2 Lines) */}
      <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 space-y-2">
        <div className="flex items-center justify-between">
          <span className="font-bold text-xs text-white flex items-center gap-1.5">
            <Sliders className="h-3.5 w-3.5 text-lime" />
            <span>Subtitle Lines</span>
          </span>
          <span className="text-[10px] font-mono text-lime font-bold">
            {(style.max_lines ?? 1) === 1 ? "1 Line" : (style.max_lines === 2 ? "2 Lines" : "Auto")}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => updateStyle("max_lines", 1)}
            className={`py-2 px-2 rounded-lg font-mono font-bold text-xs border transition ${
              (style.max_lines ?? 1) === 1
                ? "bg-lime text-black border-lime font-black shadow"
                : "bg-neutral-800 text-neutral-400 border-neutral-700 hover:text-white"
            }`}
          >
            1 Line (Punchy)
          </button>
          <button
            onClick={() => updateStyle("max_lines", 2)}
            className={`py-2 px-2 rounded-lg font-mono font-bold text-xs border transition ${
              style.max_lines === 2
                ? "bg-lime text-black border-lime font-black shadow"
                : "bg-neutral-800 text-neutral-400 border-neutral-700 hover:text-white"
            }`}
          >
            2 Lines (Dual)
          </button>
        </div>
        <div className="text-[10px] text-neutral-400">
          {(style.max_lines ?? 1) === 1
            ? "• 1 Line: Clean single horizontal row (Reels/Shorts pacing)"
            : "• 2 Lines: Balanced dual-row split (or manual line-break via Enter)"}
        </div>
      </div>

      {/* 4. Text Input Area */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-[11px] font-mono text-neutral-400 uppercase">
            Spoken Dialogue Text
          </label>
          <span className="text-[10px] font-mono text-neutral-500">Press Enter for 2nd line</span>
        </div>
        <textarea
          value={caption.translated_text || caption.text}
          onChange={(e) => {
            const newText = e.target.value;
            const wordsList = newText.trim().split(/\s+/).filter(Boolean);
            const existingWordsMap = new Map((caption.words || []).map(w => [w.word.toLowerCase(), w]));
            const words = wordsList.map((w, idx) => {
              const matched = existingWordsMap.get(w.toLowerCase());
              return {
                word: w,
                start: Number((caption.start + idx * ((caption.end - caption.start) / Math.max(1, wordsList.length))).toFixed(2)),
                end: Number((caption.start + (idx + 1) * ((caption.end - caption.start) / Math.max(1, wordsList.length))).toFixed(2)),
                is_keyword: matched?.is_keyword,
                keyword_category: matched?.keyword_category,
                keyword_color: matched?.keyword_color,
                keyword_font: matched?.keyword_font
              };
            });
            onUpdateCaption({
              ...caption,
              text: newText,
              translated_text: newText,
              words
            });
          }}
          rows={2}
          className="w-full bg-neutral-900 border border-neutral-700 rounded-lg p-2.5 text-xs text-white outline-none focus:border-lime resize-none"
        />

        {/* Interactive Word Chips: Click any word to toggle Keyword Emphasis */}
        {caption.words && caption.words.length > 0 && (
          <div className="mt-2 p-2 bg-neutral-950/70 rounded-lg border border-neutral-800">
            <div className="flex items-center justify-between text-[10px] font-mono text-neutral-400 mb-1.5">
              <span>CLICK WORD TO TOGGLE EMPHASIS</span>
              <span className="text-lime text-[9px]">⚡ High-Impact Keyword</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {caption.words.map((w, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => {
                    const newWords = [...caption.words];
                    const cur = !!newWords[idx].is_keyword;
                    newWords[idx] = {
                      ...newWords[idx],
                      is_keyword: !cur,
                      keyword_category: !cur ? 'impact' : undefined,
                      keyword_color: !cur ? (style.keyword_accent_color || '#CCFF00') : undefined,
                      keyword_font: !cur ? (style.keyword_font_family || 'Playfair Display') : undefined
                    };
                    onUpdateCaption({
                      ...caption,
                      words: newWords
                    });
                  }}
                  className={`px-2 py-0.5 rounded text-[11px] font-bold transition flex items-center gap-1 ${
                    w.is_keyword
                      ? "bg-lime text-black border border-lime shadow-[0_0_8px_rgba(180,240,0,0.4)]"
                      : "bg-neutral-800 hover:bg-neutral-700 text-neutral-300 border border-neutral-700"
                  }`}
                >
                  {w.is_keyword && <span className="text-[9px]">⚡</span>}
                  <span>{w.word}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 5. Dynamic Text Pacing & Cadence (Viewer Retention) */}
      <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 space-y-2">
        <div className="flex items-center justify-between">
          <span className="font-bold text-xs text-white flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-lime" />
            <span>Pacing & Synchronization</span>
          </span>
          <span className="text-[10px] font-mono text-lime font-bold uppercase">
            {(style.pacing_mode || "full_line").replace("_", " ")}
          </span>
        </div>

        <div className="grid grid-cols-3 gap-1.5">
          <button
            onClick={() => updateStyle("pacing_mode", "full_line")}
            className={`py-1.5 px-1 rounded-lg text-[10px] font-mono font-bold border transition text-center ${
              (style.pacing_mode || "full_line") === "full_line"
                ? "bg-lime text-black border-lime font-black shadow"
                : "bg-neutral-800 text-neutral-400 border-neutral-700 hover:text-white"
            }`}
          >
            Full Line
          </button>
          <button
            onClick={() => updateStyle("pacing_mode", "word_reveal")}
            className={`py-1.5 px-1 rounded-lg text-[10px] font-mono font-bold border transition text-center ${
              style.pacing_mode === "word_reveal"
                ? "bg-lime text-black border-lime font-black shadow"
                : "bg-neutral-800 text-neutral-400 border-neutral-700 hover:text-white"
            }`}
          >
            Word Reveal
          </button>
          <button
            onClick={() => updateStyle("pacing_mode", "phrase_chunk")}
            className={`py-1.5 px-1 rounded-lg text-[10px] font-mono font-bold border transition text-center ${
              style.pacing_mode === "phrase_chunk"
                ? "bg-lime text-black border-lime font-black shadow"
                : "bg-neutral-800 text-neutral-400 border-neutral-700 hover:text-white"
            }`}
          >
            Phrase (2-4W)
          </button>
        </div>
        <div className="text-[10px] text-neutral-400">
          {(style.pacing_mode || "full_line") === "full_line" && "• Full Line: Shows whole phrase with active karaoke tracking"}
          {style.pacing_mode === "word_reveal" && "• Word Reveal: Words appear one-by-one with speaker cadence (TikTok/Shorts style)"}
          {style.pacing_mode === "phrase_chunk" && "• Phrase Chunk: Rhythmic 2-4 word phrases synchronized to natural speech pacing"}
        </div>
      </div>

      {/* 6. Algorithmic Keyword Emphasis */}
      <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="font-bold text-xs text-white flex items-center gap-1.5">
            <span className="text-lime font-black">⚡</span>
            <span>Keyword Emphasis</span>
          </div>
          <button
            onClick={() => updateStyle("has_keyword_emphasis", style.has_keyword_emphasis === false ? true : false)}
            className={`text-xs px-2.5 py-0.5 rounded font-mono font-bold transition ${
              style.has_keyword_emphasis !== false
                ? "bg-lime text-black shadow"
                : "bg-neutral-800 text-neutral-400 border border-neutral-700 hover:text-white"
            }`}
          >
            {style.has_keyword_emphasis !== false ? "EMPHASIS ON" : "OFF"}
          </button>
        </div>

        {style.has_keyword_emphasis !== false && (
          <div className="space-y-2.5 pt-1">
            {/* Accent Color Selection */}
            <div>
              <div className="flex justify-between text-[10px] font-mono text-neutral-400 mb-1">
                <span>KEYWORD ACCENT COLOR</span>
                <span className="font-mono text-lime uppercase">{style.keyword_accent_color || "#CCFF00"}</span>
              </div>
              <div className="flex items-center gap-2">
                {[
                  { name: "Lime", color: "#CCFF00" },
                  { name: "Coral", color: "#FF4D4D" },
                  { name: "Cyan", color: "#00F0FF" },
                  { name: "Gold", color: "#FFB800" }
                ].map((c) => (
                  <button
                    key={c.color}
                    onClick={() => updateStyle("keyword_accent_color", c.color)}
                    style={{ backgroundColor: c.color }}
                    className={`h-6 flex-1 rounded border transition ${
                      (style.keyword_accent_color || "#CCFF00") === c.color
                        ? "border-white ring-2 ring-white scale-105"
                        : "border-transparent opacity-80 hover:opacity-100"
                    }`}
                  />
                ))}
              </div>
            </div>

            {/* Stylistic Font Shift */}
            <div>
              <span className="text-[10px] font-mono text-neutral-400 block mb-1">STYLISTIC FONT SHIFT</span>
              <select
                value={style.keyword_font_family || "Playfair Display"}
                onChange={(e) => updateStyle("keyword_font_family", e.target.value)}
                className="w-full bg-neutral-800 border border-neutral-700 rounded-lg p-1.5 text-xs text-white outline-none"
              >
                <option value="Playfair Display">Playfair Display (Editorial Serif Italic)</option>
                <option value="Caveat">Caveat (Handwritten / Organic)</option>
                <option value="Montserrat">Montserrat (Heavy Sans-Serif)</option>
                <option value="Inter">Inter (Ultra Clean)</option>
              </select>
            </div>

            {/* Contrast Badge Toggle */}
            <div className="flex items-center justify-between pt-1 border-t border-neutral-800">
              <div>
                <span className="text-xs font-bold text-white block">Contrast Badge</span>
                <span className="text-[10px] text-neutral-400">Solid pill behind emphasized keyword</span>
              </div>
              <button
                onClick={() => updateStyle("keyword_contrast_badge", style.keyword_contrast_badge === false ? true : false)}
                className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${
                  style.keyword_contrast_badge !== false ? "bg-lime text-black" : "bg-neutral-800 text-neutral-400"
                }`}
              >
                {style.keyword_contrast_badge !== false ? "ENABLED" : "OFF"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 5. Timing & Position Controls (Sliders + Drag) */}
      <div className="bg-neutral-900/60 p-3 rounded-xl border border-neutral-800 space-y-2.5">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className="text-[10px] font-mono text-neutral-400 block">START TIME</span>
            <span className="font-mono font-bold text-white text-xs">{caption.start.toFixed(2)}s</span>
          </div>
          <div>
            <span className="text-[10px] font-mono text-neutral-400 block">END TIME</span>
            <span className="font-mono font-bold text-white text-xs">{caption.end.toFixed(2)}s</span>
          </div>
        </div>

        {/* Vertical Position Slider */}
        <div className="pt-1">
          <div className="flex justify-between text-[10px] font-mono text-neutral-400 mb-1">
            <span>VERTICAL POSITION (Y)</span>
            <span className="text-lime font-bold">{caption.pos_y}</span>
          </div>
          <input
            type="range"
            min={0.1}
            max={0.95}
            step={0.01}
            value={caption.pos_y}
            onChange={(e) => {
              onUpdateCaption({
                ...caption,
                pos_y: Number(e.target.value)
              });
            }}
            className="w-full h-1.5 accent-lime bg-neutral-700 rounded-lg cursor-pointer"
          />
        </div>

        {/* Horizontal Position Slider */}
        <div>
          <div className="flex justify-between text-[10px] font-mono text-neutral-400 mb-1">
            <span>HORIZONTAL POSITION (X)</span>
            <span className="text-lime font-bold">{caption.pos_x}</span>
          </div>
          <input
            type="range"
            min={0.1}
            max={0.9}
            step={0.01}
            value={caption.pos_x}
            onChange={(e) => {
              onUpdateCaption({
                ...caption,
                pos_x: Number(e.target.value)
              });
            }}
            className="w-full h-1.5 accent-lime bg-neutral-700 rounded-lg cursor-pointer"
          />
        </div>

        {/* Full-screen Position Quick Presets */}
        <div className="flex items-center gap-1.5 pt-1">
          <span className="text-[9px] font-mono text-neutral-500">PRESETS:</span>
          <button
            onClick={() => onUpdateCaption({ ...caption, pos_y: 0.82, pos_x: 0.5 })}
            className="flex-1 py-1 rounded bg-neutral-800 hover:bg-neutral-700 text-[9px] font-mono text-neutral-300 hover:text-white border border-neutral-700"
          >
            Bottom (0.82)
          </button>
          <button
            onClick={() => onUpdateCaption({ ...caption, pos_y: 0.50, pos_x: 0.5 })}
            className="flex-1 py-1 rounded bg-neutral-800 hover:bg-neutral-700 text-[9px] font-mono text-neutral-300 hover:text-white border border-neutral-700"
          >
            Center (0.50)
          </button>
          <button
            onClick={() => onUpdateCaption({ ...caption, pos_y: 0.15, pos_x: 0.5 })}
            className="flex-1 py-1 rounded bg-neutral-800 hover:bg-neutral-700 text-[9px] font-mono text-neutral-300 hover:text-white border border-neutral-700"
          >
            Top (0.15)
          </button>
        </div>
      </div>

      {/* 5B. Independent Position During Graphics & Split-Screens */}
      <div className="bg-neutral-900/80 p-3 rounded-xl border border-cyan-900/40 space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Move className="h-3.5 w-3.5 text-cyan-400" />
            <span className="font-bold text-xs text-white">Graphic / Split-Screen Position</span>
          </div>
          <button
            onClick={() => {
              const hasOverride = caption.pos_y_during_graphic !== undefined;
              onUpdateCaption({
                ...caption,
                pos_y_during_graphic: hasOverride ? undefined : 0.90,
                pos_x_during_graphic: hasOverride ? undefined : caption.pos_x
              });
            }}
            className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold border transition ${
              caption.pos_y_during_graphic !== undefined
                ? "bg-cyan-500 text-black border-cyan-400"
                : "bg-neutral-800 text-neutral-400 border-neutral-700 hover:text-white"
            }`}
          >
            {caption.pos_y_during_graphic !== undefined ? "OVERRIDE ON" : "USE DEFAULT"}
          </button>
        </div>

        <p className="text-[10px] text-neutral-400 leading-relaxed">
          Reposition subtitles specifically when B-roll graphics or 50/50 split-screens appear, keeping text off the speaker's face without affecting full-screen scenes.
        </p>

        {caption.pos_y_during_graphic !== undefined ? (
          <div className="space-y-2 pt-1 border-t border-neutral-800">
            <div>
              <div className="flex justify-between text-[10px] font-mono text-neutral-400 mb-1">
                <span>GRAPHIC Y POSITION</span>
                <span className="text-cyan-400 font-bold">{caption.pos_y_during_graphic}</span>
              </div>
              <input
                type="range"
                min={0.1}
                max={0.96}
                step={0.01}
                value={caption.pos_y_during_graphic}
                onChange={(e) => {
                  onUpdateCaption({
                    ...caption,
                    pos_y_during_graphic: Number(e.target.value)
                  });
                }}
                className="w-full h-1.5 accent-cyan-400 bg-neutral-700 rounded-lg cursor-pointer"
              />
            </div>

            {/* Split Screen Quick Presets */}
            <div className="grid grid-cols-3 gap-1 pt-1">
              <button
                onClick={() => onUpdateCaption({ ...caption, pos_y_during_graphic: 0.90 })}
                className="py-1 px-1 rounded bg-neutral-800 hover:bg-neutral-700 text-[9px] font-mono text-cyan-300 border border-neutral-700 truncate text-center"
                title="Sits safely on speaker lower chest in 50/50 vertical split"
              >
                Split Bottom (0.90)
              </button>
              <button
                onClick={() => onUpdateCaption({ ...caption, pos_y_during_graphic: 0.75 })}
                className="py-1 px-1 rounded bg-neutral-800 hover:bg-neutral-700 text-[9px] font-mono text-neutral-300 border border-neutral-700 truncate text-center"
              >
                Split Mid (0.75)
              </button>
              <button
                onClick={() => onUpdateCaption({ ...caption, pos_y_during_graphic: 0.12 })}
                className="py-1 px-1 rounded bg-neutral-800 hover:bg-neutral-700 text-[9px] font-mono text-neutral-300 border border-neutral-700 truncate text-center"
              >
                Top Header (0.12)
              </button>
            </div>
          </div>
        ) : (
          <div className="text-[10px] font-mono text-neutral-500 bg-neutral-950 p-2 rounded border border-neutral-800/80">
            Defaults to <span className="text-cyan-400 font-bold">0.90</span> during 50/50 split (speaker bottom third) and <span className="text-lime font-bold">{caption.pos_y}</span> in full-screen.
          </div>
        )}
      </div>

      {/* 4. Rounded Subtitle Background Box (Mandatory Requirement) */}
      <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 space-y-3">
        <div className="flex items-center justify-between">
          <span className="font-bold text-xs text-white flex items-center gap-1.5">
            <Layers className="h-3.5 w-3.5 text-lime" />
            Rounded Background Box
          </span>
          <button
            onClick={() => updateStyle("has_background", !style.has_background)}
            className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${
              style.has_background ? "bg-lime text-black" : "bg-neutral-800 text-neutral-400"
            }`}
          >
            {style.has_background ? "ENABLED" : "OFF"}
          </button>
        </div>

        {style.has_background && (
          <div className="space-y-2.5 pt-1">
            {/* Shape Mode: Solid Box, Pill, Per-Word */}
            <div>
              <span className="text-[10px] font-mono text-neutral-400 block mb-1">SHAPE STYLE</span>
              <div className="grid grid-cols-3 gap-1 bg-neutral-800 p-1 rounded-lg border border-neutral-700">
                {(['solid_box', 'pill', 'per_word'] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => updateStyle("contrast_block_mode", mode)}
                    className={`py-1 text-[10px] font-mono font-bold rounded transition ${
                      (style.contrast_block_mode || 'solid_box') === mode
                        ? "bg-lime text-black shadow"
                        : "text-neutral-400 hover:text-white"
                    }`}
                  >
                    {mode === 'solid_box' ? 'Box' : mode === 'pill' ? 'Pill' : 'Per-Word'}
                  </button>
                ))}
              </div>
            </div>

            {/* Corner Radius Slider (0px to 32px or Pill) */}
            <div>
              <div className="flex justify-between text-[11px] font-mono text-neutral-400 mb-1">
                <span>CORNER RADIUS</span>
                <span className="text-lime font-bold">
                  {style.corner_radius >= 32 ? "Full Round (32px)" : `${style.corner_radius}px`}
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={32}
                value={style.corner_radius}
                onChange={(e) => updateStyle("corner_radius", Number(e.target.value))}
                className="w-full h-1.5 accent-lime bg-neutral-700 rounded-lg cursor-pointer"
              />
            </div>

            {/* Background Opacity */}
            <div>
              <div className="flex justify-between text-[11px] font-mono text-neutral-400 mb-1">
                <span>OPACITY</span>
                <span className="text-white font-bold">{Math.round(style.background_opacity * 100)}%</span>
              </div>
              <input
                type="range"
                min={0.1}
                max={1.0}
                step={0.05}
                value={style.background_opacity}
                onChange={(e) => updateStyle("background_opacity", Number(e.target.value))}
                className="w-full h-1.5 accent-lime bg-neutral-700 rounded-lg cursor-pointer"
              />
            </div>

            {/* Background Color & Padding */}
            <div className="grid grid-cols-3 gap-2 pt-1">
              <div>
                <span className="text-[10px] font-mono text-neutral-400 block mb-1">BG COLOR</span>
                <div className="flex items-center gap-1.5 bg-neutral-800 p-1 rounded-lg border border-neutral-700">
                  <input
                    type="color"
                    value={style.background_color}
                    onChange={(e) => updateStyle("background_color", e.target.value)}
                    className="w-5 h-5 rounded cursor-pointer bg-transparent border-0 shrink-0"
                  />
                  <span className="font-mono text-[9px] uppercase text-neutral-300 truncate">{style.background_color}</span>
                </div>
              </div>

              <div>
                <span className="text-[10px] font-mono text-neutral-400 block mb-1">PAD X</span>
                <input
                  type="number"
                  value={style.padding_x}
                  onChange={(e) => updateStyle("padding_x", Number(e.target.value))}
                  className="w-full bg-neutral-800 border border-neutral-700 rounded-lg p-1 text-center font-mono text-white text-xs outline-none"
                />
              </div>

              <div>
                <span className="text-[10px] font-mono text-neutral-400 block mb-1">PAD Y</span>
                <input
                  type="number"
                  value={style.padding_y}
                  onChange={(e) => updateStyle("padding_y", Number(e.target.value))}
                  className="w-full bg-neutral-800 border border-neutral-700 rounded-lg p-1 text-center font-mono text-white text-xs outline-none"
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 5. Word Highlighting (Karaoke Animation) */}
      <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 space-y-2.5">
        <div className="flex items-center justify-between">
          <div className="font-bold text-xs text-white flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-lime" />
            <span>Word Highlighting</span>
          </div>
          <button
            onClick={() => updateStyle("has_highlight", style.has_highlight === false ? true : false)}
            className={`text-xs px-2.5 py-0.5 rounded font-mono font-bold transition ${
              style.has_highlight !== false
                ? "bg-lime text-black shadow"
                : "bg-neutral-800 text-neutral-400 border border-neutral-700 hover:text-white"
            }`}
          >
            {style.has_highlight !== false ? "ON" : "OFF"}
          </button>
        </div>

        {style.has_highlight !== false ? (
          <>
            <div className="grid grid-cols-2 gap-2 pt-1">
              <div>
                <span className="text-[10px] font-mono text-neutral-400 block mb-1">ACTIVE WORD COLOR</span>
                <div className="flex items-center gap-1.5 bg-neutral-800 p-1.5 rounded-lg border border-neutral-700">
                  <input
                    type="color"
                    value={style.highlight_active_color}
                    onChange={(e) => updateStyle("highlight_active_color", e.target.value)}
                    className="w-5 h-5 rounded cursor-pointer bg-transparent border-0"
                  />
                  <span className="font-mono text-[11px] uppercase text-neutral-300">{style.highlight_active_color}</span>
                </div>
              </div>

              <div>
                <span className="text-[10px] font-mono text-neutral-400 block mb-1">PAST WORD COLOR</span>
                <div className="flex items-center gap-1.5 bg-neutral-800 p-1.5 rounded-lg border border-neutral-700">
                  <input
                    type="color"
                    value={style.highlight_past_color}
                    onChange={(e) => updateStyle("highlight_past_color", e.target.value)}
                    className="w-5 h-5 rounded cursor-pointer bg-transparent border-0"
                  />
                  <span className="font-mono text-[11px] uppercase text-neutral-300">{style.highlight_past_color}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-1">
              <span className="text-xs text-neutral-300">Bounce on Speak</span>
              <button
                onClick={() => updateStyle("highlight_bounce", !style.highlight_bounce)}
                className={`text-xs px-2 py-0.5 rounded font-mono font-bold ${
                  style.highlight_bounce ? "bg-lime text-black" : "bg-neutral-800 text-neutral-400"
                }`}
              >
                {style.highlight_bounce ? "ON" : "OFF"}
              </button>
            </div>
          </>
        ) : (
          <div className="text-[10px] text-neutral-400 italic">
            Highlighting is OFF. Words display uniformly with no active karaoke color change.
          </div>
        )}
      </div>

      {/* 6. Typography & Font Size (with deep size reduction) */}
      <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 space-y-2.5">
        <div className="font-bold text-xs text-white">Typography & Fonts</div>
        
        {/* Font Family Dropdown */}
        <div>
          <span className="text-[10px] font-mono text-neutral-400 block mb-1">FONT FAMILY</span>
          <select
            value={style.font_family}
            onChange={(e) => updateStyle("font_family", e.target.value)}
            className="w-full bg-neutral-800 border border-neutral-700 rounded-lg p-1.5 text-xs text-white outline-none"
          >
            <option value="Montserrat">Montserrat (Modern Sans)</option>
            <option value="Playfair Display">Playfair Display (Editorial Serif)</option>
            <option value="Inter">Inter (Clean Tech)</option>
            <option value="Caveat">Caveat (Handwritten / Doodle)</option>
          </select>
        </div>

        {/* Font Size Slider with pixel input and deep min (10px to 72px) */}
        <div>
          <div className="flex items-center justify-between text-[10px] font-mono text-neutral-400 mb-1">
            <span>FONT SIZE</span>
            <div className="flex items-center gap-1">
              <input
                type="number"
                min={8}
                max={96}
                value={style.font_size}
                onChange={(e) => updateStyle("font_size", Math.max(8, Number(e.target.value)))}
                className="w-14 bg-neutral-800 border border-neutral-700 rounded px-1.5 py-0.5 text-center font-mono font-bold text-lime text-xs outline-none"
              />
              <span className="text-neutral-400">px</span>
            </div>
          </div>

          <input
            type="range"
            min={10}
            max={72}
            value={style.font_size}
            onChange={(e) => updateStyle("font_size", Number(e.target.value))}
            className="w-full h-1.5 accent-lime bg-neutral-700 rounded-lg cursor-pointer"
          />

          {/* Quick preset chips to easily reduce or enlarge */}
          <div className="flex items-center gap-1.5 pt-1.5">
            {[14, 18, 22, 28, 36, 44].map((sz) => (
              <button
                key={sz}
                onClick={() => updateStyle("font_size", sz)}
                className={`flex-1 py-0.5 rounded text-[10px] font-mono font-bold border transition ${
                  style.font_size === sz
                    ? "bg-lime text-black border-lime"
                    : "bg-neutral-800 text-neutral-400 border-neutral-700 hover:text-white"
                }`}
              >
                {sz}
              </button>
            ))}
          </div>
        </div>

        {/* Base Text Color & Uppercase */}
        <div className="grid grid-cols-2 gap-2 pt-1">
          <div>
            <span className="text-[10px] font-mono text-neutral-400 block mb-1">BASE TEXT COLOR</span>
            <div className="flex items-center gap-1.5 bg-neutral-800 p-1.5 rounded-lg border border-neutral-700">
              <input
                type="color"
                value={style.text_color || "#FFFFFF"}
                onChange={(e) => updateStyle("text_color", e.target.value)}
                className="w-5 h-5 rounded cursor-pointer bg-transparent border-0"
              />
              <span className="font-mono text-[11px] uppercase text-neutral-300">{style.text_color || "#FFFFFF"}</span>
            </div>
          </div>

          <div className="flex flex-col justify-end">
            <button
              onClick={() => updateStyle("is_uppercase", !style.is_uppercase)}
              className={`w-full py-2 rounded-lg text-xs font-mono font-bold border transition ${
                style.is_uppercase
                  ? "bg-lime text-black border-lime font-black"
                  : "bg-neutral-800 text-neutral-400 border-neutral-700 hover:text-white"
              }`}
            >
              UPPERCASE
            </button>
          </div>
        </div>
      </div>

      {/* 7. Text Drop Shadow & Outline (ON/OFF Toggle) */}
      <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 space-y-2.5">
        <div className="flex items-center justify-between">
          <span className="font-bold text-xs text-white flex items-center gap-1.5">
            <Layers className="h-3.5 w-3.5 text-lime" />
            <span>Text Drop Shadow</span>
          </span>
          <button
            onClick={() => updateStyle("has_shadow", style.has_shadow === false ? true : false)}
            className={`text-xs px-2.5 py-0.5 rounded font-mono font-bold transition ${
              style.has_shadow !== false
                ? "bg-lime text-black shadow"
                : "bg-neutral-800 text-neutral-400 border border-neutral-700 hover:text-white"
            }`}
          >
            {style.has_shadow !== false ? "SHADOW ON" : "SHADOW OFF"}
          </button>
        </div>

        {style.has_shadow !== false ? (
          <div className="space-y-2 pt-1">
            <div className="flex justify-between text-[10px] font-mono text-neutral-400">
              <span>SHADOW BLUR</span>
              <span className="text-white font-bold">{style.shadow_blur || 4}px</span>
            </div>
            <input
              type="range"
              min={0}
              max={24}
              value={style.shadow_blur || 4}
              onChange={(e) => updateStyle("shadow_blur", Number(e.target.value))}
              className="w-full h-1.5 accent-lime bg-neutral-700 rounded-lg cursor-pointer"
            />

            <div className="flex justify-between text-[10px] font-mono text-neutral-400 pt-1">
              <span>TEXT OUTLINE</span>
              <span className="text-white font-bold">{style.outline_width}px</span>
            </div>
            <input
              type="range"
              min={0}
              max={6}
              value={style.outline_width}
              onChange={(e) => updateStyle("outline_width", Number(e.target.value))}
              className="w-full h-1.5 accent-lime bg-neutral-700 rounded-lg cursor-pointer"
            />
          </div>
        ) : (
          <div className="text-[10px] text-neutral-400 italic">
            Text shadow is OFF. Flat clean typography without blur.
          </div>
        )}
      </div>
    </div>
  );
};
