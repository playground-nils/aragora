import React from 'react';
import { render, screen, within } from '@testing-library/react';

import { BridgeRunDetail } from '../BridgeRunDetail';

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

describe('BridgeRunDetail', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    mockUseSWRFetch.mockImplementation((endpoint: string) => {
      if (endpoint === '/api/v1/agent-bridge/runs/run-123') {
        return {
          data: {
            run: {
              run_id: 'run-123',
              task: 'Review the bounded bridge slice',
              status: 'awaiting_human',
              created_at: '2026-04-21T18:00:00Z',
              updated_at: '2026-04-21T18:05:00Z',
              completed_at: null,
              next_actor: 'human',
              last_turn_index: 2,
              last_summary: 'Reviewer requested a human choice.',
              worktree_path: '/repo/.worktrees/agent-bridge',
              worktree_agent_slug: 'codex',
            },
            sessions: [
              {
                name: 'codex-a',
                harness: 'codex',
                role: 'implementer',
                model: 'gpt-5.4',
                session_id: 'thread-1',
                worktree_agent_slug: 'codex',
                worktree_path: '/repo/.worktrees/agent-bridge/codex-a',
                branch: 'codex/bridge-a',
                session_status: 'active',
                created_at: '2026-04-21T18:00:00Z',
                updated_at: '2026-04-21T18:04:00Z',
                turn_count: 2,
              },
            ],
          },
          error: null,
          isLoading: false,
          mutate: jest.fn(),
        };
      }

      if (endpoint === '/api/v1/agent-bridge/runs/run-123/events') {
        return {
          data: {
            count: 2,
            events: [
              {
                timestamp: '2026-04-21T18:01:00Z',
                type: 'run_started',
                run_id: 'run-123',
                actor: 'codex-a',
              },
              {
                timestamp: '2026-04-21T18:03:00Z',
                type: 'footer_ok',
                run_id: 'run-123',
                actor: 'claude-review',
                footer: {
                  summary: 'Reviewer requested a human choice.',
                  next_actor: null,
                  needs_human: true,
                  done: false,
                  artifacts: ['turns/0002-claude-review.json'],
                  tests_run: ['pytest tests/swarm/test_agent_bridge.py -q'],
                },
              },
            ],
          },
          error: null,
          isLoading: false,
          mutate: jest.fn(),
        };
      }

      return {
        data: null,
        error: null,
        isLoading: false,
        mutate: jest.fn(),
      };
    });
  });

  it('renders run detail, pending-human state, and ordered events', () => {
    render(<BridgeRunDetail runId="run-123" />);

    expect(screen.getByText('run-123')).toBeInTheDocument();
    expect(screen.getByText('Awaiting human input')).toBeInTheDocument();
    expect(screen.getByText('This run is paused for a human decision before the baton can advance.')).toBeInTheDocument();
    expect(screen.getByText('codex-a')).toBeInTheDocument();
    expect(screen.getByText('Branch: codex/bridge-a')).toBeInTheDocument();
    expect(screen.getByText('Worktree agent: codex')).toBeInTheDocument();
    expect(screen.getAllByText('Reviewer requested a human choice.')).toHaveLength(2);

    const items = screen.getAllByRole('listitem');
    expect(within(items[0]).getByText('run_started')).toBeInTheDocument();
    expect(within(items[1]).getByText('footer_ok')).toBeInTheDocument();
    expect(within(items[1]).getByText(/Tests: pytest tests\/swarm\/test_agent_bridge.py -q/)).toBeInTheDocument();
  });
});
