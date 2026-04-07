import { useEffect, useCallback, useRef } from 'react';
import { useTelemetryStore } from '../stores/telemetryStore';
import { TelemetryEvent } from '../lib/types';

const SSE_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/telemetry/stream`;

export const useSSE = () => {
  const { setPulse, updateAgent, updateTaskStatus, setCircuitBreaker } = useTelemetryStore();
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (eventSourceRef.current) return;

    const token = localStorage.getItem('sovereign_token');
    const url = new URL(SSE_URL);
    if (token) url.searchParams.append('token', token);

    const es = new EventSource(url.toString());
    eventSourceRef.current = es;

    es.addEventListener('pulse', (event) => {
      try {
        const pulse: TelemetryEvent = JSON.parse(event.data);
        setPulse(pulse);

        // Specific handlers
        if (pulse.type === 'AGENT_HEARTBEAT') updateAgent(pulse.payload.id, pulse.payload);
        if (pulse.type === 'TASK_PROGRESS') updateTaskStatus(pulse.payload.id, pulse.payload.status);
        if (pulse.type === 'CIRCUIT_BREAKER') setCircuitBreaker(pulse.payload.status);
      } catch (err) {
        console.error('Failed to parse pulse:', err);
      }
    });

    es.onerror = (err) => {
      console.error('SSE connection error:', err);
      es.close();
      eventSourceRef.current = null;
      // Reconnect logic
      setTimeout(connect, 5000);
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [setPulse, updateAgent, updateTaskStatus, setCircuitBreaker]);

  useEffect(() => {
    const cleanup = connect();
    return () => {
      cleanup?.();
    };
  }, [connect]);

  return { isConnected: !!eventSourceRef.current };
};
