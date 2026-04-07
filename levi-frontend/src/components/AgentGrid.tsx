import React from 'react';
import { useTelemetryStore } from '../stores/telemetryStore';
import { AgentStatus } from '../lib/types';
import { motion } from 'framer-motion';
import { Cpu, Activity, RefreshCw } from 'lucide-react';

const AgentCard = ({ agent }: { agent: AgentStatus }) => {
  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ y: -4, borderColor: '#38bdf8' }}
      className={`agent-card ${agent.status.toLowerCase()}`}
    >
      <div className="agent-header">
        <Cpu size={18} className="agent-icon" />
        <span className="agent-category">{agent.category}</span>
        <div className={`status-dot ${agent.status.toLowerCase()}`} />
      </div>

      <div className="agent-content">
        <div className="current-task">
          <label>CURRENT TASK</label>
          <span>{agent.currentTask || 'IDLE'}</span>
        </div>

        <div className="agent-stats">
          <div className="stat">
            <Activity size={14} />
            <span>{agent.latency_ms}ms</span>
          </div>
          <div className="stat">
            <RefreshCw size={14} />
            <span>{agent.retryCount} Retries</span>
          </div>
        </div>
      </div>

      <style>{`
        .agent-card {
          background: rgba(15, 23, 42, 0.4);
          backdrop-filter: blur(8px);
          border: 1px solid rgba(255, 255, 255, 0.05);
          border-radius: 12px;
          padding: 1rem;
          transition: all 0.2s ease;
          position: relative;
          overflow: hidden;
        }
        .agent-card::after {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 4px;
          height: 100%;
          background: #64748b;
        }
        .agent-card.busy::after { background: #3b82f6; }
        .agent-card.offline::after { background: #ef4444; }

        .agent-header {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          margin-bottom: 1rem;
        }
        .agent-icon { color: #94a3b8; }
        .agent-category {
          font-weight: 600;
          color: #f1f5f9;
          font-family: 'JetBrains Mono', monospace;
        }
        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          margin-left: auto;
          background: #64748b;
        }
        .status-dot.busy {
          background: #3b82f6;
          box-shadow: 0 0 8px #3b82f6;
        }
        .status-dot.offline { background: #ef4444; }

        .agent-content {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        .current-task label {
          display: block;
          font-size: 0.65rem;
          color: #64748b;
          letter-spacing: 0.05em;
          margin-bottom: 0.25rem;
        }
        .current-task span {
          display: block;
          font-size: 0.9rem;
          color: #e2e8f0;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .agent-stats {
          display: flex;
          gap: 1rem;
        }
        .stat {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.75rem;
          color: #94a3b8;
          font-family: 'JetBrains Mono', monospace;
        }
      `}</style>
    </motion.div>
  );
};

export const AgentGrid: React.FC = () => {
  const agents = useTelemetryStore((state) => Object.values(state.agents));

  return (
    <div className="agent-grid">
      {agents.length === 0 ? (
        <div className="empty-agents">Awaiting swarm connection...</div>
      ) : (
        agents.map((agent) => <AgentCard key={agent.id} agent={agent} />)
      )}

      <style>{`
        .agent-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
          gap: 1.5rem;
          padding: 1.5rem;
        }
        .empty-agents {
          grid-column: 1 / -1;
          text-align: center;
          color: #64748b;
          padding: 3rem;
          font-family: 'JetBrains Mono', monospace;
        }
      `}</style>
    </div>
  );
};
