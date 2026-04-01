import { useState, useRef, useEffect } from "react";
import { Send, Globe, FileText, Zap } from "lucide-react";
import { cn } from "../../utils/styles";
import { useChatStore } from "../../store/useChatStore";

export const ChatInput = ({ onSend, disabled }) => {
  const [value, setValue] = useState("");
  const activityPulse = useChatStore((state) => state.activityPulse);
  const mode = useChatStore((state) => state.mode);
  const inputRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (value.trim() && !disabled) {
      onSend(value.trim());
      setValue("");
    }
  };

  useEffect(() => {
    if (!disabled) inputRef.current?.focus();
  }, [disabled]);

  const isThinking = !!activityPulse;

  return (
    <form 
      onSubmit={handleSubmit}
      className={cn(
        "relative transition-all duration-300",
        disabled ? "opacity-50" : "opacity-100"
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <ModeIndicator mode={mode} />
        {isThinking && (
          <motion.div 
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-[10px] text-purple-400/80 font-heading uppercase tracking-widest flex items-center gap-2"
          >
            <div className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(168,85,247,0.8)]" />
            {activityPulse}
          </motion.div>
        )}
      </div>
      
      <div className="relative group">
        <textarea
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          placeholder="Manifest your query..."
          className="w-full bg-[#111111]/80 border border-white/10 rounded-2xl px-6 py-4 pr-16 
                     focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20
                     placeholder:text-white/20 text-sm resize-none h-14 md:h-20 transition-all shadow-xl"
        />
        
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className={cn(
            "absolute right-3 bottom-3 p-2 rounded-xl transition-all glow-hover text-white",
            isThinking ? "bg-purple-600/50 scale-105" : "bg-gradient-sovereign hover:scale-105 active:scale-95"
          )}
        >
          <Send size={18} className={cn("relative z-10", isThinking && "animate-spin-slow")} />
          {isThinking && (
               <div className="absolute inset-0 bg-white/10 resonance-pulse" />
          )}
        </button>
      </div>

      <div className="mt-3 text-[10px] text-white/20 text-center uppercase tracking-widest flex items-center justify-center gap-2">
        <Zap size={10} /> Powered by Levi Sovereign Orchestration
      </div>
    </form>
  );
};

const ModeIndicator = ({ mode }) => {
  const iconMap = {
    chat: { icon: Zap, label: "Core Intelligence", color: "text-purple-400" },
    search: { icon: Globe, label: "Cosmic Search", color: "text-blue-400" },
    document: { icon: FileText, label: "Memory Archive", color: "text-emerald-400" }
  };

  const { icon: Icon, label, color } = iconMap[mode] || iconMap.chat;

  return (
    <div className={cn("glass-pill flex items-center gap-2 px-3 py-1 rounded-lg text-[10px] uppercase font-heading tracking-widest", color)}>
      <Icon size={12} /> {label}
    </div>
  );
};
