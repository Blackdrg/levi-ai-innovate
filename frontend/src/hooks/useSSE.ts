// frontend/src/hooks/useSSE.ts
import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Sovereign v14.2: Production SSE Hook.
 * Features:
 * - Exponential backoff reconnection.
 * - Event-based message dispatch.
 * - Automated cleanup on unmount.
 * - Global/Per-Mission stream switching.
 */

interface SSEOptions {
  missionId?: string;
  onEvent?: (event: string, data: any) => void;
  autoConnect?: boolean;
}

export const useSSE = (options: SSEOptions = {}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<number>(1000);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (eventSourceRef.current) return;

    const token = localStorage.getItem('sovereign_token');
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const endpoint = options.missionId 
      ? `${baseUrl}/api/v1/telemetry/stream/${options.missionId}`
      : `${baseUrl}/api/v1/telemetry/pulse`;

    console.log(`📡 [SSE] Initiating terminal link to ${endpoint}...`);

    const es = new EventSource(`${endpoint}?token=${token}`);

    es.onopen = () => {
      console.log('✅ [SSE] Neuro-link established.');
      setIsConnected(true);
      setError(null);
      reconnectTimeoutRef.current = 1000; // Reset backoff
    };

    es.onerror = (err) => {
      console.error('❌ [SSE] Link failure:', err);
      setIsConnected(false);
      setError('Connection interrupted.');
      es.close();
      eventSourceRef.current = null;

      // Exponential Backoff
      const delay = reconnectTimeoutRef.current;
      reconnectTimeoutRef.current = Math.min(delay * 2, 30000);
      
      console.log(`🔄 [SSE] Retrying in ${delay}ms...`);
      timerRef.current = setTimeout(connect, delay);
    };

    // Generic Message Handler
    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastEvent(data);
        if (options.onEvent) options.onEvent('message', data);
      } catch (e) {
        console.warn('⚠️ [SSE] Malformed packet received:', event.data);
      }
    };

    // Mission Lifecycle Handlers
    const events = [
      'mission_started', 'mission_planned', 'mission_executed', 
      'node_completed', 'mission_complete', 'mission_error', 'fidelity_update'
    ];

    events.forEach(eventType => {
      es.addEventListener(eventType, (event: any) => {
        try {
          const data = JSON.parse(event.data);
          setLastEvent({ type: eventType, ...data });
          if (options.onEvent) options.onEvent(eventType, data);
        } catch (e) {
           console.error(`[SSE] Error parsing ${eventType}:`, e);
        }
      });
    });

    eventSourceRef.current = es;
  }, [options.missionId, options.onEvent]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      console.log('🔌 [SSE] Disconnecting neuro-link...');
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }
    setIsConnected(false);
  }, []);

  useEffect(() => {
    if (options.autoConnect !== false) {
      connect();
    }
    return () => disconnect();
  }, [connect, disconnect, options.autoConnect]);

  return { isConnected, lastEvent, error, reconnect: connect, disconnect };
};
