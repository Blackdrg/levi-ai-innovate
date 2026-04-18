import { useState, useEffect, useCallback } from 'react';
import leviService, { PulseData, EvolutionMetrics } from '../api/leviService';

export function useLeviPulse() {
  const [pulse, setPulse] = useState<PulseData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPulse = useCallback(async () => {
    try {
      const data = await leviService.getPulse();
      setPulse(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPulse();
    const interval = setInterval(fetchPulse, 5000);
    return () => clearInterval(interval);
  }, [fetchPulse]);

  return { pulse, loading, error, refetch: fetchPulse };
}

export function useLeviMissions() {
  const [missions, setMissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await leviService.listMissions();
      setMissions(data);
    } catch (err) {
      console.error('Failed to list missions', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { missions, loading, refresh };
}

export function useEvolution() {
  const [metrics, setMetrics] = useState<EvolutionMetrics | null>(null);
  const [rules, setRules] = useState<any[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const [m, r] = await Promise.all([
          leviService.getEvolutionMetrics(),
          leviService.getGraduatedPatterns()
        ]);
        setMetrics(m);
        setRules(r);
      } catch (err) {
        console.error('Evolution data fetch failed', err);
      }
    };
    load();
  }, []);

  return { metrics, rules };
}

export function useSwarm() {
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await leviService.getSwarm();
      setAgents(data);
    } catch (err) {
      console.error('Swarm fetch failed', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 10000);
    return () => clearInterval(interval);
  }, [refresh]);

  return { agents, loading, refresh };
}

export function useTelemetryPulse() {
  const [pulse, setPulse] = useState<any>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await leviService.getTelemetryPulse();
        setPulse(data);
      } catch (err) {
        console.error('Telemetry pulse failed', err);
      }
    };
    fetch();
    const interval = setInterval(fetch, 2000);
    return () => clearInterval(interval);
  }, []);

  return pulse;
}
