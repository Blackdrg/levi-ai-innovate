/**
 * hook: useStream
 * SSE logic for real-time token-by-token updates.
 */
import { useChatStore } from "../store/useChatStore";

export const useStream = () => {
  const updateLastMessage = useChatStore((state) => state.updateLastMessage);
  const setStreaming = useChatStore((state) => state.setStreaming);

  const startStream = async (url, options = {}) => {
    setStreaming(true);
    
    // We use fetch + ReadableStream for better header control than EventSource
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        ...options
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6).trim();
            if (dataStr === "[DONE]") {
                setStreaming(false);
                break;
            }
            
            try {
              const data = JSON.parse(dataStr);
              
              // ── LEVI v6.8: Multi-Part SSE Handler ──
              if (data.event === "activity") {
                // "Thinking...", "Searching...", etc.
                useChatStore.getState().setActivityPulse(data.data);
              } 
              else if (data.event === "metadata") {
                // v8 Engine info: { request_id, status }
                setRequestId(data.data.request_id);
              }
              else if (data.event === "graph") {
                useChatStore.getState().setExecutionGraph(data.data);
              }
              else if (data.event === "results") {
                useChatStore.getState().setExecutionResults(data.data);
              }
              else if (data.event === "WAVE_STARTED") {
                // v8 Sub-Mission Graph Wave Started
                useChatStore.getState().setActivityPulse(`Wave Started: ${data.data.nodes.join(", ")}`);
              }
              else if (data.event === "NODE_COMPLETED") {
                // v8 Single Agent Success pulse
                console.log(`[V8] Agent ${data.data.agent} finished ${data.data.node_id}`);
              }
              else if (data.event === "MEMORY_DREAMING") {
                // v8 Distiller pulse
                useChatStore.getState().setActivityPulse(`Dreaming Phase: ${data.data.message}`);
              }

              else if (data.event === "audit") {
                // v8 High-Fidelity Audit: { score, issues, etc }
                useChatStore.getState().setMissionFidelity(data.data.score);
                useChatStore.getState().setAuditResult(data.data);
              }
              else if (data.event === "choice" || data.token) {
                // Clear the thinking pulse once the first real token arrives
                useChatStore.getState().setActivityPulse(null);
                
                const token = data.data || data.token;
                updateLastMessage(prev => ({
                    ...prev,
                    content: (prev.content || "") + token
                }));
              } 
              else if (data.event === "done" || dataStr === "[DONE]") {
                useChatStore.getState().setActivityPulse(null);
                setStreaming(false);
              }
            } catch (e) {
              console.warn("[Stream Parse Error]", e);
            }
          }
        }
      }
    } catch (err) {
      console.error("[Stream Error]", err);
      setStreaming(false);
      throw err;
    } finally {
      setStreaming(false);
    }
  };

  return { startStream };
};
