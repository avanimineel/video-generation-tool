import React, { useState } from 'react';
import { VisualReasoningItem, api } from '../../services/api';
import { 
  Brain, 
  X, 
  Clock, 
  Image as ImageIcon, 
  Layout, 
  Layers, 
  ExternalLink, 
  Copy, 
  Check, 
  Search, 
  Sparkles, 
  Filter, 
  Play,
  CheckCircle2,
  XCircle,
  RefreshCw
} from 'lucide-react';

interface VisualReasoningLogModalProps {
  isOpen: boolean;
  onClose: () => void;
  reasoningLog: VisualReasoningItem[];
  onSeekTime?: (timeSeconds: number) => void;
  projectName?: string;
  projectId?: string;
  onOpenFeedbackDashboard?: () => void;
}

export const VisualReasoningLogModal: React.FC<VisualReasoningLogModalProps> = ({
  isOpen,
  onClose,
  reasoningLog,
  onSeekTime,
  projectName = "Active Project",
  projectId,
  onOpenFeedbackDashboard
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [copied, setCopied] = useState(false);
  const [decisionMap, setDecisionMap] = useState<Record<string, 'keep' | 'cut' | 'swap'>>({});
  const [loggingMap, setLoggingMap] = useState<Record<string, boolean>>({});

  const handleDecision = async (cue: VisualReasoningItem, decision: 'keep' | 'cut' | 'swap') => {
    const key = cue.graphic_id || `cue_${cue.cue_index}`;
    setDecisionMap(prev => ({ ...prev, [key]: decision }));
    setLoggingMap(prev => ({ ...prev, [key]: true }));
    try {
      await api.logDecision({
        project_id: projectId || projectName,
        cue_id: key,
        decision: decision,
        reasoning: cue.image_logic || cue.timestamp_logic,
        strength: (cue as any).strength || 0.8,
        graphic_type: cue.template_id || 'split_screen_vertical',
        start_sec: cue.timestamp_start,
        end_sec: cue.timestamp_end,
        search_query: cue.search_query || cue.trigger_term,
        transcript_context: cue.spoken_trigger_phrase,
        selected_asset: { url: cue.media_url }
      });
    } catch (e) {
      console.error('Failed to log decision:', e);
    } finally {
      setLoggingMap(prev => ({ ...prev, [key]: false }));
    }
  };

  if (!isOpen) return null;


  // Categories list
  const categories = ['all', ...Array.from(new Set(reasoningLog.map(r => r.cue_category || 'General Evidence')))];

  // Filtered log
  const filteredLog = reasoningLog.filter(item => {
    const matchesSearch = 
      item.spoken_trigger_phrase.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.trigger_term.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.template_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.timestamp_logic.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.image_logic.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesCat = selectedCategory === 'all' || item.cue_category === selectedCategory;
    return matchesSearch && matchesCat;
  });

  const handleCopyLog = () => {
    const textReport = reasoningLog.map((r, i) => `
[Cue ${i + 1}] ${r.template_name} @ ${r.timestamp_formatted} (${r.duration_sec}s)
Category: ${r.cue_category}
Trigger Phrase: "${r.spoken_trigger_phrase}" [Keyword: ${r.trigger_term}]
• Timestamp Logic: ${r.timestamp_logic}
• Image Selection: ${r.image_logic}
• Search Query: ${r.search_query}
• Layout Rationale: ${r.layout_logic}
• Pacing Buffer: ${r.pacing_logic}
${r.media_url ? `• Asset URL: ${r.media_url}` : ''}
--------------------------------------------------
`).join('\n');

    navigator.clipboard.writeText(`=== DAVINCI AI COMPANION - VISUAL CUE REASONING LOG ===\nProject: ${projectName}\nTotal Cues: ${reasoningLog.length}\n\n${textReport}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div 
        className="bg-white text-neutral-900 w-full max-w-5xl max-h-[90vh] rounded-2xl shadow-2xl border border-neutral-200 flex flex-col overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-neutral-200 flex items-center justify-between bg-neutral-50/80">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-lime-500/15 border border-lime-500/30 flex items-center justify-center text-lime-700 shadow-xs">
              <Brain className="h-5 w-5 stroke-[2.5]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-black tracking-tight text-neutral-900">
                  Visual Cue & Dimension Reasoning Log
                </h2>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-lime text-black uppercase tracking-wider">
                  AI Decision Engine
                </span>
              </div>
              <p className="text-xs text-neutral-500 mt-0.5">
                Transparent acoustic onset, visual evidence matching, and spatial layout rationale for each detected beat.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {onOpenFeedbackDashboard && (
              <button
                onClick={onOpenFeedbackDashboard}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-purple-50 hover:bg-purple-100 text-purple-800 border border-purple-200 transition shadow-xs"
                title="Open AI Feedback & Training Hub Dashboard"
              >
                <Brain className="h-3.5 w-3.5 text-purple-600" />
                <span>Training Hub</span>
              </button>
            )}
            <button
              onClick={handleCopyLog}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-white hover:bg-neutral-100 text-neutral-700 border border-neutral-200 transition shadow-xs"
              title="Copy formatted reasoning log to clipboard"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5 text-neutral-500" />}
              <span>{copied ? "Copied!" : "Copy Log"}</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-200/60 transition"
              title="Close modal"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

        </div>

        {/* Summary Bar & Filters */}
        <div className="px-6 py-3 border-b border-neutral-200 bg-white flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-4 text-neutral-600">
            <div className="flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-lime-600" />
              <span className="font-bold text-neutral-900">{reasoningLog.length}</span>
              <span>Total Cues Detected</span>
            </div>
            <span className="text-neutral-300">•</span>
            <div className="flex items-center gap-1.5">
              <Layers className="h-4 w-4 text-cyan-600" />
              <span className="font-bold text-neutral-900">
                {reasoningLog.filter(r => r.template_id === 'split_screen_vertical').length}
              </span>
              <span>50/50 Splits</span>
            </div>
            <span className="text-neutral-300">•</span>
            <div className="flex items-center gap-1.5">
              <Layout className="h-4 w-4 text-amber-600" />
              <span className="font-bold text-neutral-900">
                {reasoningLog.filter(r => r.template_id === 'dimension_callout').length}
              </span>
              <span>Dimensions</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Search Input */}
            <div className="relative">
              <Search className="h-3.5 w-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-400" />
              <input
                type="text"
                placeholder="Search cues, words, logic..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="pl-8 pr-3 py-1 text-xs rounded-lg bg-neutral-50 border border-neutral-200 text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-1 focus:ring-lime-500 w-48 sm:w-60"
              />
            </div>

            {/* Category Filter */}
            {categories.length > 2 && (
              <div className="flex items-center gap-1">
                <Filter className="h-3.5 w-3.5 text-neutral-400" />
                <select
                  value={selectedCategory}
                  onChange={e => setSelectedCategory(e.target.value)}
                  className="px-2 py-1 text-xs rounded-lg bg-neutral-50 border border-neutral-200 text-neutral-800 focus:outline-none focus:ring-1 focus:ring-lime-500 max-w-[160px] truncate font-medium"
                >
                  {categories.map(c => (
                    <option key={c} value={c}>
                      {c === 'all' ? 'All Categories' : c}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>

        {/* Cues List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-neutral-100/50">
          {filteredLog.length === 0 ? (
            <div className="text-center py-16 px-4">
              <div className="h-12 w-12 rounded-2xl bg-neutral-100 border border-neutral-200 flex items-center justify-center text-neutral-400 mx-auto mb-3">
                <Search className="h-6 w-6" />
              </div>
              <h3 className="text-sm font-bold text-neutral-800">No Cues Matched Your Filter</h3>
              <p className="text-xs text-neutral-500 mt-1 max-w-sm mx-auto">
                {searchTerm || selectedCategory !== 'all' 
                  ? "Try clearing your search query or selecting 'All Categories'." 
                  : "No action cues or dimension specifications were detected in the current subtitle dialogue."}
              </p>
            </div>
          ) : (
            filteredLog.map((cue, idx) => (
              <div 
                key={cue.graphic_id || idx}
                className="bg-white rounded-xl border border-neutral-200 p-4 shadow-xs hover:border-neutral-300 transition"
              >
                {/* Card Top Row */}
                <div className="flex flex-wrap items-center justify-between gap-2 mb-3 pb-2.5 border-b border-neutral-100">
                  <div className="flex items-center gap-2">
                    <span className="h-6 px-2 rounded-md bg-neutral-900 text-white font-mono text-[11px] font-bold flex items-center gap-1">
                      <Clock className="h-3 w-3 text-lime" />
                      {cue.timestamp_formatted}
                    </span>
                    <span className="text-[11px] font-mono text-neutral-400">
                      ({cue.duration_sec}s window)
                    </span>
                    <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-lime-100 text-lime-900 border border-lime-200">
                      {cue.template_name}
                    </span>
                    <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-700">
                      {cue.cue_category}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 ml-auto">
                    {/* Keep / Cut / Swap Judgment Buttons */}
                    {(() => {
                      const key = cue.graphic_id || `cue_${cue.cue_index}`;
                      const curDecision = decisionMap[key];
                      const isLogging = loggingMap[key];

                      return (
                        <div className="flex items-center gap-1 bg-neutral-100 p-0.5 rounded-lg border border-neutral-200">
                          <button
                            onClick={() => handleDecision(cue, 'keep')}
                            disabled={isLogging}
                            className={`px-2 py-0.5 rounded text-[11px] font-bold flex items-center gap-1 transition-all ${
                              curDecision === 'keep'
                                ? 'bg-emerald-600 text-white shadow-2xs'
                                : 'text-neutral-600 hover:text-emerald-700 hover:bg-emerald-50'
                            }`}
                            title="Keep: suggestion is good and elevated"
                          >
                            <CheckCircle2 className="h-3 w-3" />
                            <span>Keep</span>
                          </button>

                          <button
                            onClick={() => handleDecision(cue, 'cut')}
                            disabled={isLogging}
                            className={`px-2 py-0.5 rounded text-[11px] font-bold flex items-center gap-1 transition-all ${
                              curDecision === 'cut'
                                ? 'bg-rose-600 text-white shadow-2xs'
                                : 'text-neutral-600 hover:text-rose-700 hover:bg-rose-50'
                            }`}
                            title="Cut: suggestion should not have been made"
                          >
                            <XCircle className="h-3 w-3" />
                            <span>Cut</span>
                          </button>

                          <button
                            onClick={() => handleDecision(cue, 'swap')}
                            disabled={isLogging}
                            className={`px-2 py-0.5 rounded text-[11px] font-bold flex items-center gap-1 transition-all ${
                              curDecision === 'swap'
                                ? 'bg-amber-600 text-white shadow-2xs'
                                : 'text-neutral-600 hover:text-amber-700 hover:bg-amber-50'
                            }`}
                            title="Swap/Modify: moment was good but execution was changed"
                          >
                            <RefreshCw className="h-3 w-3" />
                            <span>Swap</span>
                          </button>
                        </div>
                      );
                    })()}

                    {onSeekTime && (
                      <button
                        onClick={() => onSeekTime(cue.timestamp_start)}
                        className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-neutral-100 hover:bg-lime hover:text-black text-neutral-700 text-[11px] font-bold transition"
                        title={`Seek video player to ${cue.timestamp_formatted}`}
                      >
                        <Play className="h-3 w-3 fill-current" />
                        <span>Seek</span>
                      </button>
                    )}
                  </div>
                </div>


                {/* Spoken Dialogue Beat */}
                <div className="mb-3 px-3 py-2 rounded-lg bg-neutral-50 border border-neutral-200/80 flex items-start gap-2">
                  <span className="text-neutral-400 font-serif italic text-sm mt-0.5">“</span>
                  <div className="text-xs text-neutral-800 leading-relaxed flex-1">
                    <span className="font-semibold text-neutral-900">{cue.spoken_trigger_phrase}</span>
                    <div className="mt-1 flex items-center gap-1.5 text-[11px] text-neutral-500">
                      <span>Detected Trigger:</span>
                      <span className="px-1.5 py-0.2 rounded bg-amber-100 text-amber-900 font-mono font-bold">
                        {cue.trigger_term}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Logic Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                  {/* Timestamp Logic */}
                  <div className="p-3 rounded-lg bg-neutral-50/70 border border-neutral-100">
                    <div className="flex items-center gap-1.5 font-bold text-neutral-900 mb-1">
                      <Clock className="h-3.5 w-3.5 text-blue-600" />
                      <span>Timestamp Choice Logic</span>
                    </div>
                    <p className="text-neutral-600 text-[11px] leading-relaxed">
                      {cue.timestamp_logic}
                    </p>
                  </div>

                  {/* Image / Media Logic */}
                  <div className="p-3 rounded-lg bg-neutral-50/70 border border-neutral-100">
                    <div className="flex items-center gap-1.5 font-bold text-neutral-900 mb-1">
                      <ImageIcon className="h-3.5 w-3.5 text-emerald-600" />
                      <span>Visual Evidence & Image Logic</span>
                    </div>
                    <p className="text-neutral-600 text-[11px] leading-relaxed mb-1.5">
                      {cue.image_logic}
                    </p>
                    {cue.search_query && (
                      <div className="flex items-center gap-1 text-[10px] text-neutral-500 font-mono">
                        <span className="font-semibold text-neutral-700">Query:</span>
                        <span className="bg-white px-1.5 py-0.5 rounded border border-neutral-200">
                          {cue.search_query}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Layout & Composition Logic */}
                  <div className="p-3 rounded-lg bg-neutral-50/70 border border-neutral-100">
                    <div className="flex items-center gap-1.5 font-bold text-neutral-900 mb-1">
                      <Layout className="h-3.5 w-3.5 text-purple-600" />
                      <span>Layout & Composition Rationale</span>
                    </div>
                    <p className="text-neutral-600 text-[11px] leading-relaxed">
                      {cue.layout_logic}
                    </p>
                  </div>

                  {/* Pacing & Spacing Logic */}
                  <div className="p-3 rounded-lg bg-neutral-50/70 border border-neutral-100">
                    <div className="flex items-center gap-1.5 font-bold text-neutral-900 mb-1">
                      <Layers className="h-3.5 w-3.5 text-amber-600" />
                      <span>Pacing & Cognitive Buffer</span>
                    </div>
                    <p className="text-neutral-600 text-[11px] leading-relaxed">
                      {cue.pacing_logic}
                    </p>
                  </div>
                </div>

                {/* Media Thumbnail & Citation Footer */}
                {cue.media_url && (
                  <div className="mt-3 pt-2.5 border-t border-neutral-100 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      {cue.media_thumb ? (
                        <img 
                          src={cue.media_thumb} 
                          alt={cue.trigger_term} 
                          className="h-10 w-16 object-cover rounded-md border border-neutral-200"
                        />
                      ) : (
                        <div className="h-10 w-16 bg-neutral-100 rounded-md flex items-center justify-center text-neutral-400">
                          <ImageIcon className="h-4 w-4" />
                        </div>
                      )}
                      <div>
                        <div className="text-[11px] font-bold text-neutral-800 truncate max-w-xs">
                          {cue.source_provider || "Curated Documentary Evidence"}
                        </div>
                        <div className="text-[10px] text-neutral-400">
                          {cue.media_type === 'video' ? 'Motion Video Cutaway' : 'Editorial High-Res Still'}
                        </div>
                      </div>
                    </div>

                    <a 
                      href={cue.media_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-[11px] font-semibold text-neutral-500 hover:text-neutral-900 transition"
                    >
                      <span>View Asset</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-neutral-200 bg-neutral-50 flex items-center justify-between text-xs text-neutral-500">
          <div>
            Showing <span className="font-bold text-neutral-800">{filteredLog.length}</span> of {reasoningLog.length} decision cues
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-neutral-900 text-white font-bold hover:bg-neutral-800 transition"
          >
            Done Reviewing
          </button>
        </div>
      </div>
    </div>
  );
};
