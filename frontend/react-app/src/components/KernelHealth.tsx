import React, { useEffect, useState } from 'react';
import { Shield, Zap, Server } from 'lucide-react';
import './KernelHealth.css';

interface KernelStatus {
  status: string;
  vram_used: number;
  vram_quota: number;
  active_agents: number;
  latency: string;
  reason?: string;
}

export const KernelHealth: React.FC = () => {
  const [kernel, setKernel] = useState<KernelStatus | null>(null);

  const fetchKernel = async () => {
    try {
      const res = await fetch('/api/v8/telemetry/kernel');
      const data = await res.json();
      setKernel(data);
    } catch (e) {
      console.error("Kernel fetch failed", e);
    }
  };

  useEffect(() => {
    fetchKernel();
    const interval = setInterval(fetchKernel, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!kernel) return null;

  return (
    <div className={`kernel-health-badge ${kernel.status}`}>
      <div className="badge-main">
        <Server size={14} className="icon" />
        <span className="label">Cognitive Kernel:</span>
        <span className="status-text">{kernel.status.toUpperCase()}</span>
      </div>
      
      {kernel.status === 'online' && (
        <div className="badge-details">
          <div className="detail-item">
            <Zap size={12} /> {kernel.latency}
          </div>
          <div className="detail-item">
            <Shield size={12} /> {kernel.active_agents} Agents
          </div>
          <div className="detail-item">
            VRAM: {(kernel.vram_used / 1024).toFixed(1)}GB / {(kernel.vram_quota / 1024).toFixed(0)}GB
          </div>
        </div>
      )}
      
      {kernel.status === 'fallback' && (
        <div className="fallback-reason">{kernel.reason}</div>
      )}
    </div>
  );
};
