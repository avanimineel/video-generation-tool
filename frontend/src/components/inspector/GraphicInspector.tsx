import React, { useState, useEffect } from 'react';
import { Sparkles, Trash2, Search, Image as ImageIcon, Film, Zap, Check, Globe, RefreshCw, Tv, Layers, Move, FileText } from 'lucide-react';
import { MotionGraphicItem, CaptionItem } from '../../types';
import { api } from '../../services/api';

interface GraphicInspectorProps {
  graphic: MotionGraphicItem | null;
  captions?: CaptionItem[];
  projectId?: string;
  onUpdateGraphic: (updated: MotionGraphicItem) => void;
  onDeleteGraphic: (id: string) => void;
}

interface MediaResult {
  title: string;
  url: string;
  thumb_url: string;
  source_credit: string;
  media_type: 'image' | 'video';
  description?: string;
  provider?: string;
  id?: string;
}

const TOPIC_PRESETS = [
  {
    name: '🏥 Cancer / Oncology',
    query: 'cancer cell division pathology',
    broll_title: 'CLINICAL ONCOLOGY',
    broll_subtitle: 'Cellular Division & Microscopic Pathology',
    source_citation: 'Source: National Cancer Institute',
    media_url: 'https://images.unsplash.com/photo-1530497610245-94d3c16cda28?auto=format&fit=crop&w=1200&q=80',
    media_type: 'image' as const
  },
  {
    name: '🫁 Pulmonary / Lungs',
    query: 'pulmonary lungs x-ray medical',
    broll_title: 'PULMONARY PATHOLOGY',
    broll_subtitle: 'Respiratory Histology & Radiography',
    source_citation: 'Source: Pulmonary Clinical Archives',
    media_url: 'https://images.unsplash.com/photo-1576091160550-2173dba999ef?auto=format&fit=crop&w=1200&q=80',
    media_type: 'image' as const
  },
  {
    name: '🧬 DNA / Cell Lab',
    query: 'dna molecular genetics laboratory',
    broll_title: 'MOLECULAR BIOLOGY',
    broll_subtitle: 'Genomic Sequencing & Cellular Analysis',
    source_citation: 'Source: Molecular Genetics Institute',
    media_url: 'https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?auto=format&fit=crop&w=1200&q=80',
    media_type: 'image' as const
  },
  {
    name: '🚀 Space / Aerospace',
    query: 'spaceflight rocket launch telemetry',
    broll_title: 'AEROSPACE ARCHIVES',
    broll_subtitle: 'Orbital Mechanics & Telemetry',
    source_citation: 'Source: NASA Historical Archive',
    media_url: 'https://images.unsplash.com/photo-1517976487507-5b3b4b45f912?auto=format&fit=crop&w=1200&q=80',
    media_type: 'image' as const
  },
  {
    name: '🏛️ Historical Doc',
    query: 'historical archival record documentary',
    broll_title: 'HISTORICAL ARCHIVES',
    broll_subtitle: 'Public Record & Primary Sources',
    source_citation: 'Source: National Documentary Archives',
    media_url: 'https://images.unsplash.com/photo-1461360370896-922624d12aa1?auto=format&fit=crop&w=1200&q=80',
    media_type: 'image' as const
  }
];

export const GraphicInspector: React.FC<GraphicInspectorProps> = ({
  graphic,
  captions = [],
  projectId,
  onUpdateGraphic,
  onDeleteGraphic
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [mediaTypeFilter, setMediaTypeFilter] = useState<'image' | 'video' | 'all'>('image');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<MediaResult[]>([]);
  const [activeMediaUrl, setActiveMediaUrl] = useState('');

  useEffect(() => {
    if (graphic) {
      const currentUrl = graphic.parameters?.media_url || graphic.media_url || '';
      setActiveMediaUrl(currentUrl);

      // Auto-populate query based on current graphic title or active caption if query is empty
      if (!searchQuery) {
        const title = graphic.parameters?.broll_title || graphic.title;
        if (title && !title.toLowerCase().includes('flight') && !title.toLowerCase().includes('split')) {
          setSearchQuery(title);
        } else {
          // Find overlapping caption
          const overlappingCap = captions.find(
            (c) => c.start <= graphic.end && c.end >= graphic.start
          );
          if (overlappingCap) {
            setSearchQuery(overlappingCap.text.slice(0, 40));
          } else {
            setSearchQuery('cancer');
          }
        }
      }
    }
  }, [graphic?.id]);

  if (!graphic) {
    return (
      <div className="p-6 text-center text-xs font-mono text-neutral-500">
        Select a motion graphic on the timeline to edit its B-roll footage, text, colors, timing, and parameters.
      </div>
    );
  }

  const updateParam = (key: string, value: any) => {
    onUpdateGraphic({
      ...graphic,
      parameters: {
        ...graphic.parameters,
        [key]: value
      }
    });
  };

  const handleApplyMedia = async (item: { url: string; media_type?: 'image' | 'video'; source_credit?: string; title?: string; id?: string; provider?: string }) => {
    let finalUrl = item.url;
    if (projectId && finalUrl && !finalUrl.includes('/asset/downloaded/') && !finalUrl.includes('/asset/')) {
      try {
        const dl = await api.downloadAsset(projectId, item as any);
        if (dl && dl.media_url) {
          finalUrl = dl.media_url;
        }
      } catch (err) {
        console.warn('Failed to download asset locally in GraphicInspector, using direct URL:', err);
      }
    }

    const updatedParams = {
      ...graphic.parameters,
      ...(graphic.parameters.title_style === 'cards_broll' && finalUrl.includes('/asset/') ? {card_media: [...(Array.isArray(graphic.parameters.card_media) ? graphic.parameters.card_media : []).filter((c:any)=>c.url!==finalUrl).slice(-2),{url:finalUrl,type:item.media_type||'image'}]} : {}),
      media_url: finalUrl,
      media_type: item.media_type || 'image',
      source_citation: item.source_credit || graphic.parameters?.source_citation || 'Source - Archive Reference'
    };

    onUpdateGraphic({
      ...graphic,
      media_url: finalUrl,
      media_type: item.media_type || 'image',
      parameters: updatedParams
    });
    setActiveMediaUrl(finalUrl);
  };

  const handleApplyPreset = (preset: typeof TOPIC_PRESETS[0]) => {
    const updatedParams = {
      ...graphic.parameters,
      broll_title: preset.broll_title,
      broll_subtitle: preset.broll_subtitle,
      source_citation: preset.source_citation,
      media_url: preset.media_url,
      media_type: preset.media_type
    };

    onUpdateGraphic({
      ...graphic,
      title: preset.broll_title,
      media_url: preset.media_url,
      media_type: preset.media_type,
      parameters: updatedParams
    });
    setActiveMediaUrl(preset.media_url);
    setSearchQuery(preset.query);
  };

  const handleSearch = async (queryToUse?: string) => {
    const q = queryToUse || searchQuery;
    if (!q.trim()) return;

    setIsSearching(true);
    try {
      const typeParam = mediaTypeFilter === 'all' ? 'image' : mediaTypeFilter;
      const res = await api.searchMedia(q.trim(), typeParam);
      if (res && res.results) {
        setSearchResults(res.results);
      }
    } catch (e) {
      console.warn('Search failed:', e);
    } finally {
      setIsSearching(false);
    }
  };

  const handleAutoMatch = async () => {
    // Look up active caption at this graphic's time
    const overlappingCap = captions.find(
      (c) => c.start <= graphic.end && c.end >= graphic.start
    );
    const textToMatch = overlappingCap ? overlappingCap.text : searchQuery || 'cancer';

    setIsSearching(true);
    try {
      const match = await api.autoMatchMedia(textToMatch);
      if (match) {
        if (match.all_results && match.all_results.length > 0) {
          setSearchResults(match.all_results);
        }
        if (match.media) {
          const updatedParams = {
            ...graphic.parameters,
            broll_title: match.broll_title || graphic.parameters?.broll_title,
            source_citation: match.source_citation || graphic.parameters?.source_citation,
            media_url: match.media.url,
            media_type: match.media.media_type || 'image'
          };
          onUpdateGraphic({
            ...graphic,
            title: match.broll_title || graphic.title,
            media_url: match.media.url,
            media_type: match.media.media_type || 'image',
            parameters: updatedParams
          });
          setActiveMediaUrl(match.media.url);
          setSearchQuery(match.search_term);
        }
      }
    } catch (e) {
      console.warn('Auto match failed:', e);
    } finally {
      setIsSearching(false);
    }
  };

  const isSplitOrBroll =
    graphic.template_id === 'split_screen_vertical' ||
    graphic.template_id === 'contextual_broll' ||
    graphic.template_id.includes('broll') ||
    graphic.parameters?.media_url !== undefined;

  return (
    <div className="p-4 space-y-5 text-xs text-neutral-200 select-none overflow-y-auto max-h-full">
      {graphic.template_id==='kinetic_typography'&&<label className="block text-neutral-900">Title animation
        <select value={String(graphic.parameters.title_style||'rise')} onChange={e=>{
          const style=e.target.value;
          const words=String(graphic.parameters.headline||graphic.title).split(/\s+/).filter(Boolean);
          const split=Math.max(1,Math.ceil(words.length/2));
          const groups=style==='staircase'?words:style==='cooked_badge'?[words[0],words.slice(1).join(' ')]:['dual','behind_subject','rise','paper'].includes(style)?[words.slice(0,split).join(' '),words.slice(split).join(' ')]:[words.join(' ')];
          let index=0;
          const lines=groups.filter(Boolean).map(text=>{const offset=graphic.parameters.timed_words?.[index]?.offset??index*.18;index+=text.split(/\s+/).length;return {text,offset};});
          onUpdateGraphic({...graphic,pos_y:style==='behind_subject'&&graphic.pos_y===.5?.19:graphic.pos_y,parameters:{...graphic.parameters,title_style:style,title_lines:lines}});
        }} className="block w-full bg-white border border-neutral-300 rounded p-2 mt-1">
          {['editorial','dual','flame_subject','script','cards_broll','behind_subject','rise','paper','typewriter','bold_pop','staircase','cooked_badge',...(graphic.parameters.stat_cards?['stat_pair']:[])].map(style=><option key={style} value={style}>{style.replace(/_/g,' ')}</option>)}
        </select>
      </label>}
      {graphic.parameters.title_style==='behind_subject'&&<p className="text-xs text-neutral-600">{graphic.parameters.subject_mask_error|| (graphic.parameters.subject_mask?'Speaker cutout ready. Background text follows the person.':'Preparing the speaker cutout when this edit saves…')}</p>}
      {graphic.parameters.title_style==='cards_broll'&&<p className="text-xs text-neutral-600">Choose up to three local images or videos below to fill the cards. Each selection adds a card.</p>}
      {graphic.parameters.sfx_track_url&&<label className="block text-neutral-900"><input type="checkbox" checked={!graphic.parameters.sfx_muted} onChange={e=>updateParam('sfx_muted',!e.target.checked)}/> Automatic sound effects</label>}
      {/* Header */}
      <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
        <div className="flex items-center gap-1.5">
          <Sparkles className="h-4 w-4 text-purple-400" />
          <span className="font-bold text-sm text-white">Graphic Inspector</span>
          <span className="text-[10px] bg-purple-950/60 border border-purple-800/60 text-purple-300 px-1.5 py-0.5 rounded font-mono">
            {graphic.template_id}
          </span>
        </div>
        <button
          onClick={() => onDeleteGraphic(graphic.id)}
          className="p-1 rounded hover:bg-red-950/60 text-neutral-400 hover:text-red-400 transition-colors"
          title="Delete graphic"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Timing Block with fine adjustment inputs */}
      <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 space-y-2.5">
        <span className="text-[10px] font-mono text-neutral-400 uppercase block">Clip Timing</span>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className="text-[9px] font-mono text-neutral-400 block mb-1">START (SEC)</span>
            <input
              type="number"
              step="0.1"
              min="0"
              value={Number(graphic.start.toFixed(2))}
              onChange={(e) => {
                const newStart = Math.max(0, Number(e.target.value));
                if (newStart < graphic.end) {
                  onUpdateGraphic({ ...graphic, start: newStart });
                }
              }}
              className="w-full bg-neutral-950 border border-neutral-700 rounded-lg p-1.5 font-mono text-white text-xs outline-none focus:border-purple-500"
            />
          </div>
          <div>
            <span className="text-[9px] font-mono text-neutral-400 block mb-1">END (SEC)</span>
            <input
              type="number"
              step="0.1"
              min={graphic.start + 0.2}
              value={Number(graphic.end.toFixed(2))}
              onChange={(e) => {
                const newEnd = Number(e.target.value);
                if (newEnd > graphic.start) {
                  onUpdateGraphic({ ...graphic, end: newEnd });
                }
              }}
              className="w-full bg-neutral-950 border border-neutral-700 rounded-lg p-1.5 font-mono text-white text-xs outline-none focus:border-purple-500"
            />
          </div>
        </div>
      </div>

      {/* Position & Scale Sliders */}
      <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono text-neutral-400 uppercase">Position & Scale</span>
          <span className="text-[9px] font-mono text-lime font-bold">
            {Math.round((graphic.scale ?? 1.0) * 100)}%
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-[9px] font-mono text-neutral-400 mb-1 block">Anchor X ({Math.round((graphic.pos_x ?? 0.5) * 100)}%)</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={graphic.pos_x ?? 0.5}
              onChange={(e) => onUpdateGraphic({ ...graphic, pos_x: parseFloat(e.target.value) })}
              className="w-full accent-cyan-400 cursor-pointer"
            />
          </div>
          <div>
            <label className="text-[9px] font-mono text-neutral-400 mb-1 block">Anchor Y ({Math.round((graphic.pos_y ?? 0.5) * 100)}%)</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={graphic.pos_y ?? 0.5}
              onChange={(e) => onUpdateGraphic({ ...graphic, pos_y: parseFloat(e.target.value) })}
              className="w-full accent-cyan-400 cursor-pointer"
            />
          </div>
        </div>
        <div>
          <label className="text-[9px] font-mono text-neutral-400 mb-1 block">Scale ({Math.round((graphic.scale ?? 1.0) * 100)}%)</label>
          <input
            type="range"
            min="0.4"
            max="2.0"
            step="0.05"
            value={graphic.scale ?? 1.0}
            onChange={(e) => onUpdateGraphic({ ...graphic, scale: parseFloat(e.target.value) })}
            className="w-full accent-lime cursor-pointer"
          />
        </div>
      </div>

      {/* Track Assignment (Section 1: V5 Hook/Title, V4 Article/Web, V3 B-Roll/Media) */}
      <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono text-neutral-400 uppercase flex items-center gap-1">
            <Layers className="w-3 h-3 text-purple-400" />
            <span>Timeline Track</span>
          </span>
          <span className="text-[9px] font-mono text-purple-400 font-bold">
            {graphic.track || 'V3'}
          </span>
        </div>
        <div className="grid grid-cols-3 gap-1">
          {(['V5', 'V4', 'V3'] as const).map((t) => (
            <button
              key={t}
              onClick={() => onUpdateGraphic({ ...graphic, track: t })}
              className={`py-1.5 px-2 rounded text-[10px] font-mono font-bold transition ${
                (graphic.track || 'V3') === t
                  ? t === 'V5'
                    ? 'bg-amber-500 text-black shadow'
                    : t === 'V4'
                    ? 'bg-cyan-500 text-black shadow'
                    : 'bg-purple-600 text-white shadow'
                  : 'bg-neutral-800 text-neutral-400 hover:text-white'
              }`}
            >
              {t === 'V5' ? 'V5: Hook' : t === 'V4' ? 'V4: Article' : 'V3: B-Roll'}
            </button>
          ))}
        </div>
      </div>

      {/* Placement Mode: Overlay vs Insert (Section 2 - Critical Requirement) */}
      <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono text-neutral-400 uppercase">Placement Behavior</span>
          <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${
            graphic.placement_mode === 'insert' ? 'bg-amber-500 text-black' : 'bg-neutral-800 text-neutral-300'
          }`}>
            {graphic.placement_mode === 'insert' ? 'CUTAWAY INSERT' : 'OVERLAY'}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          <button
            onClick={() => onUpdateGraphic({ ...graphic, placement_mode: 'overlay' })}
            className={`py-2 px-2 rounded-lg text-left transition border ${
              graphic.placement_mode !== 'insert'
                ? 'bg-purple-950/80 border-purple-500 text-white shadow'
                : 'bg-neutral-850 border-neutral-750 text-neutral-400 hover:text-white'
            }`}
          >
            <div className="text-[11px] font-bold">Overlay Mode</div>
            <div className="text-[9px] text-neutral-400 leading-tight">Speaker plays underneath, visual floats on top / split.</div>
          </button>
          <button
            onClick={() => onUpdateGraphic({ ...graphic, placement_mode: 'insert' })}
            className={`py-2 px-2 rounded-lg text-left transition border ${
              graphic.placement_mode === 'insert'
                ? 'bg-amber-950/80 border-amber-500 text-amber-200 shadow'
                : 'bg-neutral-850 border-neutral-750 text-neutral-400 hover:text-white'
            }`}
          >
            <div className="text-[11px] font-bold">Insert Cutaway</div>
            <div className="text-[9px] text-neutral-400 leading-tight">Takes over 100% full screen between footage.</div>
          </button>
        </div>
      </div>

      {/* Screen Layout (Screenshot 2: 50/50 Split Screen Mode) */}
      {graphic.placement_mode !== 'insert' && (
        <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 space-y-2">
          <span className="text-[10px] font-mono text-neutral-400 uppercase block">Screen Layout</span>
          <div className="grid grid-cols-3 gap-1">
            {[
              { id: 'none', label: 'Centered' },
              { id: 'split_50_50_vertical', label: '50/50 Split' },
              { id: 'pip_top_right', label: 'PIP Corner' }
            ].map((opt) => (
              <button
                key={opt.id}
                onClick={() => onUpdateGraphic({ ...graphic, split_layout: opt.id as any })}
                className={`py-1.5 rounded text-[10px] font-mono font-bold transition ${
                  (graphic.split_layout || 'none') === opt.id
                    ? 'bg-cyan-500 text-black shadow'
                    : 'bg-neutral-800 text-neutral-400 hover:text-white'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Static Image Motion (Ken Burns Effect - Section 5 & 42.H) */}
      <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-mono text-neutral-400 uppercase flex items-center gap-1">
            <Move className="w-3 h-3 text-lime" />
            <span>Ken Burns Motion</span>
          </span>
          <span className="text-[9px] font-mono text-lime font-bold">
            {graphic.animation || 'none'}
          </span>
        </div>
        <div className="grid grid-cols-3 gap-1">
          {[
            { id: 'none', label: 'Static' },
            { id: 'push_in', label: 'Dolly In' },
            { id: 'slow_zoom_in', label: 'Zoom In' },
            { id: 'slow_zoom_out', label: 'Zoom Out' },
            { id: 'pan_left', label: 'Pan Left' },
            { id: 'pan_right', label: 'Pan Right' },
            { id: 'tilt_up', label: 'Tilt Up' },
            { id: 'tilt_down', label: 'Tilt Down' },
            { id: 'crane_up', label: 'Crane Up' },
            { id: 'dutch', label: 'Dutch Angle' },
            { id: 'handheld', label: 'Handheld' }
          ].map((anim) => {
            const current = String(graphic.parameters?.animation || graphic.animation || 'none');
            return (
              <button
                key={anim.id}
                // The export reads parameters.animation first, so both are set; a manual choice is kept on re-plans.
                onClick={() => onUpdateGraphic({ ...graphic, animation: anim.id as any, parameters: { ...graphic.parameters, animation: anim.id, motion_chosen: true } })}
                className={`py-1 text-[10px] font-mono font-bold rounded transition ${
                  current === anim.id ? 'bg-lime text-black shadow' : 'bg-neutral-800 text-neutral-400 hover:text-white'
                }`}
              >
                {anim.label}
              </button>
            );
          })}
        </div>
        {graphic.placement_mode === 'insert' && (
          <div className="space-y-1.5 pt-1">
            {([
              ['speed', 'Speed', [['normal', 'Normal'], ['slow_motion', 'Slow Mo'], ['speed_ramp', 'Speed Ramp'], ['freeze_end', 'Freeze End']]],
              ['transition_in', 'In', [['cut', 'Cut'], ['dissolve', 'Dissolve'], ['whip', 'Whip'], ['wipe', 'Wipe'], ['flash', 'Flash']]],
              ['transition_out', 'Out', [['cut', 'Cut'], ['dissolve', 'Dissolve'], ['whip', 'Whip'], ['wipe', 'Wipe'], ['flash', 'Flash']]]
            ] as [string, string, [string, string][]][]).map(([key, label, choices]) => (
              <div key={key} className="flex items-center gap-1">
                <span className="w-10 text-[9px] font-mono uppercase text-neutral-400">{label}</span>
                <div className="flex flex-wrap gap-1">
                  {choices.map(([value, name]) => (
                    <button key={value}
                      onClick={() => onUpdateGraphic({ ...graphic, parameters: { ...graphic.parameters, [key]: value, motion_chosen: true } })}
                      className={`px-1.5 py-0.5 text-[9px] font-mono font-bold rounded ${String(graphic.parameters?.[key] || (key === 'speed' ? 'normal' : 'cut')) === value ? 'bg-lime text-black' : 'bg-neutral-800 text-neutral-400 hover:text-white'}`}>
                      {name}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* TV / CRT Scanlines Effect (Screenshot 3 & 4) */}
      <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Tv className="w-4 h-4 text-neutral-300" />
          <div>
            <div className="text-xs font-bold text-white">CRT TV Scanline Filter</div>
            <div className="text-[9px] text-neutral-400 font-mono">Broadcast & CCTV texture effect</div>
          </div>
        </div>
        <button
          onClick={() => updateParam('scanlines', !graphic.parameters?.scanlines)}
          className={`px-2.5 py-1 rounded text-xs font-mono font-bold transition ${
            graphic.parameters?.scanlines
              ? 'bg-lime text-black shadow'
              : 'bg-neutral-800 text-neutral-400 hover:text-white'
          }`}
        >
          {graphic.parameters?.scanlines ? 'ON' : 'OFF'}
        </button>
      </div>

      {/* 1. B-Roll Media Selector & Web Search (Primary for Split Screen / B-Roll) */}
      {isSplitOrBroll && (
        <div className="bg-neutral-900/90 p-3.5 rounded-xl border border-purple-500/30 space-y-3.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Globe className="h-4 w-4 text-cyan-400" />
              <span className="font-bold text-xs text-white">B-Roll Footage & Image Search</span>
            </div>
            <button
              onClick={handleAutoMatch}
              disabled={isSearching}
              className="flex items-center gap-1 text-[10px] font-semibold bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 border border-cyan-500/40 px-2 py-1 rounded transition-colors"
              title="Automatically search internet for visuals matching spoken dialogue"
            >
              <Zap className="h-3 w-3 text-cyan-400" />
              {isSearching ? 'Matching...' : '⚡ Match Dialogue'}
            </button>
          </div>

          {/* Topic Quick Presets */}
          <div>
            <span className="text-[10px] font-mono text-neutral-400 block mb-1.5">QUICK TOPIC PRESETS</span>
            <div className="flex flex-wrap gap-1.5">
              {TOPIC_PRESETS.map((preset) => (
                <button
                  key={preset.name}
                  onClick={() => handleApplyPreset(preset)}
                  className="text-[10px] bg-neutral-800 hover:bg-purple-950/60 hover:border-purple-500/50 border border-neutral-700 text-neutral-300 hover:text-white px-2 py-1 rounded-md transition-colors"
                >
                  {preset.name}
                </button>
              ))}
            </div>
          </div>

          {/* Search Input */}
          <div className="space-y-1.5">
            <span className="text-[10px] font-mono text-neutral-400 block">SEARCH FOOTAGE / IMAGES (WIKIMEDIA & ARCHIVES)</span>
            <div className="flex gap-1.5">
              <div className="relative flex-1">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder="e.g., cancer cell, lungs, cardiology..."
                  className="w-full bg-neutral-950 border border-neutral-700 rounded-lg pl-7 pr-2 py-1.5 text-xs text-white placeholder-neutral-500 outline-none focus:border-cyan-500"
                />
                <Search className="h-3.5 w-3.5 text-neutral-400 absolute left-2 top-2" />
              </div>
              <button
                onClick={() => handleSearch()}
                disabled={isSearching}
                className="bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-medium text-xs px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1"
              >
                {isSearching ? <RefreshCw className="h-3 w-3 animate-spin" /> : 'Search'}
              </button>
            </div>

            {/* Media Type Filter */}
            <div className="flex items-center gap-2 pt-1 text-[10px]">
              <span className="text-neutral-400 font-mono">TYPE:</span>
              {(['image', 'video', 'all'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => {
                    setMediaTypeFilter(t);
                    if (searchQuery) handleSearch();
                  }}
                  className={`px-2 py-0.5 rounded capitalize ${
                    mediaTypeFilter === t
                      ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40'
                      : 'text-neutral-400 hover:text-white'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* Search Results Gallery */}
          {searchResults.length > 0 && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-[10px] text-neutral-400 font-mono">
                <span>FOUND {searchResults.length} RESULTS (CLICK TO APPLY)</span>
              </div>
              <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto pr-1">
                {searchResults.map((item, idx) => {
                  const isSelected = activeMediaUrl === item.url;
                  return (
                    <div
                      key={idx}
                      onClick={() => handleApplyMedia(item)}
                      className={`group relative rounded-lg overflow-hidden border cursor-pointer transition-all bg-neutral-950 ${
                        isSelected
                          ? 'border-cyan-400 ring-2 ring-cyan-500/30 shadow-lg'
                          : 'border-neutral-800 hover:border-purple-500/60'
                      }`}
                    >
                      <div className="aspect-video bg-neutral-900 relative overflow-hidden">
                        {item.thumb_url ? (
                          <img
                            src={item.thumb_url}
                            alt={item.title}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            loading="lazy"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-neutral-600">
                            <ImageIcon className="h-6 w-6" />
                          </div>
                        )}
                        <span className="absolute bottom-1 right-1 text-[8px] font-mono px-1 py-0.5 rounded bg-black/70 text-neutral-300 uppercase">
                          {item.media_type === 'video' ? 'VID' : 'IMG'}
                        </span>
                        {isSelected && (
                          <div className="absolute top-1 right-1 bg-cyan-500 text-black p-0.5 rounded-full">
                            <Check className="h-3 w-3 stroke-[3]" />
                          </div>
                        )}
                      </div>
                      <div className="p-1.5">
                        <div className="text-[10px] text-neutral-200 font-medium truncate" title={item.title}>
                          {item.title}
                        </div>
                        <div className="text-[8px] text-neutral-500 truncate" title={item.source_credit}>
                          {item.source_credit}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Direct Custom Media URL Input */}
          <div className="space-y-1 pt-1 border-t border-neutral-800/80">
            <span className="text-[10px] font-mono text-neutral-400 block">CUSTOM IMAGE / VIDEO URL</span>
            <input
              type="text"
              value={activeMediaUrl}
              onChange={(e) => {
                setActiveMediaUrl(e.target.value);
                handleApplyMedia({ url: e.target.value });
              }}
              placeholder="Paste direct .mp4, .webm, or image URL..."
              className="w-full bg-neutral-950 border border-neutral-700 rounded-lg p-2 text-xs text-white font-mono outline-none focus:border-cyan-500"
            />
          </div>

          {/* Current Media Preview Badge */}
          {activeMediaUrl && (
            <div className="flex items-center gap-2 p-2 bg-neutral-950/80 rounded-lg border border-neutral-800">
              <div className="w-12 h-8 bg-neutral-900 rounded overflow-hidden flex-shrink-0 flex items-center justify-center border border-neutral-700">
                {graphic.parameters?.media_type === 'video' && !activeMediaUrl.includes('images.unsplash.com') && !activeMediaUrl.match(/\.(jpg|jpeg|png|webp)(\?.*)?$/i) ? (
                  <video
                    src={activeMediaUrl}
                    className="w-full h-full object-cover"
                    muted
                    onError={(e) => {
                      const target = e.currentTarget;
                      target.style.display = 'none';
                      const parent = target.parentElement;
                      if (parent && !parent.querySelector('img')) {
                        const img = document.createElement('img');
                        img.src = activeMediaUrl;
                        img.className = 'w-full h-full object-cover';
                        parent.appendChild(img);
                      }
                    }}
                  />
                ) : (
                  <img src={activeMediaUrl} alt="Active Media" className="w-full h-full object-cover" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[10px] font-semibold text-cyan-300 truncate">ACTIVE B-ROLL VISUAL</div>
                <div className="text-[9px] text-neutral-400 truncate">{activeMediaUrl}</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 2. Article Reconstruction Editor (Screenshot 5) OR B-Roll Text Overlays */}
      {graphic.template_id === 'article_reconstruction' ? (
        <div className="bg-neutral-900/80 p-3 rounded-xl border border-amber-500/30 space-y-3">
          <div className="font-bold text-xs text-amber-300 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-amber-400" />
              <span>Article Reconstruction (Screenshot 5)</span>
            </span>
            <span className="text-[9px] font-mono text-amber-400 bg-amber-950 px-1.5 py-0.5 rounded border border-amber-800/60">
              Track V4
            </span>
          </div>

          {/* Presentation Layout Selector */}
          <div>
            <label className="block text-[10px] font-mono text-neutral-400 uppercase mb-1">
              Article Presentation Layout
            </label>
            <div className="grid grid-cols-3 gap-1 bg-neutral-800 p-1 rounded-lg border border-neutral-700">
              {[
                { id: 'top_split', label: 'Top 50% Split' },
                { id: 'full_page', label: 'Full Page' },
                { id: 'card', label: 'Floating Card' }
              ].map((l) => (
                <button
                  key={l.id}
                  onClick={() => updateParam('article_layout', l.id)}
                  className={`py-1 text-[10px] font-mono font-bold rounded transition text-center ${
                    (graphic.parameters?.article_layout || 'card') === l.id
                      ? 'bg-amber-500 text-black shadow font-black'
                      : 'text-neutral-400 hover:text-white'
                  }`}
                >
                  {l.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-[10px] font-mono text-neutral-400 uppercase mb-1">
                Publisher Masthead
              </label>
              <input
                type="text"
                value={graphic.parameters?.publisher ?? 'Scroll.in'}
                onChange={(e) => updateParam('publisher', e.target.value)}
                placeholder="e.g. Scroll.in, NEJM"
                className="w-full bg-neutral-800 border border-neutral-700 rounded-lg p-2 text-xs text-white outline-none focus:border-amber-400 font-semibold"
              />
            </div>
            <div>
              <label className="block text-[10px] font-mono text-neutral-400 uppercase mb-1">
                Publication Date
              </label>
              <input
                type="text"
                value={graphic.parameters?.date ?? 'May 14, 2024'}
                onChange={(e) => updateParam('date', e.target.value)}
                placeholder="e.g. May 14, 2024"
                className="w-full bg-neutral-800 border border-neutral-700 rounded-lg p-2 text-xs text-white outline-none focus:border-amber-400 font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-[10px] font-mono text-neutral-400 uppercase mb-1">
              Article Headline
            </label>
            <textarea
              value={graphic.parameters?.headline ?? ''}
              onChange={(e) => {
                updateParam('headline', e.target.value);
                onUpdateGraphic({ ...graphic, title: e.target.value });
              }}
              rows={2}
              placeholder="Article headline..."
              className="w-full bg-neutral-800 border border-neutral-700 rounded-lg p-2 text-xs text-white outline-none focus:border-amber-400 font-serif resize-none"
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono text-neutral-400 uppercase mb-1">
              Context Body Paragraph
            </label>
            <textarea
              value={graphic.parameters?.paragraph ?? ''}
              onChange={(e) => updateParam('paragraph', e.target.value)}
              rows={3}
              placeholder="Full paragraph from article..."
              className="w-full bg-neutral-800 border border-neutral-700 rounded-lg p-2 text-[11px] text-neutral-300 outline-none focus:border-amber-400 font-serif resize-none"
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono text-cyan-400 uppercase mb-1">
              Highlighted Evidentiary Quote (Sweeps in sync with playhead)
            </label>
            <input
              type="text"
              value={graphic.parameters?.highlight_quote ?? ''}
              onChange={(e) => updateParam('highlight_quote', e.target.value)}
              placeholder="Exact sentence or quote to highlight..."
              className="w-full bg-neutral-800 border border-cyan-500/60 rounded-lg p-2 text-xs text-cyan-200 outline-none focus:border-cyan-400 font-serif"
            />
          </div>

          {/* Marker Color & Paper Theme */}
          <div className="flex items-center justify-between pt-1 border-t border-neutral-800 text-[10px] font-mono">
            <div className="flex items-center gap-1.5">
              <span className="text-neutral-400">Marker:</span>
              {[
                { hex: '#00E5FF', label: 'Cyan' },
                { hex: '#FFE600', label: 'Yellow' },
                { hex: '#CCFF00', label: 'Lime' },
                { hex: '#FF2A85', label: 'Pink' }
              ].map((c) => (
                <button
                  key={c.hex}
                  onClick={() => updateParam('marker_color', c.hex)}
                  style={{ backgroundColor: c.hex }}
                  title={c.label}
                  className={`w-4 h-4 rounded-full transition ${
                    (graphic.parameters?.marker_color || '#00E5FF') === c.hex ? 'ring-2 ring-white scale-110' : 'opacity-60 hover:opacity-100'
                  }`}
                />
              ))}
            </div>

            <div className="flex items-center gap-1">
              <span className="text-neutral-400">Theme:</span>
              <button
                onClick={() => updateParam('paper_theme', graphic.parameters?.paper_theme === 'dark_archival' ? 'editorial_clean' : 'dark_archival')}
                className="px-2 py-0.5 rounded bg-neutral-800 hover:bg-neutral-700 text-neutral-200 border border-neutral-700"
              >
                {graphic.parameters?.paper_theme === 'dark_archival' ? 'Dark' : 'Light Paper'}
              </button>
            </div>
          </div>

          {/* Screenshot 5 Underneath Callout Badge (e.g. "resigned.") */}
          <div>
            <label className="block text-[10px] font-mono text-neutral-400 uppercase mb-1">
              Keyword Callout Pill (Underneath Card)
            </label>
            <input
              type="text"
              value={graphic.parameters?.callout_badge ?? ''}
              onChange={(e) => updateParam('callout_badge', e.target.value)}
              placeholder="e.g. resigned. or arrested."
              className="w-full bg-neutral-800 border border-neutral-700 rounded-lg p-1.5 text-xs text-white font-mono outline-none focus:border-lime"
            />
          </div>

          {/* Archival Source Link / Citation URL */}
          <div>
            <label className="block text-[10px] font-mono text-neutral-400 uppercase mb-1">
              Archival Source URL / Verification Link
            </label>
            <input
              type="text"
              value={graphic.parameters?.source_url ?? ''}
              onChange={(e) => updateParam('source_url', e.target.value)}
              placeholder="e.g. scroll.in/article/1067823/hospital-assault"
              className="w-full bg-neutral-800 border border-neutral-700 rounded-lg p-1.5 text-xs text-cyan-300 font-mono outline-none focus:border-cyan-400"
            />
          </div>
        </div>
      ) : (
        <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 space-y-3">
          <div className="font-bold text-xs text-white flex items-center gap-1.5">
            <span>Header, Subtitle & Documentary Citation</span>
          </div>

          <div>
            <label className="block text-[10px] font-mono text-neutral-400 uppercase mb-1">
              B-Roll Header Title
            </label>
            <input
              type="text"
              value={graphic.parameters?.broll_title ?? graphic.title}
              onChange={(e) => {
                updateParam('broll_title', e.target.value);
                onUpdateGraphic({ ...graphic, title: e.target.value });
              }}
              placeholder="e.g. CLINICAL ONCOLOGY or CELL DIVISION"
              className="w-full bg-neutral-800 border border-neutral-700 rounded-lg p-2 text-xs text-white outline-none focus:border-purple-500 font-semibold"
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono text-neutral-400 uppercase mb-1">
              Subtitle / Context Details
            </label>
            <input
              type="text"
              value={graphic.parameters?.broll_subtitle ?? ''}
              onChange={(e) => updateParam('broll_subtitle', e.target.value)}
              placeholder="e.g. Microscopic Cell Structure Analysis"
              className="w-full bg-neutral-800 border border-neutral-700 rounded-lg p-2 text-xs text-white outline-none focus:border-purple-500"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-[10px] font-mono text-neutral-400 uppercase">
                Top-Left Source Citation
              </label>
              <span className="text-[9px] text-cyan-400 font-mono">NON-OVERLAPPING</span>
            </div>
            <input
              type="text"
              value={graphic.parameters?.source_citation ?? 'Source: Clinical Archives'}
              onChange={(e) => updateParam('source_citation', e.target.value)}
              placeholder="e.g. Source - Wikimedia Commons / NIH"
              className="w-full bg-neutral-800 border border-neutral-700 rounded-lg p-2 text-xs text-white outline-none focus:border-cyan-500"
            />
            <p className="text-[9px] text-neutral-500 mt-1">
              Anchored safely at top-left with truncation to avoid overlapping top-right badge.
            </p>
          </div>

          {/* Badge Display Toggles (Requirement 4: Direct ON/OFF controls) */}
          <div className="pt-2 border-t border-neutral-800 space-y-2">
            <span className="text-[10px] font-mono text-neutral-400 uppercase block">Documentary Badges Visibility</span>
            
            <div className="flex items-center justify-between bg-neutral-850 p-2 rounded-lg border border-neutral-750">
              <div>
                <div className="text-[11px] font-bold text-white">Source Citation Badge</div>
                <div className="text-[9px] text-neutral-400 font-mono">Top-left archival credit pill</div>
              </div>
              <button
                onClick={() => updateParam('show_source_badge', graphic.parameters?.show_source_badge === false ? true : false)}
                className={`px-2.5 py-1 rounded text-[10px] font-mono font-bold transition ${
                  graphic.parameters?.show_source_badge !== false
                    ? 'bg-lime text-black shadow'
                    : 'bg-neutral-800 text-neutral-400 hover:text-white'
                }`}
              >
                {graphic.parameters?.show_source_badge !== false ? 'ON' : 'OFF'}
              </button>
            </div>

            <div className="flex items-center justify-between bg-neutral-850 p-2 rounded-lg border border-neutral-750">
              <div>
                <div className="text-[11px] font-bold text-white">Topic Headline Pill</div>
                <div className="text-[9px] text-neutral-400 font-mono">Bottom-left documentary topic pill</div>
              </div>
              <button
                onClick={() => updateParam('show_title_badge', graphic.parameters?.show_title_badge === false ? true : false)}
                className={`px-2.5 py-1 rounded text-[10px] font-mono font-bold transition ${
                  graphic.parameters?.show_title_badge !== false
                    ? 'bg-lime text-black shadow'
                    : 'bg-neutral-800 text-neutral-400 hover:text-white'
                }`}
              >
                {graphic.parameters?.show_title_badge !== false ? 'ON' : 'OFF'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Additional Dynamic Template Parameters */}
      <div className="bg-neutral-900/80 p-3 rounded-xl border border-neutral-800 space-y-3">
        <div className="font-bold text-xs text-white">Other Template Parameters</div>
        {Object.entries(graphic.parameters)
          .filter(
            ([key]) =>
              !['broll_title', 'broll_subtitle', 'source_citation', 'media_url', 'media_type', 'publisher', 'headline', 'paragraph', 'highlight_quote', 'marker_color', 'callout_badge', 'paper_theme', 'track', 'placement_mode', 'animation', 'split_layout'].includes(key)
          )
          .map(([key, val]) => (
            <div key={key}>
              <span className="text-[10px] font-mono text-neutral-400 block uppercase mb-1">{key}</span>
              {typeof val === 'string' && val.startsWith('#') ? (
                <div className="flex items-center gap-2 bg-neutral-800 p-1.5 rounded-lg border border-neutral-700">
                  <input
                    type="color"
                    value={val}
                    onChange={(e) => updateParam(key, e.target.value)}
                    className="w-5 h-5 rounded cursor-pointer bg-transparent border-0"
                  />
                  <span className="font-mono text-[11px] uppercase">{val}</span>
                </div>
              ) : typeof val === 'string' && val.length > 40 ? (
                <textarea
                  value={val}
                  onChange={(e) => updateParam(key, e.target.value)}
                  rows={3}
                  className="w-full bg-neutral-800 border border-neutral-700 rounded-lg p-2 text-xs text-white outline-none resize-none"
                />
              ) : typeof val === 'boolean' ? (
                <button
                  onClick={() => updateParam(key, !val)}
                  className={`px-3 py-1 rounded text-xs font-mono ${
                    val ? 'bg-purple-600 text-white' : 'bg-neutral-800 text-neutral-400'
                  }`}
                >
                  {val ? 'TRUE' : 'FALSE'}
                </button>
              ) : (
                <input
                  type="text"
                  value={String(val)}
                  onChange={(e) => updateParam(key, e.target.value)}
                  className="w-full bg-neutral-800 border border-neutral-700 rounded-lg p-1.5 text-xs text-white outline-none"
                />
              )}
            </div>
          ))}
      </div>
    </div>
  );
};
