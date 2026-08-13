export interface User {
  id: string;
  email: string;
  name?: string;
}

export interface WorkflowEvent {
  id: string;
  timestamp: string;
  agent_name: string | null;
  action: string;
  tool_name: string | null;
  status: string;
  duration_ms: number | null;
  result_summary: string | null;
  error: string | null;
}

export interface Workflow {
  id: string;
  thread_id: string;
  task: string;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed';
  current_agent: string | null;
  step_count: number;
  max_steps: number;
  require_approval: boolean;
  started_at: string;
  completed_at: string | null;
  final_response: string | null;
  error_message: string | null;
  events?: WorkflowEvent[];
}

export interface Approval {
  id: string;
  workflow_run_id: string;
  thread_id: string;
  requesting_agent: string;
  action_description: string;
  reason: string;
  risk_level: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  decided_at: string | null;
  decision_note: string | null;
}

export interface Memory {
  id: string;
  content: string;
  memory_type: 'preference' | 'outcome' | 'fact';
  created_at: string;
  updated_at: string;
}

export interface AgentStats {
  agent_name: string;
  description: string;
  tools: string[];
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  success_rate: number;
  avg_duration_ms: number | null;
}

export interface Metrics {
  total: number;
  completed: number;
  failed: number;
  running: number;
  paused: number;
  pending_approvals: number;
  success_rate: number;
  avg_duration_seconds: number;
}
