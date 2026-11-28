import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { domainLabel, ProjectDomain } from '../../types';
import { api } from '../../services/api';

interface LookOption {
  id: string;
  label: string;
  detail: string;
  primary: string;
  styles: string[];
  fits: boolean;
}

interface FinishOption {
  id: string;
  label: string;
  detail: string;
  style: string;
  kind: 'frame' | 'hit';
  fits: boolean;
}

interface OverlayChooserProps {
  open: boolean;
  domain?: string;
  initialStyles: string[];
  initialNote: string;
  choiceMade: boolean;
  busy?: boolean;
  onClose: () => void;
  onStart: (styles: string[], note: string) => void;
}

export const OverlayChooser: React.FC<OverlayChooserProps> = ({
  open,
  domain,
  initialStyles,
  initialNote,
  choiceMade,
  busy = false,
  onClose,
  onStart,
}) => {
  const [looks, setLooks] = useState<LookOption[]>([]);
  const [finishes, setFinishes] = useState<FinishOption[]>([]);
  const [lookId, setLookId] = useState('');
  const [finishId, setFinishId] = useState('');
  const domainName = domainLabel(domain as ProjectDomain);

  useEffect(() => {
    if (!open) return;
    let stop = false;
    api.getOverlayStyles(domain || 'general').then((payload) => {
      if (stop) return;
      const lookRows = payload.looks || [];
      const finishRows = payload.finishes || [];
      setLooks(lookRows);
      setFinishes(finishRows);
      const saved = choiceMade ? initialStyles : (payload.preset?.styles || []);
      const fromSaved = lookRows.find((look) => saved.includes(look.primary) && look.id !== 'documentary' && look.id !== 'interface')
        || lookRows.find((look) => saved.includes(look.primary));
      const nextLook = fromSaved?.id || payload.default_look || lookRows.find((look) => look.fits)?.id || lookRows[0]?.id || '';
      const look = lookRows.find((row) => row.id === nextLook);
      const packageStyles = new Set(look?.styles || []);
      const fromFinish = finishRows.find((finish) => saved.includes(finish.style) && !packageStyles.has(finish.style));
      setLookId(nextLook);
      setFinishId(fromFinish?.id || (!choiceMade ? payload.default_finish || '' : ''));
    });
    return () => { stop = true; };
  }, [open, domain, choiceMade, initialStyles]);

  if (!open) return null;

  const look = looks.find((row) => row.id === lookId);
  const frames = finishes.filter((row) => row.kind === 'frame' && !look?.styles.includes(row.style));
  const hits = finishes.filter((row) => row.kind === 'hit');
  const start = () => {
    const selected = [...(look?.styles || [])];
    const finish = finishes.find((row) => row.id === finishId);
    if (finish && !selected.includes(finish.style)) selected.push(finish.style);
    onStart(selected, initialNote);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
      <div className="bg-white border border-neutral-200 rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col text-neutral-900">
        <div className="flex items-start justify-between gap-3 px-5 pt-5 pb-3 border-b border-neutral-200 shrink-0">
          <div>
            <h2 className="text-base font-semibold">Choose the look</h2>
            <p className="text-xs text-neutral-500 mt-1 max-w-xl">
              One look for this {domainName} video. A finish is optional and stays on top of that look.
            </p>
          </div>
          <button type="button" onClick={onClose} className="p-1 rounded-md text-neutral-500 hover:bg-neutral-100" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-[1.3fr_0.9fr] min-h-0 overflow-y-auto">
          <fieldset className="px-5 py-4 space-y-2 border-b md:border-b-0 md:border-r border-neutral-200">
            <legend className="text-[11px] font-semibold uppercase tracking-wide text-neutral-500 mb-2">Look</legend>
            {looks.map((row) => {
              const on = row.id === lookId;
              return (
                <label key={row.id} className={`flex gap-3 p-3 rounded-lg border cursor-pointer ${on ? 'border-neutral-900 bg-neutral-50' : 'border-neutral-200 bg-white hover:bg-neutral-50'}`}>
                  <input type="radio" name="look" className="mt-1" checked={on} onChange={() => { setLookId(row.id); if (row.styles.includes(finishId)) setFinishId(''); }} />
                  <span>
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold">{row.label}</span>
                      {row.fits && (
                        <span className="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-neutral-900 text-white">Fits {domainName}</span>
                      )}
                    </span>
                    <span className="block text-xs text-neutral-600 mt-1">{row.detail}</span>
                  </span>
                </label>
              );
            })}
          </fieldset>
          <fieldset className="px-5 py-4">
            <legend className="text-[11px] font-semibold uppercase tracking-wide text-neutral-500 mb-2">Finish</legend>
            <label className={`flex gap-3 p-3 rounded-lg border cursor-pointer mb-3 ${finishId === '' ? 'border-neutral-900 bg-neutral-50' : 'border-neutral-200 bg-white hover:bg-neutral-50'}`}>
              <input type="radio" name="finish" className="mt-1" checked={finishId === ''} onChange={() => setFinishId('')} />
              <span>
                <span className="text-sm font-semibold">No finish</span>
                <span className="block text-xs text-neutral-600 mt-1">The look carries the whole video.</span>
              </span>
            </label>
            {frames.length > 0 && <div className="text-[11px] font-semibold text-neutral-500 mb-1">Frame</div>}
            <div className="space-y-2 mb-3">
              {frames.map((row) => (
                <FinishRow key={row.id} row={row} selected={finishId === row.id} onSelect={() => setFinishId(row.id)} />
              ))}
            </div>
            <div className="text-[11px] font-semibold text-neutral-500 mb-1">Hit</div>
            <div className="space-y-2">
              {hits.map((row) => (
                <FinishRow key={row.id} row={row} selected={finishId === row.id} onSelect={() => setFinishId(row.id)} />
              ))}
            </div>
          </fieldset>
        </div>
        <div className="px-5 py-3 border-t border-neutral-200 flex items-center justify-between gap-3 shrink-0">
          <p className="text-xs text-neutral-500 min-w-0 truncate">{look ? look.label : 'Choose a look'}{finishId ? ` · ${finishes.find((row) => row.id === finishId)?.label}` : ''}</p>
          <div className="flex gap-2 shrink-0">
            <button type="button" onClick={onClose} className="px-3 py-1.5 text-xs font-semibold rounded-md border border-neutral-200 bg-white hover:bg-neutral-50">
              Cancel
            </button>
            <button
              type="button"
              disabled={busy || !lookId}
              onClick={start}
              className="px-3 py-1.5 text-xs font-semibold rounded-md bg-neutral-900 text-white hover:bg-neutral-800 disabled:opacity-50"
            >
              Start with this look
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

function FinishRow({ row, selected, onSelect }: { row: FinishOption; selected: boolean; onSelect: () => void }) {
  return (
    <label className={`flex gap-3 p-2.5 rounded-lg border cursor-pointer ${selected ? 'border-neutral-900 bg-neutral-50' : 'border-neutral-200 bg-white hover:bg-neutral-50'}`}>
      <input type="radio" name="finish" className="mt-0.5" checked={selected} onChange={onSelect} />
      <span>
        <span className="text-sm font-semibold">{row.label}</span>
        <span className="block text-xs text-neutral-600 mt-0.5">{row.detail}</span>
      </span>
    </label>
  );
}
