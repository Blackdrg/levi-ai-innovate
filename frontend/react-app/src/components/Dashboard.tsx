/// <reference types="react" />
// frontend_react/src/components/Dashboard.tsx
import * as React from 'react';

import { useNeuralContext } from '../contexts/NeuralContext';
import { MissionCard, Mission } from './MissionCard';
import { PeeringStatus } from './PeeringStatus';
import { Zap, Activity, Cpu, Binary } from 'lucide-react';
import { MissionCreator } from './MissionCreator';
import EvolutionDashboard from './EvolutionDashboard';
import { KernelHealth } from './KernelHealth';


export const Dashboard: React.FC = () => {
  const { activeMissions, globalLoad, telemetryHistory, graduationScore, dcnStatus } = useNeuralContext();
  const [activeTab, setActiveTab] = React.useState<'missions' | 'evolution'>('missions');


  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="header-top">
          <div className="title-section">
            <h1>LEVI-AI Sovereign OS</h1>
            <div className={`graduation-badge ${graduationScore > 0.95 ? 'graduated' : 'hardening'}`}>
              <style>{`.badge-ring { --score: ${graduationScore}; }`}</style>
              <div className="badge-ring"></div>
              <span className="badge-text">{(graduationScore * 100).toFixed(1)}% Sovereign</span>
            </div>
          </div>
          <div className="system-status">
            <div className={`status-pill ${dcnStatus === 'online' ? 'status-online' : 'status-standalone'}`}>
              <Activity size={12} /> {dcnStatus.toUpperCase()}
            </div>
          </div>
        </div>
        
        <div className="global-metrics">
          <div className="metric-item">
            <span className="metric-value">{(globalLoad * 100).toFixed(1)}%</span>
            <span className="metric-label"><Cpu size={14} /> VRAM Load</span>
          </div>
          <div className="metric-item">
            <span className="metric-value">{activeMissions.length}</span>
            <span className="metric-label"><Zap size={14} /> Active Missions</span>
          </div>
          <KernelHealth />
          <div className="nav-tabs">
            <button 
              onClick={() => setActiveTab('missions')} 
              className={`nav-btn ${activeTab === 'missions' ? 'active' : ''}`}
            >
              Mission Control
            </button>
            <button 
              onClick={() => setActiveTab('evolution')} 
              className={`nav-btn ${activeTab === 'evolution' ? 'active' : ''}`}
            >
              Revolution Engine
            </button>
          </div>
          <PeeringStatus />
        </div>
      </header>

      <main>
        {activeTab === 'missions' ? (
          <>
            <MissionCreator />
            <section className="mission-grid">
              {activeMissions.length > 0 ? (
                activeMissions.map((mission: Mission) => (
                  <MissionCard key={mission.id} mission={mission} />
                ))
              ) : (
                <div className="no-missions">
                  <p>Pulse detected. Awaiting mission dispatch...</p>
                </div>
              )}
            </section>

            <section className="telemetry-wall">
              <h2><Activity size={18} className="telemetry-icon" /> Cognitive Telemetry Stream</h2>
              <div className="telemetry-stream">
                {telemetryHistory.length > 0 ? (
                  telemetryHistory.map((pulse: any, idx: number) => (
                    <div key={`${pulse.mission_id}-${pulse.timestamp}-${idx}`} className="pulse-item">

                      <span className="pulse-time">[{new Date(pulse.timestamp).toLocaleTimeString()}]</span>
                      <span className="pulse-mission">{pulse.mission_id ? `Mission ${pulse.mission_id.substring(0,8)}` : 'System'}</span>: 
                      <span className="pulse-event">{pulse.event}</span>
                      {pulse.data && <pre className="pulse-data">{JSON.stringify(pulse.data, null, 2)}</pre>}
                    </div>
                  ))
                ) : (
                  <p className="pulse-placeholder">Awaiting neural signals from swarm...</p>
                )}
              </div>
            </section>
          </>
        ) : (
          <EvolutionDashboard />
        )}
      </main>

    </div>
  );
};
