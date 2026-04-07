import React from 'react';
import { motion } from 'framer-motion';
import { ShieldAlert, Fingerprint, Lock, ShieldCheck } from 'lucide-react';

export const SecurityPanel: React.FC = () => {
  const events = [
    { id: '1', type: 'PII_MASKED', details: 'User email masked in logs', ts: '2026-04-07 20:45' },
    { id: '2', type: 'RBAC_DENIAL', details: 'Unauthorized access attempt to /admin', ts: '2026-04-07 20:42' },
    { id: '3', type: 'PROMPT_SHIELD', details: 'Injection attempt blocked: "ignore all instructions"', ts: '2026-04-07 20:38' },
    { id: '4', type: 'EGRESS_DENIAL', details: 'Blocked outgoing request to untrusted domain', ts: '2026-04-07 20:35' },
  ];

  return (
    <div className="security-panel">
      <header className="security-header">
        <Lock className="text-red-400" />
        <h1>SECURITY AUDIT FEED</h1>
      </header>

      <div className="security-grid">
        <div className="stats-row">
          <div className="stat-card">
             <label>PROMPT_SHIELD HITS</label>
             <span className="count">142</span>
          </div>
          <div className="stat-card">
             <label>RBAC_DENIALS</label>
             <span className="count">12</span>
          </div>
          <div className="stat-card">
             <label>PII_EVENTS</label>
             <span className="count">1,024</span>
          </div>
        </div>

        <div className="event-feed">
           <label>REAL-TIME AUDIT STREAM</label>
           <div className="feed-list">
              {events.map(ev => (
                <motion.div 
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  key={ev.id} 
                  className="event-item"
                >
                  <div className="event-tag">{ev.type}</div>
                  <div className="event-details">{ev.details}</div>
                  <div className="event-time">{ev.ts}</div>
                </motion.div>
              ))}
           </div>
        </div>
      </div>

      <style>{`
        .security-panel { padding: 2rem; color: #f1f5f9; }
        .security-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 3rem; }
        h1 { font-family: 'JetBrains Mono', monospace; font-size: 1.5rem; letter-spacing: 0.1em; color: #f87171; }
        
        .stats-row { display: flex; gap: 2rem; margin-bottom: 3rem; }
        .stat-card { flex: 1; background: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.1); padding: 1.5rem; border-radius: 12px; }
        .stat-card label { display: block; font-size: 0.7rem; color: #f87171; font-weight: bold; margin-bottom: 0.5rem; }
        .stat-card .count { font-size: 1.5rem; font-weight: bold; font-family: 'JetBrains Mono', monospace; }

        .event-feed { background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); padding: 1.5rem; border-radius: 12px; }
        .event-feed label { display: block; font-size: 0.7rem; color: #64748b; font-weight: bold; margin-bottom: 1.5rem; }
        .feed-list { display: flex; flex-direction: column; gap: 1rem; }
        .event-item { background: #020617; border: 1px solid rgba(255, 255, 255, 0.03); padding: 1rem; border-radius: 8px; display: grid; grid-template-columns: 150px 1fr 150px; align-items: center; gap: 1rem; }
        .event-tag { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #f87171; font-weight: bold; background: rgba(239, 68, 68, 0.1); padding: 0.25rem 0.5rem; border-radius: 4px; text-align: center; }
        .event-details { font-size: 0.9rem; color: #cbd5e1; }
        .event-time { font-size: 0.7rem; color: #475569; font-family: 'JetBrains Mono', monospace; text-align: right; }
      `}</style>
    </div>
  );
};
