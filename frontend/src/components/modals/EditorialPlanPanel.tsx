import React, { useEffect, useState } from 'react';
import { UnderstandingReview } from './UnderstandingReview';
import { QualityPreview } from './QualityPreview';
import { api } from '../../services/api';
import { Check, Trash2, Brain, Sparkles, Save, RefreshCw } from 'lucide-react';

interface EditorialPlanPanelProps {
  projectId: string;
  onSeek: (t: number) => void;
  onUpdated: (p: any) => void;
  onBusy: (b: boolean) => void;
}

export function EditorialPlanPanel({
  projectId,
  onSeek,
  onUpdated,
  onBusy
}: EditorialPlanPanelProps) {
  const [open, setOpen] = useState(false);
  const [report, setReport] = useState<any>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [guidance, setGuidance] = useState('');
  const [savingGuidance, setSavingGuidance] = useState(false);
  const [guidanceSaved, setGuidanceSaved] = useState(false);
  const [decisionFeedback, setDecisionFeedback] = useState<Record<string, 'keep' | 'cut' | 'swap'>>({});
  const [loggingDecision, setLoggingDecision] = useState<Record<string, boolean>>({});

  async function refresh() {
    try {
      setReport(await api.getEditorialReport(projectId));
      const g = await api.getProjectGuidance(projectId);
      setGuidance(g || '');
      setError('');
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    setReport(null);
    setError('');
    if (open) {
      void refresh();
    }
  }, [open, projectId]);

  async function handleSaveGuidance() {
    setSavingGuidance(true);
    setGuidanceSaved(false);
    try {
      await api.saveProjectGuidance(projectId, guidance);
      setGuidanceSaved(true);
      setTimeout(() => setGuidanceSaved(false), 2500);
    } catch (e) {
      setError('Failed to save guidance: ' + String(e));
    } finally {
      setSavingGuidance(false);
    }
  }

  async function handleFeedbackAction(d: any, decision: 'keep' | 'cut') {
    const cueKey = d.graphic_id || `${d.segment_id}_${d.start_sec}`;
    setLoggingDecision(prev => ({ ...prev, [cueKey]: true }));
    setDecisionFeedback(prev => ({ ...prev, [cueKey]: decision }));
    try {
      await api.logDecision({
        project_id: projectId,
        cue_id: cueKey,
        decision: decision,
        reasoning: d.rationale || d.decision_reason || '',
        strength: d.utility || 0.85,
        graphic_type: d.strategy || 'split_screen_vertical',
        start_sec: d.start_sec,
        end_sec: d.end_sec,
        search_query: d.asset?.retrieval_query || d.asset?.semantic_target || d.display_text || '',
        transcript_context: d.anchor_phrase || d.display_text || '',
        selected_asset: d.asset || {}
      });
    } catch (e) {
      console.error('Failed to log feedback decision:', e);
    } finally {
      setLoggingDecision(prev => ({ ...prev, [cueKey]: false }));
    }
  }

  async function run(planOnly = false) {
    setBusy(true);
    onBusy(true);
    setError('');
    try {
      if (guidance.trim()) {
        await api.saveProjectGuidance(projectId, guidance);
      }
      const r = await api.runAutoProduction(projectId, planOnly);
      if (!r.success) throw new Error(r.error);
      if (r.project) onUpdated(r.project);
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
      onBusy(false);
    }
  }

  return (
    <>
      <div className="px-4 py-1 border-b border-neutral-200 bg-white flex items-center justify-between text-xs">
        <QualityPreview projectId={projectId} />
        <UnderstandingReview projectId={projectId} onSeek={onSeek} />
        <span className="text-neutral-500">Meaning → visual purpose → media review → timing</span>
        <button
          className="px-3 py-1 rounded border border-neutral-300 hover:bg-neutral-100 font-medium text-neutral-800 transition"
          onClick={() => setOpen(true)}
        >
          Review automatic edit
        </button>
      </div>

      {open && (
        <div className="fixed inset-0 z-[100] bg-black/40 flex items-center justify-center p-6">
          <section
            role="dialog"
            aria-label="Editorial plan"
            className="bg-white text-neutral-900 rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto p-6 flex flex-col"
          >
            <header className="flex justify-between items-center pb-3 border-b border-neutral-200">
              <div>
                <h2 className="text-xl font-bold flex items-center gap-2">
                  <Brain className="w-5 h-5 text-indigo-600" />
                  Automatic Editorial Plan & AI Calibration
                </h2>
                <p className="text-xs text-neutral-500 mt-0.5">
                  Direct the AI's visual density, review rationale, and calibrate decisions with Keep/Cut feedback.
                </p>
              </div>
              <button
                aria-label="Close editorial plan"
                onClick={() => setOpen(false)}
                className="text-neutral-400 hover:text-neutral-700 text-sm font-semibold px-2 py-1 rounded transition"
              >
                ✕ Close
              </button>
            </header>

            {/* EDITORIAL GUIDANCE / DIRECTIVES INPUT */}
            <div className="my-4 p-4 bg-gradient-to-br from-indigo-50/60 to-purple-50/40 border border-indigo-100 rounded-xl space-y-2.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-neutral-800 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                  Custom Editorial Directives & Style Guidance
                </label>
                {guidanceSaved && (
                  <span className="text-[11px] text-emerald-700 font-medium flex items-center gap-1">
                    <Check className="w-3 h-3" /> Saved!
                  </span>
                )}
              </div>
              <textarea
                value={guidance}
                onChange={(e) => setGuidance(e.target.value)}
                placeholder="e.g. Add high visual density with frequent B-roll videos, stock photos, and kinetic text. Never let speaker talk for >5 seconds without an visual. Prefer scientific medical imagery."
                rows={2}
                className="w-full bg-white border border-indigo-200 rounded-lg p-2.5 text-xs text-neutral-900 placeholder-neutral-400 focus:outline-none focus:border-indigo-500 resize-none shadow-sm"
              />
              <div className="flex items-center justify-between text-xs pt-1">
                <span className="text-[11px] text-neutral-500">
                  Directives are injected at maximum priority into the Gemini editorial planning engine.
                </span>
                <button
                  type="button"
                  disabled={savingGuidance}
                  onClick={handleSaveGuidance}
                  className="flex items-center gap-1.5 px-3 py-1 bg-white hover:bg-neutral-100 border border-neutral-300 text-neutral-800 rounded font-medium shadow-sm transition"
                >
                  <Save className="w-3 h-3 text-neutral-600" />
                  {savingGuidance ? 'Saving…' : 'Save Directives'}
                </button>
              </div>
            </div>

            {/* ACTION CONTROLS */}
            <div className="flex items-center gap-3 pb-4 border-b border-neutral-200">
              <button
                disabled={busy}
                onClick={() => run(false)}
                className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-xs shadow-sm disabled:opacity-50 transition flex items-center gap-1.5"
              >
                <Sparkles className="w-4 h-4" />
                {busy ? 'Producing Visuals…' : 'Produce Visuals & Timeline'}
              </button>
              <button
                disabled={busy}
                onClick={() => run(true)}
                className="px-3 py-2 rounded-lg bg-white hover:bg-neutral-50 border border-neutral-300 text-neutral-700 font-medium text-xs transition"
              >
                Plan Visuals Only (Preview)
              </button>
              <button
                onClick={refresh}
                className="px-3 py-2 border border-neutral-200 rounded-lg hover:bg-neutral-50 text-neutral-600 text-xs font-medium ml-auto flex items-center gap-1.5 transition"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Refresh Status
              </button>
            </div>

            {error && (
              <p role="alert" className="p-3 my-3 bg-amber-50 border border-amber-200 text-amber-900 text-xs rounded-lg">
                {error}
              </p>
            )}

            {report && (
              <div className="space-y-4 pt-4">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 font-semibold text-neutral-800">
                    <span>Status:</span>
                    <span className="capitalize px-2 py-0.5 bg-neutral-100 rounded text-neutral-700">
                      {String(report.status).replace(/_/g, ' ')}
                    </span>
                    {report.stage && (
                      <span className="text-neutral-500">· {String(report.stage).replace(/_/g, ' ')}</span>
                    )}
                  </div>
                  {report.decisions && (
                    <span className="text-neutral-500 font-mono text-[11px]">
                      {report.decisions.length} interventions planned
                    </span>
                  )}
                </div>

                {report.status === 'not_run' && (
                  <p className="my-3 text-xs text-neutral-500">
                    No editorial plan generated yet. Click "Produce Visuals & Timeline" to run Twelve Labs understanding and high-density editorial planning.
                  </p>
                )}

                {report.errors?.map((e: string, i: number) => (
                  <p key={i} role="alert" className="p-3 bg-amber-50 border border-amber-200 text-amber-900 text-xs rounded-lg">
                    {e}
                  </p>
                ))}

                {/* DECISION CARDS */}
                <div className="space-y-3 my-2">
                  {report.decisions?.map((d: any, idx: number) => {
                    const cueKey = d.graphic_id || `${d.segment_id}_${d.start_sec}`;
                    const currentFeedback = decisionFeedback[cueKey];
                    const isLogging = loggingDecision[cueKey];

                    return (
                      <article
                        key={`${d.segment_id}-${d.start_sec}-${d.strategy}-${idx}`}
                        className="border border-neutral-200 rounded-xl p-3.5 bg-white shadow-sm space-y-2 hover:border-neutral-300 transition"
                      >
                        <div className="flex justify-between items-start">
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              className="text-xs font-mono font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded hover:bg-indigo-100 transition"
                              onClick={() => onSeek(d.start_sec)}
                            >
                              {d.start_sec.toFixed(2)}s – {d.end_sec.toFixed(2)}s
                            </button>
                            <span className="text-xs font-bold text-neutral-900">
                              {d.asset?.semantic_target || d.display_text || d.intent}
                            </span>
                            <span className="text-[10px] font-semibold text-neutral-500 bg-neutral-100 px-2 py-0.5 rounded-full uppercase">
                              {d.strategy.replace(/_/g, ' ')}
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            {currentFeedback && (
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                                currentFeedback === 'keep' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                              }`}>
                                {currentFeedback}
                              </span>
                            )}
                            <button
                              type="button"
                              disabled={isLogging}
                              onClick={() => handleFeedbackAction(d, 'keep')}
                              className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium border transition ${
                                currentFeedback === 'keep'
                                  ? 'bg-emerald-600 text-white border-emerald-600'
                                  : 'bg-white hover:bg-emerald-50 text-emerald-700 border-emerald-200'
                              }`}
                              title="Keep: Lock this visual in subsequent runs"
                            >
                              <Check className="w-3 h-3" />
                              Keep
                            </button>
                            <button
                              type="button"
                              disabled={isLogging}
                              onClick={() => handleFeedbackAction(d, 'cut')}
                              className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium border transition ${
                                currentFeedback === 'cut'
                                  ? 'bg-rose-600 text-white border-rose-600'
                                  : 'bg-white hover:bg-rose-50 text-rose-700 border-rose-200'
                              }`}
                              title="Cut: Exclude and ban this asset"
                            >
                              <Trash2 className="w-3 h-3" />
                              Cut
                            </button>
                          </div>
                        </div>

                        <p className="text-xs text-neutral-700 leading-relaxed">
                          {d.decision_reason || d.rationale}
                        </p>

                        <div className="flex items-center justify-between text-[11px] text-neutral-500 pt-1 border-t border-neutral-100">
                          <span>Timing: {d.timing_method}</span>
                          <span>Utility Score: {typeof d.utility === 'number' ? d.utility.toFixed(2) : d.utility}</span>
                          <span>Layout: {d.composition?.layout || 'overlay'}</span>
                        </div>

                        <details className="mt-1 text-[11px] text-neutral-500">
                          <summary className="cursor-pointer hover:text-neutral-800">Technical Details</summary>
                          <pre className="whitespace-pre-wrap break-words mt-1 p-2 bg-neutral-50 rounded border text-[10px] font-mono">
                            {JSON.stringify(d, null, 2)}
                          </pre>
                        </details>
                      </article>
                    );
                  })}
                </div>

                <details className="border-t border-neutral-200 pt-3">
                  <summary className="text-xs font-semibold text-neutral-700 cursor-pointer">
                    Stage-by-stage processing records
                  </summary>
                  <p className="text-[11px] text-neutral-500 my-1">
                    Understanding, editorial decisions, media candidates and realized placement are saved separately.
                  </p>
                  {Object.entries(report.stages || {}).map(([name, data]) => (
                    <details key={name} className="my-1.5 text-xs">
                      <summary className="capitalize cursor-pointer text-neutral-600 font-medium">
                        {name.replace(/_/g, ' ')}
                      </summary>
                      <pre className="text-[10px] font-mono whitespace-pre-wrap break-words p-2.5 bg-neutral-50 rounded border mt-1">
                        {JSON.stringify(data, null, 2)}
                      </pre>
                    </details>
                  ))}
                </details>
              </div>
            )}
          </section>
        </div>
      )}
    </>
  );
}
