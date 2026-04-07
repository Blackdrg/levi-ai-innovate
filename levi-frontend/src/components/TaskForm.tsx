import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Zap, Clock } from 'lucide-react';
import { api } from '../lib/api';
import { useTelemetryStore } from '../stores/telemetryStore';

export const TaskForm: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [latency, setLatency] = useState<number | null>(null);
  const { updateTaskStatus } = useTelemetryStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || isSubmitting) return;

    setIsSubmitting(true);
    const startTime = performance.now();

    try {
      // Optimistic update
      const tempId = `temp-${Date.now()}`;
      updateTaskStatus(tempId, 'QUEUED');

      const response = await api.submitTask(prompt);
      const endTime = performance.now();
      setLatency(endTime - startTime);
      
      setPrompt('');
      // The SSE hook will handle the real status updates via taskStatuses store
    } catch (err) {
      console.error('Task submission failed:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="task-form-container"
    >
      <form onSubmit={handleSubmit} className="task-form">
        <div className="input-wrapper">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Command the swarm (e.g. 'Generate a DCN network diagram' or 'Audit memory bank 4')..."
            className="task-input"
            disabled={isSubmitting}
          />
          <button type="submit" className="submit-button" disabled={isSubmitting}>
            {isSubmitting ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
              >
                <Zap size={20} className="text-yellow-400" />
              </motion.div>
            ) : (
              <Send size={20} />
            )}
          </button>
        </div>

        <AnimatePresence>
          {latency !== null && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="latency-badge"
            >
              <Clock size={14} />
              <span>DAG Gen Latency: {latency.toFixed(0)}ms</span>
              {latency < 500 && <span className="target-reached">TARGET REACHED</span>}
            </motion.div>
          )}
        </AnimatePresence>
      </form>

      <style>{`
        .task-form-container {
          width: 100%;
          max-width: 800px;
          margin: 0 auto;
          padding: 1rem;
        }
        .task-form {
          position: relative;
          background: rgba(15, 23, 42, 0.6);
          backdrop-filter: blur(12px);
          border: 1px solid rgba(56, 189, 248, 0.2);
          border-radius: 12px;
          padding: 0.5rem;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        }
        .input-wrapper {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        .task-input {
          flex: 1;
          background: transparent;
          border: none;
          color: #f1f5f9;
          font-size: 1rem;
          padding: 0.75rem 1rem;
          outline: none;
        }
        .task-input::placeholder {
          color: rgba(148, 163, 184, 0.6);
        }
        .submit-button {
          background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);
          color: white;
          border: none;
          border-radius: 8px;
          width: 42px;
          height: 42px;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        .submit-button:hover {
          filter: brightness(1.1);
          transform: translateY(-1px);
        }
        .submit-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .latency-badge {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 1rem;
          font-size: 0.75rem;
          color: #94aeac;
          font-family: 'JetBrains Mono', monospace;
        }
        .target-reached {
          color: #10b981;
          font-weight: bold;
          margin-left: 0.5rem;
        }
      `}</style>
    </motion.div>
  );
};
