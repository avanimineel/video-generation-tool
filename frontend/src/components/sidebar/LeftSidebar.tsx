import React, { useState, useEffect } from 'react';
import { 
  Type, Sparkles, FolderOpen, Languages, Plus, Play, 
  Wand2, ArrowRight, CheckCircle2, Clock, FileVideo, Loader2,
  Film, RefreshCw, FileText, Camera, Compass, Layers, Zap, Info, Sliders, Search,
  Upload, Columns, Tv, Video, Download, ShieldCheck, AlertCircle, X, ExternalLink, Brain,
  Trash2, AlertTriangle
} from 'lucide-react';
import { ProjectState, GraphicTemplate, CaptionItem, ProjectSummary, DynamicSamplesResponse, DynamicGraphicSample } from '../../types';
import { api } from '../../services/api';
import { AIMotionGraphicsPanel } from '../inspector/AIMotionGraphicsPanel';

const BROLL_TOPICS = [
  { label: 'All', query: 'documentary research' },
  { label: 'Cough / Lungs', query: 'coughing respiratory' },
  { label: 'Cancer / Oncology', query: 'cancer cell oncology' },
  { label: 'Patient / Clinic', query: 'patient doctor hospital' },
  { label: 'Medical Lab', query: 'laboratory medical research' },
  { label: 'NASA / Space', query: 'apollo nasa space flight' },
  { label: 'Historical Archives', query: 'historical vintage archival' }
];

interface LeftSidebarProps {
  project: ProjectState;
  templates: GraphicTemplate[];
  projectsList: ProjectSummary[];
  selectedCaptionId: string | null;
  onSelectCaption: (id: string) => void;
  onTimeSeek: (time: number) => void;
  onTranscribe: (rawText?: string, wordsPerCap?: number, geminiApiKey?: string, modelSize?: 'base' | 'small') => Promise<void>;
  onTranslate: () => Promise<void>;
  onAddGraphic: (templateId: string, params: Record<string, any>, start?: number, end?: number, title?: string) => void;
  onSwitchProject: (id: string) => void;
  onNewProject: () => void;
  isTranscribing: boolean;
  isTranslating: boolean;
  activeLanguageView: 'english' | 'hindi';
  onToggleLanguageView: () => void;
  activeLinesMode?: 1 | 2;
  onReformatLines?: (lines: 1 | 2) => void;
  onDetectKeywords?: () => Promise<void>;
  onDetectDimensionsAndCues?: () => Promise<void>;
  onOpenReasoningLog?: () => void;
  hasReasoningLog?: boolean;
  onDirectToOmni?: (prompt: string, cameraMotion: string, headline: string) => void;
  currentTime?: number;
  onAppendVideoTrack?: (videoUrl: string, title: string, duration: number, overlayText: string, instructions: string, sourceCitation?: string) => void;
  captureCurrentCanvasFrame?: () => string | null;
  prefilledOmni?: { prompt: string; cameraMotion: string; headline: string } | null;
  onRerunAutoProduction?: (force?: boolean) => Promise<void>;
  isAutoProducing?: boolean;
  onDeleteProject?: (projectId: string) => Promise<void>;
}

export const LeftSidebar: React.FC<LeftSidebarProps> = ({
  project,
  templates,
  projectsList,
  selectedCaptionId,
  onSelectCaption,
  onTimeSeek,
  onTranscribe,
  onTranslate,
  onAddGraphic,
  onSwitchProject,
  onNewProject,
  isTranscribing,
  isTranslating,
  activeLanguageView,
  onToggleLanguageView,
  activeLinesMode = 1,
  onReformatLines,
  onDetectKeywords,
  onDetectDimensionsAndCues,
  onOpenReasoningLog,
  hasReasoningLog,
  onDirectToOmni,
  currentTime = 0,
  onAppendVideoTrack,
  captureCurrentCanvasFrame,
  prefilledOmni,
  onRerunAutoProduction,
  isAutoProducing = false,
  onDeleteProject
}) => {
  const [activeTab, setActiveTab] = useState<'subtitles' | 'graphics' | 'projects'>('subtitles');
  const [graphicsCategory, setGraphicsCategory] = useState<string>('All');
  const [graphicsViewMode, setGraphicsViewMode] = useState<'cues' | 'flow' | 'broll' | 'article' | 'standard'>('cues');
  const [dynamicResponse, setDynamicResponse] = useState<DynamicSamplesResponse | null>(null);
  const [isLoadingDynamic, setIsLoadingDynamic] = useState<boolean>(false);
  const [selectedMaxBudgetPct, setSelectedMaxBudgetPct] = useState<number>(25);
  const [selectedCategoryOverride, setSelectedCategoryOverride] = useState<string>('');
  const [isDetectingKw, setIsDetectingKw] = useState<boolean>(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [isDeletingProject, setIsDeletingProject] = useState<boolean>(false);

  // Article Reconstruction State (Screenshot 5)
  const [articleInputUrl, setArticleInputUrl] = useState('');
  const [articlePastedText, setArticlePastedText] = useState('');
  const [isParsingArticle, setIsParsingArticle] = useState(false);
  const [parsedArticleData, setParsedArticleData] = useState<any>({
    publisher: 'Scroll.in',
    headline: 'Dombivli hospital assault: Doctor resigns after attack by Shinde Sena corporator, fearing for safety',
    date: 'May 14, 2024 • Investigative Archive',
    source_url: 'https://scroll.in/latest/1067824/dombivli-hospital-assault',
    paragraph: "The 26-year-old resident medical officer at the Kalyan-Dombivli Municipal Corporation's Shastri Nagar Hospital said he had left the city after receiving threats and would 'never go back'.",
    highlight_quote: "he had left the city after receiving threats and would 'never go back'",
    marker_color: '#00E5FF',
    callout_badge: 'resigned.',
    paper_theme: 'editorial_clean'
  });

  const handleParseArticle = async (presetKey?: string) => {
    setIsParsingArticle(true);
    try {
      const activeCap = project.captions.find(c => c.id === selectedCaptionId)
        || (currentTime !== undefined ? project.captions.find(c => currentTime >= c.start && currentTime <= c.end) : null);

      const res = await api.parseArticle({
        url: presetKey ? undefined : (articleInputUrl || undefined),
        pasted_text: presetKey ? undefined : (articlePastedText || undefined),
        target_speech: activeCap?.text,
        preset_key: presetKey
      });

      if (res && res.success) {
        setParsedArticleData({
          ...res,
          callout_badge: res.callout_badge || (res.highlight_quote?.toLowerCase().includes('resign') ? 'resigned.' : undefined)
        });
      }
    } catch (e) {
      console.error('Failed to parse article:', e);
    } finally {
      setIsParsingArticle(false);
    }
  };

  const handleInsertArticleToTimeline = () => {
    const startT = currentTime;
    const endT = startT + 4.5;
    onAddGraphic(
      'article_reconstruction',
      {
        publisher: parsedArticleData.publisher || 'Scroll.in',
        headline: parsedArticleData.headline,
        date: parsedArticleData.date || 'Investigation Archive',
        source_url: parsedArticleData.source_url,
        paragraph: parsedArticleData.paragraph,
        highlight_quote: parsedArticleData.highlight_quote,
        marker_color: parsedArticleData.marker_color || '#00E5FF',
        callout_badge: parsedArticleData.callout_badge,
        paper_theme: parsedArticleData.paper_theme || 'editorial_clean',
        track: 'V4',
        placement_mode: 'overlay',
        animation: 'slow_zoom_in'
      },
      startT,
      endT,
      parsedArticleData.headline || 'Article Reconstruction'
    );
  };
  const [isDetectingCues, setIsDetectingCues] = useState<boolean>(false);
  const [rawTextInput, setRawTextInput] = useState('');
  const [wordsPerCap, setWordsPerCap] = useState(4);
  const [transcribeModelSize, setTranscribeModelSize] = useState<'base' | 'small'>('base');
  const [suggestInput, setSuggestInput] = useState('');
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [showScriptBox, setShowScriptBox] = useState(true);

  // B-Roll / Asset Research State
  const [brollSearchQuery, setBrollSearchQuery] = useState('');
  const [brollMediaType, setBrollMediaType] = useState<'image' | 'video'>('image');
  const [brollProvider, setBrollProvider] = useState<'all' | 'pexels' | 'pixabay' | 'wikimedia'>('all');
  const [brollOrientation, setBrollOrientation] = useState<'all' | 'portrait' | 'landscape'>('all');
  const [providerStatuses, setProviderStatuses] = useState<any>(null);
  const [showProviderModal, setShowProviderModal] = useState(false);
  const [downloadingItemId, setDownloadingItemId] = useState<string | null>(null);
  const [previewingVideo, setPreviewingVideo] = useState<any | null>(null);
  const [isSearchingBroll, setIsSearchingBroll] = useState(false);
  const [isAutoMatchingBroll, setIsAutoMatchingBroll] = useState(false);
  const [isUploadingAsset, setIsUploadingAsset] = useState(false);
  const [brollResults, setBrollResults] = useState<any[]>([]);
  const [brollActiveTopic, setBrollActiveTopic] = useState('All');
  const [pexelsKeyInput, setPexelsKeyInput] = useState('');
  const [pixabayKeyInput, setPixabayKeyInput] = useState('');
  const [geminiKeyInput, setGeminiKeyInput] = useState('');
  const [isSavingKeys, setIsSavingKeys] = useState(false);

  const refreshProviderStatuses = async () => {
    try {
      const data = await api.getProviderStatus();
      setProviderStatuses(data);
    } catch (e) {
      console.warn('Failed to load provider statuses:', e);
    }
  };

  const handleSaveApiKeys = async () => {
    if (!pexelsKeyInput.trim() && !pixabayKeyInput.trim() && !geminiKeyInput.trim()) {
      alert('Please enter at least one API key.');
      return;
    }
    setIsSavingKeys(true);
    try {
      await api.saveProviderKeys({
        pexels_api_key: pexelsKeyInput.trim() || undefined,
        pixabay_api_key: pixabayKeyInput.trim() || undefined,
        gemini_api_key: geminiKeyInput.trim() || undefined
      });
      await refreshProviderStatuses();
      setPexelsKeyInput('');
      setPixabayKeyInput('');
      setGeminiKeyInput('');
      alert('API keys saved to backend/.env and reloaded!');
    } catch (e: any) {
      alert('Failed to save API keys: ' + (e.message || String(e)));
    } finally {
      setIsSavingKeys(false);
    }
  };

  useEffect(() => {
    refreshProviderStatuses();
  }, []);

  const handleBrollSearch = async (
    query = brollSearchQuery,
    type = brollMediaType,
    provider = brollProvider,
    orientation = brollOrientation
  ) => {
    const q = query.trim() || 'doctor hospital';
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

  const handleAutoMatchCurrentCaption = async () => {
    const activeCap = project.captions.find(c => c.id === selectedCaptionId)
      || (currentTime !== undefined ? project.captions.find(c => currentTime >= c.start && currentTime <= c.end) : null)
      || project.captions[0];

    if (!activeCap) {
      alert('No caption found. Please select or play to a caption first.');
      return;
    }

    setIsAutoMatchingBroll(true);
    try {
      const match = await api.autoMatchMedia(activeCap.text);
      if (match) {
        setBrollSearchQuery(match.search_term || activeCap.text);
        const combined = match.all_results && match.all_results.length > 0
          ? match.all_results
          : (match.media ? [match.media] : []);
        setBrollResults(combined);
      }
    } catch (e) {
      console.error('Auto match failed:', e);
    } finally {
      setIsAutoMatchingBroll(false);
    }
  };

  const handleAssetUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !project.id) return;
    setIsUploadingAsset(true);
    try {
      const res = await api.uploadAsset(project.id, file);
      if (res && res.success) {
        setBrollResults(prev => [{
          title: res.title,
          url: res.media_url,
          thumb_url: res.media_url,
          media_type: res.media_type,
          source_credit: res.source_credit
        }, ...prev]);
      }
    } catch (err: any) {
      alert('Upload failed: ' + (err.message || String(err)));
    } finally {
      setIsUploadingAsset(false);
      e.target.value = '';
    }
  };

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

  const handleSaveToProject = async (item: any) => {
    try {
      const localUrl = await ensureDownloadedAsset(item);
      alert(`Asset downloaded locally to project media folder:\n${localUrl}`);
    } catch (err: any) {
      alert(`Save failed: ${err.message || String(err)}`);
    }
  };

  const handleAddSplitBroll = async (item: any) => {
    const localMediaUrl = await ensureDownloadedAsset(item);
    const startT = currentTime || 0;
    // B-roll duration clamped to 1.0s max unless manually extended
    const dur = 1.0;
    const endT = Math.min(project.duration_seconds || 60, startT + dur);
    onAddGraphic(
      'split_screen_vertical',
      {
        broll_title: item.title || 'Documentary Visual Evidence',
        media_url: localMediaUrl,
        media_type: item.media_type || 'image',
        source_citation: item.source_credit || 'Source: Media Archives',
        split_layout: 'split_50_50_vertical',
        placement_mode: 'overlay',
        track: 'V3',
        animation: 'slow_zoom_in',
        source_name: item.source_credit
      },
      startT,
      endT,
      item.title || '50/50 Split B-Roll'
    );
  };

  const handleAddInsertBroll = async (item: any) => {
    const localMediaUrl = await ensureDownloadedAsset(item);
    const startT = currentTime || 0;
    // B-roll cutaway duration clamped to 1.0s max unless manually extended
    const dur = 1.0;
    const endT = Math.min(project.duration_seconds || 60, startT + dur);
    onAddGraphic(
      'youtube_insert',
      {
        media_url: localMediaUrl,
        media_type: item.media_type || 'image',
        channel_name: item.source_credit || 'Archival Broadcast',
        channel_handle: '@archives',
        subscriber_count: 'Public Domain',
        video_title: item.title || 'Documentary Cutaway Footage',
        source_name: item.source_credit,
        placement_mode: 'insert',
        track: 'V3',
        animation: 'slow_zoom_in',
        scanlines: true
      },
      startT,
      endT,
      item.title || 'Cutaway Insert'
    );
  };

  const handleAddOverlayBroll = async (item: any) => {
    const localMediaUrl = await ensureDownloadedAsset(item);
    const startT = currentTime || 0;
    // B-roll duration clamped to 1.0s max unless manually extended
    const dur = 1.0;
    const endT = Math.min(project.duration_seconds || 60, startT + dur);
    onAddGraphic(
      'broll_overlay',
      {
        media_url: localMediaUrl,
        media_type: item.media_type || 'image',
        title: item.title || 'B-Roll Evidence',
        source_name: item.source_credit,
        placement_mode: 'overlay',
        track: 'V3',
        animation: 'slow_zoom_in'
      },
      startT,
      endT,
      item.title || 'B-Roll Overlay'
    );
  };

  const fetchDynamicSamples = async (maxPct = selectedMaxBudgetPct, category = selectedCategoryOverride) => {
    if (!project || !project.id) return;
    setIsLoadingDynamic(true);
    try {
      const data = await api.getDynamicSamples(project.id, maxPct, category || undefined);
      if (data) {
        setDynamicResponse(data);
      }
    } catch (err) {
      console.warn("Failed to load dynamic samples:", err);
    } finally {
      setIsLoadingDynamic(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'graphics' && project && project.id) {
      fetchDynamicSamples();
    }
  }, [project.id, activeTab]);

  const handleSuggest = async () => {
    if (!suggestInput.trim()) return;
    setIsSuggesting(true);
    try {
      const data = await api.suggestGraphics(suggestInput.trim());
      setSuggestions(data.suggestions || []);
    } catch (e) {
      console.error(e);
    } finally {
      setIsSuggesting(false);
    }
  };

  return (
    <aside className="w-84 bg-white border-r border-neutral-200 flex flex-col z-15 select-none shadow-xs text-neutral-900">
      {/* Sidebar Navigation Tabs */}
      <div className="flex border-b border-neutral-200 bg-neutral-100 p-1 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('subtitles')}
          className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition ${
            activeTab === 'subtitles' ? 'bg-white text-neutral-900 font-bold shadow-xs border border-neutral-200' : 'text-neutral-500 hover:text-neutral-900'
          }`}
        >
          <Type className="h-3.5 w-3.5 text-lime-600" />
          <span>Subtitles</span>
        </button>

        <button
          onClick={() => setActiveTab('graphics')}
          className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition ${
            activeTab === 'graphics' ? 'bg-white text-purple-600 font-bold shadow-xs border border-neutral-200' : 'text-neutral-500 hover:text-neutral-900'
          }`}
        >
          <Sparkles className="h-3.5 w-3.5 text-purple-600" />
          <span>Graphics & Visuals</span>
        </button>

        <button
          onClick={() => setActiveTab('projects')}
          className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition ${
            activeTab === 'projects' ? 'bg-white text-neutral-900 font-bold shadow-xs border border-neutral-200' : 'text-neutral-500 hover:text-neutral-900'
          }`}
        >
          <FolderOpen className="h-3.5 w-3.5" />
          <span>Projects</span>
        </button>
      </div>

      {/* TAB 1: Captions & Transcription */}
      {activeTab === 'subtitles' && (
        <div className="flex-1 flex flex-col overflow-hidden p-3 space-y-3">
          {/* Dialogue & Script Input Box */}
          <div className="bg-neutral-50 rounded-xl p-3 border border-neutral-200 space-y-2.5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono font-bold text-neutral-800 flex items-center gap-1.5">
                <Type className="h-3.5 w-3.5 text-lime-600" />
                <span>Video Script / Dialogue</span>
              </span>
              <span className="text-[10px] font-mono text-emerald-700 font-bold bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-300">
                Connected
              </span>
            </div>

            <textarea
              value={rawTextInput}
              onChange={(e) => setRawTextInput(e.target.value)}
              placeholder="Leave blank to automatically transcribe your uploaded video (Hindi, Hinglish, or English) using local Apple Silicon Whisper, or type custom script text here."
              rows={2}
              className="w-full bg-white border border-neutral-300 rounded-lg p-2.5 text-xs text-neutral-900 placeholder-neutral-400 outline-none focus:border-cyan-500 shadow-xs resize-none"
            />

            {/* Speed & Precision Selector */}
            <div className="flex items-center justify-between text-[11px] font-mono text-neutral-600 bg-white p-1.5 rounded-lg border border-neutral-200">
              <span className="flex items-center gap-1 font-semibold text-neutral-700">
                <Zap className="h-3.5 w-3.5 text-amber-500" />
                <span>Speed / Engine:</span>
              </span>
              <div className="flex items-center bg-neutral-100 p-0.5 rounded-md border border-neutral-200 text-[10px]">
                <button
                  type="button"
                  onClick={() => setTranscribeModelSize('base')}
                  className={`px-2 py-0.5 rounded font-bold transition ${
                    transcribeModelSize === 'base'
                      ? 'bg-lime text-black shadow-xs'
                      : 'text-neutral-500 hover:text-neutral-900'
                  }`}
                  title="Base model: ~10s fast turnaround (Optimized M2 Pro 8-thread CTranslate2)"
                >
                  ⚡ Fast (~10s)
                </button>
                <button
                  type="button"
                  onClick={() => setTranscribeModelSize('small')}
                  className={`px-2 py-0.5 rounded font-bold transition ${
                    transcribeModelSize === 'small'
                      ? 'bg-lime text-black shadow-xs'
                      : 'text-neutral-500 hover:text-neutral-900'
                  }`}
                  title="Small model: ~25s higher precision"
                >
                  🎯 Precision (~25s)
                </button>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={async () => {
                  try {
                    await onTranscribe(rawTextInput || undefined, wordsPerCap, undefined, transcribeModelSize);
                  } catch (e: any) {
                    alert('Transcription error: ' + (e.message || String(e)));
                  }
                }}
                disabled={isTranscribing}
                className={`flex-1 py-2.5 px-3 rounded-lg text-black font-black text-xs flex items-center justify-center gap-1.5 shadow-sm transition ${
                  isTranscribing
                    ? 'bg-lime/70 cursor-wait animate-pulse'
                    : 'bg-lime hover:bg-lime-400 active:scale-98'
                }`}
              >
                {isTranscribing ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-black" />
                    <span>Transcribing with Whisper ({transcribeModelSize === 'base' ? 'Fast' : 'Precision'})...</span>
                  </>
                ) : (
                  <>
                    <Wand2 className="h-3.5 w-3.5 stroke-[2.5]" />
                    <span>Auto-Transcribe Video</span>
                  </>
                )}
              </button>

              <button
                onClick={async () => {
                  try {
                    await onTranslate();
                  } catch (e: any) {
                    alert('Translation error: ' + (e.message || String(e)));
                  }
                }}
                disabled={isTranslating || isTranscribing}
                className={`py-2.5 px-3 rounded-lg font-bold text-xs flex items-center justify-center gap-1.5 border shadow-xs transition ${
                  isTranslating
                    ? 'bg-lime-50 border-lime-400 text-lime-800 animate-pulse cursor-wait'
                    : 'bg-white hover:bg-neutral-50 text-neutral-800 border-neutral-300 active:scale-98'
                }`}
                title="Translate Hindi / Hinglish to English"
              >
                {isTranslating ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-lime" />
                    <span>Translating...</span>
                  </>
                ) : (
                  <>
                    <Languages className="h-3.5 w-3.5 text-lime" />
                    <span>Translate</span>
                  </>
                )}
              </button>
            </div>

            {/* Active AI Processing Banner */}
            {isTranscribing && (
              <div className="bg-lime/10 border border-lime/30 rounded-lg p-2 flex items-center gap-2 text-[10px] text-lime font-mono animate-pulse">
                <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0 text-lime" />
                <span>Whisper ({transcribeModelSize === 'base' ? 'Fast Base ~10s' : 'Precision Small ~25s'}) is transcribing on Apple Silicon M2 Pro hardware...</span>
              </div>
            )}
          </div>

          {/* Language & Pacing Config */}
          <div className="flex items-center justify-between px-1 text-[11px] font-mono text-neutral-600">
            <span className="flex items-center gap-1">
              Detected: <strong className="text-neutral-900 uppercase font-bold">{project.detected_language}</strong>
            </span>
            <div className="flex items-center gap-1">
              <span>Words/line:</span>
              <select
                value={wordsPerCap}
                onChange={(e) => setWordsPerCap(Number(e.target.value))}
                className="bg-white border border-neutral-300 text-neutral-800 rounded px-1 py-0.5 outline-none font-bold shadow-xs"
              >
                <option value={3}>3 words</option>
                <option value={4}>4 words</option>
                <option value={5}>5 words</option>
              </select>
            </div>
          </div>

          {/* Subtitle Lines Configuration (1 Line vs 2 Lines) */}
          <div className="flex items-center justify-between px-2 py-1.5 bg-neutral-50 rounded-lg border border-neutral-200 text-[10px] font-mono shadow-xs">
            <span className="text-neutral-600 font-bold uppercase pl-0.5">Subtitle Lines:</span>
            <div className="flex items-center gap-1 bg-white p-0.5 rounded-md border border-neutral-200 shadow-xs">
              <button
                onClick={() => onReformatLines && onReformatLines(1)}
                className={`px-2.5 py-0.5 rounded transition ${
                  (activeLinesMode ?? 1) === 1
                    ? 'bg-lime text-black font-black shadow-xs'
                    : 'text-neutral-500 hover:text-neutral-900'
                }`}
                title="Single line per subtitle (punchy Reels/Shorts pacing)"
              >
                1 Line
              </button>
              <button
                onClick={() => onReformatLines && onReformatLines(2)}
                className={`px-2.5 py-0.5 rounded transition ${
                  activeLinesMode === 2
                    ? 'bg-lime text-black font-black shadow-xs'
                    : 'text-neutral-500 hover:text-neutral-900'
                }`}
                title="Two lines per subtitle (balanced dual-line standard)"
              >
                2 Lines
              </button>
            </div>
          </div>

          {/* Auto-Detect Medical & Impact Keywords Button */}
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
              className={`w-full py-1.5 px-2 rounded-lg text-[10px] font-mono font-black border transition flex items-center justify-center gap-1.5 shadow-xs ${
                isDetectingKw
                  ? "bg-lime/70 text-black border-lime cursor-wait animate-pulse"
                  : "bg-white hover:bg-neutral-50 text-neutral-900 border-neutral-300 hover:border-lime-500"
              }`}
            >
              <Sparkles className="w-3 h-3 text-lime-600" />
              <span>{isDetectingKw ? "Scanning Dialogue..." : "⚡ Auto-Detect Medical & Impact Keywords"}</span>
            </button>
          )}

          {/* Language View Switcher Pill */}
          <div className="flex items-center justify-between px-2 py-1.5 bg-neutral-50 rounded-lg border border-neutral-200 text-[10px] font-mono shadow-xs">
            <span className="text-neutral-600 font-bold uppercase pl-0.5">Display:</span>
            <div className="flex items-center gap-1 bg-white p-0.5 rounded-md border border-neutral-200 shadow-xs">
              <button
                onClick={() => activeLanguageView !== 'english' && onToggleLanguageView()}
                className={`px-2 py-0.5 rounded transition ${
                  activeLanguageView === 'english'
                    ? 'bg-neutral-900 text-white font-bold'
                    : 'text-neutral-500 hover:text-neutral-900'
                }`}
              >
                English
              </button>
              <button
                onClick={() => activeLanguageView !== 'hindi' && onToggleLanguageView()}
                className={`px-2 py-0.5 rounded transition ${
                  activeLanguageView === 'hindi'
                    ? 'bg-neutral-900 text-white font-bold'
                    : 'text-neutral-500 hover:text-neutral-900'
                }`}
              >
                Hindi / Orig
              </button>
            </div>
          </div>

          {/* Captions List */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {project.captions.map((c, idx) => {
              const isSelected = c.id === selectedCaptionId;
              const displayText =
                activeLanguageView === 'english'
                  ? (c.translated_text || c.text)
                  : c.text;

              return (
                <div
                  key={c.id}
                  onClick={() => {
                    onSelectCaption(c.id);
                    onTimeSeek(c.start);
                  }}
                  className={`p-2.5 rounded-xl border text-xs cursor-pointer transition shadow-xs ${
                    isSelected
                      ? 'bg-lime-50/80 border-lime-500 ring-1 ring-lime-500 text-neutral-900'
                      : 'bg-white hover:bg-neutral-50 border-neutral-200 text-neutral-800'
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] font-mono text-neutral-500 mb-1">
                    <span className="text-lime-700 font-bold">#{idx + 1}</span>
                    <span>
                      {c.start.toFixed(1)}s – {c.end.toFixed(1)}s
                    </span>
                  </div>
                  <div className="font-medium text-neutral-900 line-clamp-2">
                    {displayText}
                  </div>
                  {c.translated_text && c.translated_text !== c.text && (
                    <div className="text-[10px] text-neutral-500 italic line-clamp-1 mt-0.5">
                      {activeLanguageView === 'english' ? `Orig: ${c.text}` : `EN: ${c.translated_text}`}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 2: Motion Graphics & Dynamic Video Proposals */}
      {activeTab === 'graphics' && (
        <div className="flex-1 flex flex-col overflow-hidden p-3 space-y-3">
          {/* 5-Mode Selector: AI Cues & Dimensions | Gemini Flow | B-Roll & Assets | Article | Library */}
          <div className="flex bg-neutral-100 p-0.5 rounded-xl border border-neutral-200 text-[10px] font-semibold select-none shadow-xs">
            <button
              onClick={() => setGraphicsViewMode('cues')}
              className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1 transition ${
                graphicsViewMode === 'cues'
                  ? 'bg-white text-cyan-700 font-bold border border-neutral-200 shadow-xs'
                  : 'text-neutral-500 hover:text-neutral-900'
              }`}
              title="Spatial Layout, Dimensions (e.g. 7 CM), 50/50 Split Screens & Reasoning Log"
            >
              <Wand2 className="h-3 w-3 text-cyan-600" />
              <span>AI Cues</span>
            </button>
            <button
              onClick={() => setGraphicsViewMode('flow')}
              className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1 transition ${
                graphicsViewMode === 'flow'
                  ? 'bg-white text-purple-700 font-bold border border-neutral-200 shadow-xs'
                  : 'text-neutral-500 hover:text-neutral-900'
              }`}
              title="Gemini Flow: AI Camera Motion & Video Generation"
            >
              <Sparkles className="h-3 w-3 text-purple-600" />
              <span>Flow</span>
            </button>
            <button
              onClick={() => {
                setGraphicsViewMode('broll');
                if (brollResults.length === 0) {
                  handleBrollSearch('doctor hospital', brollMediaType);
                }
              }}
              className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1 transition ${
                graphicsViewMode === 'broll'
                  ? 'bg-white text-emerald-700 font-bold border border-neutral-200 shadow-xs'
                  : 'text-neutral-500 hover:text-neutral-900'
              }`}
              title="Multi-provider B-roll search (Pexels, Pixabay, Wikimedia, CRT cutaways)"
            >
              <Film className="h-3 w-3 text-emerald-600" />
              <span>B-Roll</span>
            </button>
            <button
              onClick={() => setGraphicsViewMode('article')}
              className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1 transition ${
                graphicsViewMode === 'article'
                  ? 'bg-white text-amber-700 font-bold border border-neutral-200 shadow-xs'
                  : 'text-neutral-500 hover:text-neutral-900'
              }`}
              title="Investigative Report & Press Article Card"
            >
              <FileText className="h-3 w-3 text-amber-600" />
              <span>Article</span>
            </button>
            <button
              onClick={() => setGraphicsViewMode('standard')}
              className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1 transition ${
                graphicsViewMode === 'standard'
                  ? 'bg-white text-neutral-800 font-bold border border-neutral-200 shadow-xs'
                  : 'text-neutral-500 hover:text-neutral-900'
              }`}
              title="Fusion Motion Graphic Templates Library"
            >
              <Layers className="h-3 w-3 text-neutral-600" />
              <span>Library</span>
            </button>
          </div>

          {/* MODE 1: Spatial & AI Cues (Dimensions '7 CM', 50/50 Splits, Beats & Reasoning Log) */}
          {graphicsViewMode === 'cues' && (
            <div className="flex-1 flex flex-col overflow-hidden space-y-2.5">
              {/* Quick AI Action Toolbar */}
              <div className="bg-neutral-950 p-2.5 rounded-xl border border-neutral-800 space-y-2 text-xs select-none">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-bold text-lime uppercase flex items-center gap-1">
                    <Sparkles className="h-3 w-3 text-lime" />
                    <span>AI Production & Spatial Cues</span>
                  </span>
                  {hasReasoningLog && (
                    <span className="text-[9px] font-mono bg-lime/20 text-lime px-1.5 py-0.5 rounded border border-lime/40">
                      Reasoning Ready
                    </span>
                  )}
                </div>

                <div className="space-y-1.5">
                  {onRerunAutoProduction && (
                    <button
                      onClick={() => onRerunAutoProduction(true)}
                      disabled={isAutoProducing}
                      className="w-full py-2 px-2.5 rounded-lg bg-lime hover:bg-lime-400 text-black font-black text-xs transition flex items-center justify-center gap-1.5 shadow"
                      title="Re-runs transcription, Twelve Labs indexing, and generates 7CM dimension callouts & split-screens"
                    >
                      {isAutoProducing ? (
                        <>
                          <Loader2 className="h-3.5 w-3.5 animate-spin text-black" />
                          <span>Running AI Production Pipeline...</span>
                        </>
                      ) : (
                        <>
                          <Zap className="h-3.5 w-3.5 fill-black" />
                          <span>⚡ Re-Run AI Production (12Labs + Cues)</span>
                        </>
                      )}
                    </button>
                  )}

                  <div className="grid grid-cols-2 gap-1.5">
                    {onDetectDimensionsAndCues && (
                      <button
                        onClick={async () => {
                          setIsDetectingCues(true);
                          try {
                            await onDetectDimensionsAndCues();
                          } finally {
                            setIsDetectingCues(false);
                          }
                        }}
                        disabled={isDetectingCues}
                        className="py-1.5 px-2 rounded-lg text-[10px] font-mono font-bold bg-neutral-900 hover:bg-neutral-800 text-cyan-300 border border-neutral-700 flex items-center justify-center gap-1"
                      >
                        <Wand2 className="w-3 h-3 text-cyan-400" />
                        <span>{isDetectingCues ? "Analyzing..." : "Detect Cues"}</span>
                      </button>
                    )}

                    {onOpenReasoningLog && (
                      <button
                        onClick={onOpenReasoningLog}
                        className="py-1.5 px-2 rounded-lg text-[10px] font-mono font-bold bg-neutral-900 hover:bg-neutral-800 text-neutral-200 border border-neutral-700 flex items-center justify-center gap-1"
                      >
                        <Brain className="w-3 h-3 text-lime" />
                        <span>Reasoning Log</span>
                      </button>
                    )}
                  </div>
                </div>
              </div>
              {/* Category & AI Budget Header Bar */}
              <div className="p-2.5 rounded-xl bg-neutral-950 border border-neutral-800/80 space-y-2 select-none">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-mono text-neutral-400 uppercase">Category:</span>
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 capitalize">
                      {dynamicResponse?.category || 'Detecting...'}
                    </span>
                  </div>
                  <button
                    onClick={() => fetchDynamicSamples(selectedMaxBudgetPct, selectedCategoryOverride)}
                    disabled={isLoadingDynamic}
                    title="Re-analyze video beats and refresh proposals"
                    className="px-2 py-0.5 rounded bg-neutral-900 hover:bg-neutral-800 text-neutral-300 border border-neutral-700 transition flex items-center gap-1 text-[10px] font-mono"
                  >
                    <RefreshCw className={`h-3 w-3 text-cyan-400 ${isLoadingDynamic ? 'animate-spin' : ''}`} />
                    <span>Refresh</span>
                  </button>
                </div>

                {/* AI Visual Treatment Budget Meter */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[10px] font-mono text-neutral-400">
                    <span>AI Treatment Runtime Budget:</span>
                    <span className="text-white font-bold">
                      {dynamicResponse
                        ? `${dynamicResponse.total_enhanced_seconds}s / ${dynamicResponse.total_runtime_seconds}s (${dynamicResponse.budget_pct_used}%)`
                        : '--'}
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-neutral-800 rounded-full overflow-hidden flex">
                    <div
                      className="h-full bg-gradient-to-r from-cyan-400 to-purple-500 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, dynamicResponse?.budget_pct_used || 0)}%` }}
                    />
                  </div>
                </div>

                {/* Budget % Pills */}
                <div className="flex items-center justify-between pt-0.5 text-[9px] font-mono">
                  <span className="text-neutral-500">Max Runtime Cap:</span>
                  <div className="flex gap-1">
                    {[15, 25, 35].map((pct) => (
                      <button
                        key={pct}
                        onClick={() => {
                          setSelectedMaxBudgetPct(pct);
                          fetchDynamicSamples(pct, selectedCategoryOverride);
                        }}
                        className={`px-1.5 py-0.5 rounded transition ${
                          selectedMaxBudgetPct === pct
                            ? 'bg-cyan-900 text-cyan-200 font-bold border border-cyan-600'
                            : 'bg-neutral-900 text-neutral-400 hover:text-white'
                        }`}
                      >
                        {pct}%
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Dynamic Sample Cards List */}
              <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
                {isLoadingDynamic ? (
                  <div className="flex flex-col items-center justify-center p-8 space-y-3 text-neutral-400">
                    <Loader2 className="h-6 w-6 animate-spin text-cyan-400" />
                    <span className="text-xs font-mono">Synthesizing dynamic samples...</span>
                  </div>
                ) : dynamicResponse && dynamicResponse.samples.length > 0 ? (
                  dynamicResponse.samples.map((sample: DynamicGraphicSample) => {
                    const isHook = sample.beat_type === 'hook';
                    const isFullSeq = sample.mode === 'full_sequence';

                    return (
                      <div
                        key={sample.sample_id}
                        className={`p-3 rounded-xl bg-neutral-900/80 border transition space-y-2 relative overflow-hidden ${
                          isHook
                            ? 'border-cyan-500/50 shadow-[0_0_15px_rgba(0,240,255,0.08)] ring-1 ring-cyan-500/30'
                            : 'border-neutral-800 hover:border-neutral-700'
                        }`}
                      >
                        {/* Timing Pill & Role Badges */}
                        <div className="flex items-center justify-between text-[10px] font-mono">
                          <button
                            onClick={() => onTimeSeek(sample.start_time)}
                            title="Jump playhead to this beat"
                            className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-200 hover:bg-neutral-700 hover:text-white transition"
                          >
                            <Clock className="h-3 w-3 text-cyan-400" />
                            <span>
                              {sample.start_time.toFixed(1)}s - {sample.end_time.toFixed(1)}s
                            </span>
                            <span className="text-neutral-500">({sample.duration_seconds}s)</span>
                          </button>

                          <div className="flex items-center gap-1">
                            <span
                              className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${
                                isHook
                                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-800/80'
                                  : sample.beat_type === 'payoff'
                                  ? 'bg-purple-950 text-purple-300 border border-purple-800/80'
                                  : 'bg-amber-950 text-amber-300 border border-amber-800/80'
                              }`}
                            >
                              {isHook ? '🎣 Hook' : sample.beat_type === 'payoff' ? '💥 Payoff' : '📑 Evidence'}
                            </span>

                            <span
                              className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                                isFullSeq
                                  ? 'bg-neutral-800 text-neutral-200'
                                  : 'bg-amber-900/30 text-amber-300 border border-amber-800/50'
                              }`}
                            >
                              {isFullSeq ? 'Full Seq' : 'Bg Only'}
                            </span>
                          </div>
                        </div>

                        {/* Dialogue context snippet */}
                        <div className="text-[11px] text-neutral-300 italic font-medium line-clamp-2 pl-2 border-l-2 border-neutral-700">
                          "{sample.dialogue_snippet || sample.reason}"
                        </div>

                        {/* Generated Headline */}
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-black text-white font-mono tracking-wide">
                            {sample.overlay_headline}
                          </span>
                          <span className="text-[10px] font-mono text-cyan-400 font-semibold">
                            {(sample.visual_type || sample.template_id || 'documentary_visual').replace(/_/g, ' ')}
                          </span>
                        </div>

                        {/* AI Director Camera Movement & Prompt */}
                        <div className="bg-neutral-950/70 p-2 rounded-lg border border-neutral-800 text-[10px] space-y-1">
                          <div className="flex items-center justify-between font-mono text-neutral-400">
                            <span className="flex items-center gap-1">
                              <Camera className="h-3 w-3 text-cyan-400" />
                              <span>{sample.camera_motion.replace(/_/g, ' ')}</span>
                            </span>
                            <span className="flex items-center gap-1">
                              <Compass className="h-3 w-3 text-purple-400" />
                              <span>{sample.motion_intensity || 'cinematic'}</span>
                            </span>
                          </div>
                          <p className="text-neutral-400 line-clamp-2 font-sans">{sample.prompt}</p>
                        </div>

                        {/* 1-Click Action Buttons */}
                        <div className="grid grid-cols-2 gap-1.5 pt-1">
                          <button
                            onClick={() => {
                              onAddGraphic(
                                sample.visual_type || sample.template_id,
                                {
                                  broll_title: sample.overlay_headline,
                                  prompt: sample.prompt,
                                  camera_motion: sample.camera_motion,
                                  motion_intensity: sample.motion_intensity || 'cinematic',
                                  track: 'V3',
                                  animation: sample.camera_motion.includes('zoom') ? 'slow_zoom_in' : 'none'
                                },
                                sample.start_time,
                                sample.end_time,
                                sample.overlay_headline
                              );
                              onTimeSeek(sample.start_time);
                            }}
                            className="py-1.5 rounded-lg bg-cyan-900/60 hover:bg-cyan-800 text-cyan-200 font-bold text-xs border border-cyan-700/60 hover:text-white transition flex items-center justify-center gap-1"
                          >
                            <Plus className="h-3 w-3 text-cyan-300" />
                            <span>Add to Timeline</span>
                          </button>

                          <button
                            onClick={() => {
                              onTimeSeek(sample.start_time);
                              if (onDirectToOmni) {
                                onDirectToOmni(sample.prompt, sample.camera_motion, sample.overlay_headline);
                              }
                            }}
                            className="py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-cyan-300 font-bold text-xs border border-cyan-800/50 hover:text-white transition flex items-center justify-center gap-1"
                          >
                            <Sparkles className="h-3 w-3 text-cyan-400" />
                            <span>Direct Omni</span>
                          </button>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="p-6 text-center text-neutral-400 text-xs">
                    No beats analyzed yet. Click Refresh to analyze video transcript.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* MODE 2: Article Reconstruction Engine (Screenshot 5) */}
          {graphicsViewMode === 'article' && (
            <div className="flex-1 flex flex-col overflow-y-auto space-y-3 pr-1">
              <div className="bg-neutral-950 p-3 rounded-xl border border-neutral-800 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-amber-300 flex items-center gap-1.5">
                    <FileText className="w-4 h-4 text-amber-400" />
                    <span>Article Reconstructor (Track V4)</span>
                  </span>
                  <span className="text-[9px] font-mono text-cyan-300 bg-cyan-950/80 px-1.5 py-0.5 rounded border border-cyan-800/60">
                    Screenshot 5
                  </span>
                </div>

                <p className="text-[10px] text-neutral-400 leading-relaxed">
                  Paste a news or medical article URL or paragraph text. Automatically pulls the authentic publisher logo/masthead, headline, matching context paragraph, and animates a kinetic fluorescent highlighter!
                </p>

                {/* URL Input */}
                <div>
                  <label className="text-[10px] font-mono text-neutral-400 block mb-1">
                    ARTICLE URL:
                  </label>
                  <input
                    type="text"
                    value={articleInputUrl}
                    onChange={(e) => setArticleInputUrl(e.target.value)}
                    placeholder="https://scroll.in/latest/... or nejm.org/..."
                    className="w-full bg-neutral-900 border border-neutral-700/80 rounded-lg p-2 text-xs text-white placeholder-neutral-500 font-mono outline-none focus:border-amber-400"
                  />
                </div>

                {/* Or Pasted Text */}
                <div>
                  <label className="text-[10px] font-mono text-neutral-400 block mb-1">
                    OR PASTE ARTICLE TEXT / QUOTE:
                  </label>
                  <textarea
                    value={articlePastedText}
                    onChange={(e) => setArticlePastedText(e.target.value)}
                    rows={2}
                    placeholder="Paste headline and paragraph text here..."
                    className="w-full bg-neutral-900 border border-neutral-700/80 rounded-lg p-2 text-xs text-white placeholder-neutral-500 font-mono outline-none focus:border-amber-400 resize-none"
                  />
                </div>

                {/* Action Button */}
                <button
                  onClick={() => handleParseArticle()}
                  disabled={isParsingArticle || (!articleInputUrl.trim() && !articlePastedText.trim())}
                  className="w-full py-2 rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black font-black text-xs flex items-center justify-center gap-1.5 transition shadow"
                >
                  {isParsingArticle ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Parsing Article & Matching Quote...</span>
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-3.5 h-3.5" />
                      <span>⚡ Reconstruct Article & Extract Quote</span>
                    </>
                  )}
                </button>
              </div>

              {/* 1-Click Curated Presets from Reference Screenshots */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-mono text-neutral-400 uppercase tracking-wider block">
                  1-Click Investigative Presets:
                </span>
                <div className="grid grid-cols-2 gap-1.5 text-[10px] font-mono">
                  <button
                    onClick={() => handleParseArticle('scroll_doctor_assault')}
                    className="p-2 rounded-lg bg-neutral-900 hover:bg-neutral-850 border border-amber-500/40 hover:border-amber-400 text-left transition"
                  >
                    <div className="font-bold text-amber-300">📰 Scroll.in (SS5)</div>
                    <div className="text-[9px] text-neutral-400 truncate">Doctor Resigns Case</div>
                  </button>

                  <button
                    onClick={() => handleParseArticle('nejm_respiratory')}
                    className="p-2 rounded-lg bg-neutral-900 hover:bg-neutral-850 border border-neutral-800 hover:border-cyan-400 text-left transition"
                  >
                    <div className="font-bold text-cyan-300">🩺 NEJM Journal</div>
                    <div className="text-[9px] text-neutral-400 truncate">Pulmonary Sequelae</div>
                  </button>

                  <button
                    onClick={() => handleParseArticle('lancet_oncology')}
                    className="p-2 rounded-lg bg-neutral-900 hover:bg-neutral-850 border border-neutral-800 hover:border-lime text-left transition"
                  >
                    <div className="font-bold text-lime">🔬 The Lancet</div>
                    <div className="text-[9px] text-neutral-400 truncate">Oncology Biopsy Trial</div>
                  </button>

                  <button
                    onClick={() => handleParseArticle('bbc_medical')}
                    className="p-2 rounded-lg bg-neutral-900 hover:bg-neutral-850 border border-neutral-800 hover:border-white text-left transition"
                  >
                    <div className="font-bold text-white">🌍 BBC News</div>
                    <div className="text-[9px] text-neutral-400 truncate">Hospital Investigation</div>
                  </button>
                </div>
              </div>

              {/* Live Preview & Configuration Card */}
              {parsedArticleData && (
                <div className="bg-neutral-950 p-3 rounded-xl border border-neutral-800 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-neutral-400 uppercase">
                      Parsed Card Preview:
                    </span>
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-neutral-900 text-amber-300 border border-amber-500/30">
                      {parsedArticleData.publisher}
                    </span>
                  </div>

                  {/* Headline input */}
                  <div>
                    <span className="text-[9px] font-mono text-neutral-500 uppercase block">Headline:</span>
                    <input
                      type="text"
                      value={parsedArticleData.headline}
                      onChange={(e) => setParsedArticleData({ ...parsedArticleData, headline: e.target.value })}
                      className="w-full bg-neutral-900 border border-neutral-700/80 rounded p-1.5 text-xs text-white font-serif outline-none"
                    />
                  </div>

                  {/* Paragraph */}
                  <div>
                    <span className="text-[9px] font-mono text-neutral-500 uppercase block">Body Paragraph:</span>
                    <textarea
                      value={parsedArticleData.paragraph}
                      onChange={(e) => setParsedArticleData({ ...parsedArticleData, paragraph: e.target.value })}
                      rows={3}
                      className="w-full bg-neutral-900 border border-neutral-700/80 rounded p-1.5 text-[11px] text-neutral-300 font-serif outline-none resize-none"
                    />
                  </div>

                  {/* Highlight Quote */}
                  <div>
                    <span className="text-[9px] font-mono text-cyan-400 uppercase block">Highlighted Quote (Sweeping):</span>
                    <input
                      type="text"
                      value={parsedArticleData.highlight_quote}
                      onChange={(e) => setParsedArticleData({ ...parsedArticleData, highlight_quote: e.target.value })}
                      className="w-full bg-neutral-900 border border-cyan-500/50 rounded p-1.5 text-xs text-cyan-200 font-serif outline-none"
                    />
                  </div>

                  {/* Marker Color & Theme Choice */}
                  <div className="flex items-center justify-between pt-1 text-[10px] font-mono">
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
                          onClick={() => setParsedArticleData({ ...parsedArticleData, marker_color: c.hex })}
                          style={{ backgroundColor: c.hex }}
                          title={c.label}
                          className={`w-4 h-4 rounded-full transition ${
                            parsedArticleData.marker_color === c.hex ? 'ring-2 ring-white scale-110' : 'opacity-70 hover:opacity-100'
                          }`}
                        />
                      ))}
                    </div>

                    <div className="flex items-center gap-1">
                      <span className="text-neutral-400">Theme:</span>
                      <button
                        onClick={() => setParsedArticleData({
                          ...parsedArticleData,
                          paper_theme: parsedArticleData.paper_theme === 'dark_archival' ? 'editorial_clean' : 'dark_archival'
                        })}
                        className="px-1.5 py-0.5 rounded bg-neutral-850 text-neutral-300 border border-neutral-700"
                      >
                        {parsedArticleData.paper_theme === 'dark_archival' ? 'Dark' : 'Light'}
                      </button>
                    </div>
                  </div>

                  {/* Add to Timeline Button */}
                  <button
                    onClick={handleInsertArticleToTimeline}
                    className="w-full py-2.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-400 hover:from-amber-400 hover:to-amber-300 text-black font-black text-xs flex items-center justify-center gap-1.5 shadow transition"
                  >
                    <Plus className="w-3.5 h-3.5 stroke-[2.5]" />
                    <span>Add Reconstructed Article to Track V4</span>
                  </button>
                </div>
              )}
            </div>
          )}

          {/* MODE 3: Reusable Standard Template Library */}
          {graphicsViewMode === 'standard' && (
            <div className="flex-1 flex flex-col overflow-hidden space-y-3">
              {/* Category Filter Bar */}
              <div className="flex gap-1 overflow-x-auto pb-1 text-[10px] font-mono select-none">
                {['All', 'Spatial & Documentary', 'Evidence Visualizer', 'Metaphor Engine', 'Authority & Branding', 'Text', 'Social & Metaphor'].map((cat) => (
                  <button
                    key={cat}
                    onClick={() => setGraphicsCategory(cat)}
                    className={`px-2 py-0.5 rounded whitespace-nowrap transition ${
                      graphicsCategory === cat
                        ? "bg-purple-600 text-white font-bold shadow"
                        : "bg-neutral-800 text-neutral-400 hover:text-white"
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
                {templates
                  .filter((tpl) => graphicsCategory === 'All' || tpl.category === graphicsCategory)
                  .map((tpl) => (
                    <div
                      key={tpl.id}
                      className="p-3 rounded-xl bg-neutral-900/60 border border-neutral-800 hover:border-neutral-700 transition"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-bold text-white">{tpl.name}</span>
                        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-300">
                          {tpl.category}
                        </span>
                      </div>
                      <p className="text-[11px] text-neutral-400 mb-2 leading-relaxed">
                        {tpl.description}
                      </p>
                      <button
                        onClick={() => onAddGraphic(tpl.id, tpl.default_params)}
                        className="w-full py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-xs font-bold text-neutral-200 border border-neutral-700 hover:text-white transition flex items-center justify-center gap-1"
                      >
                        <Plus className="h-3 w-3 text-lime" />
                        <span>Add to Timeline</span>
                      </button>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* MODE 3: B-Roll & Archival Media Search (Multi-provider) */}
          {graphicsViewMode === 'broll' && (
        <div className="flex-1 flex flex-col overflow-hidden p-3 space-y-3">
          {/* Provider Status Diagnostic Bar */}
          <div className="bg-neutral-950/90 rounded-xl p-2 border border-neutral-800 text-[10px] font-mono space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-neutral-600 font-bold flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-cyan-600" />
                <span>Stock Providers & Keys</span>
              </span>
              <button
                onClick={() => setShowProviderModal(!showProviderModal)}
                className="text-[9px] text-cyan-600 hover:text-cyan-800 font-semibold flex items-center gap-0.5"
              >
                <span>{showProviderModal ? 'Hide Config' : 'Configure Keys'}</span>
              </button>
            </div>

            {/* Quick Status Badges */}
            <div className="grid grid-cols-4 gap-1 text-[9px]">
              {['pexels', 'pixabay', 'wikimedia', 'google_ai'].map((pKey) => {
                const info = providerStatuses?.[pKey];
                const isConn = info?.connected;
                const label = pKey === 'google_ai' ? 'Google' : pKey.charAt(0).toUpperCase() + pKey.slice(1);
                return (
                  <div
                    key={pKey}
                    className={`py-0.5 px-1 rounded text-center truncate border ${
                      isConn
                        ? 'bg-emerald-50 border-emerald-300 text-emerald-700 font-bold'
                        : 'bg-neutral-100 border-neutral-200 text-neutral-500'
                    }`}
                    title={info?.message || pKey}
                  >
                    {label}: {isConn ? '✓' : '✕'}
                  </div>
                );
              })}
            </div>

            {/* Detailed Key Diagnostics & Configuration Form */}
            {showProviderModal && (
              <div className="p-2.5 bg-white rounded-lg border border-neutral-200 space-y-2 mt-1 text-[10px] text-neutral-700 shadow-xs">
                <div className="flex justify-between items-center pb-1.5 border-b border-neutral-200 font-bold text-neutral-900">
                  <span>API Key Diagnostics & Setup</span>
                  <button onClick={refreshProviderStatuses} className="text-cyan-600 hover:text-cyan-800 flex items-center gap-0.5 text-[9px] font-semibold">
                    <RefreshCw className="w-2.5 h-2.5" /> Reload
                  </button>
                </div>

                {/* Live Status Summary */}
                <div className="space-y-1">
                  {['pexels', 'pixabay', 'wikimedia', 'google_ai'].map((pKey) => {
                    const info = providerStatuses?.[pKey];
                    const label = pKey === 'google_ai' ? 'Google Gemini' : pKey.charAt(0).toUpperCase() + pKey.slice(1);
                    return (
                      <div key={pKey} className="flex justify-between items-center py-0.5 text-[9px]">
                        <span className="text-neutral-500 font-medium">{label}:</span>
                        <span className={`font-mono px-1 py-0.2 rounded text-[9px] ${
                          info?.connected ? 'bg-emerald-50 text-emerald-700 font-bold' : 'bg-neutral-100 text-neutral-600'
                        }`}>
                          {info?.masked_key || 'Not configured'} ({info?.status || 'unconfigured'})
                        </span>
                      </div>
                    );
                  })}
                </div>

                {/* Input Fields to Set Keys */}
                <div className="space-y-1.5 pt-1.5 border-t border-neutral-200">
                  <div>
                    <label className="text-[9px] font-bold text-neutral-700 block mb-0.5">Pexels API Key:</label>
                    <input
                      type="password"
                      value={pexelsKeyInput}
                      onChange={(e) => setPexelsKeyInput(e.target.value)}
                      placeholder="Paste Pexels API Key (from pexels.com/api)"
                      className="w-full bg-neutral-50 border border-neutral-300 rounded px-2 py-1 text-[10px] text-neutral-900 placeholder-neutral-400 outline-none focus:border-cyan-500 font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[9px] font-bold text-neutral-700 block mb-0.5">Pixabay API Key:</label>
                    <input
                      type="password"
                      value={pixabayKeyInput}
                      onChange={(e) => setPixabayKeyInput(e.target.value)}
                      placeholder="Paste Pixabay API Key (from pixabay.com/api/docs)"
                      className="w-full bg-neutral-50 border border-neutral-300 rounded px-2 py-1 text-[10px] text-neutral-900 placeholder-neutral-400 outline-none focus:border-cyan-500 font-mono"
                    />
                  </div>
                  <div>
                    <label className="text-[9px] font-bold text-neutral-700 block mb-0.5">Google Gemini API Key:</label>
                    <input
                      type="password"
                      value={geminiKeyInput}
                      onChange={(e) => setGeminiKeyInput(e.target.value)}
                      placeholder="Paste Gemini API Key (AIzaSy...)"
                      className="w-full bg-neutral-50 border border-neutral-300 rounded px-2 py-1 text-[10px] text-neutral-900 placeholder-neutral-400 outline-none focus:border-cyan-500 font-mono"
                    />
                  </div>
                  <button
                    onClick={handleSaveApiKeys}
                    disabled={isSavingKeys}
                    className="w-full py-1 bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-[10px] rounded transition disabled:opacity-50 flex items-center justify-center gap-1 shadow-xs"
                  >
                    {isSavingKeys ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                    <span>Save Keys to .env</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Top action controls: Search input & Auto-match button */}
          <div className="space-y-2 bg-neutral-50 rounded-xl p-2.5 border border-neutral-200">
            {/* Search Input */}
            <div className="flex items-center gap-1.5">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={brollSearchQuery}
                  onChange={(e) => setBrollSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleBrollSearch()}
                  placeholder="Search Pexels & Pixabay stock..."
                  className="w-full bg-white border border-neutral-300 rounded-lg pl-7 pr-2 py-1.5 text-xs text-neutral-900 placeholder-neutral-400 outline-none focus:border-cyan-500 font-mono shadow-xs"
                />
                <Search className="w-3.5 h-3.5 text-neutral-400 absolute left-2 top-2" />
              </div>

              <button
                onClick={() => handleBrollSearch()}
                disabled={isSearchingBroll}
                className="bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs px-2.5 py-1.5 rounded-lg transition disabled:opacity-50 flex items-center gap-1 shadow-xs"
                title="Search Stock Visuals"
              >
                {isSearchingBroll ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Find'}
              </button>
            </div>

            {/* Auto Match Button */}
            <button
              onClick={handleAutoMatchCurrentCaption}
              disabled={isAutoMatchingBroll}
              className={`w-full py-1.5 px-2 rounded-lg text-[10px] font-mono font-black border transition flex items-center justify-center gap-1.5 shadow-xs ${
                isAutoMatchingBroll
                  ? "bg-cyan-100 text-cyan-800 border-cyan-300 cursor-wait animate-pulse"
                  : "bg-white hover:bg-neutral-50 text-cyan-700 border-neutral-300 hover:border-cyan-500"
              }`}
            >
              {isAutoMatchingBroll ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin text-cyan-700" />
                  <span>Matching to Current Caption...</span>
                </>
              ) : (
                <>
                  <Wand2 className="w-3 h-3 text-cyan-600" />
                  <span>⚡ Auto-Match B-Roll (Pexels &rarr; Pixabay &rarr; Stock)</span>
                </>
              )}
            </button>

            {/* Filter Bar: Media Type, Provider, Orientation & Upload */}
            <div className="space-y-1.5 pt-1.5 border-t border-neutral-200 text-[10px] font-mono">
              {/* Type and Provider Selectors */}
              <div className="flex items-center justify-between gap-1">
                {/* Media Type Filter */}
                <div className="flex items-center gap-1 bg-white p-0.5 rounded border border-neutral-200 shadow-xs">
                  <button
                    onClick={() => {
                      setBrollMediaType('image');
                      handleBrollSearch(brollSearchQuery || 'doctor hospital', 'image', brollProvider, brollOrientation);
                    }}
                    className={`px-2 py-0.5 rounded transition ${
                      brollMediaType === 'image'
                        ? 'bg-cyan-600 text-white font-black shadow-xs'
                        : 'text-neutral-600 hover:text-neutral-900'
                    }`}
                  >
                    Images
                  </button>
                  <button
                    onClick={() => {
                      setBrollMediaType('video');
                      handleBrollSearch(brollSearchQuery || 'hospital corridor', 'video', brollProvider, brollOrientation);
                    }}
                    className={`px-2 py-0.5 rounded transition ${
                      brollMediaType === 'video'
                        ? 'bg-cyan-600 text-white font-black shadow-xs'
                        : 'text-neutral-600 hover:text-neutral-900'
                    }`}
                  >
                    Clips
                  </button>
                </div>

                {/* Provider Selector */}
                <select
                  value={brollProvider}
                  onChange={(e) => {
                    const p = e.target.value as any;
                    setBrollProvider(p);
                    handleBrollSearch(brollSearchQuery || 'medical', brollMediaType, p, brollOrientation);
                  }}
                  className="bg-white border border-neutral-300 text-[10px] rounded px-1.5 py-0.5 text-neutral-800 outline-none shadow-xs font-medium"
                >
                  <option value="all">Waterfall: Pexels &rarr; Pixabay &rarr; Stock &rarr; Wiki</option>
                  <option value="pexels">Pexels Only</option>
                  <option value="pixabay">Pixabay Only</option>
                  <option value="wikimedia">Wikimedia (Fallback Only)</option>
                </select>

                {/* Orientation Selector */}
                <select
                  value={brollOrientation}
                  onChange={(e) => {
                    const ori = e.target.value as any;
                    setBrollOrientation(ori);
                    handleBrollSearch(brollSearchQuery || 'medical', brollMediaType, brollProvider, ori);
                  }}
                  className="bg-white border border-neutral-300 text-[10px] rounded px-1.5 py-0.5 text-neutral-800 outline-none shadow-xs font-medium"
                >
                  <option value="all">Any Ratio</option>
                  <option value="portrait">9:16 Portrait</option>
                  <option value="landscape">16:9 Landscape</option>
                </select>
              </div>

              {/* Custom File Upload */}
              <div className="flex justify-end pt-1">
                <label className="cursor-pointer flex items-center gap-1 px-2 py-1 rounded bg-white hover:bg-neutral-50 border border-neutral-300 text-neutral-700 hover:text-neutral-900 transition shadow-xs">
                  <Upload className="w-3 h-3 text-cyan-600" />
                  <span>{isUploadingAsset ? 'Uploading...' : 'Custom Upload'}</span>
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
          </div>

          {/* Quick Topic Chips */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[10px] font-mono scrollbar-none">
            {BROLL_TOPICS.map((topic) => (
              <button
                key={topic.label}
                onClick={() => {
                  setBrollActiveTopic(topic.label);
                  setBrollSearchQuery(topic.query);
                  handleBrollSearch(topic.query, brollMediaType, brollProvider, brollOrientation);
                }}
                className={`px-2 py-1 rounded whitespace-nowrap border transition ${
                  brollActiveTopic === topic.label
                    ? 'bg-cyan-950/80 border-cyan-400 text-cyan-300 font-bold'
                    : 'bg-neutral-900 border-neutral-800 text-neutral-400 hover:text-neutral-200'
                }`}
              >
                {topic.label}
              </button>
            ))}
          </div>

          {/* Video Preview Modal */}
          {previewingVideo && (
            <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 backdrop-blur-sm">
              <div className="bg-neutral-950 border border-neutral-800 rounded-2xl max-w-md w-full overflow-hidden shadow-2xl space-y-3 p-3">
                <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
                  <span className="font-bold text-xs text-white truncate max-w-[280px]">
                    {previewingVideo.title || 'Stock Video Preview'}
                  </span>
                  <button
                    onClick={() => setPreviewingVideo(null)}
                    className="p-1 rounded text-neutral-400 hover:text-white hover:bg-neutral-800"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
                  <video
                    src={previewingVideo.preview_url || previewingVideo.download_url || previewingVideo.url}
                    controls
                    autoPlay
                    playsInline
                    className="w-full h-full object-contain"
                  />
                </div>
                <div className="text-[10px] text-neutral-400 flex items-center justify-between">
                  <span>Source: {previewingVideo.source_credit || previewingVideo.provider}</span>
                  {previewingVideo.duration > 0 && <span>Duration: {previewingVideo.duration}s</span>}
                </div>
                <div className="grid grid-cols-3 gap-1 pt-1">
                  <button
                    onClick={() => {
                      handleAddSplitBroll(previewingVideo);
                      setPreviewingVideo(null);
                    }}
                    className="py-1.5 rounded bg-neutral-800 hover:bg-neutral-700 text-[10px] font-bold text-cyan-300 border border-cyan-500/30"
                  >
                    50/50 Split
                  </button>
                  <button
                    onClick={() => {
                      handleAddInsertBroll(previewingVideo);
                      setPreviewingVideo(null);
                    }}
                    className="py-1.5 rounded bg-neutral-800 hover:bg-neutral-700 text-[10px] font-bold text-lime border border-lime/30"
                  >
                    Insert Cut
                  </button>
                  <button
                    onClick={() => {
                      handleAddOverlayBroll(previewingVideo);
                      setPreviewingVideo(null);
                    }}
                    className="py-1.5 rounded bg-neutral-800 hover:bg-neutral-700 text-[10px] font-bold text-white border border-neutral-700"
                  >
                    Overlay
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Results Grid / List */}
          <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
            {brollResults.length === 0 && !isSearchingBroll && (
              <div className="text-center py-8 px-4 text-neutral-500 text-xs">
                <Film className="w-8 h-8 mx-auto mb-2 text-neutral-600" />
                <p className="font-semibold text-neutral-400">Search or auto-match documentary B-roll</p>
                <p className="text-[10px] text-neutral-500 mt-1">
                  Pexels, Pixabay, and Wikimedia search results will appear here. Click to preview or add to timeline.
                </p>
              </div>
            )}

            {isSearchingBroll && (
              <div className="flex flex-col items-center justify-center py-10 space-y-2">
                <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
                <span className="text-[11px] font-mono text-neutral-400">Searching stock & archival providers...</span>
              </div>
            )}

            {brollResults.map((item, idx) => {
              const isItemDownloading = downloadingItemId === (item.id || item.url);
              const isVideo = item.media_type === 'video';

              return (
                <div
                  key={idx}
                  className="bg-neutral-950/90 border border-neutral-800 rounded-xl overflow-hidden hover:border-neutral-700 transition flex flex-col"
                >
                  {/* Media Preview Header */}
                  <div
                    onClick={() => isVideo ? setPreviewingVideo(item) : undefined}
                    className={`relative aspect-video bg-neutral-900 overflow-hidden group ${isVideo ? 'cursor-pointer' : ''}`}
                  >
                    <img
                      src={item.thumb_url || item.url || item.media_url}
                      alt={item.title}
                      className="w-full h-full object-cover transition duration-300 group-hover:scale-105"
                      loading="lazy"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/30 pointer-events-none" />

                    {/* Top Provider and Type Badges */}
                    <div className="absolute top-2 left-2 flex items-center gap-1">
                      <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-black/70 backdrop-blur text-cyan-300 border border-cyan-400/30">
                        {isVideo ? '🎬 CLIP' : '📷 B-ROLL'}
                      </span>
                      {item.provider && (
                        <span className="text-[9px] font-mono px-1 py-0.5 rounded bg-black/60 text-neutral-300 uppercase">
                          {item.provider}
                        </span>
                      )}
                    </div>

                    {/* Play icon overlay on video */}
                    {isVideo && (
                      <div className="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/40 transition">
                        <div className="w-8 h-8 rounded-full bg-cyan-500/80 text-black flex items-center justify-center shadow-lg group-hover:scale-110 transition">
                          <Play className="w-4 h-4 fill-current ml-0.5" />
                        </div>
                      </div>
                    )}

                    {/* Duration badge */}
                    {item.duration > 0 && (
                      <span className="absolute top-2 right-2 text-[9px] font-mono px-1.5 py-0.5 rounded bg-black/80 text-neutral-300">
                        {Math.round(item.duration)}s
                      </span>
                    )}

                    <span className="absolute bottom-1.5 left-2 right-2 text-[10px] font-bold text-white line-clamp-1">
                      {item.title}
                    </span>
                  </div>

                  {/* Attribution & Actions Footer */}
                  <div className="p-2.5 space-y-2 bg-neutral-900/60">
                    <div className="flex items-center justify-between text-[9px] font-mono text-neutral-400">
                      <span className="truncate max-w-[200px]">
                        {item.source_credit || item.author || 'Source: Media Archives'}
                      </span>
                      <button
                        onClick={() => handleSaveToProject(item)}
                        disabled={isItemDownloading}
                        className="text-neutral-400 hover:text-white p-0.5 rounded hover:bg-neutral-800 transition"
                        title="Download locally to project media folder"
                      >
                        {isItemDownloading ? <Loader2 className="w-3 h-3 animate-spin text-cyan-400" /> : <Download className="w-3 h-3" />}
                      </button>
                    </div>

                    {/* 1-Click Action Buttons for Timeline */}
                    <div className="grid grid-cols-3 gap-1 pt-1">
                      <button
                        onClick={() => handleAddSplitBroll(item)}
                        disabled={isItemDownloading}
                        className="py-1 px-1 rounded bg-neutral-800 hover:bg-neutral-750 text-[9px] font-mono font-bold text-cyan-300 border border-cyan-500/30 hover:border-cyan-400 transition flex items-center justify-center gap-0.5 disabled:opacity-50"
                        title="Top Half B-Roll + Bottom Half Speaker (Screenshot 2)"
                      >
                        {isItemDownloading ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <Columns className="w-2.5 h-2.5" />}
                        <span>50/50 Split</span>
                      </button>

                      <button
                        onClick={() => handleAddInsertBroll(item)}
                        disabled={isItemDownloading}
                        className="py-1 px-1 rounded bg-neutral-800 hover:bg-neutral-750 text-[9px] font-mono font-bold text-lime border border-lime/30 hover:border-lime transition flex items-center justify-center gap-0.5 disabled:opacity-50"
                        title="Full Cutaway Cut with Scanlines (Screenshot 3 & 4)"
                      >
                        {isItemDownloading ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <Tv className="w-2.5 h-2.5" />}
                        <span>Insert Cut</span>
                      </button>

                      <button
                        onClick={() => handleAddOverlayBroll(item)}
                        disabled={isItemDownloading}
                        className="py-1 px-1 rounded bg-neutral-800 hover:bg-neutral-750 text-[9px] font-mono font-bold text-neutral-200 border border-neutral-700 hover:text-white transition flex items-center justify-center gap-0.5 disabled:opacity-50"
                        title="Full-screen B-Roll Overlay on V3"
                      >
                        {isItemDownloading ? <Loader2 className="w-2.5 h-2.5 animate-spin" /> : <Layers className="w-2.5 h-2.5" />}
                        <span>Overlay</span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* MODE 4: Gemini Flow & AI Motion Generation */}
      {graphicsViewMode === 'flow' && (
        <div className="flex-1 flex flex-col overflow-hidden">
          <AIMotionGraphicsPanel
            currentTime={currentTime || 0}
            project={project}
            activeCaptionText={project.captions.find(c => c.id === selectedCaptionId)?.text || ''}
            onAppendVideoTrack={onAppendVideoTrack || (() => {})}
            captureCurrentCanvasFrame={captureCurrentCanvasFrame || (() => null)}
            prefilledOmni={prefilledOmni}
          />
        </div>
      )}
    </div>
  )}


      {/* TAB 3: Projects List (Persistent Projects) */}
      {activeTab === 'projects' && (
        <div className="flex-1 flex flex-col overflow-hidden p-3 space-y-3">
          <button
            onClick={onNewProject}
            className="w-full py-2.5 rounded-xl bg-lime hover:bg-lime-400 text-black font-black text-xs flex items-center justify-center gap-1.5 shadow transition"
          >
            <Plus className="h-3.5 w-3.5 stroke-[2.5]" />
            <span>Create New Project</span>
          </button>

          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {projectsList.map((p) => {
              const isActive = p.id === project.id;
              return (
                <div
                  key={p.id}
                  onClick={() => onSwitchProject(p.id)}
                  className={`p-3 rounded-xl border text-xs cursor-pointer transition ${
                    isActive
                      ? 'bg-neutral-800/90 border-lime ring-1 ring-lime'
                      : 'bg-neutral-900/60 hover:bg-neutral-800/60 border-neutral-800'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-white truncate mr-2">{p.name}</span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[9px] font-mono px-1 bg-neutral-700 rounded text-neutral-300">
                        {p.aspect_ratio}
                      </span>
                      {onDeleteProject && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setDeleteConfirmId(p.id);
                          }}
                          className="p-1 rounded hover:bg-red-950/80 text-neutral-400 hover:text-red-400 transition"
                          title="Move project to macOS Trash Bin"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-[10px] font-mono text-neutral-400">
                    <span>{p.caption_count} Captions</span>
                    <span>{p.duration_seconds.toFixed(0)}s</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Project Delete Confirmation Modal */}
          {deleteConfirmId && (
            <div className="p-3 bg-red-950/60 border border-red-900 rounded-xl space-y-2 text-xs">
              <div className="flex items-start gap-2 text-red-300">
                <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-red-400" />
                <div>
                  <div className="font-bold text-white">Delete Project?</div>
                  <div className="text-[10px] text-neutral-300 mt-0.5">
                    Permanently delete <strong className="text-white">{projectsList.find(p => p.id === deleteConfirmId)?.name || deleteConfirmId}</strong>? All associated files will be removed from disk.
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-end gap-1.5 pt-1">
                <button
                  onClick={() => setDeleteConfirmId(null)}
                  disabled={isDeletingProject}
                  className="px-2 py-1 rounded bg-neutral-800 hover:bg-neutral-700 text-white text-[10px]"
                >
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    if (deleteConfirmId && onDeleteProject) {
                      setIsDeletingProject(true);
                      try {
                        await onDeleteProject(deleteConfirmId);
                      } finally {
                        setIsDeletingProject(false);
                        setDeleteConfirmId(null);
                      }
                    }
                  }}
                  disabled={isDeletingProject}
                  className="px-2.5 py-1 rounded bg-red-600 hover:bg-red-500 text-white font-bold text-[10px] flex items-center gap-1"
                >
                  {isDeletingProject ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />}
                  <span>Move to Trash</span>
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </aside>
  );
};
