export type UserRole = 'User' | 'Provider' | 'Core';

export interface User {
  id: string;
  email: string;
  role: UserRole;
  token?: string;
}

export type TaskStatus = 'QUEUED' | 'RUNNING' | 'DONE' | 'FAILED' | 'HALTED';

export interface TaskNode {
  id: string;
  type: string;
  label: string;
  status: TaskStatus;
  metadata?: Record<string, any>;
}

export interface TaskEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface Task {
  id: string;
  input: string;
  status: TaskStatus;
  dag: {
    nodes: TaskNode[];
    edges: TaskEdge[];
  };
  latency_ms?: number;
  created_at: string;
}

export interface AgentStatus {
  id: string;
  category: 'Planner' | 'Execution' | 'Retrieval' | 'Critic' | 'Tool';
  currentTask?: string;
  latency_ms: number;
  retryCount: number;
  status: 'IDLE' | 'BUSY' | 'OFFLINE';
}

export interface TelemetryEvent {
  type: 'TASK_PROGRESS' | 'AGENT_HEARTBEAT' | 'METRICS_UPDATE' | 'HITL_GATE' | 'CIRCUIT_BREAKER';
  payload: any;
  timestamp: string;
}

export interface MemoryEntry {
  id: string;
  content: string;
  score?: number;
  metadata?: Record<string, any>;
  timestamp: string;
}
