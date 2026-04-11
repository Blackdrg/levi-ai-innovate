import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Filter, Download, Play, X, ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '../lib/api';
import { Task, TaskStatus } from '../lib/types';

export const TaskHistory: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState<TaskStatus | 'ALL'>('ALL');
  const [search, setSearch] = useState('');
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isReplaying, setIsReplaying] = useState(false);

  useEffect(() => {
    // Mocking for preview
    setTasks([
      { id: 't-948', input: 'Sync memory with Neo4j', status: 'DONE', dag: { nodes: [], edges: [] }, created_at: '2026-04-07 20:30' },
      { id: 't-947', input: 'Batch process video frames', status: 'FAILED', dag: { nodes: [], edges: [] }, created_at: '2026-04-07 20:25' },
      { id: 't-946', input: 'Verify auth resonance', status: 'DONE', dag: { nodes: [], edges: [] }, created_at: '2026-04-07 20:20' },
    ]);
  }, []);

  const handleExport = () => {
    const data = JSON.stringify(tasks, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `task_history_${Date.now()}.json`;
    a.click();
  };

  return (
    <div className="task-history">
      <header className="history-header">
        <h1>TASK AUDIT LOG</h1>
        <div className="history-actions">
          <div className="search-box">
            <Search size={16} />
            <input type="text" placeholder="Search tasks..." value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <select value={filter} onChange={(e) => setFilter(e.target.value as any)} className="filter-select" title="Filter by status">
            <option value="ALL">ALL STATUSES</option>
            <option value="DONE">DONE</option>
            <option value="FAILED">FAILED</option>
            <option value="RUNNING">RUNNING</option>
          </select>
          <button onClick={handleExport} className="export-btn">
            <Download size={16} />
            EXPORT JSON
          </button>
        </div>
      </header>

      <main className="history-table-container">
        <table className="history-table">
          <thead>
            <tr>
              <th>TASK ID</th>
              <th>INPUT COMMAND</th>
              <th>STATUS</th>
              <th>TIMESTAMP</th>
              <th>ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map(task => (
              <tr key={task.id} onClick={() => setSelectedTask(task)}>
                <td className="id-cell">{task.id}</td>
                <td className="input-cell">{task.input}</td>
                <td className="status-cell">
                   <div className={`status-pill ${task.status.toLowerCase()}`}>{task.status}</div>
                </td>
                <td className="time-cell">{task.created_at}</td>
                <td className="action-cell">
                  <button className="replay-btn" title="Replay Mission" onClick={(e) => { e.stopPropagation(); setIsReplaying(true); setSelectedTask(task); }}>
                    <Play size={14} />
                    REPLAY
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="pagination">
          <button disabled title="Previous Page"><ChevronLeft size={18} /></button>
          <span>PAGE 1 OF 12</span>
          <button title="Next Page"><ChevronRight size={18} /></button>
        </div>
      </main>

      <AnimatePresence>
        {selectedTask && (
          <motion.div 
            initial={{ opacity: 0, x: 300 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 300 }}
            className="task-detail-side"
          >
            <div className="detail-header">
              <h2>TASK DETAILS: {selectedTask.id}</h2>
              <button onClick={() => { setSelectedTask(null); setIsReplaying(false); }} title="Close Details"><X size={20} /></button>
            </div>
            
            <div className="detail-content">
              {isReplaying ? (
                <div className="replay-view">
                   <label>REPLAYING SSE STREAM (READ-ONLY)</label>
                   <div className="log-stream">
                      <div className="log-line">[00:00] MISSION_INITIATED</div>
                      <div className="log-line">[00:02] DAG_PLANNER_START</div>
                      <div className="log-line heartbeat">[00:05] AGENT_HEARTBEAT - Planner: BUSY</div>
                      <div className="log-line">[00:06] WAVE_1_DISPATCHED</div>
                   </div>
                </div>
              ) : (
                <div className="task-info">
                  <div className="info-grp">
                    <label>PROMPT</label>
                    <p>{selectedTask.input}</p>
                  </div>
                  <div className="info-grp">
                    <label>DAG PREVIEW</label>
                    <div className="mini-dag">[DAG Visualization Placeholder]</div>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <style>{`
        .task-history { padding: 2rem; color: #f1f5f9; display: flex; flex-direction: column; height: 100%; overflow: hidden; }
        .history-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
        h1 { font-family: 'JetBrains Mono', monospace; font-size: 1.5rem; letter-spacing: 0.1em; color: #38bdf8; }
        .history-actions { display: flex; gap: 1rem; }
        
        .search-box { background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.1); padding: 0.5rem 1rem; border-radius: 8px; display: flex; align-items: center; gap: 0.75rem; }
        .search-box input { background: transparent; border: none; color: white; outline: none; font-size: 0.85rem; }
        .filter-select { background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.1); color: #94a3b8; border-radius: 8px; padding: 0 1rem; cursor: pointer; outline: none; }
        .export-btn { background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.2); color: #38bdf8; border-radius: 8px; padding: 0.5rem 1rem; font-size: 0.8rem; font-weight: 600; display: flex; align-items: center; gap: 0.5rem; cursor: pointer; transition: all 0.2s ease; }
        .export-btn:hover { background: rgba(56, 189, 248, 0.2); }

        .history-table-container { flex: 1; display: flex; flex-direction: column; overflow: hidden; background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255,255,255,0.05); border-radius: 12px; }
        .history-table { width: 100%; border-collapse: collapse; text-align: left; table-layout: fixed; }
        .history-table th { padding: 1rem 1.5rem; font-size: 0.7rem; color: #64748b; border-bottom: 1px solid rgba(255,255,255,0.05); text-transform: uppercase; letter-spacing: 0.1em; }
        .history-table tr { cursor: pointer; transition: background 0.2s ease; }
        .history-table tr:hover { background: rgba(255,255,255,0.02); }
        .history-table td { padding: 1rem 1.5rem; font-size: 0.9rem; border-bottom: 1px solid rgba(255,255,255,0.02); }
        .id-cell { font-family: 'JetBrains Mono', monospace; color: #38bdf8; }
        .status-pill { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 99px; font-size: 0.7rem; font-weight: bold; font-family: 'JetBrains Mono', monospace; }
        .status-pill.done { background: rgba(16, 185, 129, 0.1); color: #10b981; }
        .status-pill.failed { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
        .status-pill.running { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
        .replay-btn { background: transparent; border: 1px solid rgba(255,255,255,0.1); color: #94a3b8; border-radius: 6px; padding: 0.4rem 0.8rem; font-size: 0.7rem; display: flex; align-items: center; gap: 0.4rem; cursor: pointer; transition: all 0.2s ease; }
        .replay-btn:hover { border-color: #38bdf8; color: #38bdf8; }

        .pagination { display: flex; align-items: center; justify-content: center; gap: 2rem; padding: 1.5rem; border-top: 1px solid rgba(255,255,255,0.05); }
        .pagination span { font-size: 0.75rem; color: #64748b; font-family: 'JetBrains Mono', monospace; }
        .pagination button { background: transparent; border: none; color: #38bdf8; cursor: pointer; transition: opacity 0.2s; }
        .pagination button:disabled { opacity: 0.3; cursor: not-allowed; }

        .task-detail-side { position: fixed; top: 0; right: 0; width: 400px; height: 100vh; background: #0f172a; border-left: 1px solid rgba(56, 189, 248, 0.3); box-shadow: -10px 0 30px rgba(0,0,0,0.5); z-index: 1000; padding: 2rem; display: flex; flex-direction: column; }
        .detail-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }
        .detail-header h2 { font-family: 'JetBrains Mono', monospace; font-size: 1rem; color: #38bdf8; }
        .detail-header button { background: transparent; border: none; color: #64748b; cursor: pointer; }
        
        .info-grp { margin-bottom: 2rem; }
        label { display: block; font-size: 0.7rem; color: #475569; font-weight: 700; margin-bottom: 0.5rem; text-transform: uppercase; }
        .mini-dag { height: 200px; background: #020617; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #1e293b; font-size: 0.8rem; border: 1px dashed rgba(56, 189, 248, 0.2); }
        .log-stream { background: #0a0f1d; padding: 1rem; border-radius: 8px; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #94a3b8; height: 400px; overflow: auto; border: 1px solid rgba(255,255,255,0.05); }
        .log-line { margin-bottom: 0.5rem; }
        .log-line.heartbeat { color: #f59e0b; }
      `}</style>
    </div>
  );
};
