import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  X, Play, Pause, Download, Wand2, Plus, Trash2, Copy, Undo2, Redo2, Clapperboard, Film as FilmIcon, Loader2,
  PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen, Camera, History, Columns2,
} from "lucide-react";
import { BACKEND_ORIGIN } from "../../services/api";

/* Studio: make a film in one go (Claude Code or Gemini), then edit every part of it, remix it by direction,
   compare versions, and render it. The preview is the same engine page the renderer records. */

type Obj = Record<string, any>;
type Selection = { kind: "film" } | { kind: "layer"; id: string } | { kind: "block"; id: string }
  | { kind: "camera"; index: number } | { kind: "transition"; index: number } | { kind: "sound"; index: number };

const API = `${BACKEND_ORIGIN}/api/studio`;
const SIZE: Record<string, [number, number]> = { "16:9": [1920, 1080], "9:16": [1080, 1920], "1:1": [1080, 1080] };
const BUSY = ["reading", "designing", "remixing"];
const LAYER_TYPES = ["text", "image", "shape", "path", "particles", "counter", "logo"];
const TEXT_IN = ["rise-words", "mask-up", "blur-in", "scale-pop", "type", "letters-rise", "letters-scatter"];
const ANY_IN = ["fade", "rise", "scale", "zoom-in", "pop", "blur", "mask-circle", "wipe-left", "none"];
const OUT = ["fade", "rise", "blur", "scale", "none"];
const EASES = ["", "linear", "out", "in", "inOut", "expo", "back", "elastic"];
const TRANSITIONS = ["whip", "zoom-through", "flash", "wipe", "dip"];
const ANCHORS = ["center", "top-left", "top", "top-right", "left", "right", "bottom-left", "bottom", "bottom-right"];
const MOODS = ["cinematic", "inspiring", "corporate", "electronic", "upbeat", "lofi", "calm", "none"];
const BLOCK_COLORS = ["#e0e7ff", "#fce7f3", "#dcfce7", "#fef3c7", "#e0f2fe", "#f3e8ff", "#ffedd5"];
const clone = <T,>(v: T): T => JSON.parse(JSON.stringify(v));
const round = (v: number, step = 0.05) => Math.round(v / step) * step;
const fmt = (t: number) => `${Math.floor(t / 60)}:${(t % 60).toFixed(1).padStart(4, "0")}`;

/* ---------- Small field controls ---------- */
function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="flex items-center gap-2 py-0.5 text-xs"><span className="w-24 shrink-0 text-neutral-500">{label}</span><div className="flex min-w-0 flex-1 gap-1">{children}</div></label>;
}
const inputCls = "w-full min-w-0 rounded border border-neutral-200 bg-white px-1.5 py-1 text-xs outline-none focus:border-neutral-400";
function Num({ value, onChange, step = 1, placeholder }: { value: any; onChange: (v: number | undefined) => void; step?: number; placeholder?: string }) {
  return <input type="number" step={step} value={value ?? ""} placeholder={placeholder} className={inputCls}
    onChange={e => onChange(e.target.value === "" ? undefined : Number(e.target.value))} />;
}
function Txt({ value, onChange, placeholder, area }: { value: any; onChange: (v: string) => void; placeholder?: string; area?: boolean }) {
  return area
    ? <textarea value={value ?? ""} placeholder={placeholder} rows={3} className={inputCls} onChange={e => onChange(e.target.value)} />
    : <input value={value ?? ""} placeholder={placeholder} className={inputCls} onChange={e => onChange(e.target.value)} />;
}
function Pick({ value, options, onChange }: { value: any; options: string[]; onChange: (v: string) => void }) {
  return <select value={value ?? ""} className={inputCls} onChange={e => onChange(e.target.value)}>
    {options.map(o => <option key={o} value={o}>{o || "default"}</option>)}
  </select>;
}
function Check({ value, onChange }: { value: any; onChange: (v: boolean) => void }) {
  return <input type="checkbox" checked={!!value} onChange={e => onChange(e.target.checked)} />;
}
/* A colour is a brand colour name or any CSS colour. */
function ColorField({ value, brand, onChange }: { value: any; brand: Obj; onChange: (v: string) => void }) {
  const names = Object.keys(brand?.colors || {}).filter(k => typeof brand.colors[k] === "string");
  const resolved = brand?.colors?.[value] || value;
  return <div className="flex w-full items-center gap-1">
    <input type="color" value={/^#[0-9a-f]{6}$/i.test(resolved || "") ? resolved : "#000000"} onChange={e => onChange(e.target.value)} className="h-6 w-7 shrink-0 cursor-pointer rounded border border-neutral-200" />
    <input list="brand-colors" value={value ?? ""} placeholder="brand name or #hex" className={inputCls} onChange={e => onChange(e.target.value)} />
    <datalist id="brand-colors">{names.map(n => <option key={n} value={n} />)}</datalist>
  </div>;
}
function Section({ title, children, right }: { title: string; children: React.ReactNode; right?: React.ReactNode }) {
  return <div className="border-b border-neutral-200 px-3 py-2">
    <div className="mb-1 flex items-center justify-between text-[11px] font-semibold uppercase tracking-wide text-neutral-500"><span>{title}</span>{right}</div>
    {children}
  </div>;
}

/* ---------- New film ---------- */
function NewFilm({ onMade, recent, onOpen, engines }: { onMade: (s: Obj) => void; recent: Obj[]; onOpen: (id: string) => void; engines: Obj }) {
  const [url, setUrl] = useState(""); const [prompt, setPrompt] = useState(""); const [aspect, setAspect] = useState("16:9");
  const [engine, setEngine] = useState("claude"); const [duration, setDuration] = useState<number | undefined>(24); const [error, setError] = useState("");
  const start = async () => {
    setError("");
    const res = await fetch(API, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url, prompt, aspect, engine, duration }) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { setError(data.detail || `Could not start (${res.status}).`); return; }
    onMade(data);
  };
  return <div className="mx-auto max-w-3xl space-y-6 p-8">
    <div className="space-y-3 rounded-xl border border-neutral-200 bg-white p-5">
      <div className="text-base font-semibold">New film</div>
      <p className="text-sm text-neutral-600">Give a website, an idea, or both. The AI reads the brand and writes the whole film: blocks, camera moves, every layer, transitions, sound and music. Everything it makes stays editable here, and you can remix it by direction.</p>
      <input value={url} onChange={e => setUrl(e.target.value)} placeholder="Website (optional), e.g. atomikgrowth.com" className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-neutral-400" />
      <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={3} placeholder="Idea or direction (optional), e.g. A 20 second launch film for our new podcast service; make the 52M views the climax."
        className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm outline-none focus:border-neutral-400" />
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <select value={aspect} onChange={e => setAspect(e.target.value)} className="rounded-md border border-neutral-200 px-2 py-2">
          <option value="16:9">16:9 landscape</option><option value="9:16">9:16 vertical</option><option value="1:1">1:1 square</option>
        </select>
        <select value={engine} onChange={e => setEngine(e.target.value)} className="rounded-md border border-neutral-200 px-2 py-2">
          <option value="claude" disabled={engines.claude === false}>Claude Code (your subscription){engines.claude === false ? " - not installed" : ""}</option>
          <option value="gemini" disabled={engines.gemini === false}>Gemini (API key){engines.gemini === false ? " - no key" : ""}</option>
        </select>
        <label className="flex items-center gap-1 text-neutral-600">Length <input type="number" value={duration ?? ""} onChange={e => setDuration(e.target.value ? Number(e.target.value) : undefined)} className="w-16 rounded-md border border-neutral-200 px-2 py-2" /> s</label>
        <button onClick={start} disabled={!url.trim() && !prompt.trim()} className="ml-auto flex items-center gap-1.5 rounded-md bg-neutral-900 px-4 py-2 font-semibold text-white hover:bg-neutral-800 disabled:opacity-40"><Wand2 className="h-4 w-4" /> Make film</button>
      </div>
      {engine === "gemini" && <p className="text-xs text-amber-700">Gemini calls use your API key and may be billed.</p>}
      {error && <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div>}
    </div>
    {recent.length > 0 && <div className="rounded-xl border border-neutral-200 bg-white">
      <div className="border-b border-neutral-200 px-5 py-3 text-sm font-semibold">Your films</div>
      {recent.map(f => <button key={f.id} onClick={() => onOpen(f.id)} className="flex w-full items-center justify-between border-b border-neutral-100 px-5 py-2.5 text-left text-sm last:border-0 hover:bg-neutral-50">
        <span className="truncate">{f.title || f.url || f.prompt}</span>
        <span className="ml-3 shrink-0 text-xs text-neutral-500">{f.aspect} · {f.engine === "claude" ? "Claude Code" : "Gemini"} · {f.status === "ready" ? `v${f.version}` : f.status}</span>
      </button>)}
    </div>}
  </div>;
}

/* ---------- The preview frame: the engine page, scaled to fit, driven by messages ---------- */
function Preview({ src, film, time, aspect, onSelect, onReady }: { src: string; film: Obj | null; time: number; aspect: string; onSelect?: (id: string | null) => void; onReady?: () => void }) {
  const frame = useRef<HTMLIFrameElement>(null); const box = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.4); const [ready, setReady] = useState(false);
  const [w, h] = SIZE[aspect] || SIZE["16:9"];
  useEffect(() => {
    const el = box.current; if (!el) return;
    const ro = new ResizeObserver(() => setScale(Math.min(el.clientWidth / w, el.clientHeight / h)));
    ro.observe(el); return () => ro.disconnect();
  }, [w, h]);
  useEffect(() => {
    const onMsg = (e: MessageEvent) => {
      if (e.source !== frame.current?.contentWindow) return;
      if (e.data?.type === "ready") { setReady(true); onReady?.(); }
      if (e.data?.type === "select") onSelect?.(e.data.id);
    };
    window.addEventListener("message", onMsg); return () => window.removeEventListener("message", onMsg);
  }, [onSelect, onReady]);
  useEffect(() => { setReady(false); }, [src]);
  useEffect(() => { if (ready && film) frame.current?.contentWindow?.postMessage({ type: "film", film }, "*"); }, [film, ready]);
  useEffect(() => { if (ready) frame.current?.contentWindow?.postMessage({ type: "seek", t: time }, "*"); }, [time, ready, film]);
  return <div ref={box} className="relative flex h-full w-full items-center justify-center overflow-hidden">
    <div style={{ width: w * scale, height: h * scale }} className="relative shrink-0 overflow-hidden rounded-md shadow-sm ring-1 ring-neutral-200">
      <iframe ref={frame} src={src} title="Film preview" style={{ width: w, height: h, transform: `scale(${scale})`, transformOrigin: "0 0", border: 0 }} />
    </div>
  </div>;
}

/* ---------- Timeline: blocks, camera keys, transitions, sounds and one bar per layer ---------- */
function Timeline({ film, time, onSeek, selection, onSelect, onChange }: {
  film: Obj; time: number; onSeek: (t: number) => void; selection: Selection; onSelect: (s: Selection) => void; onChange: (f: (draft: Obj) => void, commit?: boolean) => void;
}) {
  const ref = useRef<HTMLDivElement>(null); const [width, setWidth] = useState(800);
  useEffect(() => { const el = ref.current; if (!el) return; const ro = new ResizeObserver(() => setWidth(el.clientWidth - 140)); ro.observe(el); return () => ro.disconnect(); }, []);
  const D = film.duration || 20, pps = Math.max(10, width / D);
  const blockIndex = useMemo(() => Object.fromEntries((film.blocks || []).map((b: Obj, i: number) => [b.id, i])), [film.blocks]);
  const layers = useMemo(() => (film.layers || []).map((l: Obj, i: number) => ({ l, i }))
    .sort((a: Obj, b: Obj) => (blockIndex[a.l.block] ?? -1) - (blockIndex[b.l.block] ?? -1) || a.l.start - b.l.start), [film.layers, blockIndex]);
  const drag = useRef<{ index: number; mode: "move" | "l" | "r"; x: number; start: number; end: number } | null>(null);
  const timeAt = (clientX: number) => { const r = ref.current!.getBoundingClientRect(); return Math.max(0, Math.min(D, (clientX - r.left - 140 + ref.current!.scrollLeft) / pps)); };
  const onMove = (e: PointerEvent) => {
    const d = drag.current; if (!d) return;
    const dt = round((e.clientX - d.x) / pps);
    onChange(f => {
      const L = f.layers[d.index];
      if (d.mode === "move") { const len = d.end - d.start; L.start = Math.max(0, Math.min(D - len, round(d.start + dt))); L.end = round(L.start + len); }
      if (d.mode === "l") L.start = Math.max(0, Math.min(d.end - 0.1, round(d.start + dt)));
      if (d.mode === "r") L.end = Math.min(D, Math.max(d.start + 0.1, round(d.end + dt)));
    }, false);
  };
  const onUp = () => { if (drag.current) onChange(() => {}, true); drag.current = null; window.removeEventListener("pointermove", onMove); window.removeEventListener("pointerup", onUp); };
  const startDrag = (e: React.PointerEvent, index: number, mode: "move" | "l" | "r") => {
    e.stopPropagation(); const L = film.layers[index];
    drag.current = { index, mode, x: e.clientX, start: L.start, end: L.end };
    onSelect({ kind: "layer", id: L.id });
    window.addEventListener("pointermove", onMove); window.addEventListener("pointerup", onUp);
  };
  const isSel = (s: Selection) => JSON.stringify(s) === JSON.stringify(selection);
  const ticks = Array.from({ length: Math.floor(D) + 1 }, (_, i) => i).filter(i => pps * (i % 5 === 0 ? 1 : 5) > 20 || i % 5 === 0);
  return <div ref={ref} className="relative h-full select-none overflow-auto bg-white text-[11px]" onPointerDown={e => { if ((e.target as HTMLElement).dataset.track) onSeek(round(timeAt(e.clientX), 0.02)); }}>
    <div style={{ width: 140 + D * pps }} className="relative">
      {/* Ruler */}
      <div className="sticky top-0 z-20 flex h-6 border-b border-neutral-200 bg-white">
        <div className="sticky left-0 z-10 w-[140px] shrink-0 border-r border-neutral-200 bg-white" />
        <div className="relative flex-1 cursor-pointer" data-track="1">
          {ticks.map(i => <div key={i} className="pointer-events-none absolute top-0 h-full border-l border-neutral-200 pl-1 text-neutral-400" style={{ left: i * pps }}>{i % 5 === 0 || pps > 40 ? `${i}s` : ""}</div>)}
        </div>
      </div>
      {/* Blocks */}
      <Lane label="Blocks">{(film.blocks || []).map((b: Obj, i: number) => <div key={b.id} onPointerDown={e => { e.stopPropagation(); onSelect({ kind: "block", id: b.id }); onSeek(b.start); }}
        className={`absolute top-1 bottom-1 cursor-pointer truncate rounded px-1.5 leading-5 text-neutral-800 ${isSel({ kind: "block", id: b.id }) ? "ring-2 ring-neutral-900" : ""}`}
        style={{ left: b.start * pps, width: Math.max(4, (b.end - b.start) * pps - 2), background: BLOCK_COLORS[i % BLOCK_COLORS.length] }}>{b.name}</div>)}</Lane>
      {/* Camera, transitions and sounds as markers */}
      <Lane label="Camera">{(film.camera || []).map((k: Obj, i: number) => <Marker key={i} t={k.t} pps={pps} sel={isSel({ kind: "camera", index: i })} title={`Camera ${k.block || ""} zoom ${k.zoom ?? 1}`}
        onClick={() => { onSelect({ kind: "camera", index: i }); onSeek(k.t); }} shape="square" />)}</Lane>
      <Lane label="Transitions & sound">
        {(film.transitions || []).map((tr: Obj, i: number) => <Marker key={`t${i}`} t={tr.at} pps={pps} sel={isSel({ kind: "transition", index: i })} title={tr.type} onClick={() => { onSelect({ kind: "transition", index: i }); onSeek(tr.at); }} shape="diamond" />)}
        {(film.sounds || []).map((s: Obj, i: number) => <Marker key={`s${i}`} t={s.t} pps={pps} sel={isSel({ kind: "sound", index: i })} title={s.name} onClick={() => { onSelect({ kind: "sound", index: i }); onSeek(s.t); }} shape="dot" />)}
      </Lane>
      {/* Layers */}
      {layers.map(({ l, i }: Obj) => {
        const sel = selection.kind === "layer" && selection.id === l.id; const bi = blockIndex[l.block];
        return <div key={l.id} className={`flex h-6 border-b border-neutral-100 ${sel ? "bg-neutral-50" : ""}`}>
          <div onClick={() => onSelect({ kind: "layer", id: l.id })} className={`sticky left-0 z-10 w-[140px] shrink-0 cursor-pointer truncate border-r border-neutral-200 bg-white px-2 leading-6 ${sel ? "font-semibold text-neutral-900" : "text-neutral-600"}`} title={l.id}>
            <span className="mr-1 text-neutral-400">{l.type[0].toUpperCase()}</span>{l.name || (l.text ? String(l.text).slice(0, 18) : l.id)}
          </div>
          <div className="relative flex-1" data-track="1">
            <div onPointerDown={e => startDrag(e, i, "move")} className={`absolute top-0.5 bottom-0.5 cursor-grab rounded border ${sel ? "border-neutral-900" : "border-neutral-300"}`}
              style={{ left: l.start * pps, width: Math.max(6, (l.end - l.start) * pps), background: bi === undefined ? "#f5f5f5" : BLOCK_COLORS[bi % BLOCK_COLORS.length] }}>
              <div onPointerDown={e => startDrag(e, i, "l")} className="absolute inset-y-0 left-0 w-1.5 cursor-ew-resize" />
              <div onPointerDown={e => startDrag(e, i, "r")} className="absolute inset-y-0 right-0 w-1.5 cursor-ew-resize" />
            </div>
          </div>
        </div>;
      })}
      {/* Playhead */}
      <div className="pointer-events-none absolute top-0 bottom-0 z-30 w-px bg-red-500" style={{ left: 140 + time * pps }} />
    </div>
  </div>;
}
function Lane({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="flex h-7 border-b border-neutral-200">
    <div className="sticky left-0 z-10 w-[140px] shrink-0 border-r border-neutral-200 bg-neutral-50 px-2 leading-7 text-neutral-500">{label}</div>
    <div className="relative flex-1" data-track="1">{children}</div>
  </div>;
}
function Marker({ t, pps, sel, title, onClick, shape }: { t: number; pps: number; sel: boolean; title: string; onClick: () => void; shape: "square" | "diamond" | "dot" }) {
  const cls = shape === "diamond" ? "rotate-45" : shape === "dot" ? "rounded-full" : "rounded-sm";
  return <div title={title} onPointerDown={e => { e.stopPropagation(); onClick(); }}
    className={`absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 cursor-pointer border ${cls} ${sel ? "border-neutral-900 bg-neutral-900" : shape === "dot" ? "border-emerald-600 bg-emerald-200" : shape === "diamond" ? "border-violet-600 bg-violet-200" : "border-sky-600 bg-sky-200"}`}
    style={{ left: t * pps }} />;
}

/* ---------- Inspector ---------- */
function Inspector({ film, selection, assets, time, onChange, onSelect }: {
  film: Obj; selection: Selection; assets: string[]; time: number; onChange: (f: (draft: Obj) => void) => void; onSelect: (s: Selection) => void;
}) {
  const brand = film.brand || {};
  const blocks = ["", ...(film.blocks || []).map((b: Obj) => b.id)];
  if (selection.kind === "layer") {
    const index = (film.layers || []).findIndex((l: Obj) => l.id === selection.id); const L = film.layers[index];
    if (!L) return <div className="p-3 text-xs text-neutral-500">That layer no longer exists.</div>;
    const set = (path: string, v: any) => onChange(f => {
      const parts = path.split("."); let o = f.layers[index];
      for (const p of parts.slice(0, -1)) o = o[p] = o[p] || {};
      if (v === undefined || v === "") delete o[parts[parts.length - 1]]; else o[parts[parts.length - 1]] = v;
    });
    const textual = ["text", "counter", "logo"].includes(L.type);
    return <div>
      <Section title={`${L.type} layer`} right={<span className="font-mono normal-case text-neutral-400">{L.id}</span>}>
        <Row label="Name"><Txt value={L.name} onChange={v => set("name", v)} placeholder={L.id} /></Row>
        <Row label="Type"><Pick value={L.type} options={LAYER_TYPES} onChange={v => set("type", v)} /></Row>
        <Row label="Block"><Pick value={L.block || ""} options={blocks} onChange={v => set("block", v)} /></Row>
        <Row label="Start / end"><Num value={L.start} step={0.05} onChange={v => set("start", v ?? 0)} /><Num value={L.end} step={0.05} onChange={v => set("end", v ?? 1)} /></Row>
      </Section>
      {(L.type === "text" || L.type === "logo") && <Section title="Text">
        <Row label="Text"><Txt area value={L.text} onChange={v => set("text", v)} /></Row>
        <Row label="Accent words"><Txt value={(L.accent || []).join(", ")} placeholder="word numbers, e.g. 0, 3" onChange={v => set("accent", v.split(/[,\s]+/).filter(Boolean).map(Number).filter(n => !isNaN(n)))} /></Row>
      </Section>}
      {L.type === "counter" && <Section title="Counter"><Row label="Value"><Txt value={L.value} onChange={v => set("value", v)} placeholder="52M" /></Row></Section>}
      {textual && <Section title="Type style">
        <Row label="Font"><Txt value={L.style?.font} placeholder="heading / body / mono / family" onChange={v => set("style.font", v)} /></Row>
        <Row label="Size / weight"><Num value={L.style?.size} onChange={v => set("style.size", v)} placeholder="72" /><Num value={L.style?.weight} step={100} onChange={v => set("style.weight", v)} placeholder="700" /></Row>
        <Row label="Colour"><ColorField value={L.style?.color} brand={brand} onChange={v => set("style.color", v)} /></Row>
        <Row label="Align / case"><Pick value={L.style?.align || ""} options={["", "left", "center", "right"]} onChange={v => set("style.align", v)} /><Pick value={L.style?.case || ""} options={["", "upper", "lower"]} onChange={v => set("style.case", v)} /></Row>
        <Row label="Line / tracking"><Num value={L.style?.lineHeight} step={0.02} onChange={v => set("style.lineHeight", v)} placeholder="1.05" /><Num value={L.style?.tracking} step={0.01} onChange={v => set("style.tracking", v)} placeholder="-0.02" /></Row>
        <Row label="Italic"><Check value={L.style?.italic} onChange={v => set("style.italic", v || undefined)} /></Row>
        <Row label="Accent style"><Pick value={L.style?.accentStyle || ""} options={["", "color", "italic", "underline", "highlight", "outline"]} onChange={v => set("style.accentStyle", v)} /></Row>
        <Row label="Accent colour"><ColorField value={L.style?.accentColor} brand={brand} onChange={v => set("style.accentColor", v)} /></Row>
      </Section>}
      {(L.type === "image" || L.type === "logo") && <Section title="Image">
        <Row label="File"><Pick value={L.src || ""} options={["", ...assets]} onChange={v => set("src", v)} /></Row>
        {L.src && <img src={`${API}/${film.__id}/${L.src}`} alt="" className="my-1 max-h-24 rounded border border-neutral-200 object-contain" />}
        <Row label="Fit / focus"><Pick value={L.fit || ""} options={["", "cover", "contain"]} onChange={v => set("fit", v)} /><Txt value={L.focus} placeholder="50% 50%" onChange={v => set("focus", v)} /></Row>
        <Row label="Mask / radius"><Pick value={L.mask || ""} options={["", "circle"]} onChange={v => set("mask", v)} /><Num value={L.radius} onChange={v => set("radius", v)} /></Row>
        <Row label="Filter"><Pick value={L.filter || ""} options={["", "grayscale", "duotone"]} onChange={v => set("filter", v)} /></Row>
        <Row label="Ken Burns"><Pick value={L.kenburns || ""} options={["", "push_in", "pull_out", "pan_left", "pan_right"]} onChange={v => set("kenburns", v)} /></Row>
      </Section>}
      {L.type === "shape" && <Section title="Shape">
        <Row label="Shape"><Pick value={L.shape || "rect"} options={["rect", "circle", "ellipse", "ring", "line"]} onChange={v => set("shape", v)} /></Row>
        <Row label="Fill"><ColorField value={L.fill} brand={brand} onChange={v => set("fill", v)} /></Row>
        <Row label="Stroke"><ColorField value={L.stroke} brand={brand} onChange={v => set("stroke", v)} /></Row>
        <Row label="Stroke width"><Num value={L.strokeWidth} onChange={v => set("strokeWidth", v)} /></Row>
        <Row label="Radius / dash"><Num value={L.radius} onChange={v => set("radius", v)} /><Txt value={L.dash} placeholder="6 10" onChange={v => set("dash", v)} /></Row>
        <Row label="Draw on"><Check value={L.draw} onChange={v => set("draw", v || undefined)} /></Row>
      </Section>}
      {L.type === "path" && <Section title="Path">
        <Row label="Path (SVG d)"><Txt area value={L.d} onChange={v => set("d", v)} /></Row>
        <Row label="Stroke"><ColorField value={L.stroke} brand={brand} onChange={v => set("stroke", v)} /></Row>
        <Row label="Line width"><Num value={L.width} onChange={v => set("width", v)} /></Row>
        <Row label="Glow / head"><Check value={L.glow} onChange={v => set("glow", v || undefined)} /><Check value={L.head} onChange={v => set("head", v || undefined)} /></Row>
        <Row label="Sparks"><Check value={L.sparks} onChange={v => set("sparks", v || undefined)} /></Row>
      </Section>}
      {L.type === "particles" && <Section title="Particles">
        <Row label="Flow"><Pick value={L.flow || "drift"} options={["drift", "rise", "orbit", "burst"]} onChange={v => set("flow", v)} /></Row>
        <Row label="Count / seed"><Num value={L.count} onChange={v => set("count", v)} placeholder="60" /><Num value={L.seed} onChange={v => set("seed", v)} placeholder="5" /></Row>
        <Row label="Size min / max"><Num value={L.size?.[0]} onChange={v => set("size", [v ?? 2, L.size?.[1] ?? 6])} /><Num value={L.size?.[1]} onChange={v => set("size", [L.size?.[0] ?? 2, v ?? 6])} /></Row>
        <Row label="Colour"><ColorField value={L.color} brand={brand} onChange={v => set("color", v)} /></Row>
      </Section>}
      <Section title="Placement">
        <Row label="X / Y"><Num value={L.x} onChange={v => set("x", v)} placeholder="centre" /><Num value={L.y} onChange={v => set("y", v)} placeholder="centre" /></Row>
        {L.type !== "path" && L.type !== "particles" && <Row label="Anchor"><Pick value={L.anchor || "center"} options={ANCHORS} onChange={v => set("anchor", v)} /></Row>}
        <Row label="Width / height"><Num value={L.type === "path" ? undefined : L.width} onChange={v => set("width", v)} /><Num value={L.height} onChange={v => set("height", v)} /></Row>
        <Row label="Depth"><Num value={L.depth} step={0.1} onChange={v => set("depth", v)} placeholder="1 = canvas, 0 = screen" /></Row>
        <Row label="Scale / rotate"><Num value={L.scale} step={0.05} onChange={v => set("scale", v)} placeholder="1" /><Num value={L.rotate} onChange={v => set("rotate", v)} placeholder="0" /></Row>
        <Row label="Opacity / z"><Num value={L.opacity} step={0.05} onChange={v => set("opacity", v)} placeholder="1" /><Num value={L.z} onChange={v => set("z", v)} /></Row>
      </Section>
      <Section title="Entrance & exit">
        <Row label="In"><Pick value={L.in?.effect || ""} options={["", ...(textual ? TEXT_IN : []), ...ANY_IN]} onChange={v => set("in.effect", v)} /><Num value={L.in?.duration} step={0.05} onChange={v => set("in.duration", v)} placeholder="0.55" /></Row>
        <Row label="In ease / stagger"><Pick value={L.in?.ease || ""} options={EASES} onChange={v => set("in.ease", v)} /><Num value={L.in?.stagger} step={0.01} onChange={v => set("in.stagger", v)} /></Row>
        <Row label="Out"><Pick value={L.out?.effect || ""} options={["", ...OUT]} onChange={v => set("out.effect", v)} /><Num value={L.out?.duration} step={0.05} onChange={v => set("out.duration", v)} placeholder="0.4" /></Row>
        <Row label="Sound in"><Txt value={L.sound?.in} placeholder="pop, impact, sting..." onChange={v => set("sound.in", v)} /><Num value={L.sound?.gain} step={0.1} onChange={v => set("sound.gain", v)} placeholder="0.8" /></Row>
      </Section>
      <Section title="Motion keyframes" right={<button className="rounded px-1 hover:bg-neutral-100" onClick={() => onChange(f => { const l = f.layers[index]; l.motion = [...(l.motion || []), { t: round(Math.max(0, time - l.start)) }]; })}><Plus className="h-3.5 w-3.5" /></button>}>
        {(L.motion || []).length === 0 && <div className="text-xs text-neutral-400">None. Add one to move, scale, rotate or fade the layer over its life (times are from its start).</div>}
        {(L.motion || []).map((k: Obj, ki: number) => <div key={ki} className="mb-1 grid grid-cols-7 gap-1">
          {["t", "dx", "dy", "scale", "rotate", "opacity"].map(f => <input key={f} type="number" step={f === "t" || f === "scale" || f === "opacity" ? 0.05 : 1} title={f} placeholder={f} value={k[f] ?? ""} className={inputCls}
            onChange={e => onChange(d => { const m = d.layers[index].motion[ki]; if (e.target.value === "") delete m[f]; else m[f] = Number(e.target.value); })} />)}
          <button title="Remove" className="rounded hover:bg-neutral-100" onClick={() => onChange(d => { d.layers[index].motion.splice(ki, 1); })}><Trash2 className="mx-auto h-3.5 w-3.5 text-neutral-500" /></button>
        </div>)}
      </Section>
    </div>;
  }
  if (selection.kind === "block") {
    const index = (film.blocks || []).findIndex((b: Obj) => b.id === selection.id); const B = film.blocks[index];
    if (!B) return null;
    const set = (k: string, v: any) => onChange(f => { f.blocks[index][k] = v; });
    return <Section title="Block">
      <Row label="Name"><Txt value={B.name} onChange={v => set("name", v)} /></Row>
      <Row label="Start / end"><Num value={B.start} step={0.05} onChange={v => set("start", v ?? 0)} /><Num value={B.end} step={0.05} onChange={v => set("end", v ?? 1)} /></Row>
      <Row label="Canvas spot"><Num value={B.origin?.x} onChange={v => set("origin", { ...(B.origin || {}), x: v ?? 0 })} /><Num value={B.origin?.y} onChange={v => set("origin", { ...(B.origin || {}), y: v ?? 0 })} /></Row>
      <p className="mt-1 text-[11px] text-neutral-500">Layers in this block are placed relative to its spot; camera keys can fly to it by name.</p>
      <button className="mt-2 text-xs text-red-600 hover:underline" onClick={() => { onChange(f => { f.blocks.splice(index, 1); }); onSelect({ kind: "film" }); }}>Delete block (its layers stay)</button>
    </Section>;
  }
  if (selection.kind === "camera") {
    const K = film.camera?.[selection.index]; if (!K) return null;
    const set = (k: string, v: any) => onChange(f => { if (v === undefined || v === "") delete f.camera[selection.index][k]; else f.camera[selection.index][k] = v; });
    return <Section title="Camera key">
      <Row label="Time"><Num value={K.t} step={0.05} onChange={v => set("t", v ?? 0)} /></Row>
      <Row label="Block"><Pick value={K.block || ""} options={blocks} onChange={v => set("block", v)} /></Row>
      <Row label="X / Y offset"><Num value={K.x} onChange={v => set("x", v)} placeholder="0" /><Num value={K.y} onChange={v => set("y", v)} placeholder="0" /></Row>
      <Row label="Zoom / rotate"><Num value={K.zoom} step={0.01} onChange={v => set("zoom", v)} placeholder="1" /><Num value={K.rotate} step={0.5} onChange={v => set("rotate", v)} placeholder="0" /></Row>
      <Row label="Ease in"><Pick value={K.ease || ""} options={EASES} onChange={v => set("ease", v)} /></Row>
      <button className="mt-2 text-xs text-red-600 hover:underline" onClick={() => { onChange(f => { f.camera.splice(selection.index, 1); }); onSelect({ kind: "film" }); }}>Delete camera key</button>
    </Section>;
  }
  if (selection.kind === "transition") {
    const T = film.transitions?.[selection.index]; if (!T) return null;
    const set = (k: string, v: any) => onChange(f => { if (v === undefined || v === "") delete f.transitions[selection.index][k]; else f.transitions[selection.index][k] = v; });
    return <Section title="Transition">
      <Row label="At / length"><Num value={T.at} step={0.05} onChange={v => set("at", v ?? 0)} /><Num value={T.duration} step={0.05} onChange={v => set("duration", v)} placeholder="0.5" /></Row>
      <Row label="Type"><Pick value={T.type} options={TRANSITIONS} onChange={v => set("type", v)} /></Row>
      <Row label="Colour"><ColorField value={T.color} brand={brand} onChange={v => set("color", v)} /></Row>
      <Row label="Sound"><Txt value={T.sound} placeholder="whoosh (default) or none" onChange={v => set("sound", v)} /></Row>
      <button className="mt-2 text-xs text-red-600 hover:underline" onClick={() => { onChange(f => { f.transitions.splice(selection.index, 1); }); onSelect({ kind: "film" }); }}>Delete transition</button>
    </Section>;
  }
  if (selection.kind === "sound") {
    const S = film.sounds?.[selection.index]; if (!S) return null;
    const set = (k: string, v: any) => onChange(f => { f.sounds[selection.index][k] = v; });
    return <Section title="Sound">
      <Row label="Time"><Num value={S.t} step={0.05} onChange={v => set("t", v ?? 0)} /></Row>
      <Row label="Sound"><Pick value={S.name} options={(film.__sounds || []).map((s: Obj) => s.name)} onChange={v => set("name", v)} /></Row>
      <Row label="Gain"><Num value={S.gain} step={0.1} onChange={v => set("gain", v)} /></Row>
      <button className="mt-2 text-xs text-red-600 hover:underline" onClick={() => { onChange(f => { f.sounds.splice(selection.index, 1); }); onSelect({ kind: "film" }); }}>Delete sound</button>
    </Section>;
  }
  const set = (path: string, v: any) => onChange(f => { const parts = path.split("."); let o = f; for (const p of parts.slice(0, -1)) o = o[p] = o[p] || {}; o[parts[parts.length - 1]] = v; });
  return <div>
    <Section title="Film">
      <Row label="Title"><Txt value={film.title} onChange={v => set("title", v)} /></Row>
      <Row label="Length (s)"><Num value={film.duration} step={0.5} onChange={v => set("duration", v ?? 10)} /></Row>
      <Row label="Aspect"><Pick value={film.aspect} options={["16:9", "9:16", "1:1"]} onChange={v => set("aspect", v)} /></Row>
    </Section>
    <Section title="Brand colours" right={<button className="rounded px-1 hover:bg-neutral-100" title="Add a colour" onClick={() => { const n = prompt("Colour name"); if (n) set(`brand.colors.${n}`, "#888888"); }}><Plus className="h-3.5 w-3.5" /></button>}>
      {Object.entries(brand.colors || {}).filter(([, v]) => typeof v === "string").map(([k, v]) => <Row key={k} label={k}><ColorField value={v} brand={{}} onChange={nv => set(`brand.colors.${k}`, nv)} /></Row>)}
    </Section>
    <Section title="Brand fonts">
      {["heading", "body", "mono"].map(k => <Row key={k} label={k}><Txt value={brand.fonts?.[k]} placeholder="Google Font family" onChange={v => set(`brand.fonts.${k}`, v)} /></Row>)}
      <p className="text-[11px] text-neutral-500">Font changes load when the preview reloads (after saving).</p>
    </Section>
    <Section title="Background">
      <Row label="Colour"><ColorField value={film.background?.color} brand={brand} onChange={v => set("background.color", v)} /></Row>
      <Row label="Texture"><Pick value={film.background?.texture || "none"} options={["none", "dots", "grid", "guides", "vignette"]} onChange={v => set("background.texture", v)} /></Row>
      <Row label="Line colour"><ColorField value={film.background?.lineColor} brand={brand} onChange={v => set("background.lineColor", v)} /></Row>
    </Section>
    <Section title="Music">
      <Row label="Mood"><Pick value={film.music?.mood || "cinematic"} options={MOODS} onChange={v => set("music.mood", v)} /></Row>
      <p className="text-[11px] text-neutral-500">A licensed bed (Openverse) is picked for the mood at render time and ducked under the sound effects.</p>
    </Section>
  </div>;
}

/* ---------- The Studio screen ---------- */
export function Studio({ onClose }: { onClose: () => void }) {
  const [recent, setRecent] = useState<Obj[]>([]);
  const [engines, setEngines] = useState<Obj>({}); const [sounds, setSounds] = useState<Obj[]>([]);
  const [job, setJob] = useState<Obj | null>(null);
  const [film, setFilm] = useState<Obj | null>(null);
  const [past, setPast] = useState<Obj[]>([]); const [future, setFuture] = useState<Obj[]>([]);
  const [selection, setSelection] = useState<Selection>({ kind: "film" });
  const [time, setTime] = useState(0); const [playing, setPlaying] = useState(false);
  const [saveState, setSaveState] = useState(""); const [assets, setAssets] = useState<string[]>([]);
  const [frameKey, setFrameKey] = useState(0);
  const [remixText, setRemixText] = useState(""); const [remixEngine, setRemixEngine] = useState("");
  const [compare, setCompare] = useState<number | null>(null); const [compareAspect, setCompareAspect] = useState("16:9"); const [showVersions, setShowVersions] = useState(false);
  const [left, setLeft] = useState(true); const [right, setRight] = useState(true); const [error, setError] = useState("");
  const saveTimer = useRef<number | undefined>(undefined); const dragBase = useRef<Obj | null>(null);

  const refreshList = useCallback(() => fetch(API).then(r => r.json()).then(d => setRecent(d.films || [])).catch(() => {}), []);
  useEffect(() => { refreshList(); fetch(`${API}/engines`).then(r => r.json()).then(d => { setEngines(d.engines || {}); setSounds(d.sounds || []); }).catch(() => {}); }, [refreshList]);

  const loadFilm = useCallback(async (id: string) => {
    const res = await fetch(`${API}/${id}/film`); if (!res.ok) return;
    setFilm(await res.json()); setPast([]); setFuture([]); setFrameKey(k => k + 1);
    fetch(`${API}/${id}/assets`).then(r => r.json()).then(d => setAssets(d.assets || [])).catch(() => {});
  }, []);
  const open = useCallback(async (id: string) => {
    const res = await fetch(`${API}/${id}`); if (!res.ok) return;
    const state = await res.json(); setJob(state); setSelection({ kind: "film" }); setTime(0); setCompare(null);
    if (state.versions?.length) loadFilm(id); else setFilm(null);
  }, [loadFilm]);

  // Follow the job while an engine works or a render runs; load the new version when it lands.
  const busy = !!job && BUSY.includes(job.status); const rendering = job?.render?.status === "rendering";
  useEffect(() => {
    if (!job || (!busy && !rendering)) return;
    const timer = window.setInterval(async () => {
      const res = await fetch(`${API}/${job.id}`); if (!res.ok) return;
      const next = await res.json(); setJob(next);
      if (next.version !== job.version && next.versions?.length) { loadFilm(job.id); refreshList(); }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [job?.id, job?.status, job?.version, busy, rendering, loadFilm, refreshList]);

  // Playback: the editor drives the frame's clock.
  useEffect(() => {
    if (!playing || !film) return;
    let raf = 0, last = performance.now();
    const tick = (now: number) => { setTime(t => { const n = t + (now - last) / 1000; if (n >= film.duration) { setPlaying(false); return film.duration; } return n; }); last = now; raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick); return () => cancelAnimationFrame(raf);
  }, [playing, film?.duration]);

  const save = useCallback((next: Obj) => {
    if (!job) return;
    window.clearTimeout(saveTimer.current); setSaveState("Saving…");
    saveTimer.current = window.setTimeout(async () => {
      const res = await fetch(`${API}/${job.id}/film`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(next) });
      const data = await res.json().catch(() => ({}));
      setSaveState(res.ok ? "Saved" : ""); setError(res.ok ? "" : `Not saved: ${data.detail || res.status}`);
    }, 600);
  }, [job?.id]);

  /* Every edit goes through here: a draft is changed, the preview updates, the film autosaves, and undo
     keeps the step. During a drag, commit=false updates live and the drag's end records one undo step. */
  const filmRef = useRef<Obj | null>(null); filmRef.current = film;
  const change = useCallback((fn: (draft: Obj) => void, commit = true) => {
    const prev = filmRef.current; if (!prev) return;
    if (!commit && !dragBase.current) dragBase.current = prev;
    const next = clone(prev); fn(next); filmRef.current = next; setFilm(next);
    if (commit) { const base = dragBase.current || prev; setPast(p => [...p.slice(-80), base]); setFuture([]); dragBase.current = null; save(next); }
  }, [save]);
  const undo = () => { if (!past.length || !film) return; const prev = past[past.length - 1]; setFuture(f => [film, ...f]); setPast(p => p.slice(0, -1)); setFilm(prev); save(prev); };
  const redo = () => { if (!future.length || !film) return; const next = future[0]; setPast(p => [...p, film]); setFuture(f => f.slice(1)); setFilm(next); save(next); };
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = ["INPUT", "TEXTAREA", "SELECT"].includes((e.target as HTMLElement)?.tagName);
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z" && !typing) { e.preventDefault(); e.shiftKey ? redo() : undo(); }
      if (e.code === "Space" && !typing && film) { e.preventDefault(); setPlaying(p => !p); }
    };
    // The same shortcuts, forwarded by the preview frame when it has focus.
    const onFrameKey = (e: MessageEvent) => {
      const m = e.data; if (m?.type !== "key") return;
      if (m.meta && String(m.key).toLowerCase() === "z") m.shift ? redo() : undo();
      if (m.code === "Space" && film) setPlaying(p => !p);
    };
    window.addEventListener("keydown", onKey); window.addEventListener("message", onFrameKey);
    return () => { window.removeEventListener("keydown", onKey); window.removeEventListener("message", onFrameKey); };
  });

  const blockAt = (t: number) => (film?.blocks || []).find((b: Obj) => t >= b.start && t < b.end)?.id;
  const addLayer = (type: string) => change(f => {
    const id = `${type}-${Math.random().toString(36).slice(2, 6)}`;
    const base: Obj = { id, type, block: blockAt(time), start: round(time), end: Math.min(f.duration, round(time + 3)), in: { effect: type === "text" ? "rise-words" : "fade" } };
    if (type === "text") Object.assign(base, { text: "New line", style: { size: 80 } });
    if (type === "shape") Object.assign(base, { shape: "rect", width: 400, height: 240, fill: "accent", radius: 16 });
    if (type === "counter") Object.assign(base, { value: "100+", style: { size: 160, color: "accent" } });
    if (type === "image") Object.assign(base, { src: assets[0], width: 800, height: 500, radius: 16 });
    if (type === "particles") Object.assign(base, { count: 80, flow: "drift", depth: 0.4, start: 0, end: f.duration });
    if (type === "path") Object.assign(base, { d: "M 200 900 C 700 700, 1200 400, 1700 150", glow: true, head: true, in: { effect: "none", duration: 2 } });
    f.layers = [...(f.layers || []), base]; setSelection({ kind: "layer", id });
  });
  const removeSelected = () => {
    if (selection.kind !== "layer") return;
    change(f => { f.layers = f.layers.filter((l: Obj) => l.id !== selection.id); }); setSelection({ kind: "film" });
  };
  const duplicateSelected = () => {
    if (selection.kind !== "layer") return;
    change(f => { const L = f.layers.find((l: Obj) => l.id === selection.id); if (!L) return; const copy = { ...clone(L), id: `${L.id}-copy${Math.random().toString(36).slice(2, 4)}`, y: (L.y ?? 540) + 60 }; f.layers.push(copy); setSelection({ kind: "layer", id: copy.id }); });
  };
  const addCameraKey = () => change(f => { f.camera = [...(f.camera || []), { t: round(time), block: blockAt(time), zoom: 1 }].sort((a: Obj, b: Obj) => a.t - b.t); });
  const addTransition = () => change(f => { f.transitions = [...(f.transitions || []), { at: round(time), type: "whip", duration: 0.5 }]; });
  const addSound = () => change(f => { f.sounds = [...(f.sounds || []), { t: round(time), name: "whoosh", gain: 0.8 }]; });
  const addBlock = () => change(f => {
    const last = (f.blocks || [])[f.blocks.length - 1]; const id = `block${(f.blocks || []).length + 1}`;
    f.blocks = [...(f.blocks || []), { id, name: "New block", start: round(time), end: Math.min(f.duration, round(time + 4)), origin: { x: (last?.origin?.x || 0) + 2600, y: last?.origin?.y || 0 } }];
    setSelection({ kind: "block", id });
  });

  const remix = async () => {
    if (!job || !remixText.trim()) return;
    setError("");
    const res = await fetch(`${API}/${job.id}/remix`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ instruction: remixText, engine: remixEngine || undefined }) });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { setError(data.detail || "Remix could not start."); return; }
    setJob(data); setRemixText("");
  };
  const saveVersion = async () => {
    if (!job) return;
    const note = prompt("Name this version", "My edit"); if (note === null) return;
    await fetch(`${API}/${job.id}/versions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ note }) });
    open(job.id);
  };
  const restore = async (n: number) => {
    if (!job) return;
    const res = await fetch(`${API}/${job.id}/versions/${n}/restore`, { method: "POST" });
    if (res.ok) { const data = await res.json(); setPast(p => film ? [...p, film] : p); setFilm(data); setFrameKey(k => k + 1); }
  };
  const render = async () => {
    if (!job) return;
    window.clearTimeout(saveTimer.current);
    if (film) await fetch(`${API}/${job.id}/film`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(film) });
    const res = await fetch(`${API}/${job.id}/render`, { method: "POST" }); const data = await res.json().catch(() => ({}));
    if (!res.ok) setError(data.detail || "Render could not start."); else setJob(data);
  };

  // A version keeps its own shape: a 16:9 original next to a 9:16 remix.
  useEffect(() => {
    if (compare === null || !job) return;
    fetch(`${API}/${job.id}/versions/${compare}`).then(r => r.json()).then(v => setCompareAspect(v.aspect || "16:9")).catch(() => {});
  }, [compare, job?.id]);
  const filmForEditor = useMemo(() => film ? { ...film, __id: job?.id, __sounds: sounds } : null, [film, job?.id, sounds]);
  const previewFilm = film;  // Sent to the frame on every change.
  const header = <div className="flex h-12 shrink-0 items-center gap-2 border-b border-neutral-200 bg-white px-3">
    <Clapperboard className="h-4 w-4" />
    <span className="font-semibold">Studio</span>
    {job && <span className="truncate text-sm text-neutral-500">· {film?.title || job.title}</span>}
    {job && <button onClick={() => { setJob(null); setFilm(null); refreshList(); }} className="ml-2 rounded-md border border-neutral-200 px-2 py-1 text-xs hover:bg-neutral-50">New / open film</button>}
    <div className="ml-auto flex items-center gap-2 text-xs">
      {saveState && film && <span className="text-neutral-500">{saveState}</span>}
      {film && <>
        <button onClick={undo} disabled={!past.length} title="Undo (Cmd+Z)" className="rounded p-1.5 hover:bg-neutral-100 disabled:opacity-30"><Undo2 className="h-4 w-4" /></button>
        <button onClick={redo} disabled={!future.length} title="Redo (Shift+Cmd+Z)" className="rounded p-1.5 hover:bg-neutral-100 disabled:opacity-30"><Redo2 className="h-4 w-4" /></button>
        <button onClick={() => setShowVersions(v => !v)} className={`flex items-center gap-1 rounded-md border px-2 py-1 ${showVersions ? "border-neutral-900" : "border-neutral-200"} hover:bg-neutral-50`}><History className="h-3.5 w-3.5" /> Versions</button>
        <button onClick={render} disabled={rendering || busy} className="flex items-center gap-1 rounded-md bg-neutral-900 px-3 py-1.5 font-semibold text-white hover:bg-neutral-800 disabled:opacity-40">
          {rendering ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Rendering {Math.round((job?.render?.progress || 0) * 100)}%</> : <><FilmIcon className="h-3.5 w-3.5" /> Render MP4</>}
        </button>
        {job?.render?.status === "complete" && <a href={`${API}/${job.id}/video`} className="flex items-center gap-1 rounded-md border border-neutral-200 px-2 py-1.5 hover:bg-neutral-50"><Download className="h-3.5 w-3.5" /> MP4</a>}
      </>}
      <button onClick={onClose} className="rounded p-1.5 hover:bg-neutral-100" title="Close"><X className="h-4 w-4" /></button>
    </div>
  </div>;

  if (!job) return <div className="fixed inset-0 z-50 flex flex-col bg-neutral-50 text-neutral-900">{header}
    <div className="flex-1 overflow-y-auto"><NewFilm engines={engines} recent={recent} onOpen={open} onMade={s => { setJob(s); setFilm(null); }} /></div></div>;

  if (!film) return <div className="fixed inset-0 z-50 flex flex-col bg-neutral-50 text-neutral-900">{header}
    <div className="flex flex-1 items-center justify-center">
      <div className="max-w-md space-y-3 rounded-xl border border-neutral-200 bg-white p-6 text-center text-sm">
        {busy ? <Loader2 className="mx-auto h-6 w-6 animate-spin text-neutral-500" /> : null}
        <div className="font-semibold">{job.stage}</div>
        {busy && <p className="text-neutral-500">The engine reads the brief, writes the film, draws it, looks at the frames and fixes what it sees. This usually takes a few minutes; you can close the Studio and come back.</p>}
        {job.error && <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-left text-red-800">{job.error}</div>}
      </div>
    </div></div>;

  const versions: Obj[] = job.versions || [];
  return <div className="fixed inset-0 z-50 flex flex-col bg-neutral-50 text-neutral-900">
    {header}
    {(error || job.error || busy || job.render?.status === "failed") && <div className={`shrink-0 px-4 py-1.5 text-xs ${busy ? "bg-sky-50 text-sky-900" : "bg-red-50 text-red-800"}`}>
      {busy ? <span className="flex items-center gap-2"><Loader2 className="h-3.5 w-3.5 animate-spin" /> {job.stage}. Your edits are paused until it finishes.</span> : error || job.error || `Render failed: ${job.render?.error}`}
    </div>}
    <div className="flex min-h-0 flex-1">
      {/* Left: add things */}
      {left ? <div className="flex w-52 shrink-0 flex-col overflow-y-auto border-r border-neutral-200 bg-white">
        <div className="flex items-center justify-between border-b border-neutral-200 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Add <button onClick={() => setLeft(false)} title="Collapse"><PanelLeftClose className="h-4 w-4" /></button></div>
        <div className="grid grid-cols-2 gap-1 p-2 text-xs">
          {LAYER_TYPES.filter(t => t !== "logo").map(t => <button key={t} disabled={busy} onClick={() => addLayer(t)} className="flex items-center gap-1 rounded border border-neutral-200 px-2 py-1.5 capitalize hover:bg-neutral-50 disabled:opacity-40"><Plus className="h-3 w-3" />{t}</button>)}
          <button disabled={busy} onClick={addBlock} className="flex items-center gap-1 rounded border border-neutral-200 px-2 py-1.5 hover:bg-neutral-50"><Plus className="h-3 w-3" />Block</button>
          <button disabled={busy} onClick={addCameraKey} className="flex items-center gap-1 rounded border border-neutral-200 px-2 py-1.5 hover:bg-neutral-50"><Camera className="h-3 w-3" />Camera key</button>
          <button disabled={busy} onClick={addTransition} className="flex items-center gap-1 rounded border border-neutral-200 px-2 py-1.5 hover:bg-neutral-50"><Plus className="h-3 w-3" />Transition</button>
          <button disabled={busy} onClick={addSound} className="flex items-center gap-1 rounded border border-neutral-200 px-2 py-1.5 hover:bg-neutral-50"><Plus className="h-3 w-3" />Sound</button>
        </div>
        <div className="border-t border-neutral-200 p-2 text-xs">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Selected layer</div>
          <div className="flex gap-1">
            <button disabled={selection.kind !== "layer"} onClick={duplicateSelected} className="flex flex-1 items-center justify-center gap-1 rounded border border-neutral-200 py-1.5 hover:bg-neutral-50 disabled:opacity-30"><Copy className="h-3 w-3" />Duplicate</button>
            <button disabled={selection.kind !== "layer"} onClick={removeSelected} className="flex flex-1 items-center justify-center gap-1 rounded border border-neutral-200 py-1.5 text-red-600 hover:bg-red-50 disabled:opacity-30"><Trash2 className="h-3 w-3" />Delete</button>
          </div>
        </div>
        <div className="border-t border-neutral-200 p-2 text-xs">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Blocks</div>
          {(film.blocks || []).map((b: Obj) => <button key={b.id} onClick={() => { setSelection({ kind: "block", id: b.id }); setTime(b.start); }} className="block w-full truncate rounded px-2 py-1 text-left hover:bg-neutral-50">{b.name} <span className="text-neutral-400">{b.start}s</span></button>)}
          <button onClick={() => setSelection({ kind: "film" })} className="mt-1 block w-full rounded px-2 py-1 text-left text-neutral-600 hover:bg-neutral-50">Film settings</button>
        </div>
      </div> : <button onClick={() => setLeft(true)} className="w-8 shrink-0 border-r border-neutral-200 bg-white" title="Expand"><PanelLeftOpen className="mx-auto h-4 w-4" /></button>}

      {/* Centre: preview, transport, remix */}
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex min-h-0 flex-1 gap-3 p-3">
          <div className="flex min-w-0 flex-1 flex-col">
            {compare !== null && <div className="mb-1 text-center text-xs text-neutral-500">Current</div>}
            <Preview key={frameKey} src={`${API}/${job.id}/player?k=${frameKey}`} film={previewFilm} time={time} aspect={film.aspect} onSelect={id => id && setSelection({ kind: "layer", id })} />
          </div>
          {compare !== null && <div className="flex min-w-0 flex-1 flex-col">
            <div className="mb-1 flex items-center justify-center gap-2 text-xs text-neutral-500">v{compare}: {versions.find(v => v.n === compare)?.note}
              <button onClick={() => restore(compare)} className="rounded border border-neutral-200 px-1.5 hover:bg-neutral-50">Restore</button>
              <button onClick={() => setCompare(null)} className="rounded border border-neutral-200 px-1.5 hover:bg-neutral-50">Close</button></div>
            <Preview key={`c${compare}`} src={`${API}/${job.id}/player?version=${compare}`} film={null} time={time} aspect={compareAspect} />
          </div>}
        </div>
        <div className="flex shrink-0 items-center gap-2 border-t border-neutral-200 bg-white px-3 py-2">
          <button onClick={() => { if (time >= film.duration) setTime(0); setPlaying(p => !p); }} className="rounded-full bg-neutral-900 p-2 text-white hover:bg-neutral-800" title="Play / pause (Space)">{playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}</button>
          <span className="w-24 font-mono text-xs tabular-nums text-neutral-600">{fmt(time)} / {fmt(film.duration)}</span>
          <input type="range" min={0} max={film.duration} step={0.01} value={time} onChange={e => { setPlaying(false); setTime(Number(e.target.value)); }} className="flex-1" />
          <span className="text-[11px] text-neutral-400">Preview is silent; sound and music are mixed in the render.</span>
        </div>
        <div className="flex shrink-0 items-center gap-2 border-t border-neutral-200 bg-white px-3 py-2">
          <Wand2 className="h-4 w-4 text-neutral-500" />
          <input value={remixText} onChange={e => setRemixText(e.target.value)} onKeyDown={e => { if (e.key === "Enter") remix(); }} disabled={busy}
            placeholder="Remix by direction: make it punchier and faster; turn it vertical for reels; swap the stats for a testimonial; darker, more cinematic…"
            className="flex-1 rounded-md border border-neutral-200 px-3 py-1.5 text-sm outline-none focus:border-neutral-400 disabled:bg-neutral-50" />
          <select value={remixEngine} onChange={e => setRemixEngine(e.target.value)} className="rounded-md border border-neutral-200 px-2 py-1.5 text-xs">
            <option value="">{job.engine === "gemini" ? "Gemini" : "Claude Code"} (as made)</option>
            <option value="claude" disabled={engines.claude === false}>Claude Code</option>
            <option value="gemini" disabled={engines.gemini === false}>Gemini (billed)</option>
          </select>
          <button onClick={remix} disabled={busy || !remixText.trim()} className="rounded-md bg-neutral-900 px-3 py-1.5 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-40">Remix</button>
        </div>
        {showVersions && <div className="max-h-40 shrink-0 overflow-y-auto border-t border-neutral-200 bg-white px-3 py-2 text-xs">
          <div className="mb-1 flex items-center justify-between font-semibold text-neutral-500"><span>Versions (each engine run and each saved edit)</span>
            <button onClick={saveVersion} className="rounded border border-neutral-200 px-2 py-0.5 font-normal hover:bg-neutral-50">Save current as version</button></div>
          {[...versions].reverse().map(v => <div key={v.n} className="flex items-center gap-2 border-b border-neutral-100 py-1 last:border-0">
            <span className="w-8 font-mono">v{v.n}</span><span className="flex-1 truncate">{v.note}</span>
            <span className="text-neutral-400">{new Date(v.created * 1000).toLocaleString()}</span>
            <button onClick={() => setCompare(v.n)} className="flex items-center gap-1 rounded border border-neutral-200 px-1.5 hover:bg-neutral-50"><Columns2 className="h-3 w-3" />Compare</button>
            <button onClick={() => restore(v.n)} className="rounded border border-neutral-200 px-1.5 hover:bg-neutral-50">Restore</button>
          </div>)}
        </div>}
        <div className="h-56 shrink-0 border-t border-neutral-200">
          <Timeline film={film} time={time} onSeek={t => { setPlaying(false); setTime(t); }} selection={selection} onSelect={setSelection} onChange={change} />
        </div>
      </div>

      {/* Right: inspector */}
      {right ? <div className={`w-80 shrink-0 overflow-y-auto border-l border-neutral-200 bg-white ${busy ? "pointer-events-none opacity-50" : ""}`}>
        <div className="flex items-center justify-between border-b border-neutral-200 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Inspector <button onClick={() => setRight(false)} title="Collapse" className="pointer-events-auto"><PanelRightClose className="h-4 w-4" /></button></div>
        {filmForEditor && <Inspector film={filmForEditor} selection={selection} assets={assets} time={time} onSelect={setSelection}
          onChange={fn => change(fn)} />}
      </div> : <button onClick={() => setRight(true)} className="w-8 shrink-0 border-l border-neutral-200 bg-white" title="Expand"><PanelRightOpen className="mx-auto h-4 w-4" /></button>}
    </div>
  </div>;
}
