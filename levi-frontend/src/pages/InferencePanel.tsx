import * as React from 'react';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Cpu, HardDrive, Cpu as Gpu, Cloud, ToggleLeft, ToggleRight } from 'lucide-react';
import { api } from '../lib/api';

const VRAMGauge = ({ value, max }: { value: number, max: number }) => {
  const percentage = (value / max) * 100;
  const color = percentage > 85 ? '#ef4444' : percentage > 60 ? '#f59e0b' : '#10b981';

  return (
    <div className="vram-gauge">
      <div className="gauge-header">
        <span>VRAM USAGE</span>
        <span>{value}GB / {max}GB</span>
      </div>
      <div className="gauge-track">
        <motion.div 
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          className="gauge-progress"
          style={{ background: color, boxShadow: `0 0 12px ${color}66` }}
        />
      </div>

      <style>{`
        .vram-gauge { width: 100%; margin-bottom: 2rem; }
        .gauge-header {
          display: flex;
          justify-content: space-between;
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.7rem;
          color: #94a3b8;
          margin-bottom: 0.5rem;
        }
        .gauge-track {
          height: 8px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 4px;
          overflow: hidden;
        }
        .gauge-progress { height: 100%; border-radius: 4px; transition: width 0.5s ease; }
      `}</style>
    </div>
  );
};

const SemaphoreSlot = ({ active }: { active: boolean }) => (
  <div className={`semaphore-slot ${active ? 'active' : ''}`}>
    <style>{`
      .semaphore-slot {
        width: 12px;
        height: 24px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 3px;
        transition: all 0.3s ease;
      }
      .semaphore-slot.active {
        background: #3b82f6;
        border-color: #60a5fa;
        box-shadow: 0 0 10px rgba(59, 130, 246, 0.4);
      }
    `}</style>
  </div>
);

export const InferencePanel: React.FC = () => {
  const [hybridMode, setHybridMode] = useState(false);
  const [status, setStatus] = useState<any>(null);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await api.getInferenceStatus();
        setStatus(data);
      } catch (err) {
        // Mocking for preview
        setStatus({
          currentModel: 'Llama 3.3 70B (Hybrid)',
          vram: { used: 18.4, total: 24 },
          semaphores: [true, true, false, false],
          cloudBurst: false
        });
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!status) return <div className="loading">Initializing Neural Engine...</div>;

  return (
    <div className="inference-panel">
      <h1>INFERENCE CONTROL</h1>

      <div className="control-grid">
        <section className="engine-card">
          <div className="card-header">
            <Gpu size={20} className="text-blue-400" />
            <h2>NEURAL ENGINE STATUS</h2>
          </div>
          
          <VRAMGauge value={status.vram.used} max={status.vram.total} />

          <div className="model-info">
            <label>ACTIVE MODEL</label>
            <span className="model-name">{status.currentModel}</span>
          </div>

          <div className="semaphore-pnl">
            <label>WAVE SEMAPHORES (SLOTS 0-3)</label>
            <div className="slots">
              {status.semaphores.map((s: boolean, i: number) => <SemaphoreSlot key={i} active={s} />)}
            </div>
          </div>
        </section>

        <section className="mode-card">
            <div className="card-header">
                <Cloud size={20} className="text-purple-400" />
                <h2>ROUTING POLICY</h2>
            </div>

            <div className="toggle-row">
                <div className="toggle-label">
                    <span>HYBRID CLOUD BURST</span>
                    <p>Auto-offload L4 tasks to Replicate/GCP when local VRAM &gt; 90%</p>
                </div>
                <button onClick={() => setHybridMode(!hybridMode)} className="toggle-btn">
                    {hybridMode ? <ToggleRight size={32} className="text-blue-500" /> : <ToggleLeft size={32} className="text-slate-600" />}
                </button>
            </div>

            <div className={`burst-status ${status.cloudBurst ? 'active' : ''}`}>
                <div className="pulse-dot" />
                <span>CLOUD BURST: {status.cloudBurst ? 'ACTIVE' : 'STANDBY'}</span>
            </div>
        </section>
      </div>

      <style>{`
        .inference-panel {
          padding: 2rem;
          color: #f1f5f9;
        }
        .loading { padding: 3rem; text-align: center; color: #64748b; font-family: 'JetBrains Mono', monospace; }
        h1 { font-family: 'JetBrains Mono', monospace; font-size: 1.5rem; letter-spacing: 0.1em; color: #38bdf8; margin-bottom: 2rem; }
        .control-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
          gap: 2rem;
        }
        .engine-card, .mode-card {
          background: rgba(15, 23, 42, 0.4);
          border: 1px solid rgba(255, 255, 255, 0.05);
          border-radius: 16px;
          padding: 2rem;
          backdrop-filter: blur(12px);
        }
        .card-header { display: flex; align-items: center; gap: 1rem; margin-bottom: 2rem; }
        .card-header h2 { font-size: 0.9rem; font-weight: 600; color: #94a3b8; letter-spacing: 0.05em; }
        
        .model-info, .semaphore-pnl { margin-bottom: 2rem; }
        label { display: block; font-size: 0.65rem; color: #64748b; font-weight: bold; letter-spacing: 0.1em; margin-bottom: 0.75rem; }
        .model-name { font-size: 1.25rem; font-weight: 700; color: #f1f5f9; display: block; font-family: 'JetBrains Mono', monospace; }
        .slots { display: flex; gap: 0.75rem; }
        
        .toggle-row { display: flex; align-items: center; justify-content: space-between; gap: 2rem; margin-bottom: 2rem; }
        .toggle-label span { display: block; font-weight: 600; color: #f1f5f9; margin-bottom: 0.25rem; }
        .toggle-label p { font-size: 0.8rem; color: #64748b; max-width: 250px; }
        .toggle-btn { background: transparent; border: none; cursor: pointer; padding: 0; outline: none; }
        
        .burst-status {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          background: #020617;
          padding: 1rem;
          border-radius: 8px;
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.8rem;
          color: #64748b;
        }
        .burst-status.active { color: #d8b4fe; border: 1px solid #c084fc44; }
        .pulse-dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
        .burst-status.active .pulse-dot { animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.5); opacity: 0.5; } 100% { transform: scale(1); opacity: 1; } }
      `}</style>
    </div>
  );
};
