import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ShieldAlert, Fingerprint, Lock, ShieldCheck, RefreshCcw } from 'lucide-react';
import { api } from '../lib/api';

export const SecurityPanel: React.FC = () => {
  const [isRollingBack, setIsRollingBack] = useState(false);
  const [rollbackStatus, setRollbackStatus] = useState<string | null>(null);

  const handleRollback = async () => {
    if (!confirm("CRITICAL ACTION: Are you sure you want to trigger a system-wide emergency rollback? This will revert the entire cluster to the previous stable state.")) return;
    
    setIsRollingBack(true);
    setRollbackStatus("Initiating Repository Dispatch...");
    try {
      const res = await api.triggerRollback();
      if (res.status === 'triggered') {
        setRollbackStatus("SUCCESS: Rollback workflow emitted.");
      } else {
        setRollbackStatus(`FAILED: ${res.message || 'Unknown error'}`);
      }
    } catch (err: any) {
      setRollbackStatus(`ERROR: ${err.message}`);
    } finally {
      setIsRollingBack(false);
      setTimeout(() => setRollbackStatus(null), 5000);
    }
  };

  const events = [
    { id: '1', type: 'PII_MASKED', details: 'User email masked in logs', ts: '2026-04-10 20:45' },
    { id: '2', type: 'RBAC_DENIAL', details: 'Unauthorized access attempt to /admin', ts: '2026-04-10 20:42' },
    { id: '3', type: 'PROMPT_SHIELD', details: 'Injection attempt blocked: "ignore all instructions"', ts: '2026-04-10 20:38' },
    { id: '4', type: 'ROLLBACK_TRIGGER', details: 'System health check failure - Rollback initiated', ts: '2026-04-10 20:35' },
  ];

  return (
    <div className="security-panel font-['Outfit']">
      <header className="security-header">
        <div className="p-3 rounded-xl bg-red-600/10 border border-red-500/20">
          <Lock className="text-red-500" size={24} />
        </div>
        <div>
          <h1 className="text-xl font-black tracking-tight uppercase">Security Audit Feed</h1>
          <span className="text-[10px] uppercase tracking-widest font-black text-red-500/80">Sovereign Fortress Layer</span>
        </div>

        <button 
          onClick={handleRollback}
          disabled={isRollingBack}
          className={`ml-auto flex items-center gap-2 px-6 py-3 rounded-xl font-black text-xs uppercase tracking-widest transition-all duration-300 border ${
            isRollingBack 
              ? 'bg-neutral-900 text-neutral-500 border-white/5 cursor-not-allowed'
              : 'bg-red-600/10 hover:bg-red-600/20 text-red-500 border-red-500/30 active:scale-95'
          }`}
        >
          {isRollingBack ? <RefreshCcw size={16} className="animate-spin" /> : <ShieldAlert size={16} />}
          <span>{isRollingBack ? 'Initiating...' : 'Emergency Rollback'}</span>
        </button>
      </header>

      {rollbackStatus && (
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mb-8 p-4 rounded-xl border font-black text-xs uppercase tracking-widest text-center ${
            rollbackStatus.startsWith('SUCCESS') 
              ? 'bg-green-600/10 text-green-500 border-green-500/20' 
              : 'bg-red-600/10 text-red-500 border-red-500/20'
          }`}
        >
          {rollbackStatus}
        </motion.div>
      )}

      <div className="security-grid">
        <div className="stats-row">
          <div className="stat-card">
             <label>PROMPT_SHIELD HITS</label>
             <span className="count">1,542</span>
          </div>
          <div className="stat-card">
             <label>RBAC_DENIALS</label>
             <span className="count">48</span>
          </div>
          <div className="stat-card">
             <label>SYSTEM_STATE</label>
             <span className="count text-green-500">RESILIENT</span>
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
        .security-header { display: flex; align-items: center; gap: 1.5rem; margin-bottom: 3rem; }
        
        .stats-row { display: flex; gap: 2rem; margin-bottom: 3rem; }
        .stat-card { flex: 1; background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); padding: 1.5rem; border-radius: 16px; }
        .stat-card label { display: block; font-size: 0.7rem; color: #64748b; font-weight: 800; margin-bottom: 0.5rem; letter-spacing: 0.1em; }
        .stat-card .count { font-size: 1.5rem; font-weight: 900; font-family: 'Outfit', sans-serif; letter-spacing: -0.02em; }

        .event-feed { background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); padding: 2rem; border-radius: 20px; }
        .event-feed label { display: block; font-size: 0.7rem; color: #64748b; font-weight: 800; margin-bottom: 2rem; letter-spacing: 0.2em; }
        .feed-list { display: flex; flex-direction: column; gap: 1rem; }
        .event-item { background: rgba(2, 6, 23, 0.4); border: 1px solid rgba(255, 255, 255, 0.03); padding: 1.25rem; border-radius: 12px; display: grid; grid-template-columns: 180px 1fr 150px; align-items: center; gap: 1.5rem; }
        .event-tag { font-family: 'Outfit', sans-serif; font-size: 0.7rem; color: #f87171; font-weight: 900; background: rgba(239, 68, 68, 0.1); padding: 0.4rem 0.75rem; border-radius: 6px; text-align: center; letter-spacing: 0.05em; }
        .event-details { font-size: 0.9rem; color: #cbd5e1; font-weight: 500; }
        .event-time { font-size: 0.75rem; color: #475569; font-weight: 700; text-align: right; }
      `}</style>
    </div>
  );
};
