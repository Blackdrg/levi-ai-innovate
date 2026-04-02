import { apiClient, apiPostStream } from "./apiClient";

export const brainService = {
  detectIntent: async (message, sessionId = null) => {
    const response = await apiClient.post("/v1/chat", { 
      message, 
      session_id: sessionId 
    });
    return response.data;
  },

  streamChat: (message, sessionId, handlers) => {
    return apiPostStream("/v1/chat/stream", { 
      message, 
      session_id: sessionId 
    }, handlers);
  }
};

