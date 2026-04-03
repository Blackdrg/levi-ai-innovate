import React from 'react';
import { useChatStore } from '../store/useChatStore';

/**
 * Component: MissionAuditor
 * Displays v8 high-fidelity audit results and fidelity scores.
 */
export const MissionAuditor = () => {
  const audit = useChatStore((state) => state.auditResult);
  const fidelity = useChatStore((state) => state.missionFidelity);
  const isStreaming = useChatStore((state) => state.isStreaming);

  if (!audit || isStreaming) return null;

  const getFidelityColor = (score) => {
    if (score >= 0.9) return '#10b981'; // Sovereign Green
    if (score >= 0.8) return '#f59e0b'; // Amber
    return '#ef4444'; // Error Red
  };

  const fidelityColor = getFidelityColor(fidelity);

  return (
    <div className="mission-auditor-container" style={{
      marginTop: '15px',
      padding: '15px',
      background: 'rgba(255, 255, 255, 0.03)',
      borderRadius: '12px',
      border: `1px solid ${fidelityColor}33`,
      backdropFilter: 'blur(10px)',
      animation: 'fadeIn 0.5s ease-out'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: fidelityColor, boxShadow: `0 0 8px ${fidelityColor}` }}></div>
          <span style={{ fontSize: '12px', fontWeight: 'bold', color: '#fff', letterSpacing: '0.5px' }}>MISSION AUDIT COMPLETED</span>
        </div>
        <div style={{ fontSize: '18px', fontWeight: '800', color: fidelityColor }}>
          {Math.round(fidelity * 100)}% <span style={{ fontSize: '10px', fontWeight: '400', opacity: 0.6 }}>FIDELITY</span>
        </div>
      </div>

      {audit.issues && audit.issues.length > 0 && (
        <div style={{ marginBottom: '10px' }}>
          <div style={{ fontSize: '10px', opacity: 0.5, marginBottom: '4px', textTransform: 'uppercase' }}>Observations</div>
          <ul style={{ margin: 0, paddingLeft: '15px', fontSize: '11px', color: 'rgba(255,255,255,0.7)' }}>
            {audit.issues.map((issue, i) => <li key={i}>{issue}</li>)}
          </ul>
        </div>
      )}

      {audit.fix && (
        <div style={{ padding: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '6px', fontSize: '11px' }}>
          <span style={{ color: '#6366f1', fontWeight: 'bold' }}>ADAPTIVE REFINE:</span> {audit.fix}
        </div>
      )}

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}} />
    </div>
  );
};
