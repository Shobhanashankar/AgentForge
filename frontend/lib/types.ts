export type TaskStatus =
  | 'IDLE' | 'PLANNING' | 'RESEARCHING' | 'WRITING'
  | 'REVIEWING' | 'REVISING' | 'DONE' | 'FAILED';

export type AgentName = 'PlannerAgent' | 'ResearcherAgent' | 'WriterAgent' | 'ReviewerAgent' | 'Orchestrator';

export interface AgentLogEntry {
  agent: AgentName;
  event: string;
  message: string;
  timestamp: string;
  payload?: any;
}

export interface TaskResult {
  report: string;
  word_count: number;
  score: number;
  revision_count: number;
  approved?: boolean;
  note?: string;
  subtasks?: any[];
  research_summary?: { total_tasks: number; waves: number };
}

export interface Task {
  id: string;
  prompt: string;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
  agent_log: AgentLogEntry[];
  result: TaskResult | null;
  revision_count: number;
  error?: string;
}

export const PIPELINE_STAGES: { agent: AgentName; label: string; status: TaskStatus }[] = [
  { agent: 'PlannerAgent',    label: 'Planner',    status: 'PLANNING'    },
  { agent: 'ResearcherAgent', label: 'Researcher', status: 'RESEARCHING' },
  { agent: 'WriterAgent',     label: 'Writer',     status: 'WRITING'     },
  { agent: 'ReviewerAgent',   label: 'Reviewer',   status: 'REVIEWING'   },
];

export const STATUS_COLORS: Record<TaskStatus, string> = {
  IDLE:        'text-slate-400',
  PLANNING:    'text-blue-400',
  RESEARCHING: 'text-violet-400',
  WRITING:     'text-amber-400',
  REVIEWING:   'text-cyan-400',
  REVISING:    'text-orange-400',
  DONE:        'text-emerald-400',
  FAILED:      'text-red-400',
};
