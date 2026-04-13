// frontend_react/src/hooks/usePulse.ts
import { useState, useEffect, useCallback } from 'react';

/**
 * LeviBrain v15.0: Telemetry Pulse Deduplication Hook.
 * Manages the buffer of incoming signals and handles TTL expiry.
 */

interface Pulse {
  mission_id: string;
  event: string;
  data: any;
  timestamp: string;
}

export const usePulse = (maxPulseCount: number = 50) => {
  const [pulses, setPulses] = useState<Pulse[]>([]);

  const addPulse = useCallback((newPulse: Pulse) => {
    setPulses(prev => {
      // Deduplication: Avoid duplicate mission_id + event within 1s window
      if (prev.length > 0) {
        const last = prev[0];
        if (last.mission_id === newPulse.mission_id && 
            last.event === newPulse.event &&
            (new Date(newPulse.timestamp).getTime() - new Date(last.timestamp).getTime()) < 1000) {
          return prev;
        }
      }

      const updated = [newPulse, ...prev];
      if (updated.length > maxPulseCount) {
        return updated.slice(0, maxPulseCount);
      }
      return updated;
    });
  }, [maxPulseCount]);

  // Periodic pruning of very old pulses (e.g., > 10 minutes)
  useEffect(() => {
    const timer = setInterval(() => {
      const tenMinutesAgo = Date.now() - 600000;
      setPulses(prev => prev.filter(p => new Date(p.timestamp).getTime() > tenMinutesAgo));
    }, 60000);

    return () => clearInterval(timer);
  }, []);

  return { pulses, addPulse };
};
