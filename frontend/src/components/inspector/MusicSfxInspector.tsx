import React, { useState, useRef } from 'react';
import { 
  Music, Volume2, VolumeX, Play, Pause, Plus, Trash2, 
  Sparkles, Sliders, Check, Disc, Zap, Radio
} from 'lucide-react';
import { ProjectState, AudioTrackItem } from '../../types';

interface MusicSfxInspectorProps {
  project: ProjectState;
  onUpdateProject: (updated: ProjectState) => void;
  currentTime: number;
}

interface StockMusic {
  id: string;
  title: string;
  genre: string;
  duration: number;
  bpm: number;
  freq: number;
}

interface StockSfx {
  id: string;
  title: string;
  category: string;
  duration: number;
  type: 'click' | 'whoosh' | 'chime' | 'bass' | 'typewriter';
}

const STOCK_MUSIC: StockMusic[] = [
  { id: 'mus_ambient_1', title: 'Documentary Ambient', genre: 'Minimal Synth', duration: 120, bpm: 85, freq: 220 },
  { id: 'mus_lofi_1', title: 'Deep Thought Lo-Fi', genre: 'Lo-Fi Chill', duration: 110, bpm: 78, freq: 260 },
  { id: 'mus_tech_1', title: 'Data Pulse', genre: 'Tech Electronic', duration: 95, bpm: 110, freq: 330 },
  { id: 'mus_cinema_1', title: 'Clinical Precision', genre: 'Modern Cinematic', duration: 140, bpm: 90, freq: 196 },
  { id: 'mus_clean_1', title: 'Neutral Acoustic Flow', genre: 'Corporate Clean', duration: 105, bpm: 100, freq: 293 }
];

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

  const toggleMusicPreview = (track: StockMusic) => {
    const ctx = getAudioContext();
    if (!ctx) return;
    if (ctx.state === 'suspended') ctx.resume();

    if (playingPreviewId === track.id) {
      if (oscRef.current) {
        try { oscRef.current.stop(); } catch (e) {}
        oscRef.current = null;
      }
      setPlayingPreviewId(null);
      return;
    }

    if (oscRef.current) {
      try { oscRef.current.stop(); } catch (e) {}
      oscRef.current = null;
    }

    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(track.freq, now);
    gain.gain.setValueAtTime(0.15, now);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(now);
    oscRef.current = osc;
    setPlayingPreviewId(track.id);
  };

  const handleAddMusicToProject = (track: StockMusic) => {
    const newTrack: AudioTrackItem = {
      id: `music_${track.id}_${Date.now()}`,
      title: track.title,
      type: 'music',
      url: `/audio/${track.id}.mp3`,
      duration: Math.min(project.duration_seconds || 60, track.duration),
      start: 0,
      volume: musicVolume,
      duck_under_speech: autoDucking
    };

    const updated = {
      ...project,
      audio_tracks: [...(project.audio_tracks || []), newTrack]
    };
    onUpdateProject(updated);
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
              Background Music Library
            </div>

            {STOCK_MUSIC.map((track) => {
              const isPlaying = playingPreviewId === track.id;
              const isAdded = activeAudioTracks.some((t) => t.title === track.title);

              return (
                <div
                  key={track.id}
                  className="p-3 rounded-xl border border-neutral-200 bg-white hover:bg-neutral-50 transition flex items-center justify-between"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <button
                      type="button"
                      onClick={() => toggleMusicPreview(track)}
                      className={`p-2 rounded-lg border transition cursor-pointer ${
                        isPlaying
                          ? 'bg-neutral-900 text-white border-neutral-900'
                          : 'bg-neutral-100 hover:bg-neutral-200 text-neutral-700 border-neutral-200'
                      }`}
                      title={isPlaying ? 'Stop preview' : 'Play preview'}
                    >
                      {isPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5 fill-current" />}
                    </button>
                    <div className="min-w-0">
                      <div className="font-semibold text-xs text-neutral-900 truncate">{track.title}</div>
                      <div className="text-[10px] text-neutral-500 font-mono mt-0.5">
                        {track.genre} • {track.bpm} BPM
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleAddMusicToProject(track)}
                    className="px-2.5 py-1.5 rounded-lg border border-neutral-300 bg-white hover:bg-neutral-100 text-neutral-800 text-xs font-semibold transition cursor-pointer flex items-center gap-1 shrink-0 ml-2"
                  >
                    <Plus className="h-3 w-3" />
                    <span>{isAdded ? 'Add More' : 'Add'}</span>
                  </button>
                </div>
              );
            })}
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
