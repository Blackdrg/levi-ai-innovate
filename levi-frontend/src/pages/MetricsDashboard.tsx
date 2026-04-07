import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useTelemetryStore } from '../stores/telemetryStore';
import { Activity, BarChart3, TrendingUp } from 'lucide-react';

const Sparkline = ({ data, color, target }: { data: number[], color: string, target: number }) => {
  const max = Math.max(...data, target * 1.5);
  const min = Math.min(...data, 0);
  const range = max - min;
  const width = 200;
  const height = 60;

  const points = data.map((v, i) => ({
    x: (i / (data.length - 1)) * width,
    y: height - ((v - min) / range) * height
  }));

  const pathContent = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const targetY = height - ((target - min) / range) * height;

  return (
    <div className="sparkline-container">
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <line x1="0" y1={targetY} x2={width} y2={targetY} stroke="rgba(255,255,255,0.1)" strokeDasharray="4 2" />
        <path d={pathContent} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" />
        <circle cx={points[points.length - 1]?.x} cy={points[points.length - 1]?.y} r="3" fill={color} />
      </svg>

      <style>{`
        .sparkline-container { background: rgba(0,0,0,0.2); border-radius: 4px; padding: 4px; overflow: visible; }
      `}</style>
    </div>
  );
};

const MetricCard = ({ title, value, target, history, unit, color }: any) => (
  <div className="metric-card">
    <div className="metric-info">
      <h3>{title}</h3>
      <div className="metric-value">
        <span className="current">{value.toFixed(1)}{unit}</span>
        <span className="target">/ TAR: {target}{unit}</span>
      </div>
    </div>
    <Sparkline data={history} color={color} target={target} />

    <style>{`
      .metric-card {
        background: rgba(15, 23, 42, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 1.5rem;
        border-radius: 12px;
        display: flex;
        flex-direction: column;
        gap: 1rem;
      }
      h3 { font-size: 0.75rem; color: #64748b; font-weight: 700; letter-spacing: 0.05em; }
      .metric-value { display: flex; flex-direction: column; }
      .current { font-size: 1.5rem; font-weight: 700; color: #f1f5f9; font-family: 'JetBrains Mono', monospace; }
      .target { font-size: 0.7rem; color: #475569; font-weight: 600; }
    `}</style>
  </div>
);

export const MetricsDashboard: React.FC = () => {
  const pulse = useTelemetryStore((state) => state.pulse);
  const [metrics, setMetrics] = useState<any>({
    auth: { val: 42, target: 100, hist: [45, 42, 48, 41, 42, 43, 42], color: '#38bdf8' },
    dag: { val: 320, target: 500, hist: [350, 310, 340, 320, 330, 320, 320], color: '#fbbf24' },
    search: { val: 85, target: 150, hist: [90, 82, 88, 85, 87, 85, 85], color: '#10b981' },
    inference: { val: 1200, target: 2000, hist: [1300, 1150, 1250, 1200, 1210, 1200, 1200], color: '#f43f5e' },
    execution: { val: 2400, target: 5000, hist: [2600, 2350, 2500, 2400, 2450, 2400, 2400], color: '#a855f7' },
  });

  useEffect(() => {
     if (pulse?.type === 'METRICS_UPDATE') {
        // Update logic
     }
  }, [pulse]);

  return (
    <div className="metrics-dashboard">
      <header className="dashboard-header">
        <div className="title-pnl">
          <TrendingUp className="text-blue-400" />
          <h1>SYSTEM TELEMETRY v14.0</h1>
        </div>
        <div className="status-badge">SOVEREIGN_OS_ONLINE</div>
      </header>

      <div className="metrics-grid">
        <MetricCard title="AUTH LATENCY" value={metrics.auth.val} target={metrics.auth.target} history={metrics.auth.hist} unit="ms" color={metrics.auth.color} />
        <MetricCard title="DAG GENERATION" value={metrics.dag.val} target={metrics.dag.target} history={metrics.dag.hist} unit="ms" color={metrics.dag.color} />
        <MetricCard title="VECTOR SEARCH" value={metrics.search.val} target={metrics.search.target} history={metrics.search.hist} unit="ms" color={metrics.search.color} />
        <MetricCard title="LOCAL INFERENCE" value={metrics.inference.val} target={metrics.inference.target} history={metrics.inference.hist} unit="ms" color={metrics.inference.color} />
        <MetricCard title="WAVE EXECUTION" value={metrics.execution.val} target={metrics.execution.target} history={metrics.execution.hist} unit="ms" color={metrics.execution.color} />
      </div>

      <style>{`
        .metrics-dashboard { padding: 2rem; color: #f1f5f9; }
        .dashboard-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 3rem; }
        .title-pnl { display: flex; align-items: center; gap: 1rem; }
        h1 { font-family: 'JetBrains Mono', monospace; font-size: 1.5rem; letter-spacing: 0.1em; color: #38bdf8; }
        .status-badge { 
          background: rgba(16, 185, 129, 0.1); 
          border: 1px solid rgba(16, 185, 129, 0.3); 
          color: #10b981; 
          padding: 0.5rem 1rem; 
          border-radius: 99px; 
          font-family: 'JetBrains Mono', monospace; 
          font-size: 0.7rem; 
          font-weight: bold;
        }
        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 2rem;
        }
      `}</style>
    </div>
  );
};
