import React, { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { domainLabel, ProjectDomain } from '../../types';
import { api } from '../../services/api';

export interface OverlayStyleOption {
  id: string;
  label: string;
  detail: string;
  recommended: boolean;
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
  const [styles, setStyles] = useState<OverlayStyleOption[]>([]);
  const [selected, setSelected] = useState<string[]>(initialStyles);
  const [note, setNote] = useState(initialNote);
  const domainName = domainLabel(domain as ProjectDomain);

  useEffect(() => {
    if (!open) return;
    let stop = false;
    api.getOverlayStyles(domain || 'general').then((payload) => {
      if (stop) return;
      const rows = payload.styles || [];
      setStyles(rows);
      setSelected(choiceMade ? initialStyles : payload.recommended || []);
      setNote(initialNote);
    });
    return () => { stop = true; };
  }, [open, domain, choiceMade, initialStyles, initialNote]);

  if (!open) return null;

  const toggle = (id: string) => {
    setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
      <div className="bg-white border border-neutral-200 rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto text-neutral-900">
        <div className="flex items-start justify-between gap-3 px-5 pt-5 pb-3 border-b border-neutral-200">
          <div>
            <h2 className="text-base font-semibold">Choose overlays</h2>
            <p className="text-xs text-neutral-500 mt-1">
              Captions are ready. Pick the overlays for this {domainName} video. Recommended ones are already selected.
            </p>
          </div>
          <button type="button" onClick={onClose} className="p-1 rounded-md text-neutral-500 hover:bg-neutral-100" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="px-5 py-3 space-y-2">
          {styles.map((style) => {
            const on = selected.includes(style.id);
            return (
              <label key={style.id} className={`flex gap-3 p-3 rounded-lg border cursor-pointer ${on ? 'border-neutral-900 bg-neutral-50' : 'border-neutral-200 bg-white hover:bg-neutral-50'}`}>
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={on}
                  onChange={() => toggle(style.id)}
                />
                <span>
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold">{style.label}</span>
                    {style.recommended && (
                      <span className="text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-neutral-900 text-white">Fits {domainName}</span>
                    )}
                  </span>
                  <span className="block text-xs text-neutral-600 mt-1">{style.detail}</span>
                </span>
              </label>
            );
          })}
          {selected.includes('product_swap') && (
            <label className="block text-xs text-neutral-700">
              Product to show in hand
              <input
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Name or short description"
                className="mt-1 w-full rounded-md border border-neutral-200 px-2 py-1.5 text-sm text-neutral-900"
              />
            </label>
          )}
        </div>
        <div className="px-5 pb-5 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="px-3 py-1.5 text-xs font-semibold rounded-md border border-neutral-200 bg-white hover:bg-neutral-50">
            Cancel
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => onStart(selected, note)}
            className="px-3 py-1.5 text-xs font-semibold rounded-md bg-neutral-900 text-white hover:bg-neutral-800 disabled:opacity-50"
          >
            Start with these overlays
          </button>
        </div>
      </div>
    </div>
  );
};
