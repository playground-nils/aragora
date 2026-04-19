'use client';

import { useEffect, useState } from 'react';
import {
  useReviewQueue,
  useReviewQueueStats,
} from '@/hooks/useReviewQueue';
import {
  ReviewQueueList,
  StatsHeader,
} from '@/components/review-queue';

/**
 * PDB UI v0 — browser-based PR review queue.
 *
 * This is the minimum viable surface described in
 * ``docs/plans/2026-04-19-pr-intelligence-brief-addendum.md §8``. It lets the
 * founder clear a morning's worth of PRs faster than GitHub's native UI while
 * preserving the human settlement gate (approve / request-changes still flow
 * through `gh`, which runs as the founder's own GitHub identity). Defer is
 * local-only state. No auto-merge, no bot approvals.
 */
export default function ReviewQueuePage() {
  const { prs, total, visible, deferredCount, degraded, reason, isLoading, error, mutate } =
    useReviewQueue();
  const { stats, mutate: refetchStats } = useReviewQueueStats();
  const [celebrated, setCelebrated] = useState(false);
  const [showCelebration, setShowCelebration] = useState(false);

  useEffect(() => {
    if (isLoading) return;
    if (!error && visible === 0 && total > 0 && !celebrated) {
      setShowCelebration(true);
      setCelebrated(true);
      const timer = setTimeout(() => setShowCelebration(false), 4000);
      return () => clearTimeout(timer);
    }
    if (visible > 0) {
      setCelebrated(false);
    }
  }, [celebrated, error, isLoading, total, visible]);

  const refetch = () => {
    void mutate();
    void refetchStats();
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 text-slate-100">
      <div className="mb-4 flex items-baseline gap-3">
        <h1 className="font-theme-data text-2xl">Review queue</h1>
        <span className="text-xs text-slate-400">PDB UI v0</span>
      </div>

      <StatsHeader
        visible={visible}
        total={total}
        deferredCount={deferredCount}
        stats={stats}
        degraded={degraded}
        reason={reason}
      />

      {error && (
        <div
          role="alert"
          data-testid="review-queue-page-error"
          className="mb-3 rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200"
        >
          Failed to load queue: {(error as Error).message || 'unknown error'}
        </div>
      )}

      {isLoading ? (
        <div data-testid="review-queue-page-loading" className="py-8 text-center text-slate-400">
          loading queue…
        </div>
      ) : (
        <ReviewQueueList prs={prs} onSettled={refetch} />
      )}

      {showCelebration && (
        <div
          role="status"
          data-testid="review-queue-inbox-zero"
          className="fixed bottom-6 right-6 z-30 rounded border border-green-500/60 bg-green-500/10 px-4 py-3 text-sm text-green-200 shadow-xl"
        >
          <div className="font-theme-data text-base">inbox zero 🎉</div>
          <div className="text-xs text-green-300/80">
            Queue is clear. Streak: {stats?.streak ?? 0}.
          </div>
        </div>
      )}
    </div>
  );
}
