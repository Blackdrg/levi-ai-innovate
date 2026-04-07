import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle, CheckCircle, Info, X, Zap } from 'lucide-react';

interface Toast {
  id: string;
  type: 'success' | 'error' | 'info' | 'ratelimit';
  message: string;
  duration?: number;
  resetTimer?: number;
}

export const ToastContainer: React.FC = () => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  // Globally exposed function to add toasts
  useEffect(() => {
    (window as any).addSovereignToast = (toast: Omit<Toast, 'id'>) => {
      const id = Math.random().toString(36).substr(2, 9);
      setToasts(prev => [...prev, { ...toast, id }]);
      
      if (toast.duration !== 0) {
        setTimeout(() => {
          removeToast(id);
        }, toast.duration || 5000);
      }
    };
  }, []);

  const removeToast = (id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  return (
    <div className="toast-container">
      <AnimatePresence>
        {toasts.map(toast => (
          <motion.div 
            key={toast.id}
            initial={{ opacity: 0, x: 20, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 20, scale: 0.9 }}
            layout
            className={`toast ${toast.type}`}
          >
            <div className="toast-icon">
               {toast.type === 'success' && <CheckCircle size={18} />}
               {toast.type === 'error' && <AlertCircle size={18} />}
               {toast.type === 'info' && <Info size={18} />}
               {toast.type === 'ratelimit' && <Zap size={18} className="text-yellow-400" />}
            </div>
            
            <div className="toast-body">
               <p className="toast-msg">{toast.message}</p>
               {toast.type === 'ratelimit' && toast.resetTimer && (
                 <div className="reset-countdown">
                    <span className="mono">COOLING_DOWN: {toast.resetTimer}s</span>
                    <div className="progress-bar">
                       <motion.div 
                         initial={{ width: '100%' }} animate={{ width: '0%' }}
                         transition={{ duration: toast.resetTimer, ease: "linear" }}
                         className="progress"
                       />
                    </div>
                 </div>
               )}
            </div>

            <button onClick={() => removeToast(toast.id)} className="close-btn"><X size={14} /></button>
          </motion.div>
        ))}
      </AnimatePresence>

      <style>{`
        .toast-container { position: fixed; bottom: 2rem; right: 2rem; z-index: 10000; display: flex; flex-direction: column; gap: 0.75rem; width: 320px; }
        .toast {
          background: rgba(15, 23, 42, 0.9); backdrop-filter: blur(8px);
          border: 1px solid rgba(255,255,255,0.1); border-radius: 10px;
          padding: 1rem; display: flex; align-items: flex-start; gap: 0.75rem;
          box-shadow: 0 10px 25px rgba(0,0,0,0.4);
        }
        .toast.error { border-left: 4px solid #ef4444; }
        .toast.success { border-left: 4px solid #10b981; }
        .toast.ratelimit { border-left: 4px solid #fbbf24; }
        
        .toast-icon { margin-top: 2px; }
        .toast.error .toast-icon { color: #ef4444; }
        .toast.success .toast-icon { color: #10b981; }
        
        .toast-body { flex: 1; min-width: 0; }
        .toast-msg { font-size: 0.85rem; color: #f1f5f9; font-weight: 500; line-height: 1.4; }
        .close-btn { background: transparent; border: none; color: #64748b; cursor: pointer; padding: 0; margin-top: 2px; }
        .close-btn:hover { color: #f1f5f9; }

        .reset-countdown { margin-top: 0.75rem; }
        .reset-countdown span { font-size: 0.65rem; color: #fbbf24; font-weight: bold; display: block; margin-bottom: 0.4rem; letter-spacing: 0.05em; }
        .progress-bar { height: 4px; background: rgba(251, 191, 36, 0.1); border-radius: 2px; overflow: hidden; }
        .progress { height: 100%; background: #fbbf24; }
      `}</style>
    </div>
  );
};
