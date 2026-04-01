/**
 * brainService.js
 * Calls the /brain endpoint for intent detection.
 */
import { apiClient } from "./apiClient";

export const brainService = {
  detectIntent: async (message, sessionId = null) => {
    const response = await apiClient.post("/brain", { 
      message, 
      session_id: sessionId 
    });
    return response.data;
  },
};
