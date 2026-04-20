'use client';

import type { ReviewQueueStats } from '@/hooks/useReviewQueue';
import { formatDecisionSeconds } from './format';

export interface StatsHeaderProps {
  visible: number;
  total: number;
  deferredCount: number;
  stats: ReviewQueueStats | null;
  degraded?: boolean;
  reason?: string;
}

export function StatsHeader({
  visible,
  total,
  deferredCount,
  stats,
  degraded,
  reason,
}: StatsHeaderProps) {
  const median = stats?.median_decision_seconds ?? null;
  const streak = stats?.streak ?? 0;
  const approved = stats?.approved ?? 0;

  return (
    <header
      data-testid="review-queue-stats-header"
      className="mb-4 flex flex-col gap-2 border-b border-slate-700/40 pb-3 text-sm"
    >
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
        <span className="font-theme-data text-lg">
          <span data-testid="review-queue-visible">{visible}</span>
          <span className="text-slate-400"> PRs in queue</span>
        </span>
        {deferredCount > 0 && (
          <span className="text-slate-400" data-testid="review-queue-deferred-count">
            {deferredCount} deferred
          </span>
        )}
        <span className="text-slate-400">
          median decision{' '}
          <span className="text-slate-200" data-testid="review-queue-median">
            {formatDecisionSeconds(median)}
          </span>
        </span>
        <span className="text-slate-400">
          streak{' '}
          <span className="text-green-400" data-testid="review-queue-streak">
            {streak}
          </span>
        </span>
        <span className="text-slate-400" data-testid="review-queue-approved-today">
          {approved} approved today
        </span>
        <span className="ml-auto text-xs text-slate-500">
          {total} total · press <kbd className="rounded border border-slate-600 px-1">?</kbd> for
          shortcuts
        </span>
      </div>
      {degraded && (
        <div
          role="alert"
          data-testid="review-queue-degraded"
          className="rounded border border-yellow-500/40 bg-yellow-500/10 px-3 py-2 text-xs text-yellow-200"
        >
          Queue running in degraded mode: {reason || 'gh CLI unavailable'}.
        </div>
      )}
    </header>
  );
}
