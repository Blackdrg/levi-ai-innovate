import { create } from "zustand";

/**
 * useChatStore
 * Central state for LEVI conversational interactions.
 */
export const useChatStore = create((set) => ({
  messages: [],
  mode: "chat", // chat | search | document
  isStreaming: false,
  currentRequestId: null,
  activityPulse: null, // Thinking | Searching | Planning...
  engineMetadata: null, // { name: "Llama-3-8B", provider: "Local", latency: "45ms" }
  memoryCount: 0,
  sovereignStatus: "Idle",

  setMode: (mode) => set({ mode }),
  setActivityPulse: (activityPulse) => set({ activityPulse }),
  setEngineMetadata: (metadata) => set({ 
    engineMetadata: metadata,
    sovereignStatus: metadata?.provider === "Local" ? "Sovereign" : "Hybrid"
  }),
  setMemoryCount: (count) => set({ memoryCount: count }),

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

  setStreaming: (isStreaming) => set({ isStreaming }),
  setRequestId: (currentRequestId) => set({ currentRequestId }),

  clearMessages: () => set({ messages: [] }),
}));
