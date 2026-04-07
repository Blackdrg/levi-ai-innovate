import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Activity, Brain, Server, Shield, Sparkles, RefreshCw, Wind } from "lucide-react";
import pako from "pako";
import { evolutionService } from "../../services/evolutionService";
import { API_BASE } from "../../lib/auth";
import { cn } from "../../utils/styles";

export const EvolutionDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadStats = async () => {
    setLoading(true);
    try {
      const stats = await evolutionService.getStatus();
      setData(stats);
    } catch (err) {
      console.error("Evolution status sync failed", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();

    // 2. Real-time Subscription (The Brain Pulse v13.1)
    // We use EventSource with query-param token for hardened auth compatibility
    const token = localStorage.getItem("token");
    const url = `${API_BASE}/api/v1/telemetry/stream?profile=mobile${token ? `&token=${token}` : ""}`;
    
    const es = new EventSource(url, { withCredentials: true });

    es.onmessage = (e) => {
      try {
        let rawData = e.data;
        let parsedData;

        // Adaptive Pulse Decoder (matches MissionDashboard)
        if (typeof rawData === "string" && !rawData.startsWith("{")) {
            const binary = atob(rawData);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
            const decompressed = pako.inflate(bytes, { to: "string" });
            parsedData = JSON.parse(decompressed);
        } else {
            parsedData = JSON.parse(rawData);
        }

        if (parsedData) {
          setData(prev => ({ ...prev, ...parsedData.data }));
        }
      } catch (err) {
        console.warn("[Evolution] Pulse decode failed", err);
      }
    };

    return () => es.close();
  }, []);

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar bg-[#020202]">
      <div className="max-w-6xl mx-auto px-8 py-12 space-y-12">
        {/* Header Section */}
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-8 border-b border-white/5 pb-8">
          <div className="space-y-2">
             <div className="flex items-center gap-2">
                <span className="w-10 h-[1px] bg-blue-500" />
                <span className="text-[10px] uppercase tracking-[0.3em] text-blue-500 font-bold">Inference & Flux Monitoring</span>
             </div>
             <h1 className="text-5xl font-heading font-black tracking-tighter text-white uppercase italic leading-none">
                Evolution<span className="text-blue-500">.</span>Hub
             </h1>
             <p className="text-[11px] text-white/30 font-medium max-w-md">Real-time observability of the collective neural resonance and drift.</p>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="px-4 py-2 glass rounded-xl border border-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.1)]">
               <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse shadow-[0_0_8px_#3b82f6]" />
                  <span className="text-[10px] font-mono text-blue-300 uppercase tracking-widest font-black">Pulse: Active</span>
               </div>
            </div>
            <button 
              onClick={loadStats}
              className="p-3.5 glass rounded-2xl text-white/30 hover:text-white hover:border-blue-500/30 transition-all"
            >
              <RefreshCw size={20} className={cn(loading && "animate-spin text-blue-500")} />
            </button>
          </div>
        </header>

        {/* Reactor Modules (Stats) */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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

        {/* Global Integrity Display */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="glass p-12 rounded-[3rem] relative overflow-hidden group border border-white/5 shadow-2xl"
        >
          {/* Animated Brain Background */}
          <div className="absolute top-0 right-0 p-16 opacity-[0.03] pointer-events-none transition-transform group-hover:scale-110 duration-1000 rotate-12">
             <Brain size={280} />
          </div>
          <div className="absolute -left-20 -bottom-20 w-80 h-80 bg-blue-500/5 blur-[120px] rounded-full pointer-events-none" />

          <div className="relative z-10">
            <div className="flex items-center gap-4 mb-8">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.1)]">
                 <Shield className="text-emerald-500" size={24} />
              </div>
              <div className="space-y-0.5">
                 <h2 className="text-xl font-black font-heading uppercase tracking-[0.1em] text-white">System Integrity: Stable</h2>
                 <p className="text-[10px] uppercase tracking-widest text-white/30 font-bold">Resonance Level Alpha-9 Balanced</p>
              </div>
            </div>

            <p className="max-w-3xl text-sm md:text-base text-white/60 leading-relaxed mb-10 selection:bg-blue-500/30 font-medium">
              The LEVI-AI collective brain is currently undergoing real-time topological wave optimization. 
              Resonance patterns from decentralized interactions are being crystallized into the global neural model, 
              enhancing the sovereignty of all connected originator nodes via local-mesh synchronization.
            </p>

            <div className="flex flex-wrap gap-4 pt-10 border-t border-white/5">
              <div className="flex items-center gap-3 px-5 py-3 glass rounded-2xl text-[10px] uppercase font-black text-white/40 border border-white/5 hover:border-emerald-500/20 transition-all">
                <Shield size={16} className="text-emerald-500" /> AES-256 Memory Hardened
              </div>
              <div className="flex items-center gap-3 px-5 py-3 glass rounded-2xl text-[10px] uppercase font-black text-white/40 border border-white/5 hover:border-purple-500/20 transition-all">
                <Sparkles size={16} className="text-purple-500" /> v14.0.0 Sovereign Core
              </div>
              <div className="flex items-center gap-3 px-5 py-3 glass rounded-2xl text-[10px] uppercase font-black text-white/40 border border-white/5 hover:border-blue-500/20 transition-all">
                <Activity size={16} className="text-blue-500" /> DCN Pulse v13.1
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
    className="glass p-8 rounded-[2rem] border border-white/5 hover:scale-[1.02] hover:border-white/20 transition-all group relative overflow-hidden shadow-xl"
  >
    <div className={cn("p-4 rounded-2xl mb-6 bg-white/5 w-fit group-hover:scale-110 shadow-lg transition-transform", color)}>
      <Icon size={24} />
    </div>
    <div className="space-y-1 relative z-10">
       <div className="text-[10px] uppercase tracking-[0.2em] text-white/20 font-black">{title}</div>
       <div className="text-2xl font-black font-heading text-white truncate">{value}</div>
    </div>
    <div className={cn("absolute -right-4 -bottom-4 w-16 h-16 opacity-[0.03] group-hover:opacity-[0.08] transition-opacity", color)}>
       <Icon size={64} />
    </div>
  </motion.div>
);
