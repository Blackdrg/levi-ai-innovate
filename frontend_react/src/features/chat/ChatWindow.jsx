import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageBubble } from "./MessageBubble";
import { useChatStore } from "../../store/useChatStore";

export const ChatWindow = () => {
  const messages = useChatStore((state) => state.messages);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 md:px-12 py-8 scroll-smooth"
    >
      <div className="max-w-4xl mx-auto flex flex-col min-h-full">
        {messages.length === 0 ? (
          <WelcomeHero />
        ) : (
          <div className="flex-1 space-y-4">
            <AnimatePresence>
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
};

const WelcomeHero = () => (
  <motion.div 
    initial={{ opacity: 0, scale: 0.9 }}
    animate={{ opacity: 1, scale: 1 }}
    className="flex-1 flex flex-col items-center justify-center text-center py-20"
  >
    <div className="w-20 h-20 bg-gradient-sovereign rounded-3xl mb-8 flex items-center justify-center glow-hover rotate-3">
        <span className="text-4xl font-bold">L</span>
    </div>
    <h1 className="text-4xl md:text-6xl font-bold font-heading mb-4 text-gradient">
        Sovereign Intelligence
    </h1>
    <p className="text-white/40 max-w-md text-sm md:text-base leading-relaxed uppercase tracking-widest px-4">
        The definitive mind for reasoning, memory, & cosmic orchestration.
    </p>
    
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-12 w-full max-w-2xl px-4">
      <div className="glass p-4 rounded-2xl text-xs text-white/50 border border-white/5">
        "Summarize the latest trends in AI"
      </div>
      <div className="glass p-4 rounded-2xl text-xs text-white/50 border border-white/5">
        "Analyze this technical PDF"
      </div>
      <div className="glass p-4 rounded-2xl text-xs text-white/50 border border-white/5">
        "Speak in a philosophical mood"
      </div>
    </div>
  </motion.div>
);
