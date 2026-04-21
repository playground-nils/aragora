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
}

export interface BridgeRunSummary {
  run_id: string;
  task: string;
  repo_root: string;
  base_branch: string;
  status: string;
  created_at: string;
  updated_at: string;
  active_actor: string | null;
  last_summary: string;
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
  branch: string | null;
  created_at: string;
  updated_at: string;
  turn_count: number;
}

export interface BridgeEvent {
  timestamp: string;
  type: string;
  run_id: string;
  actor?: string;
  session_id?: string | null;
  artifact_path?: string;
  active_actor?: string | null;
  run_status?: string;
  footer?: BridgeFooter;
  [key: string]: unknown;
}
