import React, { useState, useMemo, useEffect } from 'react';
import { 
  Layers, Plus, Trash2, Sliders, Search, Sparkles, 
  ExternalLink, Video, Clock, LayoutGrid, Brain, RefreshCw, Eye,
  Image as ImageIcon, Upload, Wand2, Loader2, Check, ArrowRight, Type
} from 'lucide-react';
import { ProjectState, MotionGraphicItem, GraphicTemplate } from '../../types';
import { AIMotionGraphicsPanel } from './AIMotionGraphicsPanel';
import { api } from '../../services/api';

interface GraphicsTabInspectorProps {
  project: ProjectState;
  selectedGraphicId: string | null;
  onSelectGraphic: (id: string | null) => void;
  onUpdateGraphic: (updated: MotionGraphicItem) => void;
  onDeleteGraphic: (id: string) => void;
  onAddGraphic: (templateId: string, params: Record<string, any>, start?: number, end?: number, title?: string) => void;
  currentTime: number;
  onTimeSeek: (time: number) => void;
  templates: GraphicTemplate[];
  onOpenReasoningLog?: () => void;
  hasReasoningLog?: boolean;
  onAppendVideoTrack?: (videoUrl: string, title: string, duration: number, overlayText: string, instructions: string, sourceCitation?: string) => void;
  captureCurrentCanvasFrame?: () => string | null;
  prefilledOmni?: { prompt: string; cameraMotion: string; headline: string } | null;
  onUpdateProject?: (updated: ProjectState) => void;
}

const TEMPLATE_PRESETS = [
  {
    id: 'split_screen_vertical',
    name: '50/50 Vertical Split',
    desc: 'Dual-panel presentation for evidence & speaker',
    defaultParams: {
      split_ratio: 0.5,
      divider_color: '#FFFFFF'
    }
  },
  {
    id: 'article_reconstruction',
    name: 'Article / Report',
    desc: '100% full-screen clean white report document',
    defaultParams: {
      publisher: 'Clinical Research Archive',
      headline: 'Documentary Evidence & Findings',
      marker_color: '#00E5FF',
      show_highlight: true,
      paragraph: 'The speaker lists clinical and evidentiary documentation confirming findings across historical investigations.'
    }
  },
  {
    id: 'youtube_insert',
    name: 'Cutaway Insert',
    desc: 'Full screen B-roll visual cutaway without text badges',
    defaultParams: {
      animation: 'slow_zoom_in'
    }
  },
  {
    id: 'dimension_callout',
    name: 'Dimension Callout',
    desc: 'Measurement callout marker (e.g. 7 CM, Stage 1)',
    defaultParams: {
      measurement_text: '7 CM',
      subtext: 'Tumor Diameter',
      line_orientation: 'horizontal',
      line_length_pct: 65,
      color: '#38BDF8'
    }
  },
  {
    id: 'stat_counter',
    name: 'Stat Counter',
    desc: 'Animated statistical metric badge',
    defaultParams: {
      stat_number: '74%',
      label: 'Detection Accuracy',
      prefix: '',
      suffix: '%'
    }
  }
];

export const GraphicsTabInspector: React.FC<GraphicsTabInspectorProps> = ({
  project,
  selectedGraphicId,
  onSelectGraphic,
  onUpdateGraphic,
  onDeleteGraphic,
  onAddGraphic,
  currentTime = 0,
  onTimeSeek,
  templates,
  onOpenReasoningLog,
  hasReasoningLog = false,
  onAppendVideoTrack,
  captureCurrentCanvasFrame,
  prefilledOmni,
  onUpdateProject
}) => {
  const [subTab, setSubTab] = useState<'inspector' | 'broll' | 'library' | 'ai_video'>('inspector');

  // Media Density / Coverage State
  const [coverageData, setCoverageData] = useState<{
    total_duration: number;
    covered_duration: number;
    coverage_ratio: number;
    coverage_percentage: number;
    media_count: number;
    gaps: Array<{ start: number; end: number; duration: number }>;
  } | null>(null);
  const [isMaximizingDensity, setIsMaximizingDensity] = useState(false);
  const [densitySuccessMessage, setDensitySuccessMessage] = useState<string | null>(null);

  const fetchCoverage = async () => {
    try {
      const data = await api.getMediaCoverage(project.id);
      if (data) setCoverageData(data);
    } catch (e) {
      console.warn('Failed to fetch coverage:', e);
    }
  };

  useEffect(() => {
    fetchCoverage();
  }, [project.id, project.graphics.length]);

  const handleMaximizeDensity = async () => {
    setIsMaximizingDensity(true);
    setDensitySuccessMessage(null);
    try {
      const res = await api.maximizeMediaDensity(project.id);
      if (res?.message) setDensitySuccessMessage(res.message);
      if (res && res.success) {
        setDensitySuccessMessage(`B-Roll coverage boosted to ${res.new_coverage}% (+${res.added_count} visual cutaways)!`);
        if (onUpdateProject) {
          const fresh = await api.getProject(project.id);
          if (fresh) onUpdateProject(fresh);
        }
        await fetchCoverage();
      }
    } catch (e: any) {
      console.error('Failed to maximize density:', e);
    } finally {
      setIsMaximizingDensity(false);
    }
  };

  // B-Roll / Stock Search State (Pexels, Pixabay, Wikimedia)
  const [brollSearchQuery, setBrollSearchQuery] = useState('');
  const [brollMediaType, setBrollMediaType] = useState<'image' | 'video'>('image');
  const [brollProvider, setBrollProvider] = useState<'all' | 'pexels' | 'pixabay' | 'wikimedia'>('all');
  const [brollOrientation, setBrollOrientation] = useState<'all' | 'portrait' | 'landscape'>('all');
  const [isSearchingBroll, setIsSearchingBroll] = useState(false);
  const [brollResults, setBrollResults] = useState<any[]>([]);
  const [isUploadingAsset, setIsUploadingAsset] = useState(false);
  const [downloadingItemId, setDownloadingItemId] = useState<string | null>(null);

  // Editorial Calibration / Feedback State
  const [feedbackStatus, setFeedbackStatus] = useState<Record<string, 'keep' | 'cut' | 'swap'>>({});
  const [editorNotes, setEditorNotes] = useState<Record<string, string>>({});
  const [isLoggingFeedback, setIsLoggingFeedback] = useState(false);

  // Batch Title Typography & Color Sync State
  const [syncAllTitles, setSyncAllTitles] = useState(false);
  const [batchSyncSuccess, setBatchSyncSuccess] = useState(false);
  // Title Text Editing Mode: 'lines' (Detailed line cards) | 'full' (Multi-line textarea)
  const [titleTextEditMode, setTitleTextEditMode] = useState<'lines' | 'full'>('lines');

  // Active Graphic Resolution
  const selectedGraphic = useMemo(() => {
    if (selectedGraphicId) {
      const found = project.graphics.find((g) => g.id === selectedGraphicId);
      if (found) return found;
    }
    const underPlayhead = project.graphics.find((g) => currentTime >= g.start && currentTime <= g.end);
    if (underPlayhead) return underPlayhead;
    return project.graphics[0] || null;
  }, [project.graphics, selectedGraphicId, currentTime]);

  const handleGraphicFeedback = async (graphic: MotionGraphicItem, decision: 'keep' | 'cut' | 'swap') => {
    setIsLoggingFeedback(true);
    setFeedbackStatus(prev => ({ ...prev, [graphic.id]: decision }));
    try {
      const note = editorNotes[graphic.id] || '';
      await api.logDecision({
        project_id: project.id,
        cue_id: graphic.id,
        decision: decision,
        reasoning: graphic.parameters?.rationale || `Editor marked ${decision} on ${graphic.title}`,
        strength: 0.9,
        graphic_type: graphic.template_id,
        start_sec: graphic.start,
        end_sec: graphic.end,
        search_query: graphic.parameters?.search_query || graphic.title,
        transcript_context: graphic.parameters?.display_text || graphic.title,
        selected_asset: { url: graphic.media_url },
        editor_notes: note
      });
      if (decision === 'cut') {
        onDeleteGraphic(graphic.id);
      }
    } catch (e) {
      console.error('Failed to log feedback from inspector:', e);
    } finally {
      setIsLoggingFeedback(false);
    }
  };

  // Update selected graphic parameter
  const updateParam = (key: string, value: any) => {
    if (!selectedGraphic) return;
    const updated: MotionGraphicItem = {
      ...selectedGraphic,
      parameters: {
        ...(selectedGraphic.parameters || {}),
        [key]: value
      }
    };
    onUpdateGraphic(updated);
  };

  // Title Customization & Batch Sync
  const handleUpdateTitleFont = (fontFamily: string) => {
    if (!selectedGraphic) return;
    const existingLines = Array.isArray(selectedGraphic.parameters?.title_lines)
      ? selectedGraphic.parameters.title_lines
      : selectedTitleLines;

    const lines = existingLines.map((l: any, i: number) => {
      const isPrimary = (existingLines.length >= 3 && !existingLines[0]?.text) ? i === 1 : i === 0;
      return isPrimary ? { ...l, font_family: fontFamily } : l;
    });

    onUpdateGraphic({
      ...selectedGraphic,
      parameters: {
        ...(selectedGraphic.parameters || {}),
        font_family: fontFamily,
        title_lines: lines,
      },
    });

    if (syncAllTitles) {
      applyToAllTitles({ font_family: fontFamily });
    }
  };

  const handleUpdateSecondaryTitleFont = (fontFamily: string) => {
    if (!selectedGraphic) return;
    const existingLines = Array.isArray(selectedGraphic.parameters?.title_lines)
      ? selectedGraphic.parameters.title_lines
      : selectedTitleLines;

    const scriptIdx = existingLines.length > 2 ? 2 : 1;
    const lines = existingLines.map((l: any, i: number) => {
      return i === scriptIdx ? { ...l, font_family: fontFamily } : l;
    });

    onUpdateGraphic({
      ...selectedGraphic,
      parameters: {
        ...(selectedGraphic.parameters || {}),
        script_font_family: fontFamily,
        secondary_font_family: fontFamily,
        title_lines: lines,
      },
    });

    if (syncAllTitles) {
      applyToAllTitles({ script_font_family: fontFamily, secondary_font_family: fontFamily });
    }
  };

  const handleUpdateTitleLineFont = (index: number, fontFamily: string) => {
    if (!selectedGraphic) return;
    const lines = [...selectedTitleLines];
    if (index >= 0 && index < lines.length) {
      lines[index] = { ...lines[index], font_family: fontFamily };
    } else {
      lines.push({ text: '', offset: index * 0.25, font_family: fontFamily });
    }

    const updatedParams: Record<string, any> = {
      ...(selectedGraphic.parameters || {}),
      title_lines: lines,
    };
    if (index === 0) {
      updatedParams.font_family = fontFamily;
    } else if (index === 1 && lines.length === 2) {
      updatedParams.script_font_family = fontFamily;
      updatedParams.secondary_font_family = fontFamily;
    } else if (index === 2) {
      updatedParams.script_font_family = fontFamily;
      updatedParams.secondary_font_family = fontFamily;
    }

    onUpdateGraphic({
      ...selectedGraphic,
      parameters: updatedParams,
    });
  };

  const handleUpdateTitleLineColor = (index: number, color: string) => {
    if (!selectedGraphic) return;
    const lines = [...selectedTitleLines];
    if (index >= 0 && index < lines.length) {
      lines[index] = { ...lines[index], color: color };
    } else {
      lines.push({ text: '', offset: index * 0.25, color: color });
    }

    const updatedParams: Record<string, any> = {
      ...(selectedGraphic.parameters || {}),
      title_lines: lines,
    };
    if (index === 0) {
      updatedParams.primary_color = color;
    } else {
      updatedParams.accent_color = color;
    }

    onUpdateGraphic({
      ...selectedGraphic,
      parameters: updatedParams,
    });
  };

  const handleUpdatePrimaryColor = (color: string) => {
    if (!selectedGraphic) return;
    const existingLines = Array.isArray(selectedGraphic.parameters?.title_lines)
      ? selectedGraphic.parameters.title_lines
      : selectedTitleLines;

    const lines = existingLines.map((l: any, i: number) => {
      const isPrimary = (existingLines.length >= 3 && !existingLines[0]?.text) ? i === 1 : i === 0;
      return isPrimary ? { ...l, color: color } : l;
    });

    onUpdateGraphic({
      ...selectedGraphic,
      parameters: {
        ...(selectedGraphic.parameters || {}),
        primary_color: color,
        title_lines: lines,
      },
    });

    if (syncAllTitles) {
      applyToAllTitles({ primary_color: color });
    }
  };

  const handleUpdateAccentColor = (color: string) => {
    if (!selectedGraphic) return;
    const existingLines = Array.isArray(selectedGraphic.parameters?.title_lines)
      ? selectedGraphic.parameters.title_lines
      : selectedTitleLines;

    const scriptIdx = existingLines.length > 2 ? 2 : 1;
    const lines = existingLines.map((l: any, i: number) => {
      return i === scriptIdx ? { ...l, color: color } : l;
    });

    onUpdateGraphic({
      ...selectedGraphic,
      parameters: {
        ...(selectedGraphic.parameters || {}),
        accent_color: color,
        title_lines: lines,
      },
    });

    if (syncAllTitles) {
      applyToAllTitles({ accent_color: color });
    }
  };

  const applyToAllTitles = async (overrideParams?: Record<string, any>) => {
    if (!selectedGraphic) return;
    const font = overrideParams?.font_family ?? selectedGraphic.parameters?.font_family ?? 'Montserrat, sans-serif';
    const scriptFont = overrideParams?.script_font_family ?? selectedGraphic.parameters?.script_font_family ?? selectedGraphic.parameters?.secondary_font_family ?? 'Caveat, cursive';
    const primary = overrideParams?.primary_color ?? selectedGraphic.parameters?.primary_color ?? '#FFFFFF';
    const accent = overrideParams?.accent_color ?? selectedGraphic.parameters?.accent_color ?? '#FBBF24';

    const updatedGraphics = project.graphics.map((g) => {
      if (g.template_id === 'kinetic_typography') {
        const existingLines = Array.isArray(g.parameters?.title_lines) ? [...g.parameters.title_lines] : [];
        const updatedLines = existingLines.map((l: any, idx: number) => {
          const isScript = existingLines.length > 2 ? idx === 2 : idx === 1;
          return {
            ...l,
            font_family: isScript ? scriptFont : font,
            color: idx === 0 ? primary : accent,
          };
        });

        return {
          ...g,
          parameters: {
            ...(g.parameters || {}),
            font_family: font,
            script_font_family: scriptFont,
            secondary_font_family: scriptFont,
            primary_color: primary,
            accent_color: accent,
            ...(updatedLines.length > 0 ? { title_lines: updatedLines } : {}),
          },
        };
      }
      return g;
    });

    if (onUpdateProject) {
      onUpdateProject({ ...project, graphics: updatedGraphics });
    }
    try {
      await api.saveProject(project.id, { ...project, graphics: updatedGraphics });
      setBatchSyncSuccess(true);
      setTimeout(() => setBatchSyncSuccess(false), 2500);
    } catch (e) {
      console.warn('Failed to save batch titles to backend:', e);
    }
  };

  // Extend Title Duration & Sync Spoken Words
  const handleExtendTitleDuration = (extraSeconds: number, fitSentence: boolean = false) => {
    if (!selectedGraphic) return;
    let newEnd = selectedGraphic.end + extraSeconds;
    if (fitSentence && project.captions && project.captions.length > 0) {
      const matchingCap = project.captions.find(
        (c) => c.end >= selectedGraphic.end && c.start <= selectedGraphic.end + 5.0
      );
      if (matchingCap) {
        newEnd = Math.max(selectedGraphic.end + 1.0, matchingCap.end);
      } else {
        newEnd = selectedGraphic.end + 2.0;
      }
    }
    newEnd = Math.min(project.duration_seconds || 120, Math.round(newEnd * 100) / 100);

    const spokenWords: Array<{ text: string; start: number; end: number; offset: number; duration: number }> = [];
    if (project.captions) {
      project.captions.forEach((c) => {
        if (c.words && Array.isArray(c.words)) {
          c.words.forEach((w: any) => {
            if (w.start >= selectedGraphic.start - 0.15 && w.end <= newEnd + 0.3) {
              spokenWords.push({
                text: String(w.word || '').trim(),
                start: w.start,
                end: w.end,
                offset: Math.max(0, Math.round((w.start - selectedGraphic.start) * 100) / 100),
                duration: Math.max(0.15, Math.round((w.end - w.start) * 100) / 100),
              });
            }
          });
        }
      });
    }

    const newHeadline =
      spokenWords.length > 0
        ? spokenWords.map((w) => w.text).join(' ')
        : selectedGraphic.parameters?.headline || selectedGraphic.title;

    onUpdateGraphic({
      ...selectedGraphic,
      end: newEnd,
      title: newHeadline,
      parameters: {
        ...(selectedGraphic.parameters || {}),
        headline: newHeadline,
        timed_words: spokenWords.length > 0 ? spokenWords : selectedGraphic.parameters?.timed_words,
        title_lines: [{ text: newHeadline, offset: 0 }],
      },
    });
  };

  // Title Text Editing & Multi-Line Helpers
  const selectedTitleLines = useMemo(() => {
    if (!selectedGraphic) return [];
    if (Array.isArray(selectedGraphic.parameters?.title_lines) && selectedGraphic.parameters.title_lines.length > 0) {
      return selectedGraphic.parameters.title_lines;
    }
    const raw = String(selectedGraphic.parameters?.headline || selectedGraphic.title || '').trim();
    if (!raw) return [{ text: '', offset: 0 }];
    const split = raw.split(/\n+/).filter(Boolean);
    if (split.length > 1) {
      return split.map((s, i) => ({ text: s.trim(), offset: i * 0.25 }));
    }
    return [{ text: raw, offset: 0 }];
  }, [selectedGraphic?.parameters?.title_lines, selectedGraphic?.parameters?.headline, selectedGraphic?.title]);

  const handleUpdateTitleLine = (index: number, newText: string) => {
    if (!selectedGraphic) return;
    const lines = [...selectedTitleLines];
    if (index >= 0 && index < lines.length) {
      lines[index] = { ...lines[index], text: newText };
    } else {
      lines.push({ text: newText, offset: index * 0.25 });
    }

    const fullHeadline = lines.map((l) => l.text).filter(Boolean).join(' ');
    const subtitle = lines.length > 1 ? lines.slice(1).map((l) => l.text).join(' ') : (selectedGraphic.parameters?.subtitle || '');

    // Synchronize timed_words
    const words = fullHeadline.split(/\s+/).filter(Boolean);
    const existingTimed = selectedGraphic.parameters?.timed_words || [];
    const updatedTimedWords = words.map((w, idx) => {
      const clean = w.toLowerCase().replace(/[^a-z0-9]/g, '');
      const matched = existingTimed.find((tw: any) => String(tw.text).toLowerCase().replace(/[^a-z0-9]/g, '') === clean);
      return matched || {
        text: w,
        start: selectedGraphic.start + idx * 0.25,
        end: selectedGraphic.start + (idx + 1) * 0.25,
        offset: idx * 0.25,
        duration: 0.25,
      };
    });

    onUpdateGraphic({
      ...selectedGraphic,
      title: fullHeadline || selectedGraphic.title,
      parameters: {
        ...(selectedGraphic.parameters || {}),
        headline: fullHeadline,
        subtitle: subtitle,
        title_lines: lines,
        timed_words: updatedTimedWords,
      },
    });
  };

  const handleAddTitleLine = () => {
    if (!selectedGraphic) return;
    const nextOffset = selectedTitleLines.length * 0.25;
    const lines = [...selectedTitleLines, { text: '', offset: nextOffset }];
    onUpdateGraphic({
      ...selectedGraphic,
      parameters: {
        ...(selectedGraphic.parameters || {}),
        title_lines: lines,
      },
    });
  };

  const handleDeleteTitleLine = (indexToDelete: number) => {
    if (!selectedGraphic || selectedTitleLines.length <= 1) return;
    const lines = selectedTitleLines.filter((_, idx) => idx !== indexToDelete);
    const fullHeadline = lines.map((l) => l.text).join(' ');
    onUpdateGraphic({
      ...selectedGraphic,
      title: fullHeadline || selectedGraphic.title,
      parameters: {
        ...(selectedGraphic.parameters || {}),
        headline: fullHeadline,
        title_lines: lines,
      },
    });
  };

  const handleUpdateFullTitleText = (fullText: string) => {
    if (!selectedGraphic) return;
    const lineStrings = fullText.split('\n');
    const lines = lineStrings.map((str, idx) => ({
      text: str,
      offset: idx * 0.25,
    }));
    const fullHeadline = lineStrings.join(' ');
    const subtitle = lineStrings.length > 1 ? lineStrings.slice(1).join(' ') : '';

    onUpdateGraphic({
      ...selectedGraphic,
      title: fullHeadline || selectedGraphic.title,
      parameters: {
        ...(selectedGraphic.parameters || {}),
        headline: fullHeadline,
        subtitle: subtitle,
        title_lines: lines,
      },
    });
  };

  const handleAutoSplitTitleLines = () => {
    if (!selectedGraphic) return;
    const style = String(selectedGraphic.parameters?.title_style || 'rise');
    const fullText = String(selectedGraphic.parameters?.headline || selectedGraphic.title || '').trim();
    const words = fullText.split(/\s+/).filter(Boolean);
    if (words.length <= 1) return;

    let groups: string[] = [];
    if (style === 'staircase') {
      groups = words;
    } else if (style === 'cards_broll' || style === 'behind_subject') {
      if (words.length >= 3) {
        const third = Math.ceil(words.length / 3);
        groups = [
          words.slice(0, third).join(' '),
          words.slice(third, third * 2).join(' '),
          words.slice(third * 2).join(' '),
        ];
      } else {
        groups = [words[0], words.slice(1).join(' ')];
      }
    } else if (style === 'cooked_badge') {
      groups = [words[0], words.slice(1).join(' ')];
    } else {
      const half = Math.ceil(words.length / 2);
      groups = [words.slice(0, half).join(' '), words.slice(half).join(' ')];
    }

    const lines = groups.filter(Boolean).map((text, idx) => ({
      text,
      offset: idx * 0.25,
    }));

    onUpdateGraphic({
      ...selectedGraphic,
      parameters: {
        ...(selectedGraphic.parameters || {}),
        title_lines: lines,
      },
    });
  };

  const getLineRoleLabel = (style: string, index: number, total: number) => {
    if (style === 'dual') {
      if (index === 0) return { name: 'Line 1: Primary Text', tag: 'Bold Sans', badgeColor: 'bg-neutral-200 text-neutral-800' };
      if (index === 1) return { name: 'Line 2: Script Text', tag: 'Red Cursive Script', badgeColor: 'bg-rose-100 text-rose-700' };
    }
    if (style === 'cards_broll') {
      if (index === 0) return { name: 'Line 1: Top Tag', tag: 'Clean Sans', badgeColor: 'bg-blue-100 text-blue-700' };
      if (index === 1) return { name: 'Line 2: Mid Subject', tag: 'Bold Uppercase', badgeColor: 'bg-neutral-200 text-neutral-800' };
      if (index === 2) return { name: 'Line 3: Bottom Script', tag: 'Golden Cursive', badgeColor: 'bg-amber-100 text-amber-800' };
    }
    if (style === 'behind_subject') {
      if (index === 0) return { name: 'Line 1: Backdrop Upper', tag: 'Behind Speaker', badgeColor: 'bg-purple-100 text-purple-700' };
      if (index === 1) return { name: 'Line 2: Backdrop Lower', tag: 'Behind Speaker', badgeColor: 'bg-purple-100 text-purple-700' };
      if (index === 2) return { name: 'Line 3: Cursive Accent', tag: 'Foreground Script', badgeColor: 'bg-amber-100 text-amber-800' };
    }
    if (style === 'cooked_badge') {
      if (index === 0) return { name: 'Line 1: Cursive Header', tag: 'Large Red Script', badgeColor: 'bg-rose-100 text-rose-700' };
      if (index === 1) return { name: 'Line 2: Pill Badges', tag: 'Space-separated tags', badgeColor: 'bg-neutral-800 text-white' };
    }
    if (style === 'rise' || style === 'corner_pill') {
      if (index === 0) return { name: 'Line 1: Top Stack', tag: 'Bold Sans', badgeColor: 'bg-neutral-200 text-neutral-800' };
      if (index === 1) return { name: 'Line 2: Bottom Stack', tag: 'Bold Sans', badgeColor: 'bg-neutral-200 text-neutral-800' };
    }
    if (style === 'paper' || style === 'torn_paper') {
      if (index === 0) return { name: 'Line 1: Paper Text', tag: 'Serif Headline', badgeColor: 'bg-amber-100 text-amber-800' };
      if (index === 1) return { name: 'Line 2: Badge Text', tag: 'Cyan Badge Pill', badgeColor: 'bg-cyan-100 text-cyan-800' };
    }
    if (style === 'staircase' || style === 'silhouette_curve') {
      return { name: `Arc Step ${index + 1}`, tag: 'Halo Body Arch', badgeColor: 'bg-amber-100 text-amber-700' };
    }
    if (style === 'typewriter') {
      return { name: 'Typewriter Text', tag: 'Monospace Type', badgeColor: 'bg-stone-100 text-stone-800' };
    }
    if (style === 'bold_pop') {
      return { name: 'Cyber Grid Title', tag: 'Massive Uppercase', badgeColor: 'bg-cyan-100 text-cyan-700' };
    }
    if (style === 'flame_subject') {
      return { name: 'Fire Handwriting', tag: 'Caveat Cursive', badgeColor: 'bg-orange-100 text-orange-700' };
    }
    if (style === 'script') {
      return { name: 'Calligraphy Line', tag: 'Pure White Cursive', badgeColor: 'bg-indigo-100 text-indigo-700' };
    }
    return { name: `Line ${index + 1}`, tag: 'Text Line', badgeColor: 'bg-neutral-100 text-neutral-700' };
  };

  // Media Framing & Pan/Zoom
  const handleUpdateMediaFraming = (x: number, y: number, s: number) => {
    if (!selectedGraphic) return;
    onUpdateGraphic({
      ...selectedGraphic,
      pos_x: x,
      pos_y: y,
      scale: s,
      parameters: {
        ...(selectedGraphic.parameters || {}),
        media_pos_x: x,
        media_pos_y: y,
        media_scale: s,
        pos_x: x,
        pos_y: y,
        object_position: `${Math.round(x * 100)}% ${Math.round(y * 100)}%`,
      },
    });
  };


  // Add Template Preset
  const handleAddTemplate = (preset: typeof TEMPLATE_PRESETS[0]) => {
    const startT = Math.round(currentTime * 100) / 100;
    const isReport = preset.id === 'article_reconstruction' || preset.id === 'digital_highlighter';
    const dur = isReport ? 5.0 : 1.0;
    const endT = Math.min(project.duration_seconds || 60, Math.round((startT + dur) * 100) / 100);
    onAddGraphic(preset.id, preset.defaultParams, startT, endT, preset.name);
    setSubTab('inspector');
  };

  // Search Media (Pexels / Pixabay / Wikimedia)
  const handleBrollSearch = async (
    query = brollSearchQuery,
    type = brollMediaType,
    provider = brollProvider,
    orientation = brollOrientation
  ) => {
    const q = query.trim() || 'medical hospital research';
    setIsSearchingBroll(true);
    try {
      const res = await api.searchMedia(q, type, provider, orientation);
      if (res && res.results) {
        setBrollResults(res.results);
      }
    } catch (e) {
      console.error('B-roll search failed:', e);
    } finally {
      setIsSearchingBroll(false);
    }
  };

  // Upload Local File
  const handleAssetUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploadingAsset(true);
    try {
      const res = await api.uploadAsset(project.id, file);
      if (res && res.media_url) {
        if (selectedGraphic) {
          onUpdateGraphic({
            ...selectedGraphic,
            media_url: res.media_url,
            parameters: {
              ...(selectedGraphic.parameters || {}),
              media_url: res.media_url,
              media_type: file.type.startsWith('video/') ? 'video' : 'image'
            }
          });
          setSubTab('inspector');
        } else {
          onAddGraphic(
            'youtube_insert',
            { media_url: res.media_url, media_type: file.type.startsWith('video/') ? 'video' : 'image' },
            currentTime,
            Math.min(project.duration_seconds || 60, currentTime + 1.0),
            file.name
          );
          setSubTab('inspector');
        }
      }
    } catch (err: any) {
      alert('Upload failed: ' + (err.message || String(err)));
    } finally {
      setIsUploadingAsset(false);
      e.target.value = '';
    }
  };

  // Ensure downloaded asset for offline burnin
  const ensureDownloadedAsset = async (item: any): Promise<string> => {
    const currentUrl = item.download_url || item.url || item.media_url;
    if (currentUrl && (currentUrl.includes('/asset/downloaded/') || currentUrl.includes('/asset/'))) {
      return currentUrl;
    }
    const itemKey = item.id || item.url || String(Date.now());
    setDownloadingItemId(itemKey);
    try {
      const res = await api.downloadAsset(project.id, item);
      if (res && res.media_url) {
        item.media_url = res.media_url;
        item.local_path = res.local_path;
        return res.media_url;
      }
    } catch (e: any) {
      console.warn('Asset download warning, fallback to direct url:', e);
    } finally {
      setDownloadingItemId(null);
    }
    return currentUrl;
  };

  // Apply selected stock media to the current graphic
  const handleApplyMediaToSelected = async (item: any) => {
    const localUrl = await ensureDownloadedAsset(item);
    if (selectedGraphic) {
      onUpdateGraphic({
        ...selectedGraphic,
        media_url: localUrl,
        parameters: {
          ...(selectedGraphic.parameters || {}),
          media_url: localUrl,
          media_type: item.media_type || 'image'
        }
      });
      setSubTab('inspector');
    }
  };

  // Quick initial load of stock images on opening broll tab
  useEffect(() => {
    if (subTab === 'broll' && brollResults.length === 0) {
      handleBrollSearch('medical research');
    }
  }, [subTab]);

  return (
    <div className="flex flex-col h-full bg-white text-neutral-900 select-none overflow-y-auto">
      {/* 4 Top Header Tabs */}
      <div className="p-2.5 border-b border-neutral-200 bg-neutral-50 space-y-2">
        <div className="flex rounded-lg bg-neutral-200/80 p-0.5 text-xs font-medium">
          <button
            type="button"
            onClick={() => setSubTab('inspector')}
            className={`flex-1 py-1.5 rounded-md transition text-xs font-semibold ${
              subTab === 'inspector'
                ? 'bg-white text-neutral-900 shadow-2xs font-bold'
                : 'text-neutral-600 hover:text-neutral-900'
            }`}
          >
            Editor
          </button>
          <button
            type="button"
            onClick={() => setSubTab('broll')}
            className={`flex-1 py-1.5 rounded-md transition text-xs font-semibold flex items-center justify-center gap-1 ${
              subTab === 'broll'
                ? 'bg-white text-neutral-900 shadow-2xs font-bold'
                : 'text-neutral-600 hover:text-neutral-900'
            }`}
          >
            <ImageIcon className="w-3 h-3" />
            <span>Stock / B-Roll</span>
            {coverageData && (
              <span className={`text-[9px] px-1 py-0.2 rounded font-mono font-bold ${
                coverageData.coverage_percentage >= 80 
                  ? 'bg-emerald-100 text-emerald-800' 
                  : 'bg-amber-100 text-amber-800'
              }`}>
                {coverageData.coverage_percentage}%
              </span>
            )}
          </button>
          <button
            type="button"
            onClick={() => setSubTab('library')}
            className={`flex-1 py-1.5 rounded-md transition text-xs font-semibold ${
              subTab === 'library'
                ? 'bg-white text-neutral-900 shadow-2xs font-bold'
                : 'text-neutral-600 hover:text-neutral-900'
            }`}
          >
            Presets
          </button>
          <button
            type="button"
            onClick={() => setSubTab('ai_video')}
            className={`flex-1 py-1.5 rounded-md transition text-xs font-semibold flex items-center justify-center gap-1 ${
              subTab === 'ai_video'
                ? 'bg-white text-neutral-900 shadow-2xs font-bold'
                : 'text-neutral-600 hover:text-neutral-900'
            }`}
          >
            <Sparkles className="w-3 h-3" />
            <span>AI Video</span>
          </button>
        </div>

        {/* Graphic Selector Dropdown when in Editor */}
        {subTab === 'inspector' && project.graphics.length > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider shrink-0">Item:</span>
            <select
              value={selectedGraphic?.id || ''}
              onChange={(e) => {
                const targetId = e.target.value;
                onSelectGraphic(targetId);
                const g = project.graphics.find((x) => x.id === targetId);
                if (g) onTimeSeek(g.start);
              }}
              className="flex-1 bg-white border border-neutral-300 rounded-md px-2 py-1 text-xs text-neutral-900 font-medium outline-none truncate shadow-xs cursor-pointer"
            >
              {project.graphics.map((g, idx) => (
                <option key={g.id} value={g.id}>
                  #{idx + 1} {g.title} ({g.start.toFixed(1)}s - {g.end.toFixed(1)}s) [{g.track || 'V4'}]
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Main Tab Content */}
      <div className="flex-1 p-3 overflow-y-auto">
        {/* TAB 1: GRAPHIC EDITOR */}
        {subTab === 'inspector' ? (
          selectedGraphic ? (
            <div className="space-y-4">
              {/* Header: Title & Timing */}
              <div className="p-3 bg-neutral-50 border border-neutral-200 rounded-xl space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="font-bold text-sm text-neutral-900 truncate max-w-[240px]">
                    {selectedGraphic.title}
                  </div>
                  <button
                    type="button"
                    onClick={() => onDeleteGraphic(selectedGraphic.id)}
                    className="p-1 hover:bg-red-50 text-neutral-400 hover:text-red-600 rounded transition"
                    title="Delete graphic"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-neutral-500 mb-0.5 block">Start Time (s)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={selectedGraphic.start}
                      onChange={(e) => onUpdateGraphic({ ...selectedGraphic, start: parseFloat(e.target.value) || 0 })}
                      className="w-full bg-white border border-neutral-300 rounded-lg p-1.5 text-xs text-neutral-900 font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-neutral-500 mb-0.5 block">End Time (s)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={selectedGraphic.end}
                      onChange={(e) => onUpdateGraphic({ ...selectedGraphic, end: parseFloat(e.target.value) || 0 })}
                      className="w-full bg-white border border-neutral-300 rounded-lg p-1.5 text-xs text-neutral-900 font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* EDITORIAL FEEDBACK & AI MEMORY CARD */}
              <div className="p-3 bg-gradient-to-br from-indigo-50/60 to-neutral-50 border border-indigo-100 rounded-xl space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-neutral-800">
                    <Brain className="w-3.5 h-3.5 text-indigo-600" />
                    Editorial Feedback & Calibration
                  </div>
                  {feedbackStatus[selectedGraphic.id] && (
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                      feedbackStatus[selectedGraphic.id] === 'keep' 
                        ? 'bg-emerald-100 text-emerald-800' 
                        : feedbackStatus[selectedGraphic.id] === 'cut'
                        ? 'bg-rose-100 text-rose-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}>
                      {feedbackStatus[selectedGraphic.id]}
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-neutral-500 leading-tight">
                  Calibrate AI decisions. "Keep" locks this visual against auto-replacement. "Cut" removes it and blacklists the media.
                </p>
                <div className="flex items-center gap-2 pt-1">
                  <button
                    type="button"
                    disabled={isLoggingFeedback}
                    onClick={() => handleGraphicFeedback(selectedGraphic, 'keep')}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg text-xs font-medium border transition ${
                      feedbackStatus[selectedGraphic.id] === 'keep'
                        ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                        : 'bg-white hover:bg-emerald-50 text-emerald-700 border-emerald-200'
                    }`}
                  >
                    <Check className="w-3.5 h-3.5" />
                    Keep & Protect
                  </button>
                  <button
                    type="button"
                    disabled={isLoggingFeedback}
                    onClick={() => handleGraphicFeedback(selectedGraphic, 'cut')}
                    className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg text-xs font-medium border transition ${
                      feedbackStatus[selectedGraphic.id] === 'cut'
                        ? 'bg-rose-600 text-white border-rose-600 shadow-sm'
                        : 'bg-white hover:bg-rose-50 text-rose-700 border-rose-200'
                    }`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    Cut & Blacklist
                  </button>
                  <button
                    type="button"
                    onClick={() => setSubTab('broll')}
                    className="flex items-center justify-center gap-1 py-1.5 px-2.5 rounded-lg text-xs font-medium bg-white hover:bg-neutral-100 text-neutral-700 border border-neutral-200 transition"
                    title="Swap asset via media search"
                  >
                    <RefreshCw className="w-3.5 h-3.5 text-neutral-500" />
                    Swap
                  </button>
                </div>
                <div className="pt-1">
                  <input
                    type="text"
                    placeholder="Editor note for next iteration (e.g. 'More dynamic motion')..."
                    value={editorNotes[selectedGraphic.id] || ''}
                    onChange={(e) => setEditorNotes({ ...editorNotes, [selectedGraphic.id]: e.target.value })}
                    className="w-full bg-white border border-neutral-200 rounded-lg px-2.5 py-1 text-[11px] text-neutral-800 placeholder-neutral-400 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              {/* KINETIC TYPOGRAPHY / TITLE HOOK ANIMATION PANEL */}
              {selectedGraphic.template_id === 'kinetic_typography' && (
                <div className="space-y-3 p-3.5 bg-neutral-50 border border-neutral-200 rounded-xl">
                  <div className="text-xs font-bold text-neutral-900 flex items-center justify-between pb-1 border-b border-neutral-200">
                    <span>Title / Hook Animation Style</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-100 text-purple-700 font-bold">
                      {String(selectedGraphic.parameters?.title_style || 'rise').toUpperCase()}
                    </span>
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[10px] font-medium text-neutral-600 block">Style Preset</label>
                    <select
                      value={String(selectedGraphic.parameters?.title_style || 'rise')}
                      onChange={(e) => {
                        const style = e.target.value;
                        const words = String(selectedGraphic.parameters?.headline || selectedGraphic.title).split(/\s+/).filter(Boolean);
                        const split = Math.max(1, Math.ceil(words.length / 2));
                        const groups = style === 'staircase' ? words : style === 'cooked_badge' ? [words[0], words.slice(1).join(' ')] : ['dual', 'behind_subject', 'rise', 'paper'].includes(style) ? [words.slice(0, split).join(' '), words.slice(split).join(' ')] : [words.join(' ')];
                        let index = 0;
                        const lines = groups.filter(Boolean).map((text) => {
                          const offset = selectedGraphic.parameters?.timed_words?.[index]?.offset ?? index * 0.18;
                          index += text.split(/\s+/).length;
                          return { text, offset };
                        });
                        onUpdateGraphic({
                          ...selectedGraphic,
                          pos_y: style === 'behind_subject' && selectedGraphic.pos_y === 0.5 ? 0.19 : selectedGraphic.pos_y,
                          parameters: {
                            ...(selectedGraphic.parameters || {}),
                            title_style: style,
                            title_lines: lines,
                            editorial_generated: true
                          }
                        });
                      }}
                      className="w-full bg-white border border-neutral-300 rounded-lg p-2 text-xs text-neutral-900 font-semibold outline-none focus:border-neutral-900"
                    >
                      <option value="dual">1. Dual Font (Sans + Red Cursive Script)</option>
                      <option value="flame_subject">2. Flame Aura (Fiery Glow + Handwriting)</option>
                      <option value="script">3. Elegant Script (Pure White Calligraphy)</option>
                      <option value="cards_broll">4. Cards B-Roll (Floating Mini-Cards)</option>
                      <option value="behind_subject">5. Behind Subject (Bold Backdrop + Script)</option>
                      <option value="rise">6. Stacked Sans / Corner (Minimalist Bold)</option>
                      <option value="paper">7. Torn Paper (Jagged Edge + Cyan Badge)</option>
                      <option value="typewriter">8. Typewriter (Monospace + Blinking Cursor)</option>
                      <option value="bold_pop">9. Bold Pop / Grid (Cyber Grid + Arrow)</option>
                      <option value="staircase">10. Silhouette Curve (Horseshoe Arch)</option>
                      <option value="cooked_badge">11. Expressive Red Script + Pill Badges</option>
                      {selectedGraphic.parameters?.stat_cards && <option value="stat_pair">Stat Pair (India · Each Year)</option>}
                    </select>
                  </div>

                  {/* TEXT CONTENT & MULTI-LINE EDITOR */}
                  <div className="space-y-2.5 pt-2 border-t border-neutral-200/60">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <Type className="w-3.5 h-3.5 text-neutral-700" />
                        <label className="text-xs font-bold text-neutral-900">
                          Hook / Title Text Content
                        </label>
                      </div>

                      {/* Mode Switch: Line-by-Line vs Full Text */}
                      <div className="flex items-center bg-neutral-200/70 p-0.5 rounded-lg text-[10px] font-semibold">
                        <button
                          type="button"
                          onClick={() => setTitleTextEditMode('lines')}
                          className={`px-2 py-0.5 rounded-md transition ${
                            titleTextEditMode === 'lines'
                              ? 'bg-white text-neutral-900 shadow-2xs font-bold'
                              : 'text-neutral-600 hover:text-neutral-900'
                          }`}
                        >
                          Line by Line
                        </button>
                        <button
                          type="button"
                          onClick={() => setTitleTextEditMode('full')}
                          className={`px-2 py-0.5 rounded-md transition ${
                            titleTextEditMode === 'full'
                              ? 'bg-white text-neutral-900 shadow-2xs font-bold'
                              : 'text-neutral-600 hover:text-neutral-900'
                          }`}
                        >
                          Full Text
                        </button>
                      </div>
                    </div>

                    {titleTextEditMode === 'full' ? (
                      /* FULL MULTI-LINE TEXTAREA */
                      <div className="space-y-1.5">
                        <textarea
                          rows={Math.max(2, Math.min(6, selectedTitleLines.length + 1))}
                          value={selectedTitleLines.map((l: any) => l.text).join('\n')}
                          onChange={(e) => handleUpdateFullTitleText(e.target.value)}
                          placeholder="Type or paste title text (each new line becomes a styled row)..."
                          className="w-full bg-white border border-neutral-300 rounded-lg p-2.5 text-xs text-neutral-900 font-semibold outline-none focus:border-neutral-900 resize-y leading-relaxed"
                        />
                        <div className="flex items-center justify-between text-[10px] text-neutral-500">
                          <span>Press Enter to create a new line</span>
                          <button
                            type="button"
                            onClick={handleAutoSplitTitleLines}
                            className="text-indigo-600 hover:text-indigo-800 font-semibold cursor-pointer"
                          >
                            Auto-split for {String(selectedGraphic.parameters?.title_style || 'style')}
                          </button>
                        </div>
                      </div>
                    ) : (
                      /* LINE BY LINE DETAILED EDITOR */
                      <div className="space-y-2">
                        {selectedTitleLines.map((line: any, idx: number) => {
                          const style = String(selectedGraphic.parameters?.title_style || 'rise');
                          const role = getLineRoleLabel(style, idx, selectedTitleLines.length);

                          return (
                            <div
                              key={idx}
                              className="p-2.5 bg-white border border-neutral-200/90 rounded-lg space-y-2 shadow-2xs group hover:border-neutral-300 transition"
                            >
                              <div className="flex items-center justify-between text-[10px]">
                                <div className="flex items-center gap-1.5">
                                  <span className={`px-1.5 py-0.5 rounded font-mono font-bold text-[9px] ${role.badgeColor}`}>
                                    {role.name}
                                  </span>
                                  <span className="text-neutral-500 font-medium">{role.tag}</span>
                                </div>

                                <div className="flex items-center gap-1.5">
                                  {/* Timing offset chip */}
                                  <span className="text-neutral-400 font-mono text-[9px]">
                                    +{Number(line.offset || 0).toFixed(2)}s
                                  </span>
                                  {selectedTitleLines.length > 1 && (
                                    <button
                                      type="button"
                                      onClick={() => handleDeleteTitleLine(idx)}
                                      className="p-1 text-neutral-400 hover:text-red-600 hover:bg-red-50 rounded transition cursor-pointer"
                                      title="Delete line"
                                    >
                                      <Trash2 className="w-3 h-3" />
                                    </button>
                                  )}
                                </div>
                              </div>

                              <input
                                type="text"
                                value={line.text || ''}
                                onChange={(e) => handleUpdateTitleLine(idx, e.target.value)}
                                placeholder={`Enter text for ${role.name}...`}
                                className="w-full bg-neutral-50 hover:bg-white focus:bg-white border border-neutral-200 rounded-md px-2 py-1.5 text-xs text-neutral-900 font-bold outline-none focus:border-neutral-900 transition"
                              />

                              {/* Per-Line Independent Font and Color Controls */}
                              {(() => {
                                const isScriptLine = (selectedTitleLines.length > 2 && idx === 2) || (selectedTitleLines.length <= 2 && idx === 1 && (style === 'dual' || style === 'cards_broll' || style === 'cooked_badge'));
                                const currentLineFont = line.font_family || (isScriptLine ? (selectedGraphic.parameters?.script_font_family || selectedGraphic.parameters?.secondary_font_family || 'Caveat, cursive') : (selectedGraphic.parameters?.font_family || 'Montserrat, sans-serif'));
                                const currentLineColor = line.color || (isScriptLine ? (selectedGraphic.parameters?.accent_color || '#FBBF24') : (selectedGraphic.parameters?.primary_color || '#FFFFFF'));

                                return (
                                  <div className="grid grid-cols-2 gap-2 pt-1 border-t border-neutral-100 items-center">
                                    <div>
                                      <label className="text-[9px] font-semibold text-neutral-500 uppercase tracking-wider block mb-0.5">
                                        Line Font
                                      </label>
                                      <select
                                        value={currentLineFont}
                                        onChange={(e) => handleUpdateTitleLineFont(idx, e.target.value)}
                                        className="w-full bg-neutral-50 border border-neutral-200 rounded px-1.5 py-1 text-[11px] font-semibold text-neutral-800 outline-none focus:border-neutral-900"
                                      >
                                        <option value="Montserrat, sans-serif">Montserrat Black</option>
                                        <option value="Caveat, cursive">Caveat (Cursive)</option>
                                        <option value='"Snell Roundhand", "Caveat", "Dancing Script", cursive'>Snell Roundhand</option>
                                        <option value="Playfair Display, serif">Playfair Serif</option>
                                        <option value="Anton, Impact, sans-serif">Anton / Impact</option>
                                        <option value="Inter, sans-serif">Inter Clean</option>
                                        <option value="Cinzel, serif">Cinzel Cinematic</option>
                                        <option value="Bebas Neue, sans-serif">Bebas Neue Bold</option>
                                        <option value="Oswald, sans-serif">Oswald Bold</option>
                                      </select>
                                    </div>
                                    <div>
                                      <label className="text-[9px] font-semibold text-neutral-500 uppercase tracking-wider block mb-0.5">
                                        Line Color
                                      </label>
                                      <div className="flex items-center gap-1.5">
                                        <input
                                          type="color"
                                          value={currentLineColor}
                                          onChange={(e) => handleUpdateTitleLineColor(idx, e.target.value)}
                                          className="w-6 h-6 rounded border border-neutral-200 cursor-pointer p-0.5 bg-white shrink-0"
                                        />
                                        <span className="text-[10px] font-mono font-semibold text-neutral-600 truncate uppercase">
                                          {currentLineColor}
                                        </span>
                                      </div>
                                    </div>
                                  </div>
                                );
                              })()}
                            </div>
                          );
                        })}

                        {/* Line Actions: Add Line & Auto-Split */}
                        <div className="flex items-center gap-1.5 pt-1">
                          <button
                            type="button"
                            onClick={handleAddTitleLine}
                            className="flex-1 flex items-center justify-center gap-1 py-1 px-2 rounded-md bg-white hover:bg-neutral-100 border border-neutral-300 text-neutral-700 text-[11px] font-semibold shadow-2xs transition cursor-pointer"
                          >
                            <Plus className="w-3 h-3 text-neutral-500" />
                            <span>Add Line</span>
                          </button>
                          <button
                            type="button"
                            onClick={handleAutoSplitTitleLines}
                            className="flex items-center justify-center gap-1 py-1 px-2.5 rounded-md bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 text-[11px] font-semibold shadow-2xs transition cursor-pointer"
                            title="Auto-split headline into balanced lines based on title style"
                          >
                            <span>Auto-Split</span>
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* INDEPENDENT TYPOGRAPHY / FONT FAMILY SELECTION */}
                  <div className="space-y-2.5 pt-2 border-t border-neutral-200/60">
                    <div className="flex items-center justify-between">
                      <label className="text-[10px] font-bold text-neutral-700 block">Typography Fonts</label>
                      <span className="text-[9px] font-semibold text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-100">
                        Independent Font Controls
                      </span>
                    </div>

                    {/* Line 1 / Primary Font */}
                    <div className="space-y-1">
                      <label className="text-[10px] font-medium text-neutral-600 block">
                        Line 1 / Primary Font (Main Headline)
                      </label>
                      <select
                        value={selectedGraphic.parameters?.font_family || 'Montserrat, sans-serif'}
                        onChange={(e) => handleUpdateTitleFont(e.target.value)}
                        className="w-full bg-white border border-neutral-300 rounded-lg p-2 text-xs text-neutral-900 font-semibold outline-none focus:border-neutral-900"
                      >
                        <option value="Montserrat, sans-serif">Montserrat Black (Bold Editorial)</option>
                        <option value="Playfair Display, serif">Playfair Display (Serif Elegance)</option>
                        <option value="Anton, Impact, sans-serif">Anton / Impact (Punchy Condensed)</option>
                        <option value="Inter, sans-serif">Inter (Modern Swiss Minimal)</option>
                        <option value="Caveat, cursive">Caveat (Handwriting Cursive)</option>
                        <option value='"Snell Roundhand", "Caveat", "Dancing Script", cursive'>Snell Roundhand (Calligraphy Script)</option>
                        <option value="Cinzel, serif">Cinzel (Cinematic Drama)</option>
                        <option value="Bebas Neue, sans-serif">Bebas Neue (Tall Condensed Bold)</option>
                        <option value="Oswald, sans-serif">Oswald (Modern Bold)</option>
                      </select>
                    </div>

                    {/* Line 2 / Script Font */}
                    <div className="space-y-1">
                      <label className="text-[10px] font-medium text-neutral-600 block">
                        Line 2 / Script Font (Accent / Cursive)
                      </label>
                      <select
                        value={
                          selectedGraphic.parameters?.script_font_family ||
                          selectedGraphic.parameters?.secondary_font_family ||
                          'Caveat, cursive'
                        }
                        onChange={(e) => handleUpdateSecondaryTitleFont(e.target.value)}
                        className="w-full bg-white border border-neutral-300 rounded-lg p-2 text-xs text-neutral-900 font-semibold outline-none focus:border-neutral-900"
                      >
                        <option value="Caveat, cursive">Caveat (Handwriting Cursive)</option>
                        <option value='"Snell Roundhand", "Caveat", "Dancing Script", cursive'>Snell Roundhand (Calligraphy Script)</option>
                        <option value="Montserrat, sans-serif">Montserrat Black (Bold Editorial)</option>
                        <option value="Playfair Display, serif">Playfair Display (Serif Elegance)</option>
                        <option value="Anton, Impact, sans-serif">Anton / Impact (Punchy Condensed)</option>
                        <option value="Inter, sans-serif">Inter (Modern Swiss Minimal)</option>
                        <option value="Cinzel, serif">Cinzel (Cinematic Drama)</option>
                        <option value="Bebas Neue, sans-serif">Bebas Neue (Tall Condensed Bold)</option>
                        <option value="Oswald, sans-serif">Oswald (Modern Bold)</option>
                      </select>
                    </div>
                  </div>

                  {/* PRIMARY TEXT COLOR */}
                  <div className="space-y-1.5 pt-2 border-t border-neutral-200/60">
                    <div className="flex items-center justify-between">
                      <label className="text-[10px] font-medium text-neutral-600">Primary Color</label>
                      <span className="text-[10px] font-mono text-neutral-500 uppercase">{selectedGraphic.parameters?.primary_color || '#FFFFFF'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="color"
                        value={selectedGraphic.parameters?.primary_color || '#FFFFFF'}
                        onChange={(e) => handleUpdatePrimaryColor(e.target.value)}
                        className="w-8 h-8 rounded border border-neutral-300 cursor-pointer p-0.5 bg-white shrink-0"
                      />
                      <div className="flex flex-wrap gap-1.5">
                        {['#FFFFFF', '#FFE600', '#F43F5E', '#00E5FF', '#38BDF8', '#A3E635', '#18181B'].map((c) => (
                          <button
                            key={c}
                            type="button"
                            onClick={() => handleUpdatePrimaryColor(c)}
                            style={{ backgroundColor: c }}
                            className={`w-6 h-6 rounded-md border shadow-xs transition-transform hover:scale-110 ${
                              (selectedGraphic.parameters?.primary_color || '#FFFFFF').toUpperCase() === c ? 'ring-2 ring-indigo-500 ring-offset-1' : 'border-neutral-300'
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* ACCENT / HIGHLIGHT COLOR */}
                  <div className="space-y-1.5 pt-2 border-t border-neutral-200/60">
                    <div className="flex items-center justify-between">
                      <label className="text-[10px] font-medium text-neutral-600">Accent / Word Highlight Color</label>
                      <span className="text-[10px] font-mono text-neutral-500 uppercase">{selectedGraphic.parameters?.accent_color || '#FBBF24'}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="color"
                        value={selectedGraphic.parameters?.accent_color || '#FBBF24'}
                        onChange={(e) => handleUpdateAccentColor(e.target.value)}
                        className="w-8 h-8 rounded border border-neutral-300 cursor-pointer p-0.5 bg-white shrink-0"
                      />
                      <div className="flex flex-wrap gap-1.5">
                        {['#FBBF24', '#FFE600', '#EF4444', '#A3E635', '#38BDF8', '#EC4899', '#FFFFFF'].map((c) => (
                          <button
                            key={c}
                            type="button"
                            onClick={() => handleUpdateAccentColor(c)}
                            style={{ backgroundColor: c }}
                            className={`w-6 h-6 rounded-md border shadow-xs transition-transform hover:scale-110 ${
                              (selectedGraphic.parameters?.accent_color || '#FBBF24').toUpperCase() === c ? 'ring-2 ring-indigo-500 ring-offset-1' : 'border-neutral-300'
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* BATCH SYNC TO ALL TITLES */}
                  <div className="p-2.5 bg-indigo-50/70 border border-indigo-200/80 rounded-lg space-y-2">
                    <label className="flex items-center gap-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={syncAllTitles}
                        onChange={(e) => setSyncAllTitles(e.target.checked)}
                        className="rounded border-neutral-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="text-[11px] font-semibold text-neutral-800">
                        Auto-sync font & colors to all titles
                      </span>
                    </label>
                    <button
                      type="button"
                      onClick={() => applyToAllTitles()}
                      className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-xs transition cursor-pointer"
                    >
                      {batchSyncSuccess ? <Check className="w-3.5 h-3.5 text-emerald-200" /> : <Sparkles className="w-3.5 h-3.5 text-indigo-200" />}
                      <span>{batchSyncSuccess ? 'Applied to All Titles!' : 'Apply Font & Colors to All Titles'}</span>
                    </button>
                  </div>

                  {/* EXTEND DURATION & SYNC SPOKEN WORDS */}
                  <div className="space-y-2 pt-2 border-t border-neutral-200/60">
                    <label className="text-[10px] font-medium text-neutral-600 block">
                      Extend Duration & Spoken Words
                    </label>
                    <div className="grid grid-cols-4 gap-1.5">
                      <button
                        type="button"
                        onClick={() => handleExtendTitleDuration(1.0)}
                        className="py-1 px-2 rounded-md bg-white hover:bg-neutral-100 border border-neutral-300 text-neutral-800 text-[11px] font-bold shadow-2xs transition"
                      >
                        +1.0s
                      </button>
                      <button
                        type="button"
                        onClick={() => handleExtendTitleDuration(2.0)}
                        className="py-1 px-2 rounded-md bg-white hover:bg-neutral-100 border border-neutral-300 text-neutral-800 text-[11px] font-bold shadow-2xs transition"
                      >
                        +2.0s
                      </button>
                      <button
                        type="button"
                        onClick={() => handleExtendTitleDuration(3.0)}
                        className="py-1 px-2 rounded-md bg-white hover:bg-neutral-100 border border-neutral-300 text-neutral-800 text-[11px] font-bold shadow-2xs transition"
                      >
                        +3.0s
                      </button>
                      <button
                        type="button"
                        onClick={() => handleExtendTitleDuration(0, true)}
                        className="py-1 px-2 rounded-md bg-purple-50 hover:bg-purple-100 border border-purple-200 text-purple-700 text-[11px] font-bold shadow-2xs transition"
                        title="Extend to match spoken sentence end"
                      >
                        Fit Sent.
                      </button>
                    </div>
                    <p className="text-[10px] text-neutral-500 leading-tight">
                      Dynamically syncs verbatim spoken words from speech captions and highlights words in real-time.
                    </p>
                  </div>
                </div>
              )}

              {/* ARTICLE / REPORT CUSTOMIZATION PANEL */}
              {selectedGraphic.template_id === 'article_reconstruction' && (
                <div className="space-y-3 p-3.5 bg-neutral-50 border border-neutral-200 rounded-xl">
                  <div className="text-xs font-bold text-neutral-900 flex items-center justify-between pb-1 border-b border-neutral-200">
                    <span>Full-Screen Report Settings</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-neutral-200 text-neutral-700">
                      PURE WHITE
                    </span>
                  </div>

                  {/* 1. Publisher / Masthead Text & Optional Logo Upload */}
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-medium text-neutral-600 block">Publisher / Masthead</label>
                    <div className="flex items-center gap-1.5">
                      <input
                        type="text"
                        placeholder="Publisher (e.g. Science News, Research Archive)"
                        value={selectedGraphic.parameters?.publisher || ''}
                        onChange={(e) => updateParam('publisher', e.target.value)}
                        className="flex-1 bg-white border border-neutral-300 rounded-lg p-2 text-xs text-neutral-900 outline-none focus:border-neutral-900"
                      />
                      <label className="cursor-pointer px-2.5 py-2 rounded-lg bg-white hover:bg-neutral-100 border border-neutral-300 text-neutral-700 text-[10px] font-semibold flex items-center gap-1 shrink-0 transition shadow-xs">
                        <Upload className="w-3 h-3 text-cyan-600" />
                        <span>{selectedGraphic.parameters?.publisher_logo ? 'Change' : 'Logo (SVG/PNG)'}</span>
                        <input
                          type="file"
                          accept="image/*,.svg"
                          onChange={async (e) => {
                            const file = e.target.files?.[0];
                            if (!file) return;
                            try {
                              const res = await api.uploadAsset(project.id, file);
                              if (res && res.media_url) {
                                updateParam('publisher_logo', res.media_url);
                              }
                            } catch (err: any) {
                              alert('Logo upload failed: ' + String(err));
                            }
                          }}
                          className="hidden"
                        />
                      </label>
                      {selectedGraphic.parameters?.publisher_logo && (
                        <button
                          type="button"
                          onClick={() => updateParam('publisher_logo', null)}
                          className="p-2 rounded-lg text-neutral-400 hover:text-red-600 hover:bg-red-50 border border-neutral-200"
                          title="Remove Logo"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* 2. Headline Text & Size Slider */}
                  <div className="space-y-1.5 pt-2 border-t border-neutral-200/60">
                    <label className="text-[10px] font-medium text-neutral-600 block">Report Headline</label>
                    <input
                      type="text"
                      value={selectedGraphic.parameters?.headline || selectedGraphic.title || ''}
                      onChange={(e) => {
                        updateParam('headline', e.target.value);
                        onUpdateGraphic({ ...selectedGraphic, title: e.target.value });
                      }}
                      className="w-full bg-white border border-neutral-300 rounded-lg p-2 text-xs text-neutral-900 font-bold outline-none focus:border-neutral-900"
                    />
                    <div className="flex items-center justify-between text-[10px] text-neutral-500 pt-0.5">
                      <span>Headline Size: {selectedGraphic.parameters?.headline_size || 30}px</span>
                      <input
                        type="range"
                        min="18"
                        max="48"
                        step="2"
                        value={selectedGraphic.parameters?.headline_size || 30}
                        onChange={(e) => updateParam('headline_size', parseInt(e.target.value))}
                        className="w-32 accent-neutral-900 cursor-pointer"
                      />
                    </div>
                  </div>

                  {/* 3. Body Paragraph & Size Slider */}
                  <div className="space-y-1.5 pt-2 border-t border-neutral-200/60">
                    <label className="text-[10px] font-medium text-neutral-600 block">Body Paragraph / Findings</label>
                    <textarea
                      rows={3}
                      value={selectedGraphic.parameters?.paragraph || ''}
                      onChange={(e) => updateParam('paragraph', e.target.value)}
                      className="w-full bg-white border border-neutral-300 rounded-lg p-2 text-xs text-neutral-900 outline-none focus:border-neutral-900 resize-none font-serif"
                    />
                    <div className="flex items-center justify-between text-[10px] text-neutral-500 pt-0.5">
                      <span>Body Size: {selectedGraphic.parameters?.paragraph_size || 18}px</span>
                      <input
                        type="range"
                        min="12"
                        max="32"
                        step="1"
                        value={selectedGraphic.parameters?.paragraph_size || 18}
                        onChange={(e) => updateParam('paragraph_size', parseInt(e.target.value))}
                        className="w-32 accent-neutral-900 cursor-pointer"
                      />
                    </div>
                  </div>

                  {/* 4. Prominent Highlighter Sweep Toggle & Quote Input */}
                  <div className="space-y-2 pt-2 border-t border-neutral-200/60">
                    <div className="flex items-center justify-between p-2 bg-white border border-neutral-200 rounded-lg shadow-2xs">
                      <div>
                        <div className="text-xs font-bold text-neutral-900">Highlighter Sweep</div>
                        <div className="text-[10px] text-neutral-500">Animated kinetic marker wipe</div>
                      </div>
                      <button
                        type="button"
                        onClick={() => updateParam('show_highlight', selectedGraphic.parameters?.show_highlight === false ? true : false)}
                        className={`px-3 py-1 rounded-md text-xs font-bold transition ${
                          selectedGraphic.parameters?.show_highlight !== false
                            ? 'bg-neutral-900 text-white shadow-xs'
                            : 'bg-neutral-200 text-neutral-600'
                        }`}
                      >
                        {selectedGraphic.parameters?.show_highlight !== false ? 'ON' : 'OFF'}
                      </button>
                    </div>

                    <div>
                      <label className="text-[10px] font-medium text-neutral-600 mb-1 block">Text to Highlight</label>
                      <input
                        type="text"
                        placeholder="Type exact phrase from headline or paragraph to highlight..."
                        value={selectedGraphic.parameters?.highlight_quote || ''}
                        onChange={(e) => updateParam('highlight_quote', e.target.value)}
                        className="w-full bg-white border border-neutral-300 rounded-lg p-2 text-xs text-neutral-900 outline-none focus:border-neutral-900"
                      />
                    </div>

                    {/* Marker Color Selector */}
                    <div>
                      <label className="text-[10px] font-medium text-neutral-600 mb-1 block">Marker Color</label>
                      <div className="flex items-center gap-2">
                        {[
                          { name: 'Cyan', color: '#00E5FF' },
                          { name: 'Yellow', color: '#FFE600' },
                          { name: 'Lime', color: '#A3E635' },
                          { name: 'Pink', color: '#F43F5E' },
                          { name: 'Orange', color: '#FB923C' }
                        ].map((m) => (
                          <button
                            key={m.color}
                            type="button"
                            onClick={() => updateParam('marker_color', m.color)}
                            className={`flex-1 h-6 rounded border flex items-center justify-center transition-transform ${
                              (selectedGraphic.parameters?.marker_color || '#00E5FF').toLowerCase() === m.color.toLowerCase()
                                ? 'border-neutral-900 scale-105 shadow-xs ring-2 ring-neutral-900/30'
                                : 'border-neutral-200'
                            }`}
                            style={{ backgroundColor: m.color }}
                            title={m.name}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ATTACHED IMAGE / B-ROLL MEDIA CONTROLS */}
              <div className="space-y-2 p-3 bg-neutral-50 border border-neutral-200 rounded-xl">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-neutral-900">Attached Visual / Image</span>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => setSubTab('broll')}
                      className="text-[10px] font-semibold text-cyan-700 hover:text-cyan-800 bg-cyan-50 border border-cyan-200 px-2 py-0.5 rounded transition flex items-center gap-1"
                    >
                      <Search className="w-2.5 h-2.5" />
                      <span>Search Stock</span>
                    </button>
                    <label className="cursor-pointer text-[10px] font-semibold text-neutral-700 hover:text-neutral-900 bg-white border border-neutral-200 px-2 py-0.5 rounded transition flex items-center gap-1">
                      <Upload className="w-2.5 h-2.5" />
                      <span>Upload</span>
                      <input
                        type="file"
                        accept="image/*,video/*"
                        onChange={handleAssetUpload}
                        className="hidden"
                      />
                    </label>
                  </div>
                </div>

                <input
                  type="text"
                  placeholder="Paste URL or upload image above..."
                  value={selectedGraphic.media_url || selectedGraphic.parameters?.media_url || ''}
                  onChange={(e) => {
                    const url = e.target.value;
                    onUpdateGraphic({
                      ...selectedGraphic,
                      media_url: url,
                      parameters: {
                        ...(selectedGraphic.parameters || {}),
                        media_url: url
                      }
                    });
                  }}
                  className="w-full bg-white border border-neutral-300 rounded-lg p-2 text-xs text-neutral-900 font-mono outline-none focus:border-neutral-900"
                />

                {/* Show Figure Under Text Toggle & Remove */}
                {Boolean(selectedGraphic.media_url || selectedGraphic.parameters?.media_url) && (
                  <div className="space-y-2 mt-2 pt-2 border-t border-neutral-200">
                    <div className="flex items-center justify-between p-2 bg-white border border-neutral-200 rounded-lg">
                      <div>
                        <div className="text-xs font-semibold text-neutral-800">Show Figure Under Text</div>
                        <div className="text-[10px] text-neutral-500">Render illustration neatly below paragraph</div>
                      </div>
                      <button
                        type="button"
                        onClick={() => updateParam('show_image', selectedGraphic.parameters?.show_image === false ? true : false)}
                        className={`px-3 py-1 rounded-md text-xs font-bold transition cursor-pointer ${
                          selectedGraphic.parameters?.show_image !== false ? 'bg-neutral-900 text-white' : 'bg-neutral-200 text-neutral-600'
                        }`}
                      >
                        {selectedGraphic.parameters?.show_image !== false ? 'ON' : 'OFF'}
                      </button>
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        onUpdateGraphic({
                          ...selectedGraphic,
                          media_url: undefined,
                          parameters: {
                            ...(selectedGraphic.parameters || {}),
                            media_url: undefined,
                            show_image: false,
                            show_full_page_image: false
                          }
                        });
                      }}
                      className="w-full py-1.5 px-3 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg text-xs font-medium border border-red-200 transition cursor-pointer"
                    >
                      Remove Attached Figure
                    </button>
                  </div>
                )}
              </div>

              {/* POSITIONING & SCALE SLIDERS */}
              <div className="space-y-3 p-3 bg-neutral-50 border border-neutral-200 rounded-xl">
                <div className="text-xs font-bold text-neutral-900">Position & Scale</div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-neutral-500 mb-1 block">Anchor X ({Math.round((selectedGraphic.pos_x ?? 0.5) * 100)}%)</label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={selectedGraphic.pos_x ?? 0.5}
                      onChange={(e) => onUpdateGraphic({ ...selectedGraphic, pos_x: parseFloat(e.target.value) })}
                      className="w-full accent-neutral-900 cursor-pointer"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-neutral-500 mb-1 block">Anchor Y ({Math.round((selectedGraphic.pos_y ?? 0.5) * 100)}%)</label>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={selectedGraphic.pos_y ?? 0.5}
                      onChange={(e) => onUpdateGraphic({ ...selectedGraphic, pos_y: parseFloat(e.target.value) })}
                      className="w-full accent-neutral-900 cursor-pointer"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-[10px] text-neutral-500 mb-1 block">Scale ({Math.round((selectedGraphic.scale ?? 1.0) * 100)}%)</label>
                  <input
                    type="range"
                    min="0.4"
                    max="2.0"
                    step="0.05"
                    value={selectedGraphic.scale ?? 1.0}
                    onChange={(e) => onUpdateGraphic({ ...selectedGraphic, scale: parseFloat(e.target.value) })}
                    className="w-full accent-neutral-900 cursor-pointer"
                  />
                </div>
              </div>

              {/* MEDIA FRAMING & ZOOM / CROP PANEL */}
              {(selectedGraphic.media_url ||
                selectedGraphic.parameters?.asset_name ||
                selectedGraphic.template_id === 'split_screen_vertical' ||
                selectedGraphic.template_id === 'youtube_insert' ||
                selectedGraphic.parameters?.card_media ||
                selectedGraphic.parameters?.show_image) && (
                <div className="space-y-3 p-3 bg-neutral-50 border border-neutral-200 rounded-xl">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-neutral-900">Media Framing & Zoom</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-100 text-blue-700 font-bold">
                      CROP & PAN
                    </span>
                  </div>
                  <p className="text-[11px] text-neutral-500 leading-tight">
                    Adjust framing and zoom so subjects, faces, or key landmarks remain fully visible inside the frame.
                  </p>

                  {/* Vertical Framing (Pan Y) */}
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="text-[10px] font-medium text-neutral-600">Vertical Framing (Y)</label>
                      <span className="text-[10px] font-mono text-neutral-500">
                        {Math.round(((selectedGraphic.parameters?.media_pos_y ?? selectedGraphic.pos_y ?? 0.5) as number) * 100)}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={(selectedGraphic.parameters?.media_pos_y ?? selectedGraphic.pos_y ?? 0.5) as number}
                      onChange={(e) => {
                        const y = parseFloat(e.target.value);
                        const curX = (selectedGraphic.parameters?.media_pos_x ?? selectedGraphic.pos_x ?? 0.5) as number;
                        const curS = (selectedGraphic.parameters?.media_scale ?? selectedGraphic.scale ?? 1.0) as number;
                        handleUpdateMediaFraming(curX, y, curS);
                      }}
                      className="w-full accent-neutral-900 cursor-pointer"
                    />
                    <div className="flex items-center gap-1.5 pt-0.5">
                      <button
                        type="button"
                        onClick={() => {
                          const curX = (selectedGraphic.parameters?.media_pos_x ?? selectedGraphic.pos_x ?? 0.5) as number;
                          const curS = (selectedGraphic.parameters?.media_scale ?? selectedGraphic.scale ?? 1.0) as number;
                          handleUpdateMediaFraming(curX, 0.18, curS);
                        }}
                        className="flex-1 py-1 px-1.5 rounded bg-white hover:bg-neutral-100 border border-neutral-300 text-[10px] font-semibold text-neutral-800 shadow-2xs"
                      >
                        Face / Top (18%)
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          const curX = (selectedGraphic.parameters?.media_pos_x ?? selectedGraphic.pos_x ?? 0.5) as number;
                          const curS = (selectedGraphic.parameters?.media_scale ?? selectedGraphic.scale ?? 1.0) as number;
                          handleUpdateMediaFraming(curX, 0.50, curS);
                        }}
                        className="flex-1 py-1 px-1.5 rounded bg-white hover:bg-neutral-100 border border-neutral-300 text-[10px] font-semibold text-neutral-800 shadow-2xs"
                      >
                        Center (50%)
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          const curX = (selectedGraphic.parameters?.media_pos_x ?? selectedGraphic.pos_x ?? 0.5) as number;
                          const curS = (selectedGraphic.parameters?.media_scale ?? selectedGraphic.scale ?? 1.0) as number;
                          handleUpdateMediaFraming(curX, 0.82, curS);
                        }}
                        className="flex-1 py-1 px-1.5 rounded bg-white hover:bg-neutral-100 border border-neutral-300 text-[10px] font-semibold text-neutral-800 shadow-2xs"
                      >
                        Bottom (82%)
                      </button>
                    </div>
                  </div>

                  {/* Horizontal Framing (Pan X) */}
                  <div className="space-y-1.5 pt-2 border-t border-neutral-200/60">
                    <div className="flex items-center justify-between">
                      <label className="text-[10px] font-medium text-neutral-600">Horizontal Framing (X)</label>
                      <span className="text-[10px] font-mono text-neutral-500">
                        {Math.round(((selectedGraphic.parameters?.media_pos_x ?? selectedGraphic.pos_x ?? 0.5) as number) * 100)}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="1"
                      step="0.01"
                      value={(selectedGraphic.parameters?.media_pos_x ?? selectedGraphic.pos_x ?? 0.5) as number}
                      onChange={(e) => {
                        const x = parseFloat(e.target.value);
                        const curY = (selectedGraphic.parameters?.media_pos_y ?? selectedGraphic.pos_y ?? 0.5) as number;
                        const curS = (selectedGraphic.parameters?.media_scale ?? selectedGraphic.scale ?? 1.0) as number;
                        handleUpdateMediaFraming(x, curY, curS);
                      }}
                      className="w-full accent-neutral-900 cursor-pointer"
                    />
                    <div className="flex items-center gap-1.5 pt-0.5">
                      <button
                        type="button"
                        onClick={() => {
                          const curY = (selectedGraphic.parameters?.media_pos_y ?? selectedGraphic.pos_y ?? 0.5) as number;
                          const curS = (selectedGraphic.parameters?.media_scale ?? selectedGraphic.scale ?? 1.0) as number;
                          handleUpdateMediaFraming(0.20, curY, curS);
                        }}
                        className="flex-1 py-1 px-1.5 rounded bg-white hover:bg-neutral-100 border border-neutral-300 text-[10px] font-semibold text-neutral-800 shadow-2xs"
                      >
                        Left (20%)
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          const curY = (selectedGraphic.parameters?.media_pos_y ?? selectedGraphic.pos_y ?? 0.5) as number;
                          const curS = (selectedGraphic.parameters?.media_scale ?? selectedGraphic.scale ?? 1.0) as number;
                          handleUpdateMediaFraming(0.50, curY, curS);
                        }}
                        className="flex-1 py-1 px-1.5 rounded bg-white hover:bg-neutral-100 border border-neutral-300 text-[10px] font-semibold text-neutral-800 shadow-2xs"
                      >
                        Center (50%)
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          const curY = (selectedGraphic.parameters?.media_pos_y ?? selectedGraphic.pos_y ?? 0.5) as number;
                          const curS = (selectedGraphic.parameters?.media_scale ?? selectedGraphic.scale ?? 1.0) as number;
                          handleUpdateMediaFraming(0.80, curY, curS);
                        }}
                        className="flex-1 py-1 px-1.5 rounded bg-white hover:bg-neutral-100 border border-neutral-300 text-[10px] font-semibold text-neutral-800 shadow-2xs"
                      >
                        Right (80%)
                      </button>
                    </div>
                  </div>

                  {/* Media Zoom / Scale */}
                  <div className="space-y-1.5 pt-2 border-t border-neutral-200/60">
                    <div className="flex items-center justify-between">
                      <label className="text-[10px] font-medium text-neutral-600">Media Zoom (Scale)</label>
                      <span className="text-[10px] font-mono text-neutral-500">
                        {((selectedGraphic.parameters?.media_scale ?? selectedGraphic.scale ?? 1.0) as number).toFixed(2)}x
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0.5"
                      max="2.5"
                      step="0.05"
                      value={(selectedGraphic.parameters?.media_scale ?? selectedGraphic.scale ?? 1.0) as number}
                      onChange={(e) => {
                        const s = parseFloat(e.target.value);
                        const curX = (selectedGraphic.parameters?.media_pos_x ?? selectedGraphic.pos_x ?? 0.5) as number;
                        const curY = (selectedGraphic.parameters?.media_pos_y ?? selectedGraphic.pos_y ?? 0.5) as number;
                        handleUpdateMediaFraming(curX, curY, s);
                      }}
                      className="w-full accent-neutral-900 cursor-pointer"
                    />
                    <div className="flex items-center gap-1.5 pt-0.5">
                      <button
                        type="button"
                        onClick={() => {
                          const curX = (selectedGraphic.parameters?.media_pos_x ?? selectedGraphic.pos_x ?? 0.5) as number;
                          const curY = (selectedGraphic.parameters?.media_pos_y ?? selectedGraphic.pos_y ?? 0.5) as number;
                          handleUpdateMediaFraming(curX, curY, 1.0);
                        }}
                        className="flex-1 py-1 px-1.5 rounded bg-white hover:bg-neutral-100 border border-neutral-300 text-[10px] font-semibold text-neutral-800 shadow-2xs"
                      >
                        1.0x Normal
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          const curX = (selectedGraphic.parameters?.media_pos_x ?? selectedGraphic.pos_x ?? 0.5) as number;
                          const curY = (selectedGraphic.parameters?.media_pos_y ?? selectedGraphic.pos_y ?? 0.5) as number;
                          handleUpdateMediaFraming(curX, curY, 1.25);
                        }}
                        className="flex-1 py-1 px-1.5 rounded bg-white hover:bg-neutral-100 border border-neutral-300 text-[10px] font-semibold text-neutral-800 shadow-2xs"
                      >
                        1.25x Punch
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          const curX = (selectedGraphic.parameters?.media_pos_x ?? selectedGraphic.pos_x ?? 0.5) as number;
                          const curY = (selectedGraphic.parameters?.media_pos_y ?? selectedGraphic.pos_y ?? 0.5) as number;
                          handleUpdateMediaFraming(curX, curY, 1.5);
                        }}
                        className="flex-1 py-1 px-1.5 rounded bg-white hover:bg-neutral-100 border border-neutral-300 text-[10px] font-semibold text-neutral-800 shadow-2xs"
                      >
                        1.5x Close-up
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-neutral-400">
              <Layers className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <div className="text-xs font-medium">No graphic selected</div>
              <div className="text-[11px] mt-1 text-neutral-500">Click a graphic in the timeline or add one from Presets</div>
            </div>
          )
        ) : subTab === 'broll' ? (
          /* TAB 2: STOCK MEDIA & B-ROLL SEARCH (PEXELS / PIXABAY / WIKIMEDIA) */
          <div className="space-y-3">
            {/* 80%+ High Density B-Roll Coverage Control Card */}
            <div className="p-3 bg-gradient-to-br from-cyan-50/70 via-white to-blue-50/50 border border-cyan-200/80 rounded-xl space-y-2.5 shadow-2xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 font-bold text-xs text-neutral-900">
                  <Video className="w-3.5 h-3.5 text-cyan-600" />
                  <span>Visual Media Density</span>
                </div>
                {coverageData && (
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                    coverageData.coverage_percentage >= 80
                      ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                      : 'bg-amber-100 text-amber-800 border-amber-300'
                  }`}>
                    {coverageData.coverage_percentage >= 80 ? '✓ 80%+ Target Met' : `${coverageData.coverage_percentage}% Coverage`}
                  </span>
                )}
              </div>

              {/* Progress Meter */}
              <div className="space-y-1">
                <div className="flex justify-between text-[10px] text-neutral-500 font-medium">
                  <span>Timeline Visual Coverage</span>
                  <span className="font-mono font-bold text-neutral-800">
                    {coverageData ? `${coverageData.coverage_percentage}%` : 'Calculating...'}
                  </span>
                </div>
                <div className="w-full bg-neutral-200 h-2 rounded-full overflow-hidden relative">
                  <div
                    className={`h-full transition-all duration-500 ${
                      (coverageData?.coverage_percentage || 0) >= 80
                        ? 'bg-gradient-to-r from-emerald-500 to-cyan-500'
                        : 'bg-gradient-to-r from-amber-500 to-orange-500'
                    }`}
                    style={{ width: `${Math.min(100, coverageData?.coverage_percentage || 0)}%` }}
                  />
                </div>
                <div className="flex justify-between text-[9px] text-neutral-400">
                  <span>0s</span>
                  <span className="font-semibold text-neutral-600">Reviewed coverage</span>
                  <span>{coverageData ? `${coverageData.total_duration.toFixed(1)}s` : ''}</span>
                </div>
              </div>

              <div className="text-[11px] text-neutral-600 flex items-center justify-between">
                <span>
                  {coverageData?.media_count || 0} media cutaways & authentic images
                </span>
                <span className="font-mono text-[10px] text-neutral-500">
                  {coverageData ? `${coverageData.covered_duration.toFixed(1)}s / ${coverageData.total_duration.toFixed(1)}s` : ''}
                </span>
              </div>

              {densitySuccessMessage && (
                <div className="p-2 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-[11px] font-medium flex items-center gap-1.5 animate-fadeIn">
                  <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <span>{densitySuccessMessage}</span>
                </div>
              )}

              <button
                type="button"
                onClick={handleMaximizeDensity}
                disabled={isMaximizingDensity}
                className="w-full bg-neutral-900 hover:bg-neutral-800 text-white font-bold text-xs py-2 px-3 rounded-lg transition flex items-center justify-center gap-1.5 shadow-xs disabled:opacity-50 cursor-pointer"
              >
                {isMaximizingDensity ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Checking reviewed coverage...</span>
                  </>
                ) : (
                  <>
                    <Wand2 className="w-3.5 h-3.5 text-cyan-400" />
                    <span>
                      Review media coverage
                    </span>
                  </>
                )}
              </button>
            </div>

            {/* Search Input Bar */}
            <div className="space-y-2 bg-neutral-50 rounded-xl p-3 border border-neutral-200">
              <div className="flex items-center gap-1.5">
                <div className="flex-1 relative">
                  <input
                    type="text"
                    value={brollSearchQuery}
                    onChange={(e) => setBrollSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleBrollSearch()}
                    placeholder="Search Pexels & Pixabay (e.g. doctor, hospital, dna)..."
                    className="w-full bg-white border border-neutral-300 rounded-lg pl-7 pr-2 py-1.5 text-xs text-neutral-900 placeholder-neutral-400 outline-none focus:border-neutral-900 font-mono shadow-xs"
                  />
                  <Search className="w-3.5 h-3.5 text-neutral-400 absolute left-2 top-2" />
                </div>

                <button
                  onClick={() => handleBrollSearch()}
                  disabled={isSearchingBroll}
                  className="bg-neutral-900 hover:bg-neutral-800 text-white font-bold text-xs px-3 py-1.5 rounded-lg transition disabled:opacity-50 flex items-center gap-1 shadow-xs cursor-pointer"
                >
                  {isSearchingBroll ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Find'}
                </button>
              </div>

              {/* Filters: Media Type, Provider, Orientation */}
              <div className="flex items-center justify-between gap-1.5 pt-1 border-t border-neutral-200 text-[10px] font-mono">
                <div className="flex items-center gap-1 bg-white p-0.5 rounded border border-neutral-200 shadow-xs">
                  <button
                    onClick={() => {
                      setBrollMediaType('image');
                      handleBrollSearch(brollSearchQuery || 'medical', 'image', brollProvider, brollOrientation);
                    }}
                    className={`px-2 py-0.5 rounded transition cursor-pointer ${
                      brollMediaType === 'image'
                        ? 'bg-neutral-900 text-white font-bold'
                        : 'text-neutral-600 hover:text-neutral-900'
                    }`}
                  >
                    Images
                  </button>
                  <button
                    onClick={() => {
                      setBrollMediaType('video');
                      handleBrollSearch(brollSearchQuery || 'medical', 'video', brollProvider, brollOrientation);
                    }}
                    className={`px-2 py-0.5 rounded transition cursor-pointer ${
                      brollMediaType === 'video'
                        ? 'bg-neutral-900 text-white font-bold'
                        : 'text-neutral-600 hover:text-neutral-900'
                    }`}
                  >
                    Videos
                  </button>
                </div>

                <select
                  value={brollProvider}
                  onChange={(e) => {
                    const p = e.target.value as any;
                    setBrollProvider(p);
                    handleBrollSearch(brollSearchQuery || 'medical', brollMediaType, p, brollOrientation);
                  }}
                  className="bg-white border border-neutral-300 text-[10px] rounded px-1.5 py-0.5 text-neutral-800 outline-none shadow-xs font-medium cursor-pointer"
                >
                  <option value="all">Pexels + Pixabay</option>
                  <option value="pexels">Pexels Only</option>
                  <option value="pixabay">Pixabay Only</option>
                  <option value="wikimedia">Wikimedia</option>
                </select>

                <select
                  value={brollOrientation}
                  onChange={(e) => {
                    const ori = e.target.value as any;
                    setBrollOrientation(ori);
                    handleBrollSearch(brollSearchQuery || 'medical', brollMediaType, brollProvider, ori);
                  }}
                  className="bg-white border border-neutral-300 text-[10px] rounded px-1.5 py-0.5 text-neutral-800 outline-none shadow-xs font-medium cursor-pointer"
                >
                  <option value="all">Any Ratio</option>
                  <option value="portrait">9:16 Portrait</option>
                  <option value="landscape">16:9 Landscape</option>
                </select>
              </div>

              {/* Upload Custom File */}
              <div className="flex justify-end pt-1">
                <label className="cursor-pointer flex items-center gap-1 px-2.5 py-1 rounded bg-white hover:bg-neutral-50 border border-neutral-300 text-neutral-700 hover:text-neutral-900 transition text-[10px] font-semibold shadow-xs">
                  <Upload className="w-3 h-3 text-cyan-600" />
                  <span>{isUploadingAsset ? 'Uploading...' : 'Upload Custom File'}</span>
                  <input
                    type="file"
                    accept="image/*,video/*"
                    onChange={handleAssetUpload}
                    disabled={isUploadingAsset}
                    className="hidden"
                  />
                </label>
              </div>
            </div>

            {/* Search Results Grid */}
            <div className="space-y-2">
              <div className="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider flex items-center justify-between">
                <span>Results ({brollResults.length})</span>
                {selectedGraphic && (
                  <span className="text-cyan-700 font-bold truncate max-w-[200px]">Active: {selectedGraphic.title}</span>
                )}
              </div>

              {isSearchingBroll ? (
                <div className="text-center py-12 text-neutral-400">
                  <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-neutral-600" />
                  <div className="text-xs">Searching stock visuals...</div>
                </div>
              ) : brollResults.length === 0 ? (
                <div className="text-center py-12 text-neutral-400 bg-neutral-50 rounded-xl border border-neutral-200">
                  <ImageIcon className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  <div className="text-xs font-medium text-neutral-600">No stock media found</div>
                  <div className="text-[10px] mt-1 text-neutral-400">Try searching for keywords like "doctor", "hospital", "lab"</div>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-2">
                  {brollResults.map((item, idx) => {
                    const thumb = item.thumb_url || item.thumbnail || item.preview_url || item.url || item.media_url;
                    const isVid = item.media_type === 'video' || Boolean(item.duration);

                    return (
                      <div
                        key={item.id || idx}
                        className="group relative rounded-lg overflow-hidden border border-neutral-200 bg-black aspect-[4/3] flex flex-col justify-end shadow-xs hover:border-neutral-900 transition"
                      >
                        <img
                          src={thumb}
                          alt="Stock Visual"
                          className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-300 opacity-90"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent pointer-events-none" />

                        {isVid && (
                          <div className="absolute top-1.5 right-1.5 px-1.5 py-0.5 rounded bg-black/75 text-white font-mono text-[9px] flex items-center gap-1">
                            <Video className="w-2.5 h-2.5 text-cyan-400" />
                            {item.duration ? `${Math.round(item.duration)}s` : 'CLIP'}
                          </div>
                        )}

                        <div className="relative z-10 p-1.5 space-y-1">
                          <div className="flex items-center gap-1">
                            {selectedGraphic && (
                              <button
                                type="button"
                                onClick={() => handleApplyMediaToSelected(item)}
                                className="flex-1 py-1 rounded bg-neutral-900/90 hover:bg-neutral-900 text-white font-bold text-[9px] transition flex items-center justify-center gap-1 border border-white/20 cursor-pointer"
                                title="Apply image to currently selected graphic"
                              >
                                <Check className="w-2.5 h-2.5" />
                                <span>Use</span>
                              </button>
                            )}

                            <button
                              type="button"
                              onClick={async () => {
                                const localUrl = await ensureDownloadedAsset(item);
                                onAddGraphic(
                                  'youtube_insert',
                                  {
                                    media_url: localUrl,
                                    media_type: isVid ? 'video' : 'image'
                                  },
                                  currentTime,
                                  Math.min(project.duration_seconds || 60, currentTime + 4.0),
                                  'Cutaway'
                                );
                                setSubTab('inspector');
                              }}
                              className="px-1.5 py-1 rounded bg-white/90 hover:bg-white text-neutral-900 font-bold text-[9px] transition cursor-pointer"
                              title="Add as clean Cutaway"
                            >
                              + Cut
                            </button>

                            <button
                              type="button"
                              onClick={async () => {
                                const localUrl = await ensureDownloadedAsset(item);
                                onAddGraphic(
                                  'split_screen_vertical',
                                  {
                                    media_url: localUrl,
                                    media_type: isVid ? 'video' : 'image'
                                  },
                                  currentTime,
                                  Math.min(project.duration_seconds || 60, currentTime + 4.0),
                                  '50/50 Split'
                                );
                                setSubTab('inspector');
                              }}
                              className="px-1.5 py-1 rounded bg-white/90 hover:bg-white text-neutral-900 font-bold text-[9px] transition cursor-pointer"
                              title="Add as 50/50 Split"
                            >
                              + 50/50
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        ) : subTab === 'library' ? (
          /* TAB 3: PRESETS LIBRARY */
          <div className="space-y-3">
            <div className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">
              Graphic Presets ({TEMPLATE_PRESETS.length})
            </div>

            <div className="grid grid-cols-1 gap-2">
              {TEMPLATE_PRESETS.map((preset) => (
                <div
                  key={preset.id}
                  className="p-3 rounded-xl border border-neutral-200 bg-neutral-50 hover:bg-neutral-100/80 transition space-y-2"
                >
                  <div>
                    <div className="font-bold text-xs text-neutral-900">{preset.name}</div>
                    <div className="text-[11px] text-neutral-500 mt-0.5">{preset.desc}</div>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleAddTemplate(preset)}
                    className="w-full py-1.5 rounded-lg bg-neutral-900 hover:bg-neutral-800 text-white font-semibold text-xs flex items-center justify-center gap-1.5 transition shadow-xs cursor-pointer"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    <span>Insert @ Playhead</span>
                  </button>
                </div>
              ))}
            </div>

            {/* List of current project graphics */}
            {project.graphics.length > 0 && (
              <div className="pt-3 border-t border-neutral-200 space-y-2">
                <div className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">
                  Placed Graphics ({project.graphics.length})
                </div>

                {project.graphics.map((g, idx) => (
                  <div
                    key={g.id}
                    onClick={() => {
                      onSelectGraphic(g.id);
                      onTimeSeek(g.start);
                      setSubTab('inspector');
                    }}
                    className="p-2.5 rounded-xl border border-neutral-200 bg-neutral-50 hover:bg-neutral-100 transition cursor-pointer flex items-center justify-between"
                  >
                    <div>
                      <div className="font-semibold text-xs text-neutral-900">#{idx + 1} {g.title}</div>
                      <div className="text-[10px] text-neutral-500 font-mono mt-0.5">
                        {g.start.toFixed(1)}s - {g.end.toFixed(1)}s ({g.template_id})
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteGraphic(g.id);
                      }}
                      className="p-1 hover:bg-red-50 text-neutral-400 hover:text-red-600 rounded transition"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          /* TAB 4: AI VIDEO STUDIO */
          <AIMotionGraphicsPanel
            currentTime={currentTime}
            project={project}
            activeCaptionText={project.captions.find((c) => currentTime >= c.start && currentTime <= c.end)?.text || ''}
            onAppendVideoTrack={onAppendVideoTrack}
            captureCurrentCanvasFrame={captureCurrentCanvasFrame}
            prefilledOmni={prefilledOmni}
          />
        )}
      </div>
    </div>
  );
};
