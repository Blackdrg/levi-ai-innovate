import * as React from 'react';
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Database, Share2, Layers, Search, List } from 'lucide-react';
import { ForceGraph2D } from 'react-force-graph';
import { api } from '../lib/api';
import { MemoryEntry } from '../lib/types';

type MemoryTab = 'working' | 'episodic' | 'relational' | 'semantic';

export const MemoryExplorer: React.FC = () => {
  const [activeTab, setActiveTab] = useState<MemoryTab>('working');
  const [searchQuery, setSearchQuery] = useState('');
  const [results, setResults] = useState<MemoryEntry[]>([]);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [isLoading, setIsLoading] = useState(false);

  const fetchMemory = async () => {
    setIsLoading(true);
    try {
      if (activeTab === 'relational') {
        const graph = await api.getHealthGraph();
        setGraphData(graph);
      } else {
        const data = await api.searchMemory(searchQuery, activeTab);
        setResults(data);
      }
    } catch (err) {
      console.error('Failed to fetch memory:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchMemory();
  }, [activeTab]);

  return (
    <div className="memory-explorer font-['Outfit'] h-full overflow-y-auto">
      <header className="explorer-header flex justify-between items-center mb-10">
        <div>
          <h1 className="text-2xl font-black tracking-tight uppercase text-white/90">Quad-Memory Explorer</h1>
          <span className="text-[10px] uppercase tracking-widest font-black text-purple-500 opacity-80">Cognitive Persistence Layer</span>
        </div>
        
        <div className="search-bar flex items-center gap-3 bg-neutral-900/40 border border-white/5 px-4 py-2 rounded-xl focus-within:border-purple-500/50 transition-all shadow-lg shadow-black/20">
          <Search size={18} className="text-neutral-500" />
          <input 
            type="text" 
            placeholder="Search cognitive stores..." 
            className="bg-transparent border-none outline-none text-sm text-white placeholder-neutral-600 w-64"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchMemory()}
          />
        </div>
      </header>

      <nav className="tab-nav">
        {[
          { id: 'working', icon: <Layers size={16} />, label: 'WORKING (REDIS)' },
          { id: 'episodic', icon: <List size={16} />, label: 'EPISODIC (PG)' },
          { id: 'relational', icon: <Share2 size={16} />, label: 'RELATIONAL (NEO4J)' },
          { id: 'semantic', icon: <Database size={16} />, label: 'SEMANTIC (FAISS)' },
        ].map(tab => (
          <button 
            key={tab.id}
            className={activeTab === tab.id ? 'active' : ''}
            onClick={() => setActiveTab(tab.id as MemoryTab)}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </nav>

      <main className="explorer-content">
        <AnimatePresence mode="wait">
          {activeTab === 'relational' ? (
            <motion.div 
              key="relational"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="graph-container"
            >
              <ForceGraph2D
                graphData={graphData}
                nodeLabel="label"
                nodeColor={node => (node as any).color}
                nodeRelSize={8}
                linkDirectionalArrowLength={3.5}
                linkDirectionalArrowRelPos={1}
                backgroundColor="#020617"
                width={800}
                height={500}
              />
            </motion.div>
          ) : (
            <motion.div 
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="list-container"
            >
              {results.length === 0 ? (
                <div className="empty-state">No records found in this partition.</div>
              ) : (
                results.map(item => (
                  <div key={item.id} className="memory-card">
                    <div className="memory-meta">
                      <span className="timestamp">{item.timestamp}</span>
                      {item.score && <span className="score">Similarity: {item.score.toFixed(4)}</span>}
                    </div>
                    <p className="memory-text">{item.content}</p>
                  </div>
                ))
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <style>{`
        .memory-explorer {
          height: 100%;
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
          padding: 2rem;
          color: #f1f5f9;
        }
        .explorer-header h1 {
          font-family: 'JetBrains Mono', monospace;
          font-size: 1.5rem;
          letter-spacing: 0.1em;
          margin-bottom: 1.5rem;
          color: #38bdf8;
        }
        .search-bar {
          display: flex;
          align-items: center;
          gap: 1rem;
          background: rgba(15, 23, 42, 0.6);
          border: 1px solid rgba(255, 255, 255, 0.1);
          padding: 0.75rem 1rem;
          border-radius: 8px;
          max-width: 600px;
        }
        .search-bar input {
          background: transparent;
          border: none;
          color: white;
          width: 100%;
          outline: none;
        }
        .tab-nav {
          display: flex;
          gap: 1rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
          padding-bottom: 0.5rem;
        }
        .tab-nav button {
          background: transparent;
          border: none;
          color: #64748b;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.75rem 1rem;
          cursor: pointer;
          font-family: 'Inter', sans-serif;
          font-weight: 600;
          font-size: 0.8rem;
          transition: all 0.2s ease;
          border-radius: 6px;
        }
        .tab-nav button.active {
          color: #38bdf8;
          background: rgba(56, 189, 248, 0.1);
        }
        .tab-nav button:hover:not(.active) {
          color: #94a3b8;
          background: rgba(255, 255, 255, 0.05);
        }
        .explorer-content {
          flex: 1;
          background: rgba(15, 23, 42, 0.4);
          border: 1px solid rgba(255, 255, 255, 0.05);
          border-radius: 12px;
          min-height: 400px;
          overflow: hidden;
        }
        .graph-container {
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .list-container {
          padding: 1.5rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        .memory-card {
          background: rgba(2, 6, 23, 0.4);
          border: 1px solid rgba(255, 255, 255, 0.05);
          padding: 1.25rem;
          border-radius: 8px;
        }
        .memory-meta {
          display: flex;
          justify-content: space-between;
          font-size: 0.7rem;
          color: #64748b;
          margin-bottom: 0.75rem;
          font-family: 'JetBrains Mono', monospace;
        }
        .score { color: #38bdf8; }
        .memory-text {
          font-size: 0.9rem;
          line-height: 1.6;
          color: #cbd5e1;
        }
        .empty-state {
          text-align: center;
          color: #64748b;
          padding: 4rem;
          font-family: 'JetBrains Mono', monospace;
        }
      `}</style>
    </div>
  );
};
