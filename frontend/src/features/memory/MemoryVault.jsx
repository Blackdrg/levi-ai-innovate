import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Database, Trash2, Calendar, Tag, Search, RefreshCw, Layers, Shield, Sparkles } from "lucide-react";
import { memoryService } from "../../services/memoryService";
import { cn } from "../../utils/styles";

export const MemoryVault = () => {
  const [facts, setFacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  const loadMemory = async () => {
    setLoading(true);
    try {
      const data = await memoryService.getFacts();
      setFacts(data.facts || []);
    } catch (err) {
      console.error("Failed to sync memory archive", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMemory();
  }, []);

  const handleDelete = async (id) => {
    try {
      await memoryService.deleteFact(id);
      setFacts(prev => prev.filter(f => f.id !== id));
    } catch (err) {
      console.error("Failed to forget fact", err);
    }
  };

  const filteredFacts = facts.filter(f => 
    f.fact.toLowerCase().includes(filter.toLowerCase()) ||
    f.category.toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar bg-[#020202]">
      <div className="max-w-6xl mx-auto px-8 py-12 space-y-12">
        {/* Header Section */}
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-8 border-b border-white/5 pb-8">
          <div className="space-y-2">
             <div className="flex items-center gap-2">
                <span className="w-10 h-[1px] bg-emerald-500" />
                <span className="text-[10px] uppercase tracking-[0.3em] text-emerald-500 font-bold">Memory Archival Hub v13</span>
             </div>
             <h1 className="text-5xl font-heading font-black tracking-tighter text-white uppercase italic leading-none">
                Crystalline<span className="text-emerald-500">.</span>Vault
             </h1>
             <p className="text-[11px] text-white/30 font-medium max-w-md">Synchronized patterns crystallized from all past originator resonances.</p>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="relative group">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-white/20 group-focus-within:text-emerald-500 transition-colors" size={16} />
              <input 
                type="text" 
                placeholder="Scan archive for patterns..."
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="bg-white/5 border border-white/5 rounded-2xl pl-12 pr-6 py-3.5 text-xs font-medium text-white placeholder:text-white/10 focus:outline-none focus:border-emerald-500/40 w-full md:w-80 transition-all"
              />
            </div>
            <button 
              onClick={loadMemory}
              className="p-3.5 glass rounded-2xl text-white/30 hover:text-white hover:border-emerald-500/30 transition-all flex items-center justify-center"
            >
              <RefreshCw size={20} className={cn(loading && "animate-spin text-emerald-500")} />
            </button>
          </div>
        </header>

        {/* Global Stats Bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
           <MemoryStat label="Total Factoids" value={facts.length} icon={Database} color="text-emerald-500" />
           <MemoryStat label="Categories" value={new Set(facts.map(f => f.category)).size} icon={Layers} color="text-purple-500" />
           <MemoryStat label="Integrity" value="100%" icon={Shield} color="text-blue-500" />
           <MemoryStat label="Flux Rate" value="0.2/m" icon={Sparkles} color="text-amber-500" />
        </div>

        {/* Facts Grid */}
        {loading ? (
           <div className="flex flex-col items-center justify-center py-20 space-y-4">
              <RefreshCw className="text-emerald-500 animate-spin" size={32} />
              <div className="text-[10px] uppercase tracking-[0.4em] text-white/20 font-black">Syncing Neural Archive</div>
           </div>
        ) : filteredFacts.length === 0 ? (
           <div className="flex flex-col items-center justify-center py-32 text-center glass rounded-[3rem] border-dashed border-2 border-white/5 group overflow-hidden relative">
              <div className="absolute inset-0 bg-gradient-to-b from-transparent via-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />
              <div className="w-20 h-20 rounded-3xl bg-white/5 flex items-center justify-center border border-white/5 mb-8 rotate-45 group-hover:rotate-[225deg] transition-all duration-1000">
                 <Database size={32} className="text-white/10 -rotate-45 group-hover:rotate-[-225deg] transition-all duration-1000" />
              </div>
              <p className="text-white/40 text-xs uppercase tracking-[0.3em] font-black">No patterns manifested in the void.</p>
           </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            <AnimatePresence>
              {filteredFacts.map((item) => (
                <MemoryCard key={item.id} item={item} onDelete={handleDelete} />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
};

const MemoryStat = ({ label, value, icon: Icon, color }) => (
  <div className="glass p-5 rounded-3xl border border-white/5 flex items-center gap-4 group">
    <div className={cn("p-3 rounded-2xl bg-white/5 group-hover:scale-110 transition-transform", color)}>
       <Icon size={18} />
    </div>
    <div className="space-y-0.5">
       <div className="text-[9px] uppercase tracking-widest text-white/20 font-black">{label}</div>
       <div className="text-lg font-black font-heading text-white">{value}</div>
    </div>
  </div>
);

const MemoryCard = ({ item, onDelete }) => {
  const isEpisodic = item.category.toLowerCase().includes('mission') || item.category.toLowerCase().includes('chat');
  const themeColor = isEpisodic ? 'purple' : 'emerald';

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.98, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.98, y: 10 }}
      className={cn(
        "glass p-8 rounded-[2rem] group relative border border-white/5 hover:scale-[1.02] transition-all duration-500 overflow-hidden shadow-xl",
        themeColor === 'emerald' ? "hover:border-emerald-500/30" : "hover:border-purple-500/30"
      )}
    >
      {/* Crystalline Glow */}
      <div className={cn(
        "absolute -right-10 -bottom-10 w-32 h-32 blur-[60px] opacity-10 pointer-events-none group-hover:opacity-30 transition-opacity",
        themeColor === 'emerald' ? "bg-emerald-500" : "bg-purple-500"
      )} />

      <div className="flex justify-between items-start mb-6">
          <div className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-xl text-[9px] uppercase tracking-[0.2em] font-black border",
            themeColor === 'emerald' ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-purple-500/10 text-purple-400 border-purple-500/20"
          )}>
              <Tag size={10} /> {item.category}
          </div>
          <button 
            onClick={() => onDelete(item.id)}
            className="p-2 glass rounded-xl text-white/10 hover:text-red-400 hover:border-red-500/20 opacity-0 group-hover:opacity-100 transition-all translate-x-2 group-hover:translate-x-0"
          >
            <Trash2 size={14} />
          </button>
      </div>
      
      <p className="text-[14px] text-white/90 leading-relaxed mb-8 font-medium italic selection:bg-emerald-500/30">
        "{item.fact}"
      </p>

      <div className="flex items-center gap-3 pt-6 border-t border-white/5 text-[9px] text-white/20 uppercase tracking-[0.2em] font-black">
          <Calendar size={12} className={cn(themeColor === 'emerald' ? "text-emerald-500" : "text-purple-500")} />
          <span>Crystallized: {new Date(item.learned_at).toLocaleDateString()}</span>
      </div>
    </motion.div>
  );
};
