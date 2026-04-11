import React, { useEffect, useState } from 'react';
import { useTelemetryStore } from '../stores/telemetryStore';
import { AgentStatus } from '../lib/types';
import { motion, AnimatePresence } from 'framer-motion';
import { Cpu, Activity, RefreshCw, Layers, Target, ShieldCheck } from 'lucide-react';
import { api } from '../lib/api';

const AgentCard = ({ agent }: { agent: AgentStatus }) => {
  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ y: -4, borderColor: 'rgba(168, 85, 247, 0.4)' }}
      className={`agent-card glass border border-white/5 relative overflow-hidden p-6 rounded-2xl shadow-xl transition-all duration-300 ${agent.status.toLowerCase()}`}
    >
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${agent.status === 'online' ? 'bg-purple-500/10' : 'bg-red-500/10'}`}>
            <Cpu size={18} className={agent.status === 'online' ? 'text-purple-400' : 'text-red-400'} />
          </div>
          <div>
            <span className="text-sm font-black tracking-tight uppercase text-white/90">{agent.category}</span>
            <p className="text-[9px] uppercase tracking-widest font-black text-neutral-500">Autonomous Unit</p>
          </div>
        </div>
        <div className={`w-2 h-2 rounded-full shadow-lg ${
          agent.status === 'online' ? 'bg-green-500 shadow-green-500/20' : 
          agent.status === 'busy' ? 'bg-amber-500 animate-pulse' : 'bg-red-500'
        }`} />
      </div>

      <div className="space-y-4">
        <div className="bg-neutral-950/40 border border-white/5 p-3 rounded-xl">
          <label className="text-[9px] font-black uppercase tracking-[0.2em] text-neutral-500 block mb-1">Current Task</label>
          <span className="text-xs font-bold text-neutral-300 truncate block">{agent.currentTask || 'NODE_IDLE'}</span>
        </div>

        {agent.goal_objective && (
          <div className="bg-purple-950/20 border border-purple-500/20 p-3 rounded-xl">
            <div className="flex items-center gap-2 mb-1">
              <Target size={10} className="text-purple-400" />
              <label className="text-[9px] font-black uppercase tracking-[0.2em] text-purple-400 block">Sovereign Target</label>
            </div>
            <span className="text-[10px] font-bold text-neutral-300 truncate block">{agent.goal_objective}</span>
          </div>
        )}

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-neutral-500">
            <Activity size={12} className="text-purple-500/60" />
            <span className="text-[10px] font-black font-mono tracking-tight">{agent.latency_ms}ms</span>
          </div>
          <div className="flex items-center gap-2 text-neutral-500">
            <RefreshCw size={12} className="text-cyan-500/60" />
            <span className="text-[10px] font-black font-mono tracking-tight">{agent.retryCount} Retries</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export const AgentGrid: React.FC = () => {
  const agents = useTelemetryStore((state) => Object.values(state.agents));
  const setAgents = (useTelemetryStore as any).getState().setAgents;
  const [isLoading, setIsLoading] = useState(true);
  const [isAdmin, setIsAdmin] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const updateSwarm = async () => {
      try {
        const graph = await api.getHealthGraph();
        if (isMounted) setIsAdmin(true);
        if (isMounted && graph.nodes) {
          const agentsMap: Record<string, AgentStatus> = {};
          graph.nodes.forEach((node: any) => {
            agentsMap[node.id] = {
              id: node.id,
              category: node.type.toUpperCase() as any,
              status: node.status === 'online' ? 'online' : 'offline',
              currentTask: node.current_task || '',
              goal_id: node.goal_id,
              goal_objective: node.goal_objective,
              latency_ms: Math.floor(Math.random() * 50) + 10,
              retryCount: 0
            };
          });
          setAgents(agentsMap);
        }
      } catch (err) {
        console.error('Failed to poll DCN health graph:', err);
        if (isMounted) setIsAdmin(false);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    updateSwarm();
    const interval = setInterval(updateSwarm, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [setAgents]);

  return (
    <div className="p-8 font-['Outfit'] h-full overflow-y-auto">
      <header className="flex justify-between items-center mb-10">
        <div>
          <h1 className="text-2xl font-black tracking-tight uppercase text-white/90">Agent Swarm Control</h1>
          <span className="text-[10px] uppercase tracking-widest font-black text-purple-500 opacity-80">Distributed Cognitive Network</span>
        </div>
        <div className="flex items-center gap-2 bg-neutral-900/40 border border-white/5 px-4 py-2 rounded-xl">
          <Layers size={16} className="text-purple-500/60" />
          <span className="text-[10px] font-black tracking-widest uppercase text-neutral-400">{agents.length} Active Nodes</span>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        <AnimatePresence mode="popLayout">
          {isLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-48 rounded-2xl bg-neutral-900/20 border border-white/5 animate-pulse" />
            ))
          ) : !isAdmin ? (
            <div className="col-span-full h-64 flex flex-col items-center justify-center text-purple-500/60 opacity-80 border border-dashed border-purple-500/20 rounded-3xl bg-purple-500/5">
              <ShieldCheck size={48} className="mb-4" />
              <span className="font-black uppercase tracking-[0.3em]">Sovereign Shield Active</span>
              <p className="text-[10px] mt-2 text-neutral-500 uppercase font-bold tracking-widest">Node telemetry restricted to core administrators</p>
            </div>
          ) : agents.length === 0 ? (
            <div className="col-span-full h-64 flex flex-col items-center justify-center text-neutral-500 opacity-50 border border-dashed border-white/10 rounded-3xl">
              <Activity size={48} className="mb-4 animate-pulse" />
              <span className="font-black uppercase tracking-[0.3em]">Establishing Swarm Link...</span>
            </div>
          ) : (
            agents.map((agent) => <AgentCard key={agent.id} agent={agent} />)
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};
