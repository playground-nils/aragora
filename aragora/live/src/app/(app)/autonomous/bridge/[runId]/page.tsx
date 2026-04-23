'use client';

import { useParams } from 'next/navigation';
import { useEffect } from 'react';

import { BridgeRunDetail } from '@/components/autonomous/bridge';
import { Scanlines, CRTVignette } from '@/components/MatrixRain';
import { useRightSidebar } from '@/context/RightSidebarContext';

export default function AgentBridgeRunPage() {
  const params = useParams<{ runId: string }>();
  const runId = Array.isArray(params?.runId) ? params.runId[0] : params?.runId ?? '';
  const { setContext, clearContext } = useRightSidebar();

  useEffect(() => {
    setContext({
      title: 'Bridge Run',
      subtitle: runId || 'Persistent multi-harness session',
      statsContent: (
        <div className="space-y-4">
          <div className="text-xs uppercase tracking-wider text-white/40">Focus</div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-white/50">Run ID</span>
              <span className="text-[var(--accent)]">{runId || 'unknown'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-white/50">Mode</span>
              <span className="text-cyan-300">Read-only</span>
            </div>
          </div>
        </div>
      ),
    });

    return () => clearContext();
  }, [clearContext, runId, setContext]);

  return (
    <div className="relative min-h-screen bg-black text-white">
      <Scanlines />
      <CRTVignette />

      <div className="relative z-10 p-6">
        <BridgeRunDetail runId={runId} />
      </div>
    </div>
  );
}
