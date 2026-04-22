'use client';

import Link from 'next/link';

import { useSWRFetch } from '@/hooks/useSWRFetch';

import type { BridgeRunSummary } from './types';

interface BridgeRunListProps {
  endpoint?: string;
}

interface BridgeRunListResponse {
  runs: BridgeRunSummary[];
  total: number;
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

function statusLabel(status: string): string {
  if (status === 'awaiting_human') return 'Awaiting human input';
  if (status === 'completed') return 'Completed';
  if (status === 'failed') return 'Failed';
  return 'Running';
}

function statusClasses(status: string): string {
  if (status === 'completed') return 'border-[var(--accent)]/40 text-[var(--accent)]';
  if (status === 'awaiting_human') return 'border-yellow-500/40 text-yellow-300';
  if (status === 'failed') return 'border-red-500/40 text-red-300';
  return 'border-cyan-500/40 text-cyan-300';
}

export function BridgeRunList({
  endpoint = '/api/v1/agent-bridge/runs',
}: BridgeRunListProps) {
  const { data, error, isLoading, mutate } = useSWRFetch<BridgeRunListResponse>(endpoint, {
    refreshInterval: 5000,
  });

  const runs = data?.runs ?? [];

  if (error) {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
        Failed to load bridge runs.
        <button
          onClick={() => void mutate()}
          className="ml-3 underline underline-offset-2 hover:no-underline"
        >
          Retry
        </button>
      </div>
    );
  }

  if (isLoading && runs.length === 0) {
    return <div className="text-sm text-white/50">Loading bridge runs…</div>;
  }

  if (runs.length === 0) {
    return (
      <div className="rounded-lg border border-white/10 bg-white/5 p-6 text-sm text-white/50">
        No bridge runs recorded yet.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-white/50">
          {data?.total ?? runs.length} persisted run{(data?.total ?? runs.length) === 1 ? '' : 's'}
        </div>
        <button
          onClick={() => void mutate()}
          className="text-xs text-white/50 hover:text-white"
        >
          Refresh
        </button>
      </div>

      <div className="space-y-3">
        {runs.map((run) => (
          <Link
            key={run.run_id}
            href={`/autonomous/bridge/${run.run_id}`}
            className="block rounded-xl border border-white/10 bg-white/5 p-4 transition-colors hover:border-[var(--accent)]/40 hover:bg-white/10"
          >
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-theme-display text-lg text-white">{run.run_id}</span>
                  <span className={`rounded-full border px-2 py-0.5 text-[11px] uppercase tracking-[0.2em] ${statusClasses(run.status)}`}>
                    {statusLabel(run.status)}
                  </span>
                </div>
                <p className="text-sm text-white/85">{run.task}</p>
                <div className="flex flex-wrap gap-4 text-xs text-white/45">
                  <span>Worktree agent: {run.worktree_agent_slug}</span>
                  <span>Updated: {formatTimestamp(run.updated_at)}</span>
                  <span>Next actor: {run.next_actor ?? 'none'}</span>
                  <span>Turns: {run.last_turn_index}</span>
                  <span>Sessions: {run.session_count}</span>
                </div>
              </div>

              <div className="space-y-2 text-right">
                <div className="text-xs uppercase tracking-[0.2em] text-white/35">Agents</div>
                <div className="flex flex-wrap justify-end gap-2">
                  {run.agents.map((agent) => (
                    <span
                      key={`${run.run_id}-${agent.name}`}
                      className="rounded border border-white/10 bg-black/30 px-2 py-1 text-xs text-white/70"
                    >
                      {agent.name} · {agent.harness}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {run.last_summary ? (
              <div className="mt-3 border-t border-white/10 pt-3 text-sm text-white/60">
                {run.last_summary}
              </div>
            ) : null}
          </Link>
        ))}
      </div>
    </div>
  );
}
