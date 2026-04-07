import React from 'react';
import { motion } from 'framer-motion';
import { useChatStore } from '../store/useChatStore';
import { ShieldCheck, AlertTriangle, XCircle, Info, Activity } from 'lucide-react';

export const MissionAuditor = () => {
  const audit = useChatStore((state) => state.auditResult);
  const fidelity = useChatStore((state) => state.missionFidelity);
  const isStreaming = useChatStore((state) => state.isStreaming);

  if (!audit || isStreaming) return null;

  const isSuccess = fidelity >= 0.8;
  const colorClass = fidelity >= 0.9 ? 'text-emerald-500' : fidelity >= 0.7 ? 'text-amber-500' : 'text-red-500';
  const borderClass = fidelity >= 0.9 ? 'border-emerald-500/20' : fidelity >= 0.7 ? 'border-amber-500/20' : 'border-red-500/20';
  const bgClass = fidelity >= 0.9 ? 'bg-emerald-500/5' : fidelity >= 0.7 ? 'bg-amber-500/5' : 'bg-red-500/5';

  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className={`mt-6 p-6 glass rounded-2xl border ${borderClass} ${bgClass} shadow-xl relative overflow-hidden group`}
    >
      {/* Background Accent */}
      <div className={`absolute -right-4 -top-4 opacity-[0.03] transition-transform duration-1000 group-hover:scale-110`}>
         <Activity size={120} />
      </div>

      <div className="relative z-10 space-y-5">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
             <div className={`w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center border border-white/5 ${colorClass}`}>
                {fidelity >= 0.9 ? <ShieldCheck size={20} /> : fidelity >= 0.7 ? <AlertTriangle size={20} /> : <XCircle size={20} />}
             </div>
             <div>
                <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-white/40 mb-0.5">Mission Audit Registry</h4>
                <p className={`text-[9px] font-bold uppercase tracking-widest ${colorClass}`}>
                   {fidelity >= 0.9 ? 'Fidelity Verified' : fidelity >= 0.7 ? 'Heuristic Match' : 'Intervention Recommended'}
                </p>
             </div>
          </div>
          <div className="text-right">
             <div className={`text-2xl font-black font-heading leading-none ${colorClass}`}>
                {Math.round(fidelity * 100)}<span className="text-[10px] ml-0.5">%</span>
             </div>
             <div className="text-[8px] uppercase tracking-widest font-bold text-white/20 mt-1">S-Fidelity Score</div>
          </div>
        </header>

        {audit.issues && audit.issues.length > 0 && (
          <div className="space-y-2">
            <h5 className="text-[9px] uppercase tracking-widest font-black text-white/20 flex items-center gap-2">
               <Info size={10} /> Internal Observations
            </h5>
            <div className="space-y-1.5">
               {audit.issues.map((issue, i) => (
                 <div key={i} className="flex gap-2 text-[10px] text-white/70 leading-relaxed pl-1 border-l border-white/10 ml-1">
                    <span className="text-white/20 font-mono">{(i+1).toString().padStart(2, '0')}</span>
                    {issue}
                 </div>
               ))}
            </div>
          </div>
        )}

        {audit.fix && (
          <div className="pt-4 border-t border-white/5">
             <div className="bg-white/5 rounded-xl p-3 flex items-start gap-3 border border-white/5">
                <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400">
                   <Activity size={14} />
                </div>
                <div className="space-y-1">
                   <span className="text-[9px] font-black uppercase tracking-widest text-indigo-400">Adaptive Refinement Pulse</span>
                   <p className="text-[10px] text-white/60 leading-relaxed italic">
                      "{audit.fix}"
                   </p>
                </div>
             </div>
          </div>
        )}
      </div>
    </motion.div>
  );
};
