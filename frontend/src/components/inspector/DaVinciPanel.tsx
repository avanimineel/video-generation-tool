import React from 'react';
import { Tv, Send, Sparkles, CheckCircle2, AlertCircle, Layers, Film } from 'lucide-react';
import { DaVinciStatus, ProjectState } from '../../types';

interface DaVinciPanelProps {
  status: DaVinciStatus;
  project: ProjectState;
  onSync: () => void;
  onExportComp: () => void;
}

export const DaVinciPanel: React.FC<DaVinciPanelProps> = ({
  status,
  project,
  onSync,
  onExportComp
}) => {
  return (
    <div className="p-4 space-y-5 text-xs text-neutral-200 select-none overflow-y-auto max-h-full">
      <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
        <div className="font-bold text-sm text-white flex items-center gap-1.5">
          <Tv className="h-4 w-4 text-lime" />
          <span>DaVinci Resolve Bridge</span>
        </div>
        <span
          className={`h-2.5 w-2.5 rounded-full ${
            status.is_connected ? 'bg-emerald-400 animate-pulse' : 'bg-neutral-500'
          }`}
        />
      </div>

      {/* Connection Info Card */}
      <div className="bg-neutral-900/80 p-3.5 rounded-xl border border-neutral-800 space-y-2.5">
        <div className="flex items-center justify-between text-[11px] font-mono">
          <span className="text-neutral-400">RESOLVE PROCESS:</span>
          <span className={status.is_running ? 'text-emerald-400 font-bold' : 'text-neutral-400'}>
            {status.is_running ? 'RUNNING' : 'NOT DETECTED'}
          </span>
        </div>

        <div className="flex items-center justify-between text-[11px] font-mono">
          <span className="text-neutral-400">SCRIPT API:</span>
          <span className={status.script_api_available ? 'text-emerald-400 font-bold' : 'text-neutral-400'}>
            {status.script_api_available ? 'INSTALLED & READY' : 'OFFLINE'}
          </span>
        </div>

        {status.is_connected && (
          <>
            <div className="flex items-center justify-between text-[11px] font-mono">
              <span className="text-neutral-400">ACTIVE PROJECT:</span>
              <span className="text-white font-bold truncate max-w-[140px]">{status.project_name || 'None'}</span>
            </div>
            <div className="flex items-center justify-between text-[11px] font-mono">
              <span className="text-neutral-400">TIMELINE:</span>
              <span className="text-lime font-bold truncate max-w-[140px]">{status.timeline_name || 'None'}</span>
            </div>
          </>
        )}
      </div>

      {/* Target Track Mapping Structure */}
      <div className="bg-neutral-900/60 p-3 rounded-xl border border-neutral-800 space-y-2">
        <div className="font-bold text-xs text-white flex items-center gap-1.5">
          <Layers className="h-3.5 w-3.5 text-lime" />
          Target Timeline Tracks
        </div>
        <div className="space-y-1 font-mono text-[10px] text-neutral-400">
          <div className="p-1.5 rounded bg-neutral-800/80 text-purple-300">V5 — Generated Motion Graphics</div>
          <div className="p-1.5 rounded bg-neutral-800/60 text-purple-200">V4 — Additional Graphics</div>
          <div className="p-1.5 rounded bg-neutral-800/80 text-lime">V3 — Captions / Fusion Captions</div>
          <div className="p-1.5 rounded bg-neutral-800/60 text-blue-200">V2 — B-roll Video</div>
          <div className="p-1.5 rounded bg-neutral-800/80 text-blue-300">V1 — Main Source Video</div>
          <div className="p-1.5 rounded bg-neutral-800/60 text-emerald-300">A1 — Main Audio</div>
        </div>
      </div>

      {/* Sync & Export Buttons */}
      <div className="space-y-2 pt-2">
        <button
          onClick={onSync}
          className="w-full py-2.5 rounded-xl bg-lime hover:bg-lime-400 text-black font-black text-xs flex items-center justify-center gap-2 shadow-lg shadow-lime/10 transition"
        >
          <Send className="h-4 w-4 stroke-[2.5]" />
          <span>Sync Timeline to DaVinci Resolve</span>
        </button>

        <button
          onClick={onExportComp}
          className="w-full py-2 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-neutral-200 font-bold text-xs flex items-center justify-center gap-1.5 border border-neutral-700 transition"
        >
          <Sparkles className="h-3.5 w-3.5 text-purple-400" />
          <span>Export Fusion Comp (.comp)</span>
        </button>
      </div>
    </div>
  );
};
