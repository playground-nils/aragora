'use client';

import { useEffect, useState } from 'react';
import { Scanlines, CRTVignette } from '@/components/MatrixRain';

interface SwarmStatus {
  status: string;
  total_ticks: number;
  unique_issues_attempted: number;
  unique_issues_succeeded: number;
  success_rate: number;
  terminal_class_distribution: Record<string, number>;
  outcome_distribution: Record<string, number>;
  failure_reason_distribution?: Record<string, number>;
  recent_blockers?: Array<{
    issue_number: number | null;
    terminal_class: string;
    failure_reason: string | null;
    blocker_kind: string | null;
    issue_title: string | null;
  }>;
  latest_tick: {
    timestamp: string;
    issue_number: number | null;
    terminal_class: string;
    elapsed_seconds: number | null;
  };
}

function StatusBadge({ alive }: { alive: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-mono ${
      alive ? 'bg-green-900/50 text-green-400 border border-green-700' : 'bg-red-900/50 text-red-400 border border-red-700'
    }`}>
      <span className={`w-2 h-2 rounded-full ${alive ? 'bg-green-400 animate-pulse' : 'bg-red-500'}`} />
      {alive ? 'LIVE' : 'OFFLINE'}
    </span>
  );
}

function MetricCard({ label, value, subtext }: { label: string; value: string | number; subtext?: string }) {
  return (
    <div className="border border-green-800/50 bg-black/40 rounded p-4">
      <div className="text-green-600 text-xs font-mono uppercase tracking-wider">{label}</div>
      <div className="text-green-400 text-2xl font-mono mt-1">{value}</div>
      {subtext && <div className="text-green-700 text-xs font-mono mt-1">{subtext}</div>}
    </div>
  );
}

function TerminalClassBar({ name, count, total }: { name: string; count: number; total: number }) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  const isSuccess = name.startsWith('success') || name.startsWith('deliverable');
  return (
    <div className="flex items-center gap-2 text-xs font-mono">
      <div className="w-48 truncate text-green-500">{name}</div>
      <div className="flex-1 bg-green-900/20 rounded-full h-3 overflow-hidden">
        <div
          className={`h-full rounded-full ${isSuccess ? 'bg-green-600' : 'bg-red-800'}`}
          style={{ width: `${Math.max(pct, 2)}%` }}
        />
      </div>
      <div className="w-12 text-right text-green-600">{count}</div>
      <div className="w-12 text-right text-green-700">{pct.toFixed(0)}%</div>
    </div>
  );
}

function BlockerRow({ blocker }: { blocker: SwarmStatus['recent_blockers'] extends Array<infer T> ? T : never }) {
  return (
    <div className="border-b border-green-900/30 py-2 text-xs font-mono">
      <div className="flex items-center gap-2">
        <span className="text-red-500">✗</span>
        <span className="text-green-500">#{blocker.issue_number}</span>
        <span className="text-green-700">{blocker.terminal_class}</span>
      </div>
      {blocker.failure_reason && (
        <div className="text-green-600 ml-5 mt-0.5 truncate">{blocker.failure_reason}</div>
      )}
      {blocker.issue_title && (
        <div className="text-green-800 ml-5 mt-0.5 truncate">{blocker.issue_title}</div>
      )}
    </div>
  );
}

export default function SwarmStatusPage() {
  const [data, setData] = useState<SwarmStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string>('');

  useEffect(() => {
    async function fetchStatus() {
      try {
        const res = await fetch('/api/v1/swarm/status');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setData(json);
        setError(null);
        setLastUpdate(new Date().toLocaleTimeString());
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to fetch');
      }
    }
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const totalTicks = data?.total_ticks ?? 0;
  const successRate = data?.success_rate ?? 0;
  const terminalClasses = data?.terminal_class_distribution ?? {};
  const blockers = data?.recent_blockers ?? [];
  const isAlive = data?.status === 'active' && totalTicks > 0;

  return (
    <div className="min-h-screen bg-black text-green-400 relative">
      <Scanlines />
      <CRTVignette />
      <div className="relative z-10 max-w-6xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-mono text-green-400 tracking-tight">
              SWARM STATUS
            </h1>
            <p className="text-green-700 text-xs font-mono mt-1">
              Autonomous execution operator surface
            </p>
          </div>
          <div className="flex items-center gap-4">
            <StatusBadge alive={isAlive} />
            {lastUpdate && (
              <span className="text-green-800 text-xs font-mono">
                Updated {lastUpdate}
              </span>
            )}
          </div>
        </div>

        {error && (
          <div className="bg-red-900/20 border border-red-800 rounded p-4 mb-6 text-red-400 text-sm font-mono">
            {error}
          </div>
        )}

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <MetricCard
            label="Success Rate"
            value={`${(successRate * 100).toFixed(1)}%`}
            subtext={`${data?.unique_issues_succeeded ?? 0}/${data?.unique_issues_attempted ?? 0} issues`}
          />
          <MetricCard
            label="Total Ticks"
            value={totalTicks}
            subtext="dispatch cycles"
          />
          <MetricCard
            label="Issues Attempted"
            value={data?.unique_issues_attempted ?? 0}
            subtext="unique GitHub issues"
          />
          <MetricCard
            label="Latest Tick"
            value={data?.latest_tick?.elapsed_seconds
              ? `${Math.round(data.latest_tick.elapsed_seconds)}s`
              : '—'}
            subtext={data?.latest_tick?.terminal_class || '—'}
          />
        </div>

        {/* Terminal Class Distribution */}
        <div className="border border-green-800/50 bg-black/40 rounded p-6 mb-8">
          <h2 className="text-green-500 text-sm font-mono uppercase tracking-wider mb-4">
            Terminal Class Distribution
          </h2>
          <div className="space-y-2">
            {Object.entries(terminalClasses)
              .sort(([, a], [, b]) => b - a)
              .map(([name, count]) => (
                <TerminalClassBar key={name} name={name} count={count} total={totalTicks} />
              ))}
            {Object.keys(terminalClasses).length === 0 && (
              <div className="text-green-800 text-xs font-mono">No data yet</div>
            )}
          </div>
        </div>

        {/* Recent Blockers */}
        {blockers.length > 0 && (
          <div className="border border-green-800/50 bg-black/40 rounded p-6 mb-8">
            <h2 className="text-green-500 text-sm font-mono uppercase tracking-wider mb-4">
              Recent Blockers ({blockers.length})
            </h2>
            <div className="space-y-1">
              {blockers.map((b, i) => (
                <BlockerRow key={i} blocker={b} />
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="text-center text-green-900 text-xs font-mono mt-12">
          Aragora Swarm Operator Surface · Refreshes every 30s
        </div>
      </div>
    </div>
  );
}
