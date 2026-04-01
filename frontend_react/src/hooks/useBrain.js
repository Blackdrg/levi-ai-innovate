/**
 * hook: useBrain
 * Orchestrates the routing decisions.
 */
import { brainService } from "../services/brainService";
import { useChatStore } from "../store/useChatStore";

export const useBrain = () => {
  const setMode = useChatStore((state) => state.setMode);

  const decideRoute = async (message) => {
    try {
      const { route, confidence, complexity } = await brainService.detectIntent(message);
      
      console.log(`[Brain] Route: ${route}, Confidence: ${confidence}, Complexity: ${complexity}`);
      
      // Update UI mode based on brain decision
      if (route === "search") setMode("search");
      else if (route === "document") setMode("document");
      else setMode("chat");
      
      return { route, confidence, complexity };
    } catch (err) {
      console.error("[Brain Error] Falling back to default chat.", err);
      setMode("chat");
      return { route: "chat", confidence: 0 };
    }
  };

  return { decideRoute };
};
