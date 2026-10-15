import React, { useState, useMemo } from 'react';
import { 
  Type, Search, Plus, Trash2, Copy, Scissors, RefreshCw, 
  Languages, AlignLeft, AlignCenter, AlignRight, Sliders, 
  Check, CheckSquare, Square, Sparkles, ArrowRight, Clock
} from 'lucide-react';
import { ProjectState, CaptionItem, CaptionStyle } from '../../types';

interface SubtitlesInspectorProps {
  project: ProjectState;
  selectedCaptionId: string | null;
  onSelectCaption: (id: string) => void;
  onUpdateCaption: (updated: CaptionItem) => void;
  onDeleteCaption: (id: string) => void;
  onDuplicateCaption?: (id: string) => void;
  onSplitCaption?: (id: string, time: number) => void;
  onAddCaption?: () => void;
  onTimeSeek: (time: number) => void;
  onTranscribe?: () => Promise<void>;
  isTranscribing?: boolean;
  activeLanguageView: 'english' | 'hindi';
  onToggleLanguageView: () => void;
  activeLinesMode?: 1 | 2;
  onReformatLines?: (lines: 1 | 2) => void;
  onDetectKeywords?: () => Promise<void>;
  syncStylesToAll?: boolean;
  onToggleSyncStylesToAll?: () => void;
  onApplyStyleToAll?: () => void;
  currentTime?: number;
}

const FONT_OPTIONS = [
  'Inter', 'Montserrat', 'Roboto', 'Oswald', 
  'Poppins', 'Plus Jakarta Sans', 'Playfair Display'
];

export const SubtitlesInspector: React.FC<SubtitlesInspectorProps> = ({
  project,
  selectedCaptionId,
  onSelectCaption,
  onUpdateCaption,
  onDeleteCaption,
  onDuplicateCaption,
  onSplitCaption,
  onAddCaption,
  onTimeSeek,
  activeLanguageView,
  onToggleLanguageView,
  activeLinesMode = 1,
  onReformatLines,
  onDetectKeywords,
  syncStylesToAll = true,
  onToggleSyncStylesToAll,
  onApplyStyleToAll,
  currentTime = 0
}) => {
  const [subTab, setSubTab] = useState<'transcript' | 'style'>('transcript');
  const [searchQuery, setSearchQuery] = useState('');
  const [isDetectingKw, setIsDetectingKw] = useState(false);
  const [appliedNotice, setAppliedNotice] = useState(false);

  // Priority: 1. Selected by ID, 2. Caption at playhead, 3. First caption
  const selectedCaption = useMemo(() => {
    if (selectedCaptionId) {
      const found = project.captions.find((c) => c.id === selectedCaptionId);
      if (found) return found;
    }
    const atPlayhead = project.captions.find((c) => currentTime >= c.start && currentTime <= c.end);
    if (atPlayhead) return atPlayhead;
    return project.captions[0] || null;
  }, [project.captions, selectedCaptionId, currentTime]);

  const filteredCaptions = useMemo(() => {
    if (!searchQuery.trim()) return project.captions;
    const q = searchQuery.toLowerCase();
    return project.captions.filter(
      (c) => c.text.toLowerCase().includes(q) || (c.translated_text && c.translated_text.toLowerCase().includes(q))
    );
  }, [project.captions, searchQuery]);

  const updateStyle = (key: keyof CaptionStyle, value: any) => {
    if (!selectedCaption) return;
    const updated: CaptionItem = {
      ...selectedCaption,
      style: {
        ...selectedCaption.style,
        [key]: value
      }
    };
    onUpdateCaption(updated);
  };

  const applyAestheticPreset = (preset: 'minimal' | 'bold' | 'documentary') => {
    if (!selectedCaption) return;
    let s: Partial<CaptionStyle> = {};
    if (preset === 'minimal') {
      s = {
        font_family: 'Inter',
        font_weight: '700',
        font_size: 28,
        text_color: '#FFFFFF',
        outline_width: 1,
        outline_color: '#000000',
        has_background: true,
        background_color: '#18181B',
        background_opacity: 0.75,
        corner_radius: 8,
        padding_x: 14,
        padding_y: 6,
        highlight_active_color: '#38BDF8',
        is_uppercase: false,
        contrast_block_mode: 'solid_box'
      };
    } else if (preset === 'bold') {
      s = {
        font_family: 'Montserrat',
        font_weight: '900',
        font_size: 34,
        text_color: '#FFFFFF',
        outline_width: 2,
        outline_color: '#000000',
        has_background: true,
        background_color: '#09090B',
        background_opacity: 0.85,
        corner_radius: 12,
        padding_x: 18,
        padding_y: 8,
        highlight_active_color: '#FACC15',
        is_uppercase: true,
        contrast_block_mode: 'solid_box'
      };
    } else if (preset === 'documentary') {
      s = {
        font_family: 'Roboto',
        font_weight: '600',
        font_size: 26,
        text_color: '#F4F4F5',
        outline_width: 0,
        outline_color: '#000000',
        has_background: true,
        background_color: '#1E293B',
        background_opacity: 0.8,
        corner_radius: 9999,
        padding_x: 16,
        padding_y: 6,
        highlight_active_color: '#818CF8',
        is_uppercase: false,
        contrast_block_mode: 'pill'
      };
    }

    const updated: CaptionItem = {
      ...selectedCaption,
      style: {
        ...selectedCaption.style,
        ...s
      }
    };
    onUpdateCaption(updated);
  };

  const handleApplyToAll = () => {
    if (onApplyStyleToAll) {
      onApplyStyleToAll();
      setAppliedNotice(true);
      setTimeout(() => setAppliedNotice(false), 2000);
    }
  };

  const isMinimalActive = selectedCaption?.style.font_family === 'Inter' && selectedCaption?.style.font_size === 28;
  const isBoldActive = selectedCaption?.style.font_family === 'Montserrat' && selectedCaption?.style.font_size === 34;
  const isDocActive = selectedCaption?.style.font_family === 'Roboto' && selectedCaption?.style.font_size === 26;

  return (
    <div className="flex flex-col h-full bg-white text-neutral-900 select-none">
      {/* Top Controls Bar */}
      <div className="p-3 border-b border-neutral-200 bg-neutral-50 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex rounded-lg bg-neutral-200/80 p-0.5 text-xs font-medium">
            <button
              onClick={() => setSubTab('transcript')}
              className={`flex-1 py-1.5 rounded-md transition text-xs font-medium ${
                subTab === 'transcript'
                  ? 'bg-white text-neutral-900 shadow-2xs font-semibold'
                  : 'text-neutral-600 hover:text-neutral-900'
              }`}
            >
              Transcript ({project.captions.length})
            </button>
            <button
              onClick={() => setSubTab('style')}
              className={`flex-1 py-1.5 rounded-md transition text-xs font-medium ${
                subTab === 'style'
                  ? 'bg-white text-neutral-900 shadow-2xs font-semibold'
                  : 'text-neutral-600 hover:text-neutral-900'
              }`}
            >
              Style & Presets
            </button>
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={onToggleLanguageView}
              className="px-2 py-1 text-[11px] font-semibold rounded-md border border-neutral-300 bg-white hover:bg-neutral-100 transition cursor-pointer flex items-center gap-1"
              title="Toggle Hindi / English text display"
            >
              <Languages className="h-3 w-3 text-neutral-600" />
              <span>{activeLanguageView === 'english' ? 'English' : 'Hindi'}</span>
            </button>

            {onReformatLines && (
              <button
                onClick={() => onReformatLines(activeLinesMode === 1 ? 2 : 1)}
                className="px-2 py-1 text-[11px] font-semibold rounded-md border border-neutral-300 bg-white hover:bg-neutral-100 transition cursor-pointer"
                title="Toggle 1-line vs 2-line subtitle chunks"
              >
                {activeLinesMode === 1 ? '1 Line' : '2 Lines'}
              </button>
            )}
          </div>
        </div>

        {/* Quick Actions Row */}
        <div className="flex items-center gap-2 pt-1">
          {onDetectKeywords && (
            <button
              onClick={async () => {
                setIsDetectingKw(true);
                try {
                  await onDetectKeywords();
                } finally {
                  setIsDetectingKw(false);
                }
              }}
              disabled={isDetectingKw}
              className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg bg-neutral-900 hover:bg-black text-white text-xs font-semibold transition cursor-pointer"
            >
              <Sparkles className="h-3.5 w-3.5" />
              <span>{isDetectingKw ? 'Analyzing...' : 'Highlight Keywords'}</span>
            </button>
          )}

          {onAddCaption && (
            <button
              onClick={onAddCaption}
              className="px-2.5 py-1.5 rounded-lg border border-neutral-300 bg-white hover:bg-neutral-100 text-neutral-700 text-xs font-semibold transition cursor-pointer flex items-center gap-1"
              title="Add caption at current playhead"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Add</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto">
        {subTab === 'transcript' ? (
          <div className="p-3 space-y-2">
            {/* Search Input */}
            <div className="relative mb-2">
              <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-neutral-400" />
              <input
                type="text"
                placeholder="Search dialogue transcript..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-neutral-50 border border-neutral-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-neutral-900 outline-none focus:border-neutral-400 focus:bg-white transition"
              />
            </div>

            {/* Captions List */}
            {filteredCaptions.length === 0 ? (
              <div className="py-8 text-center text-xs text-neutral-400">
                No captions found.
              </div>
            ) : (
              filteredCaptions.map((cap, idx) => {
                const isSelected = cap.id === selectedCaption?.id;
                const isCurrent = currentTime >= cap.start && currentTime <= cap.end;

                return (
                  <div
                    key={cap.id}
                    onClick={() => {
                      onSelectCaption(cap.id);
                      onTimeSeek(cap.start);
                    }}
                    className={`p-3 rounded-xl border transition cursor-pointer ${
                      isSelected
                        ? 'border-neutral-900 bg-neutral-50/80 shadow-2xs'
                        : isCurrent
                        ? 'border-neutral-400 bg-neutral-50/40'
                        : 'border-neutral-200 bg-white hover:bg-neutral-50/60'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5 text-[11px] text-neutral-500 font-mono">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-neutral-700">#{idx + 1}</span>
                        <span>{cap.start.toFixed(2)}s - {cap.end.toFixed(2)}s</span>
                        <span className="text-neutral-400">({(cap.end - cap.start).toFixed(1)}s)</span>
                      </div>

                      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                        {onSplitCaption && (
                          <button
                            onClick={() => onSplitCaption(cap.id, (cap.start + cap.end) / 2)}
                            className="p-1 rounded hover:bg-neutral-200 text-neutral-500 hover:text-neutral-800 transition"
                            title="Split at midpoint"
                          >
                            <Scissors className="h-3 w-3" />
                          </button>
                        )}
                        {onDuplicateCaption && (
                          <button
                            onClick={() => onDuplicateCaption(cap.id)}
                            className="p-1 rounded hover:bg-neutral-200 text-neutral-500 hover:text-neutral-800 transition"
                            title="Duplicate caption"
                          >
                            <Copy className="h-3 w-3" />
                          </button>
                        )}
                        <button
                          onClick={() => onDeleteCaption(cap.id)}
                          className="p-1 rounded hover:bg-red-50 text-neutral-400 hover:text-red-600 transition"
                          title="Delete caption"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    </div>

                    {/* Inline Editable Textarea */}
                    <textarea
                      value={activeLanguageView === 'hindi' && cap.text ? cap.text : (cap.translated_text || cap.text)}
                      onChange={(e) => {
                        const newText = e.target.value;
                        const wordTokens = newText.trim().split(/\s+/).filter(Boolean);
                        const dur = cap.end - cap.start;
                        const wDur = dur / Math.max(1, wordTokens.length);

                        const updatedWords = wordTokens.map((w, wIdx) => {
                          const existingWord = cap.words[wIdx];
                          return {
                            word: w,
                            start: cap.start + wIdx * wDur,
                            end: cap.start + (wIdx + 1) * wDur,
                            is_keyword: existingWord?.is_keyword,
                            keyword_category: existingWord?.keyword_category,
                            keyword_color: existingWord?.keyword_color
                          };
                        });

                        const updated: CaptionItem = {
                          ...cap,
                          text: activeLanguageView === 'hindi' ? newText : cap.text,
                          translated_text: activeLanguageView === 'english' ? newText : cap.translated_text,
                          words: updatedWords
                        };
                        onUpdateCaption(updated);
                      }}
                      rows={cap.text.length > 50 ? 2 : 1}
                      className="w-full bg-transparent text-xs font-semibold text-neutral-900 border-none outline-none resize-none focus:bg-white/80 rounded p-1 transition"
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                );
              })
            )}
          </div>
        ) : (
          /* Style & Aesthetic Presets Tab */
          <div className="p-4 space-y-4 text-xs text-neutral-800">
            {/* Aesthetic Presets */}
            <div className="space-y-2">
              <div className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">
                Aesthetic Presets
              </div>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => applyAestheticPreset('minimal')}
                  className={`p-2.5 rounded-xl border text-center font-medium transition cursor-pointer ${
                    isMinimalActive
                      ? 'border-neutral-900 bg-neutral-900 text-white shadow-2xs'
                      : 'border-neutral-200 bg-neutral-50 hover:bg-neutral-100 text-neutral-900'
                  }`}
                >
                  <div className="font-bold text-xs">Minimal</div>
                  <div className={`text-[10px] mt-0.5 ${isMinimalActive ? 'text-neutral-300' : 'text-neutral-500'}`}>
                    Inter 28px
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => applyAestheticPreset('bold')}
                  className={`p-2.5 rounded-xl border text-center font-medium transition cursor-pointer ${
                    isBoldActive
                      ? 'border-neutral-900 bg-neutral-900 text-white shadow-2xs'
                      : 'border-neutral-200 bg-neutral-50 hover:bg-neutral-100 text-neutral-900'
                  }`}
                >
                  <div className="font-bold text-xs">Bold Pop</div>
                  <div className={`text-[10px] mt-0.5 ${isBoldActive ? 'text-neutral-300' : 'text-neutral-500'}`}>
                    Montserrat 34px
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => applyAestheticPreset('documentary')}
                  className={`p-2.5 rounded-xl border text-center font-medium transition cursor-pointer ${
                    isDocActive
                      ? 'border-neutral-900 bg-neutral-900 text-white shadow-2xs'
                      : 'border-neutral-200 bg-neutral-50 hover:bg-neutral-100 text-neutral-900'
                  }`}
                >
                  <div className="font-bold text-xs">Documentary</div>
                  <div className={`text-[10px] mt-0.5 ${isDocActive ? 'text-neutral-300' : 'text-neutral-500'}`}>
                    Roboto 26px
                  </div>
                </button>
              </div>
            </div>

            {/* Global Sync Control */}
            <div className="p-3 bg-neutral-50 rounded-xl border border-neutral-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-xs text-neutral-900">Apply to All Captions</span>
                {onToggleSyncStylesToAll && (
                  <button
                    type="button"
                    onClick={onToggleSyncStylesToAll}
                    className="text-neutral-700 hover:text-neutral-900 cursor-pointer"
                  >
                    {syncStylesToAll ? <CheckSquare className="h-4 w-4 text-neutral-900" /> : <Square className="h-4 w-4 text-neutral-400" />}
                  </button>
                )}
              </div>
              <button
                type="button"
                onClick={handleApplyToAll}
                className="w-full py-1.5 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white font-semibold text-xs transition cursor-pointer"
              >
                {appliedNotice ? 'Applied to All Captions' : 'Apply Style to All Subtitles'}
              </button>
            </div>

            {selectedCaption && (
              <>
                {/* Typography Controls */}
                <div className="space-y-3 pt-2 border-t border-neutral-200">
                  <div className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">
                    Typography
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[11px] text-neutral-500 mb-1 block">Font Family</label>
                      <select
                        value={selectedCaption.style.font_family || 'Montserrat'}
                        onChange={(e) => updateStyle('font_family', e.target.value)}
                        className="w-full bg-neutral-50 border border-neutral-200 rounded-lg p-1.5 text-xs text-neutral-900 outline-none"
                      >
                        {FONT_OPTIONS.map((f) => (
                          <option key={f} value={f}>{f}</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-[11px] text-neutral-500">Font Size</label>
                        <span className="text-[10px] font-mono font-bold text-neutral-900 bg-neutral-100 px-1 py-0.2 rounded border border-neutral-200">
                          {selectedCaption.style.font_size || 32}px
                        </span>
                      </div>
                      <input
                        type="range"
                        min="14"
                        max="64"
                        step="1"
                        value={selectedCaption.style.font_size || 32}
                        onChange={(e) => updateStyle('font_size', Number(e.target.value))}
                        className="w-full accent-neutral-900 cursor-pointer"
                      />
                    </div>
                  </div>

                  {/* Sizing Quick Presets */}
                  <div className="flex items-center gap-1 pt-0.5">
                    {[20, 26, 32, 38, 46, 54].map((sz) => (
                      <button
                        key={sz}
                        type="button"
                        onClick={() => updateStyle('font_size', sz)}
                        className={`flex-1 py-0.5 text-[10px] font-mono rounded border transition ${
                          selectedCaption.style.font_size === sz
                            ? 'bg-neutral-900 text-white border-neutral-900 font-bold shadow-2xs'
                            : 'bg-white hover:bg-neutral-100 text-neutral-600 border-neutral-200'
                        }`}
                      >
                        {sz}
                      </button>
                    ))}
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <div>
                      <label className="text-[11px] text-neutral-500 mb-1 block">Text Color</label>
                      <div className="flex items-center gap-2">
                        <input
                          type="color"
                          value={selectedCaption.style.text_color || '#FFFFFF'}
                          onChange={(e) => updateStyle('text_color', e.target.value)}
                          className="h-7 w-8 rounded border border-neutral-200 cursor-pointer bg-white"
                        />
                        <span className="font-mono text-xs text-neutral-700">{selectedCaption.style.text_color || '#FFFFFF'}</span>
                      </div>
                    </div>

                    <div>
                      <label className="text-[11px] text-neutral-500 mb-1 block">Active Word Color</label>
                      <div className="flex items-center gap-2">
                        <input
                          type="color"
                          value={selectedCaption.style.highlight_active_color || '#38BDF8'}
                          onChange={(e) => updateStyle('highlight_active_color', e.target.value)}
                          className="h-7 w-8 rounded border border-neutral-200 cursor-pointer bg-white"
                        />
                        <span className="font-mono text-xs text-neutral-700">{selectedCaption.style.highlight_active_color || '#38BDF8'}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Background Box / Pill Controls */}
                <div className="space-y-3 pt-2 border-t border-neutral-200">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">Background Container</span>
                    <button
                      type="button"
                      onClick={() => updateStyle('has_background', !selectedCaption.style.has_background)}
                      className="text-neutral-700 hover:text-neutral-900 cursor-pointer"
                    >
                      {selectedCaption.style.has_background ? <CheckSquare className="h-4 w-4 text-neutral-900" /> : <Square className="h-4 w-4 text-neutral-400" />}
                    </button>
                  </div>

                  {selectedCaption.style.has_background && (
                    <div className="space-y-2 bg-neutral-50 p-3 rounded-xl border border-neutral-200">
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="text-[11px] text-neutral-500 mb-1 block">Box Color</label>
                          <div className="flex items-center gap-2">
                            <input
                              type="color"
                              value={selectedCaption.style.background_color || '#000000'}
                              onChange={(e) => updateStyle('background_color', e.target.value)}
                              className="h-7 w-8 rounded border border-neutral-200 cursor-pointer bg-white"
                            />
                            <span className="font-mono text-xs text-neutral-700">{selectedCaption.style.background_color || '#000000'}</span>
                          </div>
                        </div>

                        <div>
                          <label className="text-[11px] text-neutral-500 mb-1 block">Opacity ({Math.round((selectedCaption.style.background_opacity ?? 0.8) * 100)}%)</label>
                          <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.05"
                            value={selectedCaption.style.background_opacity ?? 0.8}
                            onChange={(e) => updateStyle('background_opacity', parseFloat(e.target.value))}
                            className="w-full accent-neutral-900 mt-2 cursor-pointer"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2 pt-1">
                        <div>
                          <label className="text-[11px] text-neutral-500 mb-1 block">Corner Radius ({selectedCaption.style.corner_radius ?? 12}px)</label>
                          <input
                            type="range"
                            min="0"
                            max="32"
                            value={selectedCaption.style.corner_radius ?? 12}
                            onChange={(e) => updateStyle('corner_radius', parseInt(e.target.value))}
                            className="w-full accent-neutral-900 mt-2 cursor-pointer"
                          />
                        </div>

                        <div>
                          <label className="text-[11px] text-neutral-500 mb-1 block">Padding ({selectedCaption.style.padding_x ?? 16}px)</label>
                          <input
                            type="range"
                            min="4"
                            max="32"
                            value={selectedCaption.style.padding_x ?? 16}
                            onChange={(e) => {
                              const v = parseInt(e.target.value);
                              const updated: CaptionItem = {
                                ...selectedCaption,
                                style: {
                                  ...selectedCaption.style,
                                  padding_x: v,
                                  padding_y: Math.round(v * 0.45)
                                }
                              };
                              onUpdateCaption(updated);
                            }}
                            className="w-full accent-neutral-900 mt-2 cursor-pointer"
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Advanced Features & Toggles */}
                <div className="space-y-3 pt-2 border-t border-neutral-200">
                  <div className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">
                    Effects & Highlights
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="flex items-center justify-between bg-neutral-50 p-2 rounded-lg border border-neutral-200">
                      <span className="text-[11px] text-neutral-700">Active Word Color</span>
                      <button
                        type="button"
                        onClick={() => updateStyle('has_highlight', selectedCaption.style.has_highlight === false ? true : false)}
                        className="text-neutral-700 hover:text-neutral-900 cursor-pointer"
                      >
                        {selectedCaption.style.has_highlight !== false ? <CheckSquare className="h-4 w-4 text-neutral-900" /> : <Square className="h-4 w-4 text-neutral-400" />}
                      </button>
                    </div>

                    <div className="flex items-center justify-between bg-neutral-50 p-2 rounded-lg border border-neutral-200">
                      <span className="text-[11px] text-neutral-700">Letter Shadow</span>
                      <button
                        type="button"
                        onClick={() => updateStyle('has_shadow', selectedCaption.style.has_shadow === false ? true : false)}
                        className="text-neutral-700 hover:text-neutral-900 cursor-pointer"
                      >
                        {selectedCaption.style.has_shadow !== false ? <CheckSquare className="h-4 w-4 text-neutral-900" /> : <Square className="h-4 w-4 text-neutral-400" />}
                      </button>
                    </div>

                    <div className="flex items-center justify-between bg-neutral-50 p-2 rounded-lg border border-neutral-200">
                      <span className="text-[11px] text-neutral-700">Outline</span>
                      <button
                        type="button"
                        onClick={() => updateStyle('outline_width', (selectedCaption.style.outline_width || 0) > 0 ? 0 : 2)}
                        className="text-neutral-700 hover:text-neutral-900 cursor-pointer"
                      >
                        {(selectedCaption.style.outline_width || 0) > 0 ? <CheckSquare className="h-4 w-4 text-neutral-900" /> : <Square className="h-4 w-4 text-neutral-400" />}
                      </button>
                    </div>

                    <div className="flex items-center justify-between bg-neutral-50 p-2 rounded-lg border border-neutral-200">
                      <span className="text-[11px] text-neutral-700">Keyword Highlights</span>
                      <button
                        type="button"
                        onClick={() => updateStyle('has_keyword_emphasis', selectedCaption.style.has_keyword_emphasis === false ? true : false)}
                        className="text-neutral-700 hover:text-neutral-900 cursor-pointer"
                      >
                        {selectedCaption.style.has_keyword_emphasis !== false ? <CheckSquare className="h-4 w-4 text-neutral-900" /> : <Square className="h-4 w-4 text-neutral-400" />}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Positioning Section */}
                <div className="space-y-3 pt-2 border-t border-neutral-200">
                  <div className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">
                    Positioning
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="flex justify-between mb-1">
                        <label className="text-[11px] text-neutral-500">Horizontal (X)</label>
                        <span className="text-[10px] font-mono font-bold text-neutral-900">
                          {Math.round(selectedCaption.pos_x * 100)}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.01"
                        value={selectedCaption.pos_x}
                        onChange={(e) => {
                          onUpdateCaption({
                            ...selectedCaption,
                            pos_x: parseFloat(e.target.value)
                          });
                        }}
                        className="w-full accent-neutral-900 cursor-pointer"
                      />
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <label className="text-[11px] text-neutral-500">Vertical (Y)</label>
                        <span className="text-[10px] font-mono font-bold text-neutral-900">
                          {Math.round(selectedCaption.pos_y * 100)}%
                        </span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.01"
                        value={selectedCaption.pos_y}
                        onChange={(e) => {
                          onUpdateCaption({
                            ...selectedCaption,
                            pos_y: parseFloat(e.target.value)
                          });
                        }}
                        className="w-full accent-neutral-900 cursor-pointer"
                      />
                    </div>
                  </div>
                </div>

              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
