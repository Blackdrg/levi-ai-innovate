import { create } from "zustand";

/**
 * useChatStore
 * Central state for LEVI conversational interactions.
 */
export const useChatStore = create((set) => ({
  messages: [],
  mode: "chat", // chat | search | document
  isStreaming: false,
  isDeepResearch: false,
  currentRequestId: null,
  activityPulse: null, // Thinking | Searching | Planning...
  activeAgent: null, // research_agent | search_agent | etc.
  sovereignShield: false, // PII Guard Active
  engineMetadata: null, // { name: "Llama-3-8B", provider: "Local", latency: "45ms" }
  memoryCount: 0,
  sovereignStatus: "Idle",
  executionGraph: null, // DAG from v8 planner
  executionResults: [], // ToolResults from v8 executor
  missionFidelity: 0.0, // 0.0 - 1.0 from audit
  auditResult: null, // { total_score, issues, fix, etc. }

  setMode: (mode) => set({ mode }),
  setDeepResearch: (isDeep) => set({ isDeepResearch: isDeep }),
  setActivityPulse: (activityPulse) => set({ activityPulse }),
  setActiveAgent: (agent) => set({ activeAgent: agent }),
  setSovereignShield: (active) => set({ sovereignShield: active }),
  setEngineMetadata: (metadata) => set({ 
    engineMetadata: metadata,
    sovereignStatus: metadata?.provider === "Local" ? "Sovereign" : "Hybrid-v8"
  }),
  setMemoryCount: (count) => set({ memoryCount: count }),
  setExecutionGraph: (graph) => set({ executionGraph: graph }),
  setExecutionResults: (results) => set({ executionResults: results }),
  setMissionFidelity: (score) => set({ missionFidelity: score }),
  setAuditResult: (audit) => set({ auditResult: audit }),

  addMessage: (msg) =>
    set((state) => ({ 
      messages: [...state.messages, { ...msg, id: Date.now(), engine: null }] 
    })),

  updateLastMessage: (updater) =>
    set((state) => {
      const newMessages = [...state.messages];
      if (newMessages.length > 0) {
        const index = newMessages.length - 1;
        const last = newMessages[index];
        newMessages[index] = typeof updater === 'function' ? updater(last) : { ...last, ...updater };
      }
      return { messages: newMessages };
    }),

  setStreaming: (streaming) => {
    if (streaming) {
        set({ isStreaming: true, missionFidelity: 0.0, auditResult: null });
    } else {
        set({ isStreaming: false });
    }
  },
  setRequestId: (currentRequestId) => set({ currentRequestId }),

  clearMessages: () => set({ messages: [], executionGraph: null, executionResults: [], missionFidelity: 0.0 }),
}));
