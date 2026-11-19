import React, { useEffect, useState } from 'react';
import { BACKEND_ORIGIN, api } from '../../services/api';
import { Search, Image as ImageIcon } from 'lucide-react';

interface SegmentPictureProps {
  projectId: string;
  graphicId?: string;
  startSec: number;
  endSec: number;
  transcript: string;
  initialQuery: string;
  currentUrl?: string | null;
  onReplaced: (project: any, mediaUrl: string) => void;
}

function pictureSrc(url?: string | null) {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  return `${BACKEND_ORIGIN}${url}`;
}

export function SegmentPicture({
  projectId,
  graphicId,
  startSec,
  endSec,
  transcript,
  initialQuery,
  currentUrl,
  onReplaced
}: SegmentPictureProps) {
  const [query, setQuery] = useState(initialQuery);
  const [note, setNote] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [shown, setShown] = useState(currentUrl || '');
  useEffect(() => { if (currentUrl) setShown(currentUrl); }, [currentUrl]);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function search() {
    const term = query.trim();
    if (!term) return;
    setBusy('search');
    setError('');
    setMessage('');
    try {
      const found = await api.searchMedia(term, 'image', 'all');
      setResults(found.results || []);
      if (!found.results?.length) setMessage('No images came back for that search.');
    } catch (exc) {
      setError(String(exc));
    } finally {
      setBusy('');
    }
  }

  async function choose(asset: any) {
    setBusy(String(asset.id || 'download'));
    setError('');
    try {
      const saved = await api.replaceVisual(projectId, {
        graphic_id: graphicId,
        start_sec: startSec,
        end_sec: endSec,
        transcript,
        editor_note: note.trim(),
        search_query: query.trim(),
        asset
      });
      setShown(saved.media_url);
      setMessage(note.trim()
        ? 'Image replaced. This note is saved for the next similar section and added to the training file.'
        : 'Image replaced and saved for the next similar section.');
      onReplaced(saved.project, saved.media_url);
    } catch (exc) {
      setError(String(exc));
    } finally {
      setBusy('');
    }
  }

  return (
    <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-2.5 space-y-2">
      <div className="flex gap-3">
        <div className="h-20 w-16 shrink-0 overflow-hidden rounded-md border border-neutral-200 bg-white">
          {shown ? (
            <img src={pictureSrc(shown)} alt="" className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full items-center justify-center text-neutral-300">
              <ImageIcon className="h-5 w-5" />
            </div>
          )}
        </div>
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex gap-1.5">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => { if (event.key === 'Enter') void search(); }}
              aria-label="Search the internet for this section"
              placeholder="Search Pexels, Pixabay, then Wikimedia"
              className="min-w-0 flex-1 rounded-md border border-neutral-300 bg-white px-2 py-1 text-xs text-neutral-900"
            />
            <button
              type="button"
              disabled={busy === 'search'}
              onClick={() => void search()}
              className="flex items-center gap-1 rounded-md border border-neutral-300 bg-white px-2 py-1 text-xs font-medium text-neutral-800 hover:bg-neutral-100 disabled:opacity-50"
            >
              <Search className="h-3 w-3" />
              {busy === 'search' ? 'Searching…' : 'Search'}
            </button>
          </div>
          <input
            value={note}
            onChange={(event) => setNote(event.target.value)}
            aria-label="What this section should show"
            placeholder="What this section should show. Saved for similar sections and the training file."
            className="w-full rounded-md border border-neutral-300 bg-white px-2 py-1 text-xs text-neutral-900"
          />
        </div>
      </div>
      {results.length > 0 && (
        <div className="flex gap-1.5 overflow-x-auto pb-1">
          {results.slice(0, 8).map((asset) => (
            <button
              key={String(asset.id)}
              type="button"
              disabled={Boolean(busy)}
              title={asset.title || 'Use this image'}
              onClick={() => void choose(asset)}
              className="h-16 w-12 shrink-0 overflow-hidden rounded border border-neutral-200 bg-white hover:border-indigo-400 disabled:opacity-50"
            >
              <img src={asset.thumb_url || asset.url} alt="" className="h-full w-full object-cover" />
            </button>
          ))}
        </div>
      )}
      {message && <p className="text-[11px] text-emerald-700">{message}</p>}
      {error && <p className="text-[11px] text-amber-800">{error}</p>}
    </div>
  );
}
