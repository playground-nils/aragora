'use client';

import Link from 'next/link';

import { useSWRFetch } from '@/hooks/useSWRFetch';

import type { BridgeEvent, BridgeRunSummary, BridgeSession } from './types';

interface BridgeRunDetailProps {
  runId: string;
}

interface BridgeRunDetailResponse {
  run: Omit<BridgeRunSummary, 'session_count' | 'agents'>;
  sessions: BridgeSession[];
}

interface BridgeEventResponse {
  events: BridgeEvent[];
  count: number;
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function humanStatus(status: string): string {
  if (status === 'waiting_human') return 'Awaiting human input';
  if (status === 'completed') return 'Completed';
  if (status === 'failed') return 'Failed';
  return 'Running';
}

function eventSummary(event: BridgeEvent): string {
  const footer = typeof event.footer === 'object' && event.footer ? event.footer : null;
  if (footer && typeof footer.summary === 'string' && footer.summary) {
    return footer.summary;
  }
  if (typeof event.reason === 'string' && event.reason) {
    return event.reason;
  }
  return event.type.replaceAll('_', ' ');
}

export function BridgeRunDetail({ runId }: BridgeRunDetailProps) {
  const run = useSWRFetch<BridgeRunDetailResponse>(`/api/v1/agent-bridge/runs/${runId}`, {
    refreshInterval: 5000,
  });
  const events = useSWRFetch<BridgeEventResponse>(`/api/v1/agent-bridge/runs/${runId}/events`, {
    refreshInterval: 5000,
  });

  if (run.error) {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
        Failed to load bridge run {runId}.
      </div>
    );
  }

  if (run.isLoading || !run.data) {
    return <div className="text-sm text-white/50">Loading bridge run…</div>;
  }

  const runData = run.data.run;
  const sessions = run.data.sessions ?? [];
  const eventItems = events.data?.events ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="mb-2 text-xs uppercase tracking-[0.25em] text-white/35">
            Agent Bridge Run
          </div>
          <h1 className="font-theme-display text-3xl text-white">{runData.run_id}</h1>
          <p className="mt-2 max-w-3xl text-sm text-white/70">{runData.task}</p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/autonomous/bridge"
            className="rounded border border-white/10 px-3 py-2 text-sm text-white/60 transition-colors hover:border-white/20 hover:text-white"
          >
            All runs
          </Link>
          <button
            onClick={() => {
              void run.mutate();
              void events.mutate();
            }}
            className="rounded border border-[var(--accent)]/30 px-3 py-2 text-sm text-[var(--accent)] transition-colors hover:border-[var(--accent)]/60"
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.3fr_0.9fr]">
        <section className="rounded-xl border border-white/10 bg-white/5 p-4">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm uppercase tracking-[0.2em] text-white/40">Run State</h2>
            <span className="rounded-full border border-white/10 px-2 py-1 text-xs text-white/70">
              {humanStatus(runData.status)}
            </span>
          </div>

          <dl className="grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-xs uppercase tracking-[0.2em] text-white/35">Base branch</dt>
              <dd className="mt-1 text-sm text-white/85">{runData.base_branch}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-[0.2em] text-white/35">Active actor</dt>
              <dd className="mt-1 text-sm text-white/85">{runData.active_actor ?? 'none'}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-[0.2em] text-white/35">Created</dt>
              <dd className="mt-1 text-sm text-white/85">{formatTimestamp(runData.created_at)}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-[0.2em] text-white/35">Updated</dt>
              <dd className="mt-1 text-sm text-white/85">{formatTimestamp(runData.updated_at)}</dd>
            </div>
          </dl>

          {runData.status === 'waiting_human' ? (
            <div className="mt-4 rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-3 text-sm text-yellow-200">
              This run is paused for a human decision before the baton can advance.
            </div>
          ) : null}

          {runData.last_summary ? (
            <div className="mt-4 rounded-lg border border-white/10 bg-black/20 p-3 text-sm text-white/70">
              {runData.last_summary}
            </div>
          ) : null}
        </section>

        <section className="rounded-xl border border-white/10 bg-white/5 p-4">
          <h2 className="mb-4 text-sm uppercase tracking-[0.2em] text-white/40">Sessions</h2>
          <div className="space-y-3">
            {sessions.map((session) => (
              <div
                key={session.name}
                className="rounded-lg border border-white/10 bg-black/20 p-3"
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium text-white">{session.name}</div>
                    <div className="text-xs text-white/45">
                      {session.harness}
                      {session.model ? ` · ${session.model}` : ''}
                    </div>
                  </div>
                  <div className="text-xs text-white/45">{session.turn_count} turns</div>
                </div>
                <div className="mt-3 space-y-1 text-xs text-white/50">
                  <div>Role: {session.role || 'unassigned'}</div>
                  <div>Branch: {session.branch ?? 'pending worktree'}</div>
                  <div>Worktree: {session.worktree_path ?? 'pending worktree'}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="rounded-xl border border-white/10 bg-white/5 p-4">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm uppercase tracking-[0.2em] text-white/40">Event Feed</h2>
          <div className="text-xs text-white/40">{eventItems.length} events</div>
        </div>

        {events.error ? (
          <div className="text-sm text-red-300">Failed to load event log.</div>
        ) : eventItems.length === 0 ? (
          <div className="text-sm text-white/50">No events recorded yet.</div>
        ) : (
          <ol className="space-y-3">
            {eventItems.map((event, index) => (
              <li
                key={`${event.timestamp}-${event.type}-${index}`}
                className="rounded-lg border border-white/10 bg-black/20 p-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-sm text-white">
                    <span className="font-medium">{event.type}</span>
                    {event.actor ? <span className="text-white/45"> · {event.actor}</span> : null}
                  </div>
                  <div className="text-xs text-white/45">{formatTimestamp(event.timestamp)}</div>
                </div>

                <div className="mt-2 text-sm text-white/65">{eventSummary(event)}</div>

                {event.footer && Array.isArray(event.footer.tests_run) && event.footer.tests_run.length > 0 ? (
                  <div className="mt-2 text-xs text-white/45">
                    Tests: {event.footer.tests_run.join(', ')}
                  </div>
                ) : null}

                {event.footer && Array.isArray(event.footer.artifacts) && event.footer.artifacts.length > 0 ? (
                  <div className="mt-1 text-xs text-white/45">
                    Artifacts: {event.footer.artifacts.join(', ')}
                  </div>
                ) : null}
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}
