import { apiClient, apiPostStream } from "./apiClient";

export const brainService = {
  detectIntent: async (message, sessionId = null) => {
    const response = await apiClient.post("/chat", { 
      message, 
      session_id: sessionId 
    });
    return response.data;
  },

  streamChat: (message, sessionId, handlers) => {
    return apiPostStream("/chat/stream", { 
      message, 
      session_id: sessionId 
    }, handlers);
  }
};

