import {FeedbackComposer} from './FeedbackComposer';
import {ProjectState} from '../../types';
import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, XCircle, RefreshCw, Filter, Copy, Check, 
  Sparkles, Download, ArrowRight, ShieldAlert, SlidersHorizontal, 
  Clock, Hash, Brain, Layers, Tag
} from 'lucide-react';
import { api } from '../../services/api';
import { EditorialDecision, FeedbackStats, FewShotExportResponse } from '../../types';

interface EditorialFeedbackModalProps {
  project: ProjectState;
  currentTime: number;
  onUpdated: (p:ProjectState)=>void;
  isOpen: boolean;
  onClose: () => void;
  currentProjectId?: string;
  onJumpToTime?: (seconds: number) => void;
}

export const EditorialFeedbackModal: React.FC<EditorialFeedbackModalProps> = ({
  project, currentTime, onUpdated,
  isOpen,
  onClose,
  currentProjectId,
  onJumpToTime
}) => {
  const [activeTab, setActiveTab] = useState<'decisions' | 'few_shot'>('decisions');
  const [decisions, setDecisions] = useState<EditorialDecision[]>([]);
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [fewShotData, setFewShotData] = useState<FewShotExportResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  // Filters
  const [filterDecision, setFilterDecision] = useState<string>('all');
  const [filterGraphicType, setFilterGraphicType] = useState<string>('all');
  const [filterMinStrength, setFilterMinStrength] = useState<number>(0.0);
  const [filterProject, setFilterProject] = useState<string>(currentProjectId || 'all');

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [statsRes, decisionsRes] = await Promise.all([
        api.getFeedbackStats(filterProject),
        api.getFeedbackDecisions({
          decision: filterDecision,
          graphic_type: filterGraphicType,
          min_strength: filterMinStrength > 0 ? filterMinStrength : undefined,
          project_id: filterProject,
          limit: 150
        })
      ]);
      setStats(statsRes);
      setDecisions(decisionsRes.decisions || []);

      if (activeTab === 'few_shot') {
        const exportRes = await api.getFewShotExport();
        setFewShotData(exportRes);
      }
    } catch (e) {
      console.error('Failed to load feedback data:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadData();
    }
  }, [isOpen, filterDecision, filterGraphicType, filterMinStrength, filterProject, activeTab]);

  useEffect(()=>{if(isOpen)setFilterProject(currentProjectId||'all');},[isOpen,currentProjectId]);
  if (!isOpen) return null;

  const handleCopyFewShot = () => {
    if (!fewShotData?.markdown) return;
    navigator.clipboard.writeText(fewShotData.markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div role="dialog" aria-label="Editorial feedback" className="fixed inset-0 z-[100] flex items-center justify-center p-3 sm:p-6 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div 
        className="bg-white text-neutral-900 w-full max-w-6xl max-h-[92vh] rounded-2xl shadow-2xl border border-neutral-200 flex flex-col overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-neutral-200 flex items-center justify-between bg-neutral-50/80">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-700 shadow-xs">
              <Brain className="h-5 w-5 stroke-[2.5]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-black tracking-tight text-neutral-900">
                  AI Editorial Feedback & Training Hub
                </h2>
                <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 uppercase tracking-wider">
                  Human-In-The-Loop
                </span>
              </div>
              <p className="text-xs text-neutral-500 mt-0.5">
                Saved corrections guide the next automatic edit; model weights are not retrained.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadData}
              className="p-2 text-neutral-500 hover:text-neutral-800 hover:bg-neutral-100 rounded-lg transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-neutral-400 hover:text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        <FeedbackComposer key={project.id} project={project} time={currentTime} onSaved={loadData} onUpdated={onUpdated} />
        {/* Aggregated Totals Banner */}
        <div className="bg-neutral-900 text-white px-6 py-3 flex flex-wrap items-center justify-between gap-4 border-b border-neutral-800">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-neutral-400">Total Decisions:</span>
              <span className="text-lg font-black text-white">{stats?.total_decisions ?? 0}</span>
            </div>
            <div className="h-4 w-px bg-neutral-700 hidden sm:block" />
            <div className="flex items-center gap-4 text-xs font-bold">
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                {stats?.kept ?? 0} Kept ({stats?.keep_rate_pct ?? 0}%)
              </span>
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-500/20 text-rose-300 border border-rose-500/30">
                <XCircle className="h-3.5 w-3.5 text-rose-400" />
                {stats?.cut ?? 0} Cut ({stats?.cut_rate_pct ?? 0}%)
              </span>
              <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/20 text-amber-300 border border-amber-500/30">
                <RefreshCw className="h-3.5 w-3.5 text-amber-400" />
                {stats?.swapped ?? 0} Modified ({stats?.swap_rate_pct ?? 0}%)
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1 bg-neutral-800 p-1 rounded-lg text-xs font-bold">
            <button
              onClick={() => setActiveTab('decisions')}
              className={`px-3 py-1 rounded-md transition-colors ${activeTab === 'decisions' ? 'bg-white text-black shadow-xs' : 'text-neutral-400 hover:text-white'}`}
            >
              Decision Log ({decisions.length})
            </button>
            <button
              onClick={() => setActiveTab('few_shot')}
              className={`px-3 py-1 rounded-md transition-colors flex items-center gap-1.5 ${activeTab === 'few_shot' ? 'bg-purple-600 text-white shadow-xs' : 'text-neutral-400 hover:text-white'}`}
            >
              <Sparkles className="h-3 w-3" />
              Few-Shot Prompt Exporter
            </button>
          </div>
        </div>

        {activeTab === 'decisions' ? (
          <>
            {/* Filter Bar */}
            <div className="px-6 py-3 border-b border-neutral-200 bg-neutral-50 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-1.5 font-bold text-neutral-600">
                  <Filter className="h-3.5 w-3.5" />
                  <span>Filter by:</span>
                </div>

                {/* Decision filter */}
                <select
                  value={filterDecision}
                  onChange={(e) => setFilterDecision(e.target.value)}
                  className="bg-white border border-neutral-300 rounded-lg px-2.5 py-1 font-semibold text-neutral-800 focus:outline-hidden focus:ring-1 focus:ring-purple-500"
                >
                  <option value="all">All Decisions</option>
                  <option value="keep">Kept Only</option>
                  <option value="cut">Cut Only</option>
                  <option value="swap">Modified Only</option>
                </select>

                {/* Graphic Type filter */}
                <select
                  value={filterGraphicType}
                  onChange={(e) => setFilterGraphicType(e.target.value)}
                  className="bg-white border border-neutral-300 rounded-lg px-2.5 py-1 font-semibold text-neutral-800 focus:outline-hidden focus:ring-1 focus:ring-purple-500"
                >
                  <option value="all">All Graphic Types</option>
                  <option value="split_screen_vertical">50/50 Split Screen</option>
                  <option value="dimension_callout">Dimension Callout</option>
                  <option value="youtube_insert">Cutaway Insert</option>
                  <option value="article_reconstruction">Research Report</option>
                </select>

                {/* Strength range */}
                <div className="flex items-center gap-2 bg-white px-2.5 py-1 border border-neutral-300 rounded-lg">
                  <span className="font-semibold text-neutral-500">Min Strength:</span>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={filterMinStrength}
                    onChange={(e) => setFilterMinStrength(parseFloat(e.target.value))}
                    className="w-20 accent-purple-600"
                  />
                  <span className="font-bold text-neutral-900 w-7">{filterMinStrength.toFixed(1)}</span>
                </div>
              </div>

              <div className="text-neutral-500 font-semibold">
                Showing {decisions.length} recorded decisions
              </div>
            </div>

            {/* Decisions List */}
            <div className="flex-1 overflow-y-auto p-6 space-y-3.5 bg-neutral-100/50">
              {decisions.length === 0 ? (
                <div className="text-center py-16 text-neutral-400">
                  <Brain className="h-10 w-10 mx-auto text-neutral-300 mb-2 stroke-[1.5]" />
                  <p className="font-bold text-sm text-neutral-600">No decisions match current filter criteria</p>
                  <p className="text-xs text-neutral-400 mt-1">Review AI cues in the studio to log your Keep, Cut, and Swap decisions.</p>
                </div>
              ) : (
                decisions.map((d) => {
                  const isKeep = d.decision === 'keep';
                  const isCut = d.decision === 'cut';
                  const isSwap = d.decision === 'swap';

                  return (
                    <div 
                      key={d.id}
                      className="bg-white rounded-xl border border-neutral-200 p-4.5 shadow-2xs hover:border-neutral-300 transition-all flex flex-col md:flex-row gap-4 justify-between"
                    >
                      <div className="space-y-2 flex-1">
                        {/* Top Meta Line */}
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider ${
                            isKeep ? 'bg-emerald-100 text-emerald-800 border border-emerald-300' :
                            isCut ? 'bg-rose-100 text-rose-800 border border-rose-300' :
                            'bg-amber-100 text-amber-800 border border-amber-300'
                          }`}>
                            {isKeep && <CheckCircle2 className="h-3 w-3" />}
                            {isCut && <XCircle className="h-3 w-3" />}
                            {isSwap && <RefreshCw className="h-3 w-3" />}
                            {d.decision}
                          </span>

                          <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-neutral-100 text-neutral-700 flex items-center gap-1">
                            <Clock className="h-3 w-3 text-neutral-400" />
                            {d.start_sec.toFixed(2)}s - {d.end_sec.toFixed(2)}s
                          </span>

                          <span className="text-xs font-bold px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">
                            Strength: {(d.strength * 100).toFixed(0)}%
                          </span>

                          <span className="text-xs font-mono text-neutral-400 ml-auto">
                            {d.project_id}
                          </span>
                        </div>

                        {/* Transcript Context */}
                        {d.transcript_context && (
                          <div className="text-xs bg-neutral-50 px-3 py-1.5 rounded-lg border border-neutral-100 text-neutral-700">
                            <span className="font-bold text-neutral-500">Spoken Context: </span>
                            "{d.transcript_context}"
                          </div>
                        )}

                        {/* Pegasus Reasoning */}
                        <div className="text-xs text-neutral-700 leading-relaxed">
                          <span className="font-bold text-neutral-900">AI Reasoning: </span>
                          {d.reasoning || "Editorial context not recorded."}
                        </div>

                        {/* Query & Graphic Type */}
                        <div className="flex flex-wrap items-center gap-3 text-xs text-neutral-600">
                          <div>
                            <span className="font-bold text-neutral-500">Suggested Graphic: </span>
                            <span className="font-mono font-bold text-neutral-800">{d.graphic_type}</span>
                          </div>
                          <div>
                            <span className="font-bold text-neutral-500">Visual Query: </span>
                            <span className="italic text-neutral-800">"{d.search_query}"</span>
                          </div>
                        </div>

                        {/* Swap details if swapped */}
                        {isSwap && d.swap_details && (
                          <div className="text-xs bg-amber-50/80 border border-amber-200 p-2.5 rounded-lg text-amber-900 flex items-center gap-2">
                            <ArrowRight className="h-4 w-4 text-amber-600 shrink-0" />
                            <div>
                              <span className="font-bold">Editor Change: </span>
                              {d.swap_details.reason || JSON.stringify(d.swap_details)}
                            </div>
                          </div>
                        )}

                        {/* Editor Notes */}
                        {d.editor_notes && (
                          <div className="text-xs text-neutral-500 italic">
                            <span className="font-bold text-neutral-600 not-italic">Notes: </span>
                            {d.editor_notes}
                          </div>
                        )}
                      </div>

                      {/* Right Action Column */}
                      <div className="flex md:flex-col items-end justify-between md:justify-center gap-2 shrink-0 border-t md:border-t-0 md:border-l border-neutral-100 pt-2 md:pt-0 md:pl-4">
                        {onJumpToTime && (
                          <button
                            onClick={() => onJumpToTime(d.start_sec)}
                            className="px-3 py-1.5 rounded-lg bg-neutral-100 hover:bg-neutral-200 text-neutral-700 font-bold text-xs flex items-center gap-1.5 transition-colors"
                          >
                            <Clock className="h-3 w-3" />
                            Jump to Cue
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </>
        ) : (
          /* Few-Shot Learning Exporter Tab */
          <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-neutral-50">
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3 text-amber-900">
              <ShieldAlert className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
              <div className="text-xs space-y-1">
                <p className="font-bold text-sm text-amber-900">
                  Manual Curation Safeguard (No Automatic Production Alteration)
                </p>
                <p className="text-amber-800">
                  This exporter formats your logged editorial decisions into clean few-shot training examples for Pegasus prompt tuning.
                  Per system design, decisions are **never** injected automatically into the live production prompt.
                  Copy and review these examples manually before deploying prompt revisions.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-neutral-200">
              <div className="flex items-center gap-4 text-xs font-bold text-neutral-700">
                <span>Total Exported: <strong className="text-neutral-900">{fewShotData?.total_exported ?? 0}</strong></span>
                <span>Positive (Keep): <strong className="text-emerald-600">{fewShotData?.positive_count ?? 0}</strong></span>
                <span>Negative (Cut): <strong className="text-rose-600">{fewShotData?.negative_count ?? 0}</strong></span>
                <span>Modified (Swap): <strong className="text-amber-600">{fewShotData?.modified_count ?? 0}</strong></span>
              </div>

              <button
                onClick={handleCopyFewShot}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-bold text-xs rounded-xl shadow-xs flex items-center gap-2 transition-all active:scale-95"
              >
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied ? 'Copied to Clipboard!' : 'Copy Few-Shot Markdown'}
              </button>
            </div>

            <div className="bg-neutral-900 text-neutral-200 font-mono text-xs p-5 rounded-xl border border-neutral-800 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-[50vh]">
              {fewShotData?.markdown || 'Loading few-shot examples...'}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
