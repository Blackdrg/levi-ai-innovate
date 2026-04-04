import { apiStream } from '../../services/apiClient';
import './MobileDashboard.css';

/**
 * LeviBrain v13.0: Mobile Sovereign Dashboard (React)
 * High-fidelity system oversight for the autonomous cognitive monolith.
 */
const MobileDashboard = () => {
  const [telemetry, setTelemetry] = useState({
    fidelity: 0.98,
    neural_load: 8,
    evolution_progress: 100,
    active_agents: 5,
    status: 'ONLINE'
  });

  const [events, setEvents] = useState([
    { id: 1, title: 'Neural Pulse', detail: 'Sovereign Bridge v13.0.0 established.', time: 'Now', type: 'sync' },
    { id: 2, title: 'Memory Distillation', detail: 'Dreaming Phase successful. Traits crystallized.', time: '15m ago', type: 'evolution' }
  ]);

  // Connect to real-time evolution pulse v4.1
  useEffect(() => {
    // profile=mobile triggers server-side filtering and zlib compression
    const cleanup = apiStream('/api/v8/telemetry/stream?profile=mobile', (data) => {
      if (data.type === 'evolution_update') {
        setTelemetry(prev => ({
          ...prev,
          evolution_progress: data.progress,
          fidelity: data.fidelity
        }));
      } else if (data.type === 'perception') {
          setEvents(prev => [{
              id: Date.now(),
              title: 'Brain Perception',
              detail: `Decision: ${data.data.decision} path elected.`,
              time: 'Now',
              type: 'sync'
          }, ...prev.slice(0, 9)]);
      }
    });

    return () => cleanup();
  }, []);

  return (
    <div className="mobile-dashboard">
      <header className="dash-header">
        <div>
          <p className="vital-label">Sovereign OS</p>
          <h1>LEVI-AI v13.0.0</h1>
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
