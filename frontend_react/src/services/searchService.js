/**
 * searchService.js
 * Interface for dedicated factual search.
 */
import { apiClient } from "./apiClient";

export const searchService = {
  search: async (query, sessionId = "") => {
    const response = await apiClient.post("/search", {
      query,
      session_id: sessionId
    });
    return response.data;
  },
};
