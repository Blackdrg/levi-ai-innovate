import { apiClient } from "./apiClient";

export const evolutionService = {
  getStatus: async () => {
    try {
      const response = await apiClient.get("/learning/status");
      return response.data;
    } catch (err) {
      console.error("Failed to sync neural status", err);
      return { status: "unknown", active_model: "Disconnected" };
    }
  },

  getStats: async () => {
    try {
      const response = await apiClient.get("/learning/stats");
      return response.data;
    } catch (err) {
      console.error("Failed to sync evolution stats", err);
      return {};
    }
  }
};
