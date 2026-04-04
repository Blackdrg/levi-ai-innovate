import { create } from 'zustand'

export const useMissionStore = create((set, get) => ({
  activeMission: null,
  missions: [],
  streamEvents: [],    // live SSE events for current mission
  isStreaming: false,

  setActiveMission: (mission) => set({ activeMission: mission, streamEvents: [] }),

  pushEvent: (event) =>
    set(s => ({ streamEvents: [...s.streamEvents, event] })),

  clearStream: () => set({ streamEvents: [], isStreaming: false }),

  setStreaming: (val) => set({ isStreaming: val }),
}))
