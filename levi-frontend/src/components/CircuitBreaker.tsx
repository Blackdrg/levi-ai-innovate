import React, { useEffect } from 'react';
import { useTelemetryStore } from '../stores/telemetryStore';
import { api } from '../lib/api';
import { Activity, ShieldAlert, ShieldCheck, ShieldOff } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export const CircuitBreaker: React.FC = () => {
  const status = useTelemetryStore((state) => state.circuitBreaker);
  const { setCircuitBreaker } = useTelemetryStore();

  useEffect(() => {
    const pollHealth = async () => {
      try {
        const health = await api.checkHealth();
        if (health.status === 'online') {
          setCircuitBreaker('CLOSED');
        } else {
          setCircuitBreaker('OPEN');
        }
      } catch (err) {
        setCircuitBreaker('OPEN');
      }
    };

    pollHealth();
    const interval = setInterval(pollHealth, 5000);
    return () => clearInterval(interval);
  }, [setCircuitBreaker]);

  const getStatusConfig = () => {
    switch (status) {
      case 'CLOSED':
        return { icon: <ShieldCheck size={14} />, label: 'SYSTEM CLOSED (STABLE)', color: '#10b981', bg: 'rgba(16, 185, 129, 0.1)' };
      case 'OPEN':
        return { icon: <ShieldAlert size={14} />, label: 'SYSTEM OPEN (FAULT)', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)' };
      case 'HALF-OPEN':
        return { icon: <ShieldOff size={14} />, label: 'HALF-OPEN (TESTING)', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)' };
      default:
        return { icon: <Activity size={14} />, label: 'UNKNOWN', color: '#64748b', bg: 'rgba(100, 116, 139, 0.1)' };
    }
  };

  const config = getStatusConfig();

  return (
    <motion.div 
      animate={{ opacity: 1, scale: 1 }}
      initial={{ opacity: 0, scale: 0.9 }}
      className="circuit-breaker-chip"
      style={{ color: config.color, background: config.bg, borderColor: `${config.color}33` }}
    >
      {config.icon}
      <span>{config.label}</span>

      <style>{`
        .circuit-breaker-chip {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.4rem 0.8rem;
          border-radius: 99px;
          border: 1px solid;
          font-family: 'JetBrains Mono', monospace;
          font-size: 0.65rem;
          font-weight: 700;
          letter-spacing: 0.05em;
          white-space: nowrap;
          box-shadow: 0 4px 12px rgba(0,0,0,0.2);
          transition: all 0.3s ease;
        }
      `}</style>
    </motion.div>
  );
};
