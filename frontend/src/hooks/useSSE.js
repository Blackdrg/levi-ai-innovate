import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * useSSE Hook
 * Sovereign v14.2: Real-time telemetry stream with client-side filtering.
 * 
 * @param {string} missionId - The ID of the mission to filter for.
 * @param {string} endpoint - The SSE endpoint (default: /api/v1/telemetry/stream).
 */
export function useSSE(missionId, endpoint = '/api/v1/telemetry/stream') {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState('connecting');
  const [error, setError] = useState(null);
  const eventSourceRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
        eventSourceRef.current.close();
    }

    const url = `${endpoint}/${missionId}`;
    console.log(`[SSE] Connecting to ${url}...`);
    
    const es = new EventSource(url, { withCredentials: true });
    eventSourceRef.current = es;

    es.onopen = () => {
      console.log('[SSE] Connection established.');
      setStatus('connected');
      setError(null);
      reconnectAttemptsRef.current = 0;
    };

    es.onerror = (err) => {
      console.error('[SSE] Connection error:', err);
      setStatus('error');
      setError('Connection interrupted');
      es.close();

      // Exponential backoff reconnection
      const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
      reconnectAttemptsRef.current += 1;
      
      console.log(`[SSE] Attempting reconnect in ${delay}ms...`);
      reconnectTimeoutRef.current = setTimeout(connect, delay);
    };

    // Generic Message Handler
    es.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        
        // Client-side filtering: Only keep events for this mission
        // (Note: The server uses per-user channels, so all mission events for this user arrive here)
        if (payload.data && (payload.data.mission_id === missionId || payload.data.request_id === missionId)) {
            setEvents((prev) => [...prev, payload]);
        }
      } catch (e) {
        console.warn('[SSE] Failed to parse event data:', event.data);
      }
    };

    // Typed Handlers
    const handleTypedEvent = (event) => {
        try {
            const data = JSON.parse(event.data);
            // Filtering logic
            if (data.mission_id === missionId || data.request_id === missionId || !data.mission_id) {
                setEvents((prev) => [...prev, { type: event.type, data }]);
            }
        } catch (e) {
            console.error(`[SSE] Error parsing ${event.type} event:`, e);
        }
    };

    es.addEventListener('mission_started', handleTypedEvent);
    es.addEventListener('mission_planned', handleTypedEvent);
    es.addEventListener('mission_executed', handleTypedEvent);
    es.addEventListener('node_completed', handleTypedEvent);
    es.addEventListener('mission_error', handleTypedEvent);
    es.addEventListener('heartbeat', (e) => {
        // Heartbeats can be ignored or used to keep status alive
    });

  }, [missionId, endpoint]);

  useEffect(() => {
    if (missionId) {
        connect();
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [missionId, connect]);

  const clearEvents = () => setEvents([]);

  return { events, status, error, clearEvents };
}
