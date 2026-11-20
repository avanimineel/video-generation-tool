import React, { useMemo, useState } from 'react';
import { CaptionItem, ProjectState, WordTiming } from '../../types';
import { api } from '../../services/api';

interface CaptionReviewProps {
  project: ProjectState;
  onSeek: (time: number) => void;
  onSaved: (project: ProjectState) => void;
  onRedoCaptions?: () => void;
}

interface Reading {
  kind: string;
  label: string;
  text: string;
}

interface Draft {
  source: string;
  spoken: string;
  start: string;
  end: string;
  note: string;
}

function timeWords(text: string, start: number, end: number, previous: WordTiming[]): WordTiming[] {
  const tokens = text.trim().split(/\s+/).filter(Boolean);
  if (!tokens.length) return [];
  const each = Math.max(0.05, end - start) / tokens.length;
  return tokens.map((word, index) => ({
    ...(previous[index] || {}),
    word,
    start: Math.round((start + index * each) * 1000) / 1000,
    end: Math.round((start + (index + 1) * each) * 1000) / 1000,
    highlight: false,
  }));
}

function draftFrom(caption: CaptionItem): Draft {
  return {
    source: caption.text || '',
    spoken: caption.translated_text || caption.text || '',
    start: String(caption.start),
    end: String(caption.end),
    note: '',
  };
}

export function CaptionReview({ project, onSeek, onSaved, onRedoCaptions }: CaptionReviewProps) {
  const [query, setQuery] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [status, setStatus] = useState('');
  const [busyId, setBusyId] = useState('');
  const [joining, setJoining] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [inferenceSummary, setInferenceSummary] = useState('');
  const [readings, setReadings] = useState<Reading[]>([]);

  const counts = useMemo(() => {
    const tally = new Map<string, number>();
    for (const caption of project.captions) {
      const key = (caption.text || '').trim();
      if (!key) continue;
      tally.set(key, (tally.get(key) || 0) + 1);
    }
    return tally;
  }, [project.captions]);

  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return project.captions;
    return project.captions.filter((caption) =>
      caption.text.toLowerCase().includes(needle)
      || (caption.translated_text || '').toLowerCase().includes(needle)
    );
  }, [project.captions, query]);

  function openEdit(caption: CaptionItem) {
    setEditingId(caption.id);
    setDraft(draftFrom(caption));
    setReadings([]);
    setInferenceSummary('');
    setStatus('');
    onSeek(caption.start);
    const domain = project.settings?.domain_profile || 'general';
    const earlier = project.captions
      .filter((item) => item.start < caption.start)
      .map((item) => item.text || '')
      .filter(Boolean);
    api.captionChoices({
      source_text: caption.text || '',
      english: caption.translated_text || '',
      domain,
      earlier_lines: earlier,
    }).then((result) => {
      setReadings(result.options || []);
    }).catch(() => {
      setReadings([]);
    });
  }

  async function persist(caption: CaptionItem, nextDraft: Draft, train: boolean) {
    const start = Number(nextDraft.start);
    const end = Number(nextDraft.end);
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
      setStatus('The end time has to be after the start time.');
      return;
    }
    const spoken = nextDraft.spoken.trim();
    const source = nextDraft.source.trim();
    if (!spoken && !source) {
      setStatus('Add the spoken line before saving.');
      return;
    }
    const timed = timeWords(spoken || source, start, end, caption.words || []);
    const updated: CaptionItem = {
      ...caption,
      start,
      end,
      text: source || caption.text,
      translated_text: spoken || source,
      words: timed,
      editor_locked: true,
    };
    const next: ProjectState = {
      ...project,
      captions: project.captions.map((item) => (item.id === caption.id ? updated : item)),
    };
    setBusyId(caption.id);
    setStatus('');
    try {
      await api.saveProject(project.id, next);
      onSaved(next);
      let noteSaved = false;
      if (nextDraft.note.trim()) {
        await api.keepSectionNote({
          project_id: project.id,
          caption_id: caption.id,
          source_text: source,
          spoken_text: spoken || source,
          note: nextDraft.note.trim(),
          start_sec: start,
          end_sec: end,
        });
        noteSaved = true;
      }
      if (train) {
        const chosen = await api.chooseTranslationLine({
          source_text: source,
          english: spoken || source,
          domain: project.settings?.domain_profile || 'general',
          project_id: project.id,
          start_sec: start,
          end_sec: end,
        });
        const taught = chosen.taught
          ? 'Updated on this video and taught for the same section on a new video.'
          : 'Updated on this video. It was not taught, because this wording misses the medical meaning.';
        setStatus(noteSaved ? `${taught} The note is kept for the next similar section.` : taught);
      } else {
        setStatus(noteSaved ? 'Updated on this video. The note is kept for the next similar section.' : 'Updated on this video only.');
      }
    } catch (err) {
      setStatus(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId('');
    }
  }

  async function suggestNote(caption: CaptionItem) {
    if (!draft) return;
    setSuggesting(true);
    setStatus('');
    try {
      const earlier = project.captions
        .filter((item) => item.start < caption.start)
        .map((item) => item.text || '')
        .filter(Boolean);
      const sourceLine = draft.source.trim();
      if (!sourceLine) {
        setStatus('Add the source line before asking for a suggestion.');
        return;
      }
      const result = await api.suggestSectionNote({
        source_text: sourceLine,
        english: draft.spoken,
        domain: project.settings?.domain_profile || 'general',
        earlier_lines: earlier,
      });
      setDraft((current) => (current ? { ...current, note: result.note } : current));
      setInferenceSummary(result.inference_summary || '');
      setStatus('Suggestion uses the source line and the inference summary. Change any word before you save.');
    } catch (err) {
      setStatus(err instanceof Error ? err.message : String(err));
    } finally {
      setSuggesting(false);
    }
  }

  async function joinSentences() {
    setJoining(true);
    setStatus('Joining the understood lines into sentences…');
    try {
      const result = await api.translate(project.id);
      if (result.captions) {
        onSaved({ ...project, captions: result.captions });
        setStatus('Joined into sentences. Edited lines were kept.');
      }
    } catch (err) {
      setStatus(err instanceof Error ? err.message : String(err));
    } finally {
      setJoining(false);
    }
  }

  return (
    <section className="rounded-xl border border-neutral-200 bg-neutral-50 p-3 space-y-2">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-neutral-900">Captions on the timeline</h3>
          <p className="text-[11px] text-neutral-600 mt-0.5">
            {project.captions.length} lines. Select a time to play that moment. Save edit keeps that line, and Join sentences gathers the understood lines into one caption.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={joining}
            onClick={() => { void joinSentences(); }}
            className="rounded-md bg-neutral-900 px-2 py-1 text-[11px] font-semibold text-white hover:bg-neutral-800 disabled:opacity-50"
          >
            {joining ? 'Joining…' : 'Join sentences'}
          </button>
          {onRedoCaptions && (
            <button
              type="button"
              onClick={onRedoCaptions}
              className="rounded-md border border-neutral-300 bg-white px-2 py-1 text-[11px] font-semibold text-neutral-900 hover:bg-neutral-100"
            >
              Redo captions
            </button>
          )}
        </div>
      </div>
      <div className="flex justify-end">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search captions"
          className="w-48 rounded-md border border-neutral-300 bg-white px-2 py-1 text-xs text-neutral-900"
        />
      </div>
      {status && !editingId && <p className="text-[11px] text-neutral-600">{status}</p>}
      <div className="max-h-80 overflow-y-auto space-y-1.5">
        {rows.length === 0 && (
          <p className="text-xs text-neutral-500 px-1 py-4">No captions match this search.</p>
        )}
        {rows.map((caption) => {
          const repeated = (counts.get((caption.text || '').trim()) || 0) >= 4;
          const open = editingId === caption.id && draft;
          return (
            <article key={caption.id} className="rounded-lg border border-neutral-200 bg-white p-2">
              <div className="flex items-start gap-2">
                <button
                  type="button"
                  className="shrink-0 rounded bg-neutral-100 px-2 py-0.5 font-mono text-[11px] font-semibold text-neutral-800 hover:bg-neutral-200"
                  onClick={() => onSeek(caption.start)}
                >
                  {caption.start.toFixed(2)}–{caption.end.toFixed(2)}s
                </button>
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-neutral-900">{caption.translated_text || caption.text}</p>
                  {caption.translated_text && caption.translated_text !== caption.text && (
                    <p className="text-[11px] text-neutral-500 truncate">{caption.text}</p>
                  )}
                  {repeated && <p className="text-[11px] text-amber-800">This source line is repeated.</p>}
                </div>
                <button
                  type="button"
                  className="shrink-0 rounded border border-neutral-300 bg-white px-2 py-0.5 text-[11px] font-semibold text-neutral-800 hover:bg-neutral-100"
                  onClick={() => (open ? setEditingId(null) : openEdit(caption))}
                >
                  {open ? 'Close' : 'Edit'}
                </button>
              </div>
              {open && draft && (
                <div className="mt-2 space-y-1.5">
                  <p className="text-[11px] font-semibold text-neutral-800">Choose the reading for this section</p>
                  <div className="space-y-1">
                    {readings.map((reading) => {
                      const selected = draft.spoken.trim() === reading.text;
                      return (
                        <button
                          key={reading.kind}
                          type="button"
                          onClick={() => setDraft({ ...draft, spoken: reading.text })}
                          className={`block w-full rounded-md border px-2 py-1.5 text-left text-xs ${selected ? 'border-neutral-900 bg-neutral-100 text-neutral-900' : 'border-neutral-200 bg-white text-neutral-800 hover:bg-neutral-50'}`}
                        >
                          <span className="block text-[10px] font-semibold uppercase tracking-wide text-neutral-500">{reading.label}</span>
                          {reading.text}
                        </button>
                      );
                    })}
                    {readings.length === 0 && (
                      <p className="text-[11px] text-neutral-500">No other reading for this section. You can type one below.</p>
                    )}
                  </div>
                  <label className="block text-[11px] text-neutral-600">
                    English for this section
                    <textarea
                      value={draft.spoken}
                      onChange={(event) => setDraft({ ...draft, spoken: event.target.value })}
                      rows={2}
                      className="mt-0.5 w-full rounded border border-neutral-300 px-2 py-1 text-xs text-neutral-900"
                    />
                  </label>
                  <label className="block text-[11px] text-neutral-600">
                    Source line
                    <textarea
                      value={draft.source}
                      onChange={(event) => setDraft({ ...draft, source: event.target.value })}
                      rows={2}
                      className="mt-0.5 w-full rounded border border-neutral-300 px-2 py-1 text-xs text-neutral-900"
                    />
                  </label>
                  <div className="flex gap-2">
                    <label className="text-[11px] text-neutral-600">
                      Start
                      <input
                        value={draft.start}
                        onChange={(event) => setDraft({ ...draft, start: event.target.value })}
                        className="mt-0.5 block w-24 rounded border border-neutral-300 px-2 py-1 font-mono text-xs"
                      />
                    </label>
                    <label className="text-[11px] text-neutral-600">
                      End
                      <input
                        value={draft.end}
                        onChange={(event) => setDraft({ ...draft, end: event.target.value })}
                        className="mt-0.5 block w-24 rounded border border-neutral-300 px-2 py-1 font-mono text-xs"
                      />
                    </label>
                  </div>
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[11px] text-neutral-600">Note for the next similar section</span>
                      <button
                        type="button"
                        disabled={suggesting}
                        onClick={() => { void suggestNote(caption); }}
                        className="rounded border border-neutral-300 bg-white px-2 py-0.5 text-[11px] font-semibold text-neutral-900 hover:bg-neutral-100 disabled:opacity-50"
                      >
                        {suggesting ? 'Asking AI…' : 'Suggest from AI'}
                      </button>
                    </div>
                    <input
                      value={draft.note}
                      onChange={(event) => setDraft({ ...draft, note: event.target.value })}
                      placeholder="Type a note, or edit the AI suggestion"
                      className="mt-0.5 w-full rounded border border-neutral-300 bg-white px-2 py-1 text-xs text-neutral-900"
                    />
                    <p className="mt-0.5 text-[10px] text-neutral-500">Suggest from AI uses the source line and the inference summary. Change any word, then save.</p>
                    {inferenceSummary && (
                      <p className="mt-0.5 text-[10px] text-neutral-700">Inference summary: {inferenceSummary}</p>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      disabled={busyId === caption.id}
                      onClick={() => { void persist(caption, draft, false); }}
                      className="rounded border border-neutral-300 bg-white px-2 py-1 text-[11px] font-semibold text-neutral-900 hover:bg-neutral-100 disabled:opacity-50"
                    >
                      Update this video
                    </button>
                    <button
                      type="button"
                      disabled={busyId === caption.id}
                      onClick={() => { void persist(caption, draft, true); }}
                      className="rounded bg-neutral-900 px-2 py-1 text-[11px] font-semibold text-white hover:bg-neutral-800 disabled:opacity-50"
                    >
                      Update this video and the model
                    </button>
                    <span className="text-[11px] text-neutral-500">{status}</span>
                  </div>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
