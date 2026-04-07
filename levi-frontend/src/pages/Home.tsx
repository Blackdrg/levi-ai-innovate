import React from 'react';
import { TaskForm } from '../components/TaskForm';
import { DAGView } from '../components/DAGView';
import { motion } from 'framer-motion';

export const Home: React.FC = () => {
  return (
    <div className="home-dashboard">
      <section className="command-center">
        <TaskForm />
      </section>
      
      <section className="visualization-center">
        <div className="section-header">
           <div className="pulse-dot active" />
           <h2>ACTIVE_SWARM_DAG</h2>
        </div>
        <div className="graph-wrapper">
          <DAGView 
            initialNodes={[
              { id: 'n1', type: 'sovereign', data: { label: 'GoalEngine', status: 'DONE' }, position: { x: 250, y: 0 } },
              { id: 'n2', type: 'sovereign', data: { label: 'DAGPlanner', status: 'RUNNING' }, position: { x: 250, y: 150 } },
              { id: 'n3', type: 'sovereign', data: { label: 'GraphExecutor', status: 'QUEUED' }, position: { x: 100, y: 300 } },
              { id: 'n4', type: 'sovereign', data: { label: 'MemoryManager', status: 'QUEUED' }, position: { x: 400, y: 300 } },
            ]}
            initialEdges={[
              { id: 'e1-2', source: 'n1', target: 'n2' },
              { id: 'e2-3', source: 'n2', target: 'n3' },
              { id: 'e2-4', source: 'n2', target: 'n4' },
            ]}
          />
        </div>
      </section>

      <style>{`
        .home-dashboard { padding: 2rem; display: flex; flex-direction: column; gap: 3rem; }
        .section-header { display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem; padding: 0 1rem; }
        .section-header h2 { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #94a3b8; letter-spacing: 0.1em; }
        .pulse-dot { width: 8px; height: 8px; border-radius: 50%; background: #64748b; }
        .pulse-dot.active { background: #3b82f6; box-shadow: 0 0 10px #3b82f6; animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
        
        .graph-wrapper { 
          background: rgba(15, 23, 42, 0.4); 
          border: 1px solid rgba(255, 255, 255, 0.05); 
          border-radius: 16px; 
          overflow: hidden; 
          box-shadow: 0 20px 50px rgba(0,0,0,0.5); 
        }
      `}</style>
    </div>
  );
};
