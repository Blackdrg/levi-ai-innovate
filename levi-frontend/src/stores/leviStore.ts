import { create } from 'zustand';

interface AgentStatus {
  name: string;
  status: 'READY' | 'BUSY' | 'OFFLINE';
  latency: number;
  model: string;
}

interface SyscallLog {
  id: number;
  name: string;
  timestamp: number;
  args: number[];
}

interface HealLog {
  timestamp: string;
  action: string;
  target: string;
  result: string;
  fidelity: number;
}

interface LeviState {
  // Telemetry v22.0
  pulse: any | null;
  agents: AgentStatus[];
  syscalls: SyscallLog[];
  healLogs: HealLog[];
  thermal: {
    cpu: number;
    vram: number;
    gpu_util: number;
    gpu_temp: number;
    status: string;
  };
  ksm: {
    savings_pct: number;
    status: string;
  };
  sovereignty: {
    boot_time: string;
    pii_scrub_rate: string;
    bft_finality: string;
  };
  
  // Mission Tracking
  activeMissions: string[];
  wsConnected: boolean;
  
  // Actions
  setWsConnected: (status: boolean) => void;
  setPulse: (pulse: any) => void;
  addSyscall: (sc: SyscallLog) => void;
  addHealLog: (log: HealLog) => void;
  updateThermal: (t: Partial<LeviState['thermal']>) => void;
  setAgents: (agents: AgentStatus[]) => void;
}

export const useLeviStore = create<LeviState>((set) => ({
  pulse: null,
  agents: [
    { name: 'Sovereign', status: 'READY', latency: 3.4, model: 'Coordinator' },
    { name: 'Artisan',   status: 'READY', latency: 320, model: 'Worker' },
    { name: 'Analyst',   status: 'READY', latency: 450, model: 'Researcher' },
    { name: 'Critic',    status: 'READY', latency: 280, model: 'Forensic' },
    { name: 'Scout',     status: 'READY', latency: 150, model: 'Search' }
  ],
  syscalls: [],
  healLogs: [],
  thermal: {
    cpu: 45,
    vram: 12.4,
    gpu_util: 32,
    gpu_temp: 48,
    status: 'STABLE'
  },
  ksm: {
    savings_pct: 35.0,
    status: 'ACTIVE'
  },
  sovereignty: {
    boot_time: '...',
    pii_scrub_rate: '...',
    bft_finality: '...'
  },
  activeMissions: [],
  wsConnected: false,

  setWsConnected: (status) => set({ wsConnected: status }),
  setPulse: (pulse) => set({ pulse }),
  
  addSyscall: (sc) => set((state) => ({
    syscalls: [sc, ...state.syscalls].slice(0, 50)
  })),

  addHealLog: (log) => set((state) => ({
    healLogs: [log, ...state.healLogs].slice(0, 20)
  })),

  updateThermal: (t) => set((state) => ({
    thermal: { ...state.thermal, ...t }
  })),

  setAgents: (agents) => set({ agents }),
}));
