'use client';

import { useCallback, useEffect, useState } from 'react';
import type { ReviewQueuePR, SettlementAction } from '@/hooks/useReviewQueue';
import { BriefPanel } from './BriefPanel';
import {
  ciGlyph,
  formatAge,
  toneColor,
  verdictGlyph,
} from './format';
import { fetchBrief, type ReviewQueueBrief } from '@/hooks/useReviewQueue';

export interface ReviewQueueCardProps {
  pr: ReviewQueuePR;
  selected: boolean;
  expanded: boolean;
  onSelect: () => void;
  onToggleExpand: () => void;
  onSettle: (action: SettlementAction, options?: { note?: string; reason?: string }) => Promise<void>;
}

export function ReviewQueueCard({
  pr,
  selected,
  expanded,
  onSelect,
  onToggleExpand,
  onSettle,
}: ReviewQueueCardProps) {
  const ci = ciGlyph(pr.ci);
  const verdict = verdictGlyph(pr.brief_present, pr.verdict);
  const [pendingAction, setPendingAction] = useState<SettlementAction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reasonDraft, setReasonDraft] = useState('');
  const [reasonForAction, setReasonForAction] = useState<SettlementAction | null>(null);
  const [brief, setBrief] = useState<ReviewQueueBrief | null>(null);
  const [briefLoading, setBriefLoading] = useState(false);
  const [briefFetched, setBriefFetched] = useState(false);
  const [briefError, setBriefError] = useState<string | null>(null);

  const loadBrief = useCallback(async () => {
    if (briefFetched || briefLoading) return;
    setBriefLoading(true);
    setBriefError(null);
    try {
      const data = await fetchBrief(pr.number);
      setBrief(data);
      setBriefFetched(true);
    } catch (err) {
      setBriefError((err as Error).message || 'Failed to load brief');
    } finally {
      setBriefLoading(false);
    }
  }, [briefFetched, briefLoading, pr.number]);

  const handleExpand = useCallback(() => {
    onToggleExpand();
  }, [onToggleExpand]);

  useEffect(() => {
    if (expanded) {
      void loadBrief();
    }
  }, [expanded, loadBrief]);

  const runSettle = useCallback(
    async (action: SettlementAction, options?: { note?: string; reason?: string }) => {
      setError(null);
      setPendingAction(action);
      try {
        await onSettle(action, options);
      } catch (err) {
        setError((err as Error).message || 'action failed');
      } finally {
        setPendingAction(null);
      }
    },
    [onSettle],
  );

  const handleApprove = useCallback(() => {
    if (pr.brief_present && pr.verdict && pr.verdict !== 'approve_candidate') {
      const ok = typeof window !== 'undefined'
        ? window.confirm(
            `Brief verdict is ${pr.verdict}. Approve anyway?`,
          )
        : true;
      if (!ok) return;
    } else if (!pr.brief_present) {
      const ok = typeof window !== 'undefined'
        ? window.confirm('No brief on file. Approve without PDB brief?')
        : true;
      if (!ok) return;
    }
    void runSettle('approve');
  }, [pr.brief_present, pr.verdict, runSettle]);

  const handleRequestChanges = useCallback(() => {
    setReasonForAction('request-changes');
    setReasonDraft('');
  }, []);

  const handleDefer = useCallback(() => {
    void runSettle('defer', { reason: 'deferred from web UI' });
  }, [runSettle]);

  const handleOpenDiff = useCallback(() => {
    if (typeof window === 'undefined' || !pr.url) return;
    window.open(pr.url, '_blank', 'noopener,noreferrer');
  }, [pr.url]);

  const submitReason = useCallback(() => {
    const action = reasonForAction;
    if (!action) return;
    const reason = reasonDraft.trim();
    if (!reason) {
      setError('reason is required');
      return;
    }
    setReasonForAction(null);
    void runSettle(action, { reason });
  }, [reasonDraft, reasonForAction, runSettle]);

  return (
    <article
      data-testid={`review-queue-card-${pr.number}`}
      data-selected={selected ? 'true' : 'false'}
      aria-selected={selected}
      tabIndex={selected ? 0 : -1}
      role="option"
      onClick={onSelect}
      className={
        'rounded border px-3 py-2 text-sm transition-colors ' +
        (selected
          ? 'border-green-500/60 bg-slate-900/80'
          : 'border-slate-700/40 bg-slate-900/40 hover:border-slate-600')
      }
    >
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-mono text-xs text-slate-400">#{pr.number}</span>
        <span className={`font-theme-data text-base ${toneColor(verdict.tone)}`} title={verdict.label}>
          {verdict.glyph}
        </span>
        <span className={`font-mono text-sm ${toneColor(ci.tone)}`} title={ci.label}>
          {ci.glyph} {ci.label}
        </span>
        <span className="truncate text-slate-200">{pr.title}</span>
        <span className="ml-auto text-xs text-slate-400">
          by {pr.author || 'unknown'} · {formatAge(pr.age_seconds)}
        </span>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-400">
        {pr.touched_subsystems.slice(0, 6).map((sub) => (
          <span
            key={sub}
            className="rounded border border-slate-700 bg-slate-800/60 px-1.5 py-0.5 text-[10px]"
          >
            {sub}
          </span>
        ))}
        {pr.touched_subsystems.length > 6 && (
          <span className="text-slate-500">+{pr.touched_subsystems.length - 6} more</span>
        )}
        <span className="ml-auto font-mono text-slate-500">
          +{pr.additions} / -{pr.deletions}
        </span>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-2">
        <button
          type="button"
          data-testid={`review-queue-approve-${pr.number}`}
          onClick={(ev) => {
            ev.stopPropagation();
            handleApprove();
          }}
          disabled={pendingAction !== null}
          className="rounded border border-green-500/40 bg-green-500/10 px-2 py-0.5 text-xs text-green-300 hover:bg-green-500/20 disabled:opacity-40"
        >
          {pendingAction === 'approve' ? 'approving…' : 'Approve'}
        </button>
        <button
          type="button"
          data-testid={`review-queue-request-changes-${pr.number}`}
          onClick={(ev) => {
            ev.stopPropagation();
            handleRequestChanges();
          }}
          disabled={pendingAction !== null}
          className="rounded border border-red-500/40 bg-red-500/10 px-2 py-0.5 text-xs text-red-300 hover:bg-red-500/20 disabled:opacity-40"
        >
          {pendingAction === 'request-changes' ? 'requesting…' : 'Request changes'}
        </button>
        <button
          type="button"
          data-testid={`review-queue-defer-${pr.number}`}
          onClick={(ev) => {
            ev.stopPropagation();
            handleDefer();
          }}
          disabled={pendingAction !== null}
          className="rounded border border-slate-500/40 bg-slate-500/10 px-2 py-0.5 text-xs text-slate-300 hover:bg-slate-500/20 disabled:opacity-40"
        >
          {pendingAction === 'defer' ? 'deferring…' : 'Defer'}
        </button>
        <button
          type="button"
          data-testid={`review-queue-open-diff-${pr.number}`}
          onClick={(ev) => {
            ev.stopPropagation();
            handleOpenDiff();
          }}
          className="rounded border border-slate-600 px-2 py-0.5 text-xs text-slate-300 hover:bg-slate-800"
        >
          Open diff
        </button>
        <button
          type="button"
          data-testid={`review-queue-expand-${pr.number}`}
          onClick={(ev) => {
            ev.stopPropagation();
            handleExpand();
          }}
          className="ml-auto rounded border border-slate-600 px-2 py-0.5 text-xs text-slate-300 hover:bg-slate-800"
          aria-expanded={expanded}
        >
          {expanded ? 'Collapse' : 'Expand'}
        </button>
      </div>

      {error && (
        <div
          role="alert"
          data-testid={`review-queue-error-${pr.number}`}
          className="mt-2 rounded border border-red-500/40 bg-red-500/10 px-2 py-1 text-xs text-red-200"
        >
          {error}
        </div>
      )}

      {reasonForAction === 'request-changes' && (
        <div
          data-testid={`review-queue-reason-${pr.number}`}
          className="mt-2 flex flex-col gap-2 rounded border border-slate-700 bg-slate-800/40 p-2"
        >
          <label className="text-xs text-slate-300" htmlFor={`reason-${pr.number}`}>
            Reason (required). Kept bounded so the repair loop converges.
          </label>
          <textarea
            id={`reason-${pr.number}`}
            data-testid={`review-queue-reason-input-${pr.number}`}
            value={reasonDraft}
            onChange={(ev) => setReasonDraft(ev.target.value)}
            rows={2}
            className="rounded border border-slate-600 bg-slate-900 px-2 py-1 text-sm text-slate-100"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={submitReason}
              data-testid={`review-queue-reason-submit-${pr.number}`}
              className="rounded border border-red-500/40 bg-red-500/10 px-2 py-0.5 text-xs text-red-200"
            >
              Send request-changes
            </button>
            <button
              type="button"
              onClick={() => setReasonForAction(null)}
              className="rounded border border-slate-600 px-2 py-0.5 text-xs text-slate-300"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {expanded && (
        <div className="mt-3 space-y-2">
          <BriefPanel brief={brief} loading={briefLoading} error={briefError} />
          <div className="rounded border border-slate-700/40 bg-slate-900/40 px-3 py-2 text-xs text-slate-300">
            <div className="mb-1 font-theme-data uppercase text-slate-400">CI detail</div>
            <div>
              {pr.ci.total === 0
                ? 'no checks on this PR'
                : `${pr.ci.success} green · ${pr.ci.pending} pending · ${pr.ci.failure} failing (of ${pr.ci.total})`}
            </div>
          </div>
        </div>
      )}
    </article>
  );
}
