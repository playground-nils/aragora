import React from 'react';
import { render, screen } from '@testing-library/react';

import { BridgeRunList } from '../BridgeRunList';

const mockUseSWRFetch = jest.fn();

jest.mock('next/link', () => ({
  __esModule: true,
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  ),
}));

jest.mock('@/hooks/useSWRFetch', () => ({
  useSWRFetch: (...args: unknown[]) => mockUseSWRFetch(...args),
}));

describe('BridgeRunList', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders persisted runs and detail links', () => {
    mockUseSWRFetch.mockReturnValue({
      data: {
        total: 1,
        runs: [
          {
            run_id: 'run-123',
            task: 'Review the bounded bridge slice',
            status: 'running',
            created_at: '2026-04-21T18:00:00Z',
            updated_at: '2026-04-21T18:05:00Z',
            completed_at: null,
            next_actor: 'claude-review',
            last_turn_index: 1,
            last_summary: 'Codex implemented the bounded change.',
            worktree_path: '/repo/.worktrees/agent-bridge',
            worktree_agent_slug: 'codex',
            session_count: 2,
            agents: [
              { name: 'codex-a', harness: 'codex', role: 'implementer', model: 'gpt-5.4', turn_count: 1, status: 'active' },
              { name: 'claude-review', harness: 'claude', role: 'reviewer', model: 'claude-opus-4-7', turn_count: 0, status: 'not_started' },
            ],
          },
        ],
      },
      error: null,
      isLoading: false,
      mutate: jest.fn(),
    });

    render(<BridgeRunList />);

    expect(screen.getByText('run-123')).toBeInTheDocument();
    expect(screen.getByText('Review the bounded bridge slice')).toBeInTheDocument();
    expect(screen.getByText('Codex implemented the bounded change.')).toBeInTheDocument();
    expect(screen.getByText('codex-a · codex')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /run-123/i })).toHaveAttribute(
      'href',
      '/autonomous/bridge/run-123',
    );
  });
});
