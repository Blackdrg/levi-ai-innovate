import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Database, Trash2, Calendar, Tag, Search, RefreshCw } from "lucide-react";
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
    <div className="flex-1 overflow-y-auto px-6 md:px-12 py-10">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
          <div>
            <h1 className="text-3xl md:text-5xl font-bold font-heading text-gradient mb-2">Memory Archive</h1>
            <p className="text-xs uppercase tracking-[0.2em] text-white/40">Crystallized patterns from your resonances</p>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/20" size={14} />
              <input 
                type="text" 
                placeholder="Search archive..."
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="bg-white/5 border border-white/10 rounded-xl px-10 py-2 text-xs focus:outline-none focus:border-purple-500/50 w-full md:w-64"
              />
            </div>
            <button 
              onClick={loadMemory}
              className="p-2 glass rounded-xl text-white/40 hover:text-white transition-colors"
            >
              <RefreshCw size={18} className={cn(loading && "animate-spin")} />
            </button>
          </div>
        </div>

        {/* Facts Grid */}
        {loading ? (
           <div className="flex items-center justify-center py-20 text-white/20 uppercase tracking-widest text-xs">
             Synchronizing Archive...
           </div>
        ) : filteredFacts.length === 0 ? (
           <div className="flex flex-col items-center justify-center py-20 text-center glass rounded-3xl border-dashed border-2 border-white/5">
             <Database size={40} className="text-white/10 mb-4" />
             <p className="text-white/40 text-sm">No patterns have been crystallized yet.</p>
           </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

const MemoryCard = ({ item, onDelete }) => (
  <motion.div
    layout
    initial={{ opacity: 0, scale: 0.95 }}
    animate={{ opacity: 1, scale: 1 }}
    exit={{ opacity: 0, scale: 0.95 }}
    className="glass p-6 rounded-2xl group relative border border-white/5 hover:border-purple-500/30 transition-all"
  >
    <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-2 px-2 py-1 bg-purple-500/10 rounded-lg text-[9px] uppercase tracking-wider text-purple-400 font-bold border border-purple-500/20">
            <Tag size={10} /> {item.category}
        </div>
        <button 
          onClick={() => onDelete(item.id)}
          className="p-1.5 text-white/10 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
        >
          <Trash2 size={14} />
        </button>
    </div>
    
    <p className="text-sm text-white/80 leading-relaxed mb-6 font-medium italic">
      "{item.fact}"
    </p>

    <div className="flex items-center gap-2 text-[10px] text-white/20 uppercase tracking-widest">
        <Calendar size={12} /> Learned on {new Date(item.learned_at).toLocaleDateString()}
    </div>
  </motion.div>
);
