'use client';

import type { ReviewQueueBrief } from '@/hooks/useReviewQueue';

export interface BriefPanelProps {
  brief: ReviewQueueBrief | null;
  loading?: boolean;
  error?: string | null;
}

/**
 * Renders the role-structured synthesis sections from a PDB brief.
 *
 * For v0, the source briefs are manually written (schema from
 * ``docs/plans/2026-04-19-pr-intelligence-brief-addendum.md §5``). Fields
 * that are missing simply render "—" rather than breaking the layout.
 */
export function BriefPanel({ brief, loading, error }: BriefPanelProps) {
  if (loading) {
    return (
      <div
        data-testid="brief-panel-loading"
        className="rounded border border-slate-700/40 px-3 py-2 text-xs text-slate-400"
      >
        Loading brief…
      </div>
    );
  }

  if (error) {
    return (
      <div
        data-testid="brief-panel-error"
        role="alert"
        className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-200"
      >
        {error}
      </div>
    );
  }

  if (!brief) {
    return (
      <div
        data-testid="brief-panel-empty"
        className="rounded border border-slate-700/40 bg-slate-800/40 px-3 py-2 text-xs text-slate-400"
      >
        No brief generated yet. Use the CLI or wait for the PDB protocol to populate one.
      </div>
    );
  }

  const sections: Array<{ key: keyof ReviewQueueBrief; label: string }> = [
    { key: 'logic', label: 'Logic' },
    { key: 'security', label: 'Security' },
    { key: 'maintainability', label: 'Maintainability' },
    { key: 'skeptic', label: 'Skeptic' },
  ];

  return (
    <div
      data-testid="brief-panel"
      className="space-y-3 rounded border border-slate-700/40 bg-slate-900/40 px-3 py-3 text-sm"
    >
      <div className="flex flex-wrap items-center gap-3 border-b border-slate-700/40 pb-2">
        <span className="font-theme-data text-xs uppercase text-slate-400">Verdict</span>
        <span className="font-theme-data text-sm" data-testid="brief-verdict">
          {brief.verdict || '—'}
        </span>
        {brief.confidence !== null && brief.confidence !== undefined && (
          <span className="text-xs text-slate-400" data-testid="brief-confidence">
            confidence {brief.confidence}/5
          </span>
        )}
        <span className="ml-auto font-mono text-xs text-slate-500">
          head {brief.head_sha?.slice(0, 12) || '—'}
        </span>
      </div>
      {sections.map(({ key, label }) => {
        const value = brief[key];
        const text = typeof value === 'string' && value.trim() ? value : '—';
        return (
          <div key={key} data-testid={`brief-section-${key}`}>
            <div className="font-theme-data text-xs uppercase text-slate-400">{label}</div>
            <div className="whitespace-pre-wrap text-slate-200">{text}</div>
          </div>
        );
      })}
    </div>
  );
}
