import { apiClient } from "./apiClient";

export const studioService = {
  getTypes: async () => {
    try {
      const response = await apiClient.get("/v1/ai_studio/types");
      return response.data.types || [];
    } catch (err) {
      console.error("Failed to sync studio types", err);
      return [];
    }
  },

  getTones: async () => {
    try {
      const response = await apiClient.get("/v1/ai_studio/tones");
      return response.data.tones || [];
    } catch (err) {
      console.error("Failed to sync studio tones", err);
      return [];
    }
  },

  generate: async (payload) => {
    try {
      const response = await apiClient.post("/v1/ai_studio/generate", payload);
      return response.data;
    } catch (err) {
      console.error("Content generation failure", err);
      throw err;
    }
  }
};
