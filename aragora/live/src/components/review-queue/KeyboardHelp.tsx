'use client';

import { useEffect } from 'react';

export interface KeyboardHelpProps {
  open: boolean;
  onClose: () => void;
}

const SHORTCUTS: Array<{ keys: string; description: string }> = [
  { keys: 'j / k', description: 'Navigate down / up between cards' },
  { keys: '↵ / space', description: 'Toggle expand the selected card' },
  { keys: 'a', description: 'Approve the selected PR (confirms if brief disagrees)' },
  { keys: 'r', description: 'Request changes — opens reason prompt' },
  { keys: 'd', description: 'Defer the PR for 4 hours (local state only)' },
  { keys: 'o', description: 'Open the diff on github.com in a new tab' },
  { keys: '?', description: 'Toggle this help overlay' },
  { keys: 'Esc', description: 'Close this overlay or the active card' },
];

export function KeyboardHelp({ open, onClose }: KeyboardHelpProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (ev: KeyboardEvent) => {
      if (ev.key === 'Escape') {
        ev.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="review-queue-help-title"
      data-testid="review-queue-keyboard-help"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <div
        className="max-w-md rounded border border-slate-700 bg-slate-900 p-4 text-sm text-slate-200 shadow-xl"
        onClick={(ev) => ev.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-700 pb-2">
          <h2 id="review-queue-help-title" className="font-theme-data text-base">
            Keyboard shortcuts
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-slate-600 px-2 py-0.5 text-xs text-slate-300 hover:bg-slate-800"
          >
            close
          </button>
        </div>
        <table className="mt-3 w-full">
          <tbody>
            {SHORTCUTS.map((row) => (
              <tr key={row.keys} className="border-t border-slate-800">
                <td className="py-1 pr-3 font-mono text-xs text-slate-400">
                  <kbd className="rounded border border-slate-600 px-1">{row.keys}</kbd>
                </td>
                <td className="py-1 text-slate-200">{row.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
