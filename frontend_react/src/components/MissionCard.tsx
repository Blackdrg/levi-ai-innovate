// frontend_react/src/components/MissionCard.tsx
import * as React from 'react';
import './MissionCard.css';

export interface Mission {
  id: string;
  objective: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'ABORTED';
  progress: number;
  fidelity_score: number;
}

interface MissionCardProps {
  mission: Mission;
}

export const MissionCard: React.FC<MissionCardProps> = ({ mission }) => {
  const progressRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (progressRef.current) {
      progressRef.current.style.width = `${mission.progress * 100}%`;
    }
  }, [mission.progress]);

  return (
    <div className={`mission-card status-${mission.status}`}>
      <div className="card-header">
        <h3>{mission.objective.length > 60 ? mission.objective.substring(0, 57) + "..." : mission.objective}</h3>
        <span className="status-badge">{mission.status}</span>
      </div>

      <div className="card-body">
        <div className="progress-bar-bg">
          <div ref={progressRef} className="progress-bar-fill"></div>
        </div>
        
        <div className="card-footer">
          <span>ID: {mission.id.substring(0, 8)}</span>
          <span className={mission.fidelity_score > 0.8 ? 'fidelity-high' : 'fidelity-metric'}>
            Fidelity: {(mission.fidelity_score * 100).toFixed(1)}%
          </span>
        </div>
      </div>
    </div>
  );
};
