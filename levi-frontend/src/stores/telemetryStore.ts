import { create } from 'zustand';
import { TelemetryEvent, AgentStatus, TaskStatus } from '../lib/types';

interface TelemetryState {
  pulse: TelemetryEvent | null;
  agents: Record<string, AgentStatus>;
  taskStatuses: Record<string, TaskStatus>;
  circuitBreaker: 'CLOSED' | 'OPEN' | 'HALF-OPEN';
  setPulse: (event: TelemetryEvent) => void;
  updateAgent: (agentId: string, status: AgentStatus) => void;
  updateTaskStatus: (taskId: string, status: TaskStatus) => void;
  setCircuitBreaker: (status: 'CLOSED' | 'OPEN' | 'HALF-OPEN') => void;
}

export const useTelemetryStore = create<TelemetryState>((set) => ({
  pulse: null,
  agents: {},
  taskStatuses: {},
  circuitBreaker: 'CLOSED',
  setPulse: (pulse) => set({ pulse }),
  setAgents: (agentsMap: Record<string, AgentStatus>) => set({ agents: agentsMap }),
  updateAgent: (id, status) => set((state) => ({
    agents: { ...state.agents, [id]: status }
  })),
  updateTaskStatus: (id, status) => set((state) => ({
    taskStatuses: { ...state.taskStatuses, [id]: status }
  })),
  setCircuitBreaker: (status) => set({ circuitBreaker: status }),
}));
