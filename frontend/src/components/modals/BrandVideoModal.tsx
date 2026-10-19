import { useEffect, useState } from "react";
import { X, Clapperboard, Download } from "lucide-react";
import { BACKEND_ORIGIN } from "../../services/api";

type Film = {
  id: string; url: string; aspect: string; status: string; stage: string; progress: number; error?: string;
  brand?: { name: string; colors: { background: string; text: string; accent: string }; fonts: { heading: string; body: string }; cta: string };
  scenes?: string[]; duration?: number;
};

const API = `${BACKEND_ORIGIN}/api/brand-video`;
const busy = (film?: Film | null) => !!film && ['reading', 'writing', 'recording'].includes(film.status);

export function BrandVideoModal({ onClose }: { onClose: () => void }) {
  const [url, setUrl] = useState("");
  const [aspect, setAspect] = useState("16:9");
  const [film, setFilm] = useState<Film | null>(null);
  const [recent, setRecent] = useState<Film[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(API).then(r => r.json()).then(d => setRecent(d.films || [])).catch(() => {});
  }, [film?.status]);

  // Poll while the film is being read, written and recorded.
  useEffect(() => {
    if (!busy(film)) return;
    const timer = setInterval(async () => {
      const res = await fetch(`${API}/${film!.id}`);
      if (res.ok) setFilm(await res.json());
    }, 1500);
    return () => clearInterval(timer);
  }, [film?.id, film?.status]);

  const start = async () => {
    setError("");
    const res = await fetch(API, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url, aspect }) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { setError(data.detail || `Could not start (${res.status}).`); return; }
    setFilm(data);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="w-full max-w-3xl max-h-[92vh] overflow-y-auto rounded-xl border border-neutral-200 bg-white text-neutral-900 shadow-xl">
        <div className="flex items-center justify-between border-b border-neutral-200 px-5 py-3">
          <div className="flex items-center gap-2 font-semibold"><Clapperboard className="h-4 w-4" /> Brand film from a website</div>
          <button onClick={onClose} className="rounded p-1 hover:bg-neutral-100" title="Close"><X className="h-4 w-4" /></button>
        </div>
        <div className="space-y-4 p-5 text-sm">
          <p className="text-neutral-600">Reads the site in Chrome, keeps its colours, fonts, pitch, services, steps and proof, and records a short launch film. Every line comes from the site. No paid services are used.</p>
          <div className="flex flex-wrap gap-2">
            <input value={url} onChange={e => setUrl(e.target.value)} placeholder="oonex.in" disabled={busy(film)}
              className="min-w-[220px] flex-1 rounded-md border border-neutral-200 px-3 py-2 outline-none focus:border-neutral-400" />
            <select value={aspect} onChange={e => setAspect(e.target.value)} disabled={busy(film)} className="rounded-md border border-neutral-200 px-2 py-2">
              <option value="16:9">16:9 landscape</option><option value="9:16">9:16 vertical</option><option value="1:1">1:1 square</option>
            </select>
            <button onClick={start} disabled={!url.trim() || busy(film)}
              className="rounded-md bg-neutral-900 px-4 py-2 font-semibold text-white hover:bg-neutral-800 disabled:opacity-40">Make film</button>
          </div>
          {error && <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-red-800">{error}</div>}

          {film && (
            <div className="space-y-3 rounded-lg border border-neutral-200 p-4">
              <div className="flex items-center justify-between">
                <div className="font-medium">{film.brand?.name || film.url}</div>
                <div className="text-xs text-neutral-500">{film.stage}{busy(film) ? ` · ${Math.round((film.progress || 0) * 100)}%` : ''}</div>
              </div>
              {busy(film) && <div className="h-1.5 overflow-hidden rounded bg-neutral-100"><div className="h-full bg-neutral-900 transition-all" style={{ width: `${Math.round((film.progress || 0) * 100)}%` }} /></div>}
              {film.error && <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-red-800">{film.error}</div>}
              {film.brand && (
                <div className="flex flex-wrap items-center gap-3 text-xs text-neutral-600">
                  {Object.entries(film.brand.colors).filter(([k]) => ['background', 'text', 'accent'].includes(k)).map(([k, v]) => (
                    <span key={k} className="flex items-center gap-1"><span className="inline-block h-3.5 w-3.5 rounded border border-neutral-200" style={{ background: String(v) }} />{k}</span>
                  ))}
                  <span>Fonts: {film.brand.fonts.heading} / {film.brand.fonts.body}</span>
                  <span>Call to action: {film.brand.cta}</span>
                </div>
              )}
              {film.status === 'complete' && (
                <>
                  <video src={`${API}/${film.id}/film`} controls autoPlay className="w-full rounded-md bg-black" style={{ aspectRatio: film.aspect.replace(':', ' / ') }} />
                  <a href={`${API}/${film.id}/film`} download className="inline-flex items-center gap-1.5 rounded-md border border-neutral-200 px-3 py-1.5 font-medium hover:bg-neutral-50">
                    <Download className="h-3.5 w-3.5" /> Download MP4
                  </a>
                </>
              )}
            </div>
          )}

          {recent.length > 0 && (
            <div>
              <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-neutral-500">Recent films</div>
              <div className="flex flex-wrap gap-2">
                {recent.map(f => (
                  <button key={f.id} onClick={() => setFilm(f)} className="rounded-md border border-neutral-200 px-2.5 py-1 text-xs hover:bg-neutral-50">
                    {f.brand?.name || f.url} · {f.aspect} · {f.status}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
