import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTelemetryStore } from '../stores/telemetryStore';
import { api } from '../lib/api';
import { ShieldCheck, XCircle, AlertTriangle } from 'lucide-react';

export const HITLModal: React.FC = () => {
  const pulse = useTelemetryStore((state) => state.pulse);
  const [activeEvent, setActiveEvent] = useState<any>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    if (pulse?.type === 'HITL_GATE') {
      setActiveEvent(pulse.payload);
    }
  }, [pulse]);

  const handleAction = async (approved: boolean) => {
    if (isProcessing || !activeEvent) return;
    setIsProcessing(true);
    try {
      if (approved) {
        await api.approveTask(activeEvent.taskId);
      } else {
        // Assume a reject endpoint exists or handle accordingly
        // await api.rejectTask(activeEvent.taskId);
      }
      setActiveEvent(null);
    } catch (err) {
      console.error('HITL Action failed:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <AnimatePresence>
      {activeEvent && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="modal-overlay"
        >
          <motion.div 
            initial={{ scale: 0.9, y: 20 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.9, y: 20 }}
            className="hitl-modal"
          >
            <div className="modal-header">
              <AlertTriangle size={24} className="text-yellow-400" />
              <h2>HUMAN-IN-THE-LOOP INTERVENTION</h2>
            </div>

            <div className="modal-content">
              <p className="task-id">TASK_ID: <span>{activeEvent.taskId}</span></p>
              <div className="reason-pnl">
                <label>REASON FOR GATE</label>
                <div className="reason-text">{activeEvent.reason || 'High-stakes decision point detected.'}</div>
              </div>
              <div className="context-pnl">
                <label>CONTEXT</label>
                <pre>{JSON.stringify(activeEvent.context, null, 2)}</pre>
              </div>
            </div>

            <div className="modal-footer">
              <button 
                onClick={() => handleAction(false)} 
                className="btn-reject"
                disabled={isProcessing}
              >
                <XCircle size={18} />
                REJECT MISSION
              </button>
              <button 
                onClick={() => handleAction(true)} 
                className="btn-approve"
                disabled={isProcessing}
              >
                <ShieldCheck size={18} />
                AUTHORIZE PROGRESSION
              </button>
            </div>
          </motion.div>

          <style>{`
            .modal-overlay {
              position: fixed;
              top: 0;
              left: 0;
              width: 100vw;
              height: 100vh;
              background: rgba(2, 6, 23, 0.9);
              backdrop-filter: blur(8px);
              display: flex;
              align-items: center;
              justify-content: center;
              z-index: 9999;
            }
            .hitl-modal {
              width: 100%;
              max-width: 600px;
              background: #0f172a;
              border: 2px solid #3b82f6;
              box-shadow: 0 0 40px rgba(59, 130, 246, 0.3);
              border-radius: 16px;
              overflow: hidden;
              padding: 2rem;
            }
            .modal-header {
              display: flex;
              align-items: center;
              gap: 1rem;
              margin-bottom: 2rem;
            }
            .modal-header h2 {
              font-family: 'JetBrains Mono', monospace;
              font-size: 1.25rem;
              color: #f1f5f9;
              letter-spacing: 0.1em;
            }
            .modal-content {
              display: flex;
              flex-direction: column;
              gap: 1.5rem;
              margin-bottom: 2.5rem;
            }
            .task-id {
              font-family: 'JetBrains Mono', monospace;
              font-size: 0.8rem;
              color: #64748b;
            }
            .task-id span { color: #38bdf8; }
            
            label {
              display: block;
              font-size: 0.7rem;
              color: #94a3b8;
              font-weight: bold;
              letter-spacing: 0.1em;
              margin-bottom: 0.5rem;
            }
            .reason-text {
              background: rgba(59, 130, 246, 0.1);
              padding: 1rem;
              border-radius: 8px;
              color: #e2e8f0;
              border: 1px solid rgba(59, 130, 246, 0.2);
            }
            pre {
              background: #020617;
              padding: 1rem;
              border-radius: 8px;
              font-family: 'JetBrains Mono', monospace;
              font-size: 0.8rem;
              color: #94a3b8;
              max-height: 200px;
              overflow: auto;
              border: 1px solid rgba(255, 255, 255, 0.05);
            }
            .modal-footer {
              display: flex;
              justify-content: flex-end;
              gap: 1rem;
            }
            button {
              display: flex;
              align-items: center;
              gap: 0.75rem;
              padding: 0.75rem 1.5rem;
              border-radius: 8px;
              font-weight: 600;
              font-family: 'Inter', sans-serif;
              cursor: pointer;
              transition: all 0.2s ease;
              font-size: 0.9rem;
            }
            .btn-reject {
              background: transparent;
              border: 1px solid #ef4444;
              color: #ef4444;
            }
            .btn-reject:hover:not(:disabled) {
              background: rgba(239, 68, 68, 0.1);
            }
            .btn-approve {
              background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
              border: none;
              color: white;
            }
            .btn-approve:hover:not(:disabled) {
              filter: brightness(1.1);
              transform: translateY(-2px);
            }
            button:disabled {
              opacity: 0.5;
              cursor: not-allowed;
            }
          `}</style>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
