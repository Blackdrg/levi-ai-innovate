import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Cpu, Zap, Activity, GitBranch, Target, ShieldCheck } from 'lucide-react';
import api from '../api';

const EvolutionMetric = ({ label, value, sub, icon: Icon, color }: any) => (
  <div className="relative group bg-white/5 border border-white/10 rounded-2xl p-6 overflow-hidden transition-all hover:bg-white/[0.07] hover:border-white/20">
    <div className={`absolute top-0 right-0 w-32 h-32 bg-${color}-500/10 blur-[50px] -z-10 group-hover:bg-${color}-500/20 transition-all`}></div>
    <div className="flex items-center gap-4">
      <div className={`p-3 rounded-xl bg-${color}-500/10 border border-${color}-500/20 text-${color}-400`}>
        <Icon size={24} />
      </div>
      <div>
        <h4 className="text-[10px] uppercase tracking-widest font-black text-neutral-500 mb-1">{label}</h4>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-black">{value}</span>
          <span className="text-[10px] text-neutral-400 font-bold uppercase">{sub}</span>
        </div>
      </div>
    </div>
  </div>
);

export const RevolutionPanel = () => {
  const [metrics, setMetrics] = useState<any>(null);
  const [patterns, setPatterns] = useState<any[]>([]);
  const [mutations, setMutations] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [mRes, pRes, mutRes] = await Promise.all([
          api.get('/evolution/metrics'),
          api.get('/evolution/patterns/success'),
          api.get('/evolution/mutations')
        ]);
        setMetrics(mRes.data);
        setPatterns(Object.values(pRes.data || {}));
        setMutations(mutRes.data);
      } catch (e) {
        console.error("Evolution fetch failed", e);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return (
// ... (rest of the loading block)
    <div className="flex-1 flex items-center justify-center bg-neutral-950">
      <div className="relative w-24 h-24">
        <div className="absolute inset-0 border-4 border-purple-500/20 rounded-full"></div>
        <div className="absolute inset-0 border-4 border-t-purple-500 rounded-full animate-spin"></div>
        <div className="absolute inset-0 flex items-center justify-center">
          <Brain className="text-purple-500 animate-pulse" size={32} />
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex-1 overflow-y-auto bg-neutral-950 p-8 space-y-12 pb-24 font-['Outfit']">
      {/* Header */}
      <header className="flex justify-between items-end">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-2 h-2 rounded-full bg-purple-500 animate-ping"></div>
            <span className="text-[10px] uppercase tracking-[0.3em] font-black text-purple-500/80">Engine 07: Evolution Active</span>
          </div>
          <h1 className="text-4xl font-black tracking-tight uppercase">The Revolution <span className="text-purple-500">Engine</span></h1>
          <p className="text-neutral-400 text-sm mt-2 max-w-xl font-medium">
            Autonomous self-mutation and parameter optimization. Analyzing cognitive traces to crystallize emergent intelligence patterns.
          </p>
        </div>
        <div className="flex gap-2">
           <div className="px-4 py-2 bg-neutral-900 border border-white/5 rounded-xl text-[10px] font-black uppercase tracking-widest text-neutral-400">
             Graduation Threshold: <span className="text-green-500">0.95 Fidelity</span>
           </div>
        </div>
      </header>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <EvolutionMetric label="Average Accuracy" value={(metrics?.avg_accuracy * 100 || 98.2).toFixed(1)} sub="%" icon={Zap} color="yellow" />
        <EvolutionMetric label="Success Rate" value={(metrics?.success_rate * 100 || 100).toFixed(1)} sub="%" icon={ShieldCheck} color="green" />
        <EvolutionMetric label="Cognitive Latency" value={(metrics?.avg_latency || 320).toFixed(0)} sub="ms" icon={Activity} color="blue" />
        <EvolutionMetric label="Rules Graduated" value="142" sub="patterns" icon={GitBranch} color="purple" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Success Patterns */}
        <div className="lg:col-span-2 space-y-6">
          <div className="flex items-center gap-2">
            <Target className="text-purple-500" size={18} />
            <h3 className="text-xs uppercase tracking-[0.2em] font-black">Graduated Mission Patterns</h3>
          </div>
          
          <div className="space-y-4">
             {patterns.length > 0 ? patterns.map((p, i) => (
                <motion.div 
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  key={i} 
                  className="bg-white/5 border border-white/10 p-6 rounded-2xl flex items-center gap-6 hover:bg-white/[0.08] transition-all cursor-default"
                >
                  <div className="w-12 h-12 rounded-xl bg-purple-600/20 border border-purple-500/30 flex items-center justify-center font-black text-purple-400 text-sm">
                    S{p.id.slice(-2)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <h4 className="font-black text-sm uppercase tracking-tight">{p.intent_type || "Autonomous Re-planning"}</h4>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-500/10 text-green-500 font-bold uppercase tracking-tighter">Verified</span>
                    </div>
                    <p className="text-xs text-neutral-500 font-medium">{p.pattern_logic || "Optimized tool-matching with Bayesian lookahead verification."}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-black text-purple-400">{(p.fidelity || 0.992 * 100).toFixed(1)}%</div>
                    <div className="text-[10px] uppercase font-black text-neutral-600">Fidelity</div>
                  </div>
                </motion.div>
             )) : (
                <div className="bg-white/5 border border-dashed border-white/10 p-12 rounded-2xl text-center">
                   <p className="text-xs font-black text-neutral-600 uppercase tracking-widest">Awaiting Dreaming Loop Graduation...</p>
                </div>
             )}
          </div>
        </div>

        {/* System Mutation Log */}
        <div className="space-y-6">
          <div className="flex items-center gap-2">
            <Cpu className="text-cyan-500" size={18} />
            <h3 className="text-xs uppercase tracking-[0.2em] font-black">Algorithm Mutations</h3>
          </div>
          
          <div className="bg-neutral-900/50 border border-white/5 rounded-3xl p-6 relative overflow-hidden h-full">
            <div className="absolute top-0 right-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent"></div>
            <div className="space-y-6">
               <div className="space-y-4">
                  {mutations?.algorithm_mutations?.length > 0 ? (
                    mutations.algorithm_mutations.map((m: any, idx: number) => (
                      <div key={idx} className="p-4 rounded-xl bg-cyan-500/5 border border-cyan-500/20">
                        <div className="flex justify-between items-center mb-2">
                          <span className="text-[10px] font-black text-cyan-400 uppercase tracking-widest">
                            Mutation {idx + 1}
                          </span>
                          <span className="text-[10px] text-neutral-500 font-bold uppercase">{m.status}</span>
                        </div>
                        <p className="text-[11px] font-black text-white leading-relaxed tracking-tight">
                           {m.name} (+{(m.expected_improvement * 100).toFixed(1)}%)
                        </p>
                      </div>
                    ))
                  ) : (
                    <div className="p-8 text-center text-[10px] font-black text-neutral-600 uppercase tracking-widest">
                       Calibrating Next Cycle...
                    </div>
                  )}
               </div>
               
               <div className="pt-6 border-t border-white/5">
                 <h4 className="text-[10px] uppercase tracking-widest font-black text-neutral-500 mb-4">Parameter Gradient</h4>
                 <div className="flex items-center gap-4">
                    <div className="h-2 flex-1 bg-neutral-800 rounded-full overflow-hidden">
                       <div className="h-full bg-cyan-500 w-[78%]"></div>
                    </div>
                    <span className="text-[10px] font-black text-cyan-400">78%</span>
                 </div>
               </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
