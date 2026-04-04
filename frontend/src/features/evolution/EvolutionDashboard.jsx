import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Activity, Brain, Server, Shield, Sparkles, RefreshCw } from "lucide-react";
import { evolutionService } from "../../services/evolutionService";
import { apiStream } from "../../services/apiClient";
import { cn } from "../../utils/styles";

export const EvolutionDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Initial Load
    const init = async () => {
      setLoading(true);
      const stats = await evolutionService.getStatus();
      setData(stats);
      setLoading(false);
    };
    init();

    // 2. Real-time Subscription (The Brain Pulse v4.1)
    const cleanup = apiStream("/api/v8/telemetry/stream", (update) => {
      setData(prev => ({ ...prev, ...update }));
    });

    return () => cleanup();
  }, []);

  return (
    <div className="flex-1 overflow-y-auto px-6 md:px-12 py-10 relative">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-12">
          <div>
            <h1 className="text-3xl md:text-5xl font-bold font-heading text-gradient mb-2">Global Evolution</h1>
            <p className="text-xs uppercase tracking-[0.2em] text-white/40">Collective Neural Resonance Status</p>
          </div>
          <button 
            onClick={loadStats}
            className="p-3 glass rounded-2xl text-white/40 hover:text-white transition-colors"
          >
            <RefreshCw size={20} className={cn(loading && "animate-spin")} />
          </button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <StatCard 
            title="Sovereign Model" 
            value={data?.active_model || "Resonating..."} 
            icon={Brain} 
            color="text-purple-400" 
            delay={0}
          />
          <StatCard 
            title="Neural Samples" 
            value={data?.training_samples?.toLocaleString() || "Syncing..."} 
            icon={Activity} 
            color="text-blue-400" 
            delay={0.1}
          />
          <StatCard 
            title="Knowledge Base" 
            value={data?.knowledge_base_entries?.toLocaleString() || "Hydrating..."} 
            icon={Server} 
            color="text-emerald-400" 
            delay={0.2}
          />
        </div>

        {/* Status Section */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="glass p-8 md:p-12 rounded-3xl relative overflow-hidden group"
        >
          <div className="absolute top-0 right-0 p-12 opacity-5 pointer-events-none transition-transform group-hover:scale-110 duration-1000">
             <Brain size={240} />
          </div>

          <div className="relative z-10">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-3 h-3 rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/50 animate-pulse" />
              <h2 className="text-xl font-bold font-heading uppercase tracking-widest">System Integrity: Stable</h2>
            </div>

            <p className="max-w-2xl text-white/60 leading-relaxed mb-8">
              The LEVI-AI collective brain is currently undergoing real-time optimization. 
              Resonance patterns from decentralized interactions are being crystallized into the global neural model, 
              enhancing the sovereignty of all connected originator nodes.
            </p>

            <div className="flex flex-wrap gap-4">
              <div className="flex items-center gap-2 px-4 py-2 glass-pill rounded-xl text-[10px] uppercase font-bold text-white/40 border border-white/5">
                <Shield size={14} className="text-emerald-500" /> AES-256 Memory Hardened
              </div>
              <div className="flex items-center gap-2 px-4 py-2 glass-pill rounded-xl text-[10px] uppercase font-bold text-white/40 border border-white/5">
                <Sparkles size={14} className="text-purple-500" /> v13.0.0 Monolith Architecture
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

const StatCard = ({ title, value, icon: Icon, color, delay }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ delay }}
    className="glass p-6 rounded-3xl border border-white/5 hover:border-white/10 transition-all group"
  >
    <div className={cn("p-2 rounded-xl mb-4 bg-white/5 w-fit group-hover:scale-110 transition-transform", color)}>
      <Icon size={20} />
    </div>
    <div className="text-[10px] uppercase tracking-widest text-white/30 mb-1">{title}</div>
    <div className="text-xl font-bold font-heading text-white truncate">{value}</div>
  </motion.div>
);
