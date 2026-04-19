import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLeviStore } from '../stores/leviStore';
import { Activity, Thermometer, Cpu, Shield, Braces } from 'lucide-react';

const ThermalGauge = ({ label, value, unit, color, max }: any) => {
  const percentage = Math.min((value / max) * 100, 100);
  
  return (
    <div className="p-4 rounded-2xl bg-white/5 border border-white/10 relative overflow-hidden group">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-2">
          <Thermometer size={16} className="text-neutral-500" />
          <span className="text-[10px] font-black uppercase tracking-widest text-neutral-400">{label}</span>
        </div>
        <span className="text-xl font-black font-mono">{value.toFixed(1)}{unit}</span>
      </div>
      
      <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden">
        <motion.div 
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          className="h-full"
          style={{ background: color }}
        />
      </div>
      
      {/* Decorative Glow */}
      <div className="absolute top-0 right-0 w-24 h-24 blur-3xl opacity-10 rounded-full" style={{ background: color }}></div>
    </div>
  );
};

const AgentTile = ({ agent }: any) => (
  <div className={`p-3 rounded-xl border transition-all duration-300 ${
    agent.status === 'READY' ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-400' : 'bg-red-500/5 border-red-500/20 text-red-400'
  }`}>
    <div className="flex justify-between items-start mb-2">
      <span className="text-[10px] font-black tracking-tighter">{agent.name}</span>
      <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${agent.status === 'READY' ? 'bg-emerald-500' : 'bg-red-500'}`} />
    </div>
    <div className="text-[8px] font-mono opacity-60 uppercase">{agent.model}</div>
    <div className="mt-2 text-xs font-black">{agent.latency}ms</div>
  </div>
);

export const MetricsDashboard: React.FC = () => {
  const { agents, thermal, syscalls, ksm } = useLeviStore();

  return (
    <div className="p-8 h-full overflow-y-auto space-y-8 no-scrollbar">
      <header className="flex justify-between items-end">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Shield size={16} className="text-blue-500" />
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-blue-500">Live Telemetry</span>
          </div>
          <h2 className="text-3xl font-black uppercase tracking-tight">Sovereign Cluster v22</h2>
        </div>
        <div className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
          <span className="text-[10px] font-black uppercase tracking-widest text-emerald-500">Node_Status: ACTIVE</span>
        </div>
      </header>

      {/* Primary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <ThermalGauge label="Kernel CPU Temp" value={thermal.cpu} unit="°C" color="#3b82f6" max={100} />
        <ThermalGauge label="Sovereign GPU Temp" value={thermal.gpu_temp} unit="°C" color={thermal.gpu_temp > 75 ? "#ef4444" : "#f59e0b"} max={100} />
        <ThermalGauge label="Neural VRAM Usage" value={thermal.vram} unit="GB" color="#8b5cf6" max={24} />
        
        {/* KSM Deduplication (Section 94) */}
        <div className="p-4 rounded-2xl bg-white/5 border border-purple-500/20 relative overflow-hidden group">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-2">
              <Shield size={16} className="text-purple-400" />
              <span className="text-[10px] font-black uppercase tracking-widest text-purple-400">KSM Savings</span>
            </div>
            <span className="text-xl font-black font-mono text-purple-400">{ksm.savings_pct}%</span>
          </div>
          <div className="text-[8px] font-black uppercase text-neutral-500 tracking-tighter">
            HAL-0 Memory Deduplication: ACTIVE
          </div>
          <div className="absolute -bottom-2 -right-2 opacity-5 text-purple-500">
             <Cpu size={80} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Agent Grid */}
        <section className="glass rounded-3xl p-6 border border-white/5">
          <div className="flex items-center gap-2 mb-6">
            <Cpu size={18} className="text-neutral-500" />
            <h3 className="text-xs font-black uppercase tracking-widest">Cognitive Swarm (16 Nodes)</h3>
          </div>
          <div className="grid grid-cols-4 gap-4">
            {agents.map((agent, i) => (
              <AgentTile key={i} agent={agent} />
            ))}
          </div>
        </section>

        {/* Syscall Monitor */}
        <section className="glass rounded-3xl p-6 border border-white/5 flex flex-col h-[400px]">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <Braces size={18} className="text-neutral-500" />
              <h3 className="text-xs font-black uppercase tracking-widest">HAL-0 Syscall Monitor</h3>
            </div>
            <span className="text-[10px] font-mono text-neutral-500">Tracing: Kernel_Entry_Vector</span>
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-2 font-mono text-[10px] pr-2 custom-scrollbar">
            <AnimatePresence initial={false}>
              {syscalls.map((sc) => (
                <motion.div
                  key={sc.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="p-2 rounded bg-white/5 border-l-2 border-blue-500/50 flex justify-between group hover:bg-white/10 transition-colors"
                >
                  <div className="flex gap-4">
                    <span className="text-blue-500 font-bold">0x{sc.name.split('_')[1] || '??'}</span>
                    <span className="text-neutral-300">{sc.name}</span>
                  </div>
                  <div className="flex gap-4 opacity-40 group-hover:opacity-100 transition-opacity">
                    <span className="text-neutral-500">ARGS: {sc.args.join(', ')}</span>
                    <span className="text-neutral-600">{new Date(sc.timestamp).toLocaleTimeString()}</span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </section>
      </div>

      <style>{`
        .glass { background: rgba(255, 255, 255, 0.02); backdrop-filter: blur(12px); }
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: rgba(255,255,255,0.02); }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(59, 130, 246, 0.2); border-radius: 10px; }
      `}</style>
    </div>
  );
};
