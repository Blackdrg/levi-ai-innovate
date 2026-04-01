/**
 * memoryService.js
 * Handles retrieval and management of learned facts.
 */
import { apiClient } from "./apiClient";

export const memoryService = {
  getFacts: async () => {
    try {
      const response = await apiClient.get("/api/memory/facts");
      return response.data;
    } catch (err) {
      console.error("[MemoryService] Failed to retrieve facts:", err);
      return [];
    }
  },
  saveFact: async (fact, category = "general") => {
    const response = await apiClient.post("/api/memory/save", { fact, category });
    return response.data;
  },
  deleteFact: async (factId) => {
    const response = await apiClient.delete(`/api/memory/facts/${factId}`);
    return response.data;
  },
  clearAll: async () => {
    const response = await apiClient.delete("/api/memory/facts/clear-all");
    return response.data;
  },
};
