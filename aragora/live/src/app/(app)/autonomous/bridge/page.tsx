'use client';

import Link from 'next/link';
import { useEffect } from 'react';

import { BridgeRunList } from '@/components/autonomous/bridge';
import { Scanlines, CRTVignette } from '@/components/MatrixRain';
import { useRightSidebar } from '@/context/RightSidebarContext';

export default function AgentBridgeRunsPage() {
  const { setContext, clearContext } = useRightSidebar();

  useEffect(() => {
    setContext({
      title: 'Agent Bridge',
      subtitle: 'Persistent CLI-resume orchestration',
      statsContent: (
        <div className="space-y-4">
          <div className="text-xs uppercase tracking-wider text-white/40">Transport</div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-white/50">Primary path</span>
              <span className="text-[var(--accent)]">CLI resume</span>
            </div>
            <div className="flex justify-between">
              <span className="text-white/50">Persistence</span>
              <span className="text-cyan-300">Repo-local</span>
            </div>
            <div className="flex justify-between">
              <span className="text-white/50">Transport fallback</span>
              <span className="text-white/60">tmux legacy</span>
            </div>
          </div>
        </div>
      ),
      actionsContent: (
        <div className="space-y-2">
          <a
            href="/autonomous"
            className="block w-full rounded bg-white/5 px-3 py-2 text-center text-sm transition-colors hover:bg-white/10"
          >
            Autonomous Home
          </a>
        </div>
      ),
    });

    return () => clearContext();
  }, [clearContext, setContext]);

  return (
    <div className="relative min-h-screen bg-black text-white">
      <Scanlines />
      <CRTVignette />

      <div className="relative z-10 p-6">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="mb-2 text-xs uppercase tracking-[0.25em] text-white/35">
              Autonomous Bridge
            </div>
            <h1 className="font-theme-display text-3xl text-white">Agent Bridge Runs</h1>
            <p className="mt-2 max-w-3xl text-sm text-white/55">
              Observe persistent Codex, Claude, and Droid sessions without relying on tmux keystroke
              transport. This surface reads broker state from <code className="text-white/75">.aragora/agent_bridge</code>.
            </p>
          </div>

          <Link
            href="/autonomous"
            className="rounded border border-white/10 px-3 py-2 text-sm text-white/60 transition-colors hover:border-white/20 hover:text-white"
          >
            Back to Autonomous
          </Link>
        </div>

        <BridgeRunList />
      </div>
    </div>
  );
}
