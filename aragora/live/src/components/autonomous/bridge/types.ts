export interface BridgeFooter {
  summary: string;
  next_actor: string | null;
  needs_human: boolean;
  done: boolean;
  artifacts: string[];
  tests_run: string[];
}

export interface BridgeAgentSummary {
  name: string;
  harness: string;
  role: string;
  model: string | null;
  turn_count: number;
  status: string;
}

export interface BridgeRunSummary {
  run_id: string;
  task: string;
  status: string;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
  next_actor: string | null;
  last_turn_index: number;
  last_summary: string;
  worktree_path: string;
  worktree_agent_slug: string;
  session_count: number;
  agents: BridgeAgentSummary[];
}

export interface BridgeSession {
  name: string;
  harness: string;
  role: string;
  model: string | null;
  session_id: string | null;
  worktree_path: string | null;
  worktree_agent_slug: string | null;
  branch: string | null;
  session_status: string;
  created_at: string | null;
  updated_at: string | null;
  turn_count: number;
}

export interface BridgeEvent {
  timestamp: string;
  type: string;
  run_id: string;
  actor?: string;
  harness?: string;
  session_id?: string | null;
  artifact_path?: string;
  next_actor?: string | null;
  parse_status?: string | null;
  reason?: string;
  footer?: BridgeFooter;
  [key: string]: unknown;
}
