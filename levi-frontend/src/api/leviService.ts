import api from './client';

export interface PulseData {
  system_graduation_score: number;
  vram_status: {
    total_vram_gb: number;
    used_vram_gb: number;
    usage_percent: number;
  };
  active_missions: number;
  dcn_health: string;
}

export interface MissionRequest {
  message: string;
  session_id?: string;
  context?: Record<string, any>;
  priority?: number;
}

export interface MissionResponse {
  mission_id: string;
  status: string;
  mode: string;
  timestamp: string;
}

export interface MissionStatus {
  id: string;
  status: string;
  objective: string;
  payload: any;
  created_at: string;
}

export interface EvolutionMetrics {
  avg_accuracy: number;
  avg_latency: number;
  success_rate: number;
  total_missions: number;
}

export interface AuditLog {
  id: string;
  event_type: string;
  timestamp: string;
  details: string;
  verified: boolean;
}

const leviService = {
  // --- AUTH ---
  login: async (email: string, pass: string) => {
    const { data } = await api.post('/auth/login', { email, password: pass });
    return data;
  },
  signup: async (email: string, pass: string, username?: string) => {
    const { data } = await api.post('/auth/signup', { email, password: pass, username });
    return data;
  },
  getMe: async () => {
    const { data } = await api.get('/auth/me');
    return data;
  },

  // --- PULSE & TELEMETRY ---
  getPulse: async (): Promise<PulseData> => {
    const { data } = await api.get('/brain/pulse');
    return data;
  },

  getHealth: async () => {
    // Note: /readyz and /healthz are usually at root or /api
    const { data } = await api.get('/../../readyz');
    return data;
  },

  // --- ORCHESTRATOR / MISSIONS ---
  dispatchMission: async (req: MissionRequest): Promise<MissionResponse> => {
    const { data } = await api.post('/orchestrator/mission', req);
    return data;
  },

  getMissionStatus: async (id: string): Promise<MissionStatus> => {
    const { data } = await api.get(`/orchestrator/mission/${id}`);
    return data;
  },

  listMissions: async (): Promise<MissionStatus[]> => {
    const { data } = await api.get('/orchestrator');
    return data;
  },

  // --- EVOLUTION ---
  getEvolutionMetrics: async (): Promise<EvolutionMetrics> => {
    const { data } = await api.get('/evolution/metrics');
    return data;
  },

  getGraduatedPatterns: async () => {
    const { data } = await api.get('/evolution/patterns/success');
    return data;
  },

  // --- COMPLIANCE ---
  getAuditLogs: async (limit = 50): Promise<AuditLog[]> => {
    const { data } = await api.get(`/compliance/logs?limit=${limit}`);
    return data;
  },

  verifyAuditChain: async () => {
    const { data } = await api.get('/compliance/verify');
    return data;
  },

  // --- GOALS ---
  listGoals: async () => {
    const { data } = await api.get('/goals');
    return data;
  },

  createGoal: async (objective: string, priority = 1.0) => {
    const { data } = await api.post('/goals', { objective, priority });
    return data;
  },

  // --- MARKETPLACE ---
  browseMarketplace: async (category?: string, sortBy = "downloads") => {
    const { data } = await api.get(`/marketplace/browse?sortBy=${sortBy}${category ? `&category=${category}` : ''}`);
    return data;
  },

  installAgent: async (marketId: number) => {
    const { data } = await api.post(`/marketplace/install/${marketId}`);
    return data;
  },

  // --- MEMORY ---
  getMemoryTiers: async () => {
    const { data } = await api.get('/memory/tiers');
    return data;
  },

  // --- VAULT / DOCUMENTS ---
  uploadDocument: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post('/vault/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return data;
  },

  listDocuments: async () => {
    const { data } = await api.get('/vault/list');
    return data;
  },

  // --- AGENTS ---
  getSwarm: async (): Promise<any[]> => {
    const { data } = await api.get('/agents/swarm');
    return data;
  },

  // --- ANALYTICS ---
  getTelemetryPulse: async () => {
    const { data } = await api.get('/analytics/pulse');
    return data;
  }
};

export default leviService;
