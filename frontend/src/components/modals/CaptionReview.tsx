import React, { useMemo, useState } from 'react';
import { CaptionItem, ProjectState, WordTiming } from '../../types';
import { api } from '../../services/api';

interface CaptionReviewProps {
  project: ProjectState;
  onSeek: (time: number) => void;
  onSaved: (project: ProjectState) => void;
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

export function CaptionReview({ project, onSeek, onSaved }: CaptionReviewProps) {
  const [query, setQuery] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [status, setStatus] = useState('');
  const [busyId, setBusyId] = useState('');

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
    setStatus('');
    onSeek(caption.start);
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
      if (train) {
        const result = await api.saveCaptionMapping({
          project_id: project.id,
          caption_id: caption.id,
          start_sec: start,
          end_sec: end,
          source_text: source,
          spoken_text: spoken || source,
          note: nextDraft.note,
        });
        setStatus(result.success
          ? 'Saved on the timeline and stored for the next transcription and edit.'
          : (result.detail || 'The caption was saved. The training example was not.'));
      } else {
        setStatus('Caption saved on the timeline.');
      }
    } catch (err) {
      setStatus(err instanceof Error ? err.message : String(err));
    } finally {
      setBusyId('');
    }
  }

  return (
    <section className="rounded-xl border border-neutral-200 bg-neutral-50 p-3 space-y-2">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-neutral-900">Captions on the timeline</h3>
          <p className="text-[11px] text-neutral-600 mt-0.5">
            {project.captions.length} lines. Select a time to play that moment, edit the words, then save the mapping for the next run.
          </p>
        </div>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search captions"
          className="w-48 rounded-md border border-neutral-300 bg-white px-2 py-1 text-xs text-neutral-900"
        />
      </div>
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
                  <label className="block text-[11px] text-neutral-600">
                    Spoken line
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
                  <label className="block text-[11px] text-neutral-600">
                    Note for the next similar section
                    <input
                      value={draft.note}
                      onChange={(event) => setDraft({ ...draft, note: event.target.value })}
                      className="mt-0.5 w-full rounded border border-neutral-300 px-2 py-1 text-xs"
                    />
                  </label>
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      disabled={busyId === caption.id}
                      onClick={() => { void persist(caption, draft, false); }}
                      className="rounded border border-neutral-300 bg-white px-2 py-1 text-[11px] font-semibold text-neutral-900 hover:bg-neutral-100 disabled:opacity-50"
                    >
                      Save edit
                    </button>
                    <button
                      type="button"
                      disabled={busyId === caption.id}
                      onClick={() => { void persist(caption, draft, true); }}
                      className="rounded bg-neutral-900 px-2 py-1 text-[11px] font-semibold text-white hover:bg-neutral-800 disabled:opacity-50"
                    >
                      Save mapping for training
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
