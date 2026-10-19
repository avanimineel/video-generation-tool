import React, { useState, useRef, useEffect } from 'react';
import { 
  Music, Volume2, VolumeX, Play, Pause, Plus, Trash2, 
  Sparkles, Sliders, Check, Disc, Zap, Radio
} from 'lucide-react';
import { ProjectState, AudioTrackItem } from '../../types';
import { BACKEND_ORIGIN } from '../../services/api';

interface MusicSfxInspectorProps {
  project: ProjectState;
  onUpdateProject: (updated: ProjectState) => void;
  currentTime: number;
}

// Licensed tracks found on Openverse through the backend (CC0, CC BY or CC BY-SA, commercial use allowed).
interface LicensedTrack {
  id: string;
  title: string;
  creator: string;
  license: string;
  attribution: string;
  credit_required: boolean;
  duration: number;
  preview_url: string;
}

const MUSIC_API = `${BACKEND_ORIGIN}/api/music`;
const MOODS = ['cinematic', 'inspiring', 'corporate', 'electronic', 'upbeat', 'lofi', 'calm'];

interface StockSfx {
  id: string;
  title: string;
  category: string;
  duration: number;
  type: 'click' | 'whoosh' | 'chime' | 'bass' | 'typewriter';
}


const STOCK_SFX: StockSfx[] = [
  { id: 'sfx_click', title: 'Tactile UI Click', category: 'Interface', duration: 0.15, type: 'click' },
  { id: 'sfx_whoosh', title: 'Smooth Air Swoosh', category: 'Transition', duration: 0.45, type: 'whoosh' },
  { id: 'sfx_chime', title: 'Glass Stat Chime', category: 'Callout', duration: 0.8, type: 'chime' },
  { id: 'sfx_bass', title: 'Deep Sub Impact', category: 'Cinematic', duration: 1.2, type: 'bass' },
  { id: 'sfx_type', title: 'Mechanical Typewriter', category: 'Text Pop', duration: 0.1, type: 'typewriter' }
];

export const MusicSfxInspector: React.FC<MusicSfxInspectorProps> = ({
  project,
  onUpdateProject,
  currentTime = 0
}) => {
  const [activeCategory, setActiveCategory] = useState<'music' | 'sfx'>('music');
  const [playingPreviewId, setPlayingPreviewId] = useState<string | null>(null);
  const [musicVolume, setMusicVolume] = useState<number>(0.35);
  const [autoDucking, setAutoDucking] = useState<boolean>(true);
  const [mood, setMood] = useState<string>('cinematic');
  const [query, setQuery] = useState<string>('');
  const [tracks, setTracks] = useState<LicensedTrack[]>([]);
  const [searching, setSearching] = useState<boolean>(false);
  const [musicError, setMusicError] = useState<string>('');
  const [addingId, setAddingId] = useState<string | null>(null);
  const previewRef = useRef<HTMLAudioElement | null>(null);

  const searchMusic = async (nextMood = mood, text = query) => {
    setSearching(true); setMusicError('');
    try {
      const params = new URLSearchParams({ min_seconds: String(Math.min(60, Math.ceil(project.duration_seconds || 30))) });
      if (text.trim()) params.set('q', text.trim()); else params.set('mood', nextMood);
      const res = await fetch(`${MUSIC_API}/search?${params}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Search failed (${res.status})`);
      setTracks(data.tracks || []);
    } catch (e: any) { setMusicError(e.message || 'Music search failed'); setTracks([]); }
    finally { setSearching(false); }
  };
  useEffect(() => { searchMusic(); return () => { previewRef.current?.pause(); }; }, []);

  // Web Audio Preview Synthesizer (Instant 0-latency sound generation without broken external CDNs)
  const audioCtxRef = useRef<AudioContext | null>(null);
  const oscRef = useRef<OscillatorNode | null>(null);

  const getAudioContext = () => {
    if (!audioCtxRef.current) {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) audioCtxRef.current = new AudioCtx();
    }
    return audioCtxRef.current;
  };

  const playSfxTone = (type: StockSfx['type']) => {
    const ctx = getAudioContext();
    if (!ctx) return;
    if (ctx.state === 'suspended') ctx.resume();

    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    if (type === 'click') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(1200, now);
      osc.frequency.exponentialRampToValueAtTime(150, now + 0.08);
      gain.gain.setValueAtTime(0.4, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.08);
      osc.start(now);
      osc.stop(now + 0.08);
    } else if (type === 'whoosh') {
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(180, now);
      osc.frequency.linearRampToValueAtTime(600, now + 0.2);
      osc.frequency.linearRampToValueAtTime(120, now + 0.45);
      gain.gain.setValueAtTime(0.05, now);
      gain.gain.linearRampToValueAtTime(0.25, now + 0.2);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.45);
      osc.start(now);
      osc.stop(now + 0.45);
    } else if (type === 'chime') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(1046.5, now); // C6
      gain.gain.setValueAtTime(0.3, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.8);
      osc.start(now);
      osc.stop(now + 0.8);
    } else if (type === 'bass') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(80, now);
      osc.frequency.exponentialRampToValueAtTime(35, now + 1.0);
      gain.gain.setValueAtTime(0.5, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 1.2);
      osc.start(now);
      osc.stop(now + 1.2);
    } else if (type === 'typewriter') {
      osc.type = 'square';
      osc.frequency.setValueAtTime(800, now);
      gain.gain.setValueAtTime(0.15, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.05);
      osc.start(now);
      osc.stop(now + 0.05);
    }
  };

  const toggleMusicPreview = (track: LicensedTrack) => {
    if (playingPreviewId === track.id) { previewRef.current?.pause(); setPlayingPreviewId(null); return; }
    previewRef.current?.pause();
    const audio = new Audio(track.preview_url);
    audio.volume = 0.8; audio.onended = () => setPlayingPreviewId(null);
    audio.play().catch(() => setMusicError('This preview could not be played.'));
    previewRef.current = audio; setPlayingPreviewId(track.id);
  };

  // The backend downloads the track, keeps its licence and credit, and saves it as the project's music bed.
  const handleAddMusicToProject = async (track: LicensedTrack) => {
    setAddingId(track.id); setMusicError('');
    try {
      const res = await fetch(`${MUSIC_API}/${project.id}/add`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ music_id: track.id, volume: musicVolume, duck_under_speech: autoDucking }) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Could not add (${res.status})`);
      onUpdateProject(data);
    } catch (e: any) { setMusicError(e.message || 'Could not add the track'); }
    finally { setAddingId(null); }
  };

  const handleAddSfxToPlayhead = (sfx: StockSfx) => {
    const newTrack: AudioTrackItem = {
      id: `sfx_${sfx.id}_${Date.now()}`,
      title: sfx.title,
      type: 'sfx',
      url: `/audio/${sfx.id}.mp3`,
      duration: sfx.duration,
      start: Math.round(currentTime * 100) / 100,
      volume: 0.8,
      duck_under_speech: false
    };

    playSfxTone(sfx.type);

    const updated = {
      ...project,
      audio_tracks: [...(project.audio_tracks || []), newTrack]
    };
    onUpdateProject(updated);
  };

  const handleDeleteAudioTrack = (trackId: string) => {
    const updated = {
      ...project,
      audio_tracks: (project.audio_tracks || []).filter((t) => t.id !== trackId)
    };
    onUpdateProject(updated);
  };

  const activeAudioTracks = project.audio_tracks || [];

  return (
    <div className="flex flex-col h-full bg-white text-neutral-900 select-none overflow-y-auto">
      {/* Top Header & Sub-Tabs */}
      <div className="p-3 border-b border-neutral-200 bg-neutral-50 space-y-3">
        <div className="flex rounded-lg bg-neutral-200/80 p-0.5 text-xs font-medium">
          <button
            type="button"
            onClick={() => setActiveCategory('music')}
            className={`flex-1 py-1.5 rounded-md transition text-xs font-medium ${
              activeCategory === 'music'
                ? 'bg-white text-neutral-900 shadow-2xs font-semibold'
                : 'text-neutral-600 hover:text-neutral-900'
            }`}
          >
            Music Tracks
          </button>
          <button
            type="button"
            onClick={() => setActiveCategory('sfx')}
            className={`flex-1 py-1.5 rounded-md transition text-xs font-medium ${
              activeCategory === 'sfx'
                ? 'bg-white text-neutral-900 shadow-2xs font-semibold'
                : 'text-neutral-600 hover:text-neutral-900'
            }`}
          >
            Sound Effects
          </button>
        </div>

        {/* Global Ducking & Volume Controls */}
        <div className="p-2.5 bg-white rounded-xl border border-neutral-200 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-neutral-800">Speech Ducking</span>
            <button
              type="button"
              onClick={() => setAutoDucking(!autoDucking)}
              className={`px-2 py-0.5 rounded text-[11px] font-semibold border transition ${
                autoDucking
                  ? 'bg-neutral-900 text-white border-neutral-900'
                  : 'bg-neutral-100 text-neutral-600 border-neutral-200 hover:bg-neutral-200'
              }`}
            >
              {autoDucking ? 'Auto-Duck On (-14dB)' : 'Off'}
            </button>
          </div>

          <div className="flex items-center gap-2 pt-1 text-xs">
            <Volume2 className="h-3.5 w-3.5 text-neutral-500 shrink-0" />
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={musicVolume}
              onChange={(e) => setMusicVolume(parseFloat(e.target.value))}
              className="flex-1 accent-neutral-900"
            />
            <span className="font-mono text-[11px] text-neutral-600 w-8 text-right">{Math.round(musicVolume * 100)}%</span>
          </div>
        </div>
      </div>

      {/* Main List */}
      <div className="p-3 space-y-3">
        {activeCategory === 'music' ? (
          <div className="space-y-2">
            <div className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">
              Licensed Music (Openverse)
            </div>
            <div className="flex flex-wrap gap-1">
              {MOODS.map(m => (
                <button key={m} type="button" onClick={() => { setMood(m); setQuery(''); searchMusic(m, ''); }}
                  className={`px-2 py-1 rounded-md border text-[11px] capitalize ${mood === m && !query ? 'bg-neutral-900 text-white border-neutral-900' : 'bg-white border-neutral-200 hover:bg-neutral-50'}`}>{m}</button>
              ))}
            </div>
            <form onSubmit={e => { e.preventDefault(); searchMusic(mood, query); }} className="flex gap-1.5">
              <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search, e.g. warm piano"
                className="flex-1 min-w-0 rounded-md border border-neutral-200 px-2 py-1.5 text-xs outline-none focus:border-neutral-400" />
              <button type="submit" className="px-2.5 rounded-md border border-neutral-300 text-xs font-semibold hover:bg-neutral-50">Search</button>
            </form>
            {searching && <div className="text-xs text-neutral-500">Searching licensed music…</div>}
            {musicError && <div className="text-xs text-red-700 bg-red-50 border border-red-200 rounded-md px-2 py-1.5">{musicError}</div>}
            {!searching && !musicError && tracks.length === 0 && <div className="text-xs text-neutral-500">No long instrumental tracks found. Try another mood.</div>}

            {tracks.map((track) => {
              const isPlaying = playingPreviewId === track.id;
              const isAdded = activeAudioTracks.some((t: AudioTrackItem) => t.music_id === track.id);
              return (
                <div key={track.id} className="p-3 rounded-xl border border-neutral-200 bg-white hover:bg-neutral-50 transition flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <button type="button" onClick={() => toggleMusicPreview(track)}
                      className={`p-2 rounded-lg border transition cursor-pointer ${isPlaying ? 'bg-neutral-900 text-white border-neutral-900' : 'bg-neutral-100 hover:bg-neutral-200 text-neutral-700 border-neutral-200'}`}
                      title={isPlaying ? 'Stop preview' : 'Play preview'}>
                      {isPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5 fill-current" />}
                    </button>
                    <div className="min-w-0">
                      <div className="font-semibold text-xs text-neutral-900 truncate">{track.title}</div>
                      <div className="text-[10px] text-neutral-500 font-mono mt-0.5 truncate">
                        {track.creator} • {Math.round(track.duration)}s • {track.license.toUpperCase()}{track.credit_required ? ' • credit needed' : ''}
                      </div>
                    </div>
                  </div>
                  <button type="button" onClick={() => handleAddMusicToProject(track)} disabled={addingId === track.id}
                    className="px-2.5 py-1.5 rounded-lg border border-neutral-300 bg-white hover:bg-neutral-100 text-neutral-800 text-xs font-semibold transition cursor-pointer flex items-center gap-1 disabled:opacity-50">
                    {isAdded ? <Check className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
                    <span>{addingId === track.id ? 'Adding…' : isAdded ? 'Added' : 'Use'}</span>
                  </button>
                </div>
              );
            })}
            {activeAudioTracks.filter((t: AudioTrackItem) => t.type === 'music' && t.attribution).map((t: AudioTrackItem) => (
              <div key={t.id} className="text-[10px] text-neutral-600 bg-neutral-50 border border-neutral-200 rounded-md px-2 py-1.5">
                {t.credit_required ? 'Credit to include in your post: ' : 'In use (CC0, no credit needed): '}{t.attribution}
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            <div className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">
              Sound Effects (One-Shots)
            </div>

            {STOCK_SFX.map((sfx) => {
              return (
                <div
                  key={sfx.id}
                  className="p-3 rounded-xl border border-neutral-200 bg-white hover:bg-neutral-50 transition flex items-center justify-between"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <button
                      type="button"
                      onClick={() => playSfxTone(sfx.type)}
                      className="p-2 rounded-lg bg-neutral-100 hover:bg-neutral-200 text-neutral-700 border border-neutral-200 transition cursor-pointer"
                      title="Test SFX sound"
                    >
                      <Play className="h-3.5 w-3.5 fill-current" />
                    </button>
                    <div className="min-w-0">
                      <div className="font-semibold text-xs text-neutral-900 truncate">{sfx.title}</div>
                      <div className="text-[10px] text-neutral-500 font-mono mt-0.5">
                        {sfx.category} • {sfx.duration}s
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleAddSfxToPlayhead(sfx)}
                    className="px-2.5 py-1.5 rounded-lg bg-neutral-900 hover:bg-black text-white text-xs font-semibold transition cursor-pointer flex items-center gap-1 shrink-0 ml-2"
                    title={`Insert ${sfx.title} at playhead`}
                  >
                    <Plus className="h-3 w-3" />
                    <span>Insert @ Playhead</span>
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* Active Audio Tracks on Timeline */}
        {activeAudioTracks.length > 0 && (
          <div className="pt-3 border-t border-neutral-200 space-y-2">
            <div className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">
              Timeline Audio Tracks ({activeAudioTracks.length})
            </div>

            {activeAudioTracks.map((trk) => (
              <div
                key={trk.id}
                className="p-2.5 rounded-xl border border-neutral-200 bg-neutral-50 flex items-center justify-between text-xs"
              >
                <div className="min-w-0">
                  <div className="font-semibold text-neutral-900 text-xs truncate">{trk.title}</div>
                  <div className="text-[10px] text-neutral-500 font-mono mt-0.5">
                    {trk.type.toUpperCase()} • Start: {trk.start.toFixed(1)}s • Vol: {Math.round(trk.volume * 100)}%
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => handleDeleteAudioTrack(trk.id)}
                  className="p-1.5 hover:bg-red-50 text-neutral-400 hover:text-red-600 rounded-lg transition cursor-pointer"
                  title="Remove audio track"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
