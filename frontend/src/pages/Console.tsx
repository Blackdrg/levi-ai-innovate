import React, { useState, ChangeEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Zap, Send, ShieldAlert, Sparkles, Orbit, Activity } from "lucide-react";
import { apiFetch } from "../lib/auth";
import { MissionDashboard } from "../components/MissionDashboard";

export default function Console() {
  const [query, setQuery] = useState("");
  const [isLaunching, setIsLaunching] = useState(false);
  const [missionId, setMissionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const tier = detectTier(query);

  const handleLaunch = async () => {
    if (!query.trim()) return;
    
    setIsLaunching(true);
    setError(null);
    setMissionId(null);

    try {
      const res = await apiFetch("/api/v1/orchestrator/mission", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          input: query, 
          context: { tier, session_id: "console_v14" } 
        }),
      });

      if (!res.ok) throw new Error("Sovereign mission failed to launch.");
      
      const data = await res.json();
      setMissionId(data.mission_id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Celestial misalignment detected.");
    } finally {
      setIsLaunching(false);
    }
  };

  return (
    <div className="flex-1 p-8 overflow-y-auto custom-scrollbar bg-[#020202]">
      <div className="max-w-5xl mx-auto space-y-10">
        
        {/* Header Section */}
        <header className="flex items-center justify-between">
          <div className="space-y-1">
             <div className="flex items-center gap-2 mb-1">
                <span className="w-8 h-[1px] bg-emerald-500/50" />
                <span className="text-[9px] uppercase tracking-[0.4em] text-emerald-500 font-black">Authorized Intelligence Access</span>
             </div>
             <h1 className="text-5xl font-heading font-black tracking-tighter text-white uppercase italic leading-none">
                Sovereign<span className="text-emerald-500">.</span>Console
             </h1>
             <p className="text-[10px] uppercase tracking-[0.2em] text-white/20 font-bold ml-1">v14.0.0 Autonomous-SOVEREIGN Engine // Grade: Graduated</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-2 px-3 py-1.5 glass rounded-lg border border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.1)]">
               <Orbit className="text-emerald-500 animate-spin-slow" size={16} />
               <span className="text-[10px] font-mono text-emerald-300 uppercase tracking-widest font-bold">Resonance: Active</span>
            </div>
            <div className="text-[8px] text-white/10 font-mono uppercase">Node ID: SOVEREIGN-V14-ALPHA</div>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-10">
          
          {/* Submission Panel */}
          <div className="lg:col-span-3 space-y-8">
            <div className="relative group">
               <div className="absolute -inset-[2px] bg-gradient-to-r from-emerald-500/20 via-purple-500/20 to-blue-500/20 rounded-[2.5rem] blur-xl opacity-20 group-focus-within:opacity-100 transition-all duration-1000" />
               <div className="relative bg-[#050505] rounded-[2.5rem] border border-white/5 p-8 space-y-6 shadow-2xl">
                  <div className="flex items-center justify-between text-white/20">
                     <div className="flex gap-1">
                        <div className="w-1.5 h-1.5 rounded-full bg-white/10" />
                        <div className="w-1.5 h-1.5 rounded-full bg-white/10" />
                        <div className="w-1.5 h-1.5 rounded-full bg-white/10" />
                     </div>
                     <span className="text-[9px] uppercase tracking-widest font-bold">Neural Input Buffer v14</span>
                  </div>

                  <textarea 
                    value={query}
                    onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setQuery(e.target.value)}
                    placeholder="Initialize sovereign mission protocol..."
                    className="w-full h-56 bg-transparent border-none outline-none text-white/95 placeholder:text-white/10 resize-none font-sans text-xl leading-relaxed selection:bg-emerald-500/30"
                    disabled={isLaunching}
                  />
                  
                  <div className="flex items-center justify-between pt-6 border-t border-white/5">
                     <div className="flex items-center gap-4">
                        <TierBadge tier={tier} />
                        <div className="flex flex-col">
                           <span className="text-[9px] text-white/40 font-bold uppercase tracking-widest">Predictive Logic</span>
                           <span className="text-[8px] text-white/20 italic">Tier {tier} detected via quantum heuristic</span>
                        </div>
                     </div>
                     <button 
                       onClick={handleLaunch}
                       disabled={isLaunching || !query.trim()}
                       className="group relative px-8 py-3.5 bg-white text-black rounded-2xl flex items-center gap-3 hover:scale-105 active:scale-95 transition-all disabled:opacity-30 disabled:scale-100 overflow-hidden"
                     >
                        <div className="absolute inset-0 bg-gradient-to-r from-emerald-400 to-purple-400 opacity-0 group-hover:opacity-10 transition-opacity" />
                        <span className="text-xs font-black uppercase tracking-widest relative z-10">
                           {isLaunching ? "Establishing Link..." : "Launch Mission"}
                        </span>
                        {isLaunching ? <Orbit size={16} className="animate-spin relative z-10" /> : <Send size={16} className="relative z-10" />}
                     </button>
                  </div>
               </div>
            </div>

            {error && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="p-5 rounded-2xl border border-red-500/20 bg-red-500/5 flex items-center gap-4 text-red-400 shadow-[0_0_20px_rgba(239,68,68,0.05)]">
                 <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center border border-red-500/20">
                    <ShieldAlert size={20} />
                 </div>
                 <div className="flex flex-col gap-0.5">
                    <span className="text-[10px] uppercase font-black tracking-widest">Celestial Fault Detected</span>
                    <span className="text-xs font-medium text-red-400/80">{error}</span>
                 </div>
              </motion.div>
            )}

            {!missionId && !isLaunching && (
              <div className="p-20 border border-dashed border-white/5 rounded-[2.5rem] flex flex-col items-center justify-center opacity-20 hover:opacity-30 transition-opacity group">
                 <div className="relative mb-6">
                    <Sparkles className="text-white relative z-10" size={48} strokeWidth={1} />
                    <div className="absolute inset-0 bg-emerald-500/50 blur-2xl rounded-full opacity-0 group-hover:opacity-50 transition-all duration-1000" />
                 </div>
                 <p className="text-[10px] text-white uppercase tracking-[0.3em] font-black text-center">Awaiting Sovereign Intent<br/><span className="text-[8px] font-normal opacity-50">Local Resonance established</span></p>
              </div>
            )}
          </div>

          {/* Results Sidebar */}
          <div className="lg:col-span-1 space-y-6">
             <AnimatePresence mode="wait">
               {missionId ? (
                 <motion.div 
                   key={missionId}
                   initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
                   className="space-y-6"
                 >
                    <div className="flex items-center gap-2 mb-2">
                       <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_#10b981]" />
                       <span className="text-[10px] uppercase tracking-widest font-black text-white/40">Real-time Stream</span>
                    </div>
                    <MissionDashboard missionId={missionId} />
                    
                    <div className="p-6 glass rounded-2xl border border-white/5 shadow-xl">
                       <h4 className="text-[10px] font-black text-white/30 uppercase tracking-[0.2em] mb-4 flex items-center justify-between">
                          Mission Logs
                          <Activity size={12} className="text-emerald-500" />
                       </h4>
                       <div className="space-y-3 max-h-64 overflow-y-auto text-[10px] font-mono custom-scrollbar pr-2">
                          <div className="flex gap-2">
                             <span className="text-emerald-500 font-bold">[LOG_V14]</span>
                             <span className="text-white/60">Mission {missionId.slice(0, 8)} linked.</span>
                          </div>
                          <div className="flex gap-2">
                             <span className="text-purple-500 font-bold">[SYNC]</span>
                             <span className="text-white/60">Tier {tier} context locked.</span>
                          </div>
                          <div className="flex gap-2">
                             <span className="text-blue-500 font-bold">[CORE]</span>
                             <span className="text-white/60">Sovereign resonance at 99.9%.</span>
                          </div>
                       </div>
                    </div>
                 </motion.div>
               ) : (
                 <div className="h-full p-8 glass rounded-[2rem] border border-white/5 flex flex-col items-center justify-center gap-6 opacity-30 group relative overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-white/5 to-transparent -translate-y-full group-hover:translate-y-full transition-transform duration-[2000ms]" />
                    <div className="w-16 h-16 rounded-3xl bg-white/5 flex items-center justify-center border border-white/10 group-hover:border-emerald-500/20 transition-colors">
                       <Zap size={24} className="text-white group-hover:text-emerald-400 transition-colors" />
                    </div>
                    <div className="text-center space-y-3">
                       <h4 className="text-[10px] font-black text-white uppercase tracking-[0.2em]">Neural Pulse</h4>
                       <p className="text-[10px] text-white/40 leading-relaxed max-w-[180px] mx-auto">
                          Waiting for cognitive emission. Launch a mission to witness the absolute autonomy of the Sovereign OS.
                       </p>
                    </div>
                 </div>
               )}
             </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}

function TierBadge({ tier }: { tier: string }) {
   const colors = {
      "L1": "from-emerald-600 to-green-600",
      "L2": "from-blue-600 to-cyan-600",
      "L3": "from-purple-600 to-pink-600",
      "L4": "from-red-600 to-orange-600"
   };
   return (
      <div className={`px-2.5 py-1 rounded bg-gradient-to-r ${colors[tier as keyof typeof colors]} flex items-center gap-1.5 shadow-[0_0_8px_rgba(0,0,0,0.5)]`}>
         <Zap size={10} className="text-white fill-white/20" />
         <span className="text-[10px] font-black text-white">{tier}</span>
      </div>
   );
}

function detectTier(q: string): "L1" | "L2" | "L3" | "L4" {
  const words = q.trim().split(/\s+/).length;
  if (!q.trim()) return "L1";
  if (words < 10) return "L1";
  if (q.includes("build") || q.includes("code") || q.includes("develop")) return "L2";
  if (q.includes("research") || q.includes("summarize") || q.includes("analyze")) return "L3";
  return "L4";
}
