import React, { useState, useEffect } from 'react';
import './MobileDashboard.css';

/**
 * LeviBrain v8.9: Mobile Sovereign Dashboard
 * High-fidelity system oversight for the autonomous cognitive monolith.
 */
const MobileDashboard = () => {
  const [telemetry, setTelemetry] = useState({
    fidelity: 0.85,
    neural_load: 12,
    evolution_progress: 45,
    active_agents: 4,
    status: 'OPTIMAL'
  });

  const [events, setEvents] = useState([
    { id: 1, title: 'Knowledge Sync', detail: 'KnowledgeNexus reconciled 12 facts.', time: '2m ago', type: 'sync' },
    { id: 2, title: 'Memory Pruning', detail: 'Cleared 4.2MB of low-significance nodes.', time: '15m ago', type: 'prune' },
    { id: 3, title: 'Trait Evolution', detail: 'Hybrid Reasoning v2 promoted.', time: '1h ago', type: 'evolution' }
  ]);

  // Connect to real-time evolution pulse
  useEffect(() => {
    const eventSource = new EventSource('/api/v8/telemetry/stream');
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'evolution_update') {
        setTelemetry(prev => ({
          ...prev,
          evolution_progress: data.progress,
          fidelity: data.fidelity
        }));
      }
    };

    return () => eventSource.close();
  }, []);

  return (
    <div className="mobile-dashboard">
      <header className="dash-header">
        <div>
          <p className="vital-label">Sovereign OS</p>
          <h1>LEVI-AI v8.9</h1>
        </div>
        <div className="status-badge">{telemetry.status}</div>
      </header>

      <section className="vitals-grid">
        <div className="vital-card">
          <div className="vital-value" style={{ color: '#00f2fe' }}>
            {(telemetry.fidelity * 100).toFixed(1)}%
          </div>
          <div className="vital-label">Fidelity</div>
        </div>
        <div className="vital-card">
          <div className="vital-value">{telemetry.active_agents}</div>
          <div className="vital-label">Swarm Size</div>
        </div>
        <div className="vital-card">
          <div className="vital-value">{telemetry.neural_load}%</div>
          <div className="vital-label">Neural Load</div>
        </div>
        <div className="vital-card">
          <div className="vital-value">0.4ms</div>
          <div className="vital-label">Latency</div>
        </div>
      </section>

      <section className="evolution-track">
        <div className="track-header">
          <span>Active Evolution Loop</span>
          <span style={{ color: '#00f2fe' }}>{telemetry.evolution_progress}%</span>
        </div>
        <div className="progress-bar-container">
          <div 
            className="progress-bar-fill" 
            style={{ width: `${telemetry.evolution_progress}%` }}
          ></div>
        </div>
        <p className="vital-label">Wisdom Density Threshold: 0.75</p>
      </section>

      <section>
        <h2 style={{ fontSize: '1rem', marginBottom: '15px', fontWeight: '600' }}>Mission Audit Trace</h2>
        <div className="mission-list">
          {events.map(event => (
            <div key={event.id} className="mission-item">
              <div className="mission-icon">
                {event.type === 'sync' && '◈'}
                {event.type === 'prune' && '⟁'}
                {event.type === 'evolution' && '✦'}
              </div>
              <div className="mission-info">
                <h3>{event.title}</h3>
                <p>{event.detail}</p>
              </div>
              <div style={{ marginLeft: 'auto', fontSize: '0.6rem', opacity: 0.3 }}>
                {event.time}
              </div>
            </div>
          ))}
        </div>
      </section>

      <nav className="bottom-nav">
        <div className="nav-item active">
          <span style={{ fontSize: '1.2rem' }}>☷</span>
          <span style={{ fontSize: '0.6rem' }}>Core</span>
        </div>
        <div className="nav-item">
          <span style={{ fontSize: '1.2rem' }}>⬚</span>
          <span style={{ fontSize: '0.6rem' }}>Brain</span>
        </div>
        <div className="nav-item">
          <span style={{ fontSize: '1.2rem' }}>⟴</span>
          <span style={{ fontSize: '0.6rem' }}>Evolution</span>
        </div>
        <div className="nav-item">
          <span style={{ fontSize: '1.2rem' }}>⚙</span>
          <span style={{ fontSize: '0.6rem' }}>Shield</span>
        </div>
      </nav>
    </div>
  );
};

export default MobileDashboard;
