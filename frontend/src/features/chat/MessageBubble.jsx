import { motion } from "framer-motion";
import { Copy, Sparkles, Check, ShieldCheck, Waves } from "lucide-react";
import { useState } from "react";
import { cn } from "../../utils/styles";

export const MessageBubble = ({ message }) => {
  const isBot = message.role === "assistant";
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "flex w-full mb-6 relative group",
        isBot ? "justify-start" : "justify-end"
      )}
    >
      <div
        className={cn(
          "max-w-[85%] px-5 py-3 rounded-2xl text-sm leading-relaxed relative",
          isBot 
            ? "glass text-white/90 rounded-tl-none border-l-purple-500/50 border-l-2 shadow-xl shadow-purple-500/5" 
            : "bg-purple-600/20 border border-purple-500/30 text-white rounded-tr-none"
        )}
      >
        <div className="flex items-center justify-between gap-4 mb-2">
          <div className="flex items-center gap-2 opacity-50 text-[10px] uppercase tracking-widest font-heading">
            {isBot ? "Levi Intelligence" : "Originator"}
          </div>
          
          {isBot && !message.streaming && (
            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
               <button 
                 onClick={handleCopy}
                 className="hover:text-purple-400 transition-colors"
                 title="Copy resonance"
               >
                 {copied ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
               </button>
               <button className="hover:text-purple-400 transition-colors" title="Deeper Insight">
                 <Sparkles size={12} />
               </button>
            </div>
          )}
        </div>
        
        <div className="whitespace-pre-wrap markdown-content">
          {message.content}
        </div>

        {isBot && (
          <div className="flex items-center gap-3 mt-3 pt-2 border-t border-white/5 opacity-50 text-[9px] uppercase tracking-tighter font-bold">
            {message.metadata?.is_sensitive && (
              <div className="flex items-center gap-1 text-emerald-400 group-hover:animate-pulse">
                <ShieldCheck size={10} /> Sovereign Shield Active
              </div>
            )}
            {message.metadata?.was_optimized && (
              <div className="flex items-center gap-1 text-purple-400">
                <Waves size={10} /> Hive Optimized
              </div>
            )}
            {message.engine && (
              <div className="ml-auto">
                {message.engine} | {message.metadata?.latency_ms || 0}ms
              </div>
            )}
          </div>
        )}

        {message.streaming && (
          <div className="inline-flex gap-1 ml-1 translate-y-1">
            <span className="typing-dot" />
            <span className="typing-dot" />
            <span className="typing-dot" />
          </div>
        )}
      </div>
    </motion.div>
  );
};

