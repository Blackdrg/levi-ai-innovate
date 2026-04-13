// frontend_react/src/contexts/NeuralContext.tsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

/**
 * Global state management for LEVI-AI dashboard.
 * Uses Context API + custom pulse stream integration.
 */

interface Mission {
  id: string;
  objective: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'ABORTED';
  progress: number;
  fidelity_score: number;
  graph?: {
    nodes: any[];
    edges: any[];
    waves: number;
  };
}

interface TelemetryPulse {
  mission_id: string;
  status: string;
  event: string;
  data: any;
  timestamp: string;
}

interface NeuralContextType {
  activeMissions: Mission[];
  telemetryHistory: TelemetryPulse[];
  globalLoad: number;  
  updateMission: (id: string, update: Partial<Mission>) => void;
  addMission: (mission: Mission) => void;
}

const NeuralContext = createContext<NeuralContextType | undefined>(undefined);

export const NeuralProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [activeMissions, setActiveMissions] = useState<Mission[]>([]);
  const [telemetryHistory, setTelemetryHistory] = useState<TelemetryPulse[]>([]);
  const [globalLoad, setGlobalLoad] = useState(0);

  useEffect(() => {
    const token = localStorage.getItem('sovereign_token');
    if (!token) return;

    const eventSource = new EventSource(`/api/v8/telemetry/stream?token=${token}`);

    // Fixed: backend emits 'pulse' event, not 'mission_pulse'
    eventSource.addEventListener('pulse', (e) => {
      try {
        const pulse = JSON.parse(e.data) as TelemetryPulse;
        
        // 1. Update Telemetry History (Last 15 pulses)
        setTelemetryHistory(prev => [pulse, ...prev].slice(0, 15));
        
        // 2. Update mission status if applicable
        if (pulse.mission_id) {
          setActiveMissions(prev =>
            prev.map(m => m.id === pulse.mission_id ? { ...m, status: (pulse.data?.status || pulse.status) as any } : m)
          );
        }
      } catch (err) {
        console.error("Pulse parsing error:", err);
      }
    });

    eventSource.addEventListener('system_load', (e) => {
      try {
        const data = JSON.parse(e.data);
        setGlobalLoad(data.load || 0);
      } catch (err) {
        console.error("Load parsing error:", err);
      }
    });

    eventSource.onerror = (err) => {
      console.error("SSE Connection failed:", err);
      eventSource.close();
    };

    return () => eventSource.close();
  }, []);

  const updateMission = useCallback((id: string, update: Partial<Mission>) => {
    setActiveMissions(prev => prev.map(m => m.id === id ? { ...m, ...update } : m));
  }, []);

  const addMission = useCallback((mission: Mission) => {
    setActiveMissions(prev => [mission, ...prev]);
  }, []);

  return (
    <NeuralContext.Provider value={{ activeMissions, telemetryHistory, globalLoad, updateMission, addMission }}>
      {children}
    </NeuralContext.Provider>
  );
};

export const useNeuralContext = () => {
  const context = useContext(NeuralContext);
  if (context === undefined) {
    throw new Error('useNeuralContext must be used within a NeuralProvider');
  }
  return context;
};
