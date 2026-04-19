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

interface LeviState {
  // Telemetry v22.0
  pulse: any | null;
  agents: AgentStatus[];
  syscalls: SyscallLog[];
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
  
  // Actions
  setPulse: (pulse: any) => void;
  addSyscall: (sc: SyscallLog) => void;
  updateThermal: (t: Partial<LeviState['thermal']>) => void;
  setAgents: (agents: AgentStatus[]) => void;
}

export const useLeviStore = create<LeviState>((set) => ({
  pulse: null,
  agents: Array.from({ length: 16 }, (_, i) => ({
    name: `AGENT_${i+1}`,
    status: 'READY',
    latency: 0,
    model: 'SOVEREIGN_V22'
  })),
  syscalls: [],
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
    boot_time: '115ms',
    pii_scrub_rate: '100%',
    bft_finality: 'Tier-4'
  },
  activeMissions: [],

  setPulse: (pulse) => set({ pulse }),
  
  addSyscall: (sc) => set((state) => ({
    syscalls: [sc, ...state.syscalls].slice(0, 50)
  })),

  updateThermal: (t) => set((state) => ({
    thermal: { ...state.thermal, ...t }
  })),

  setAgents: (agents) => set({ agents }),
}));
