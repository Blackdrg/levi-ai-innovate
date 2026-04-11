import React, { useEffect, useState } from "react";
import pako from "pako";
import { Zap, Activity, Shield, Cpu, Layers } from "lucide-react";

interface Pulse {
  mission_id: string;
  status: string;
  current_wave: number;
  active_agents: string[];
  cu_consumed: number;
  fidelity_score: number;
  resource_saturation: string;
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function MissionDashboard({ missionId }: { missionId: string }) {
  const [pulse, setPulse] = useState<Pulse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    // Connect to Sovereign v13.0 Pulse (Mobile profile for zlib test)
    // We pass the token in query param because EventSource doesn't support headers
    const url = `${API_BASE}/api/v1/telemetry/stream?mission_id=${missionId}&profile=mobile${token ? `&token=${token}` : ""}`;
    
    const es = new EventSource(url, { withCredentials: true });

    es.onerror = (e) => {
      console.error("[Pulse] Stream disconnect:", e);
      setError("Celestial link lost. Reconnecting...");
    };

    es.onmessage = (e) => {
      try {
        let rawData = e.data;
        let parsedData;

        // 1. Adaptive Pulse v4.1 Decoder (zlib -> base64)
        if (typeof rawData === "string" && !rawData.startsWith("{")) {
            try {
              const binary = atob(rawData);
              const bytes = new Uint8Array(binary.length);
              for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
              
              const decompressed = pako.inflate(bytes, { to: "string" });
              parsedData = JSON.parse(decompressed);
            } catch (err) {
              console.warn("[Pulse] Compressed decode failed, attempting JSON fallback");
              parsedData = JSON.parse(rawData);
            }
        } else {
            parsedData = JSON.parse(rawData);
        }

        if (parsedData) {
          // Adjust for data wrapper if present
          const data = parsedData.event === "mission_update" ? parsedData.data : parsedData;
          setPulse(data);
          setError(null);
        }
      } catch (err) {
        console.error("[Pulse] Critical decode error:", err);
      }
    };

    return () => es.close();
  }, [missionId]);

  const saturationRef = React.useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (saturationRef.current && pulse?.resource_saturation) {
      saturationRef.current.style.width = pulse.resource_saturation;
    }
  }, [pulse?.resource_saturation]);

  if (error) return <div className="text-red-500 text-xs animate-pulse p-4 border border-red-500/20 rounded-lg">{error}</div>;
  if (!pulse) return (
    <div className="flex flex-col items-center gap-4 p-8 glass rounded-2xl border border-white/10">
      <Activity className="text-purple-500 animate-spin-slow" />
      <span className="text-sm font-heading tracking-widest text-white/30 uppercase">Establishing Neural Pulse...</span>
    </div>
  );

  return (
    <div className="p-4 md:p-6 glass rounded-2xl border border-white/10 shadow-2xl relative overflow-hidden group">
      {/* Background Glow */}
      <div className="absolute -top-10 -right-10 w-32 h-32 bg-purple-500/20 blur-3xl rounded-full group-hover:bg-purple-500/30 transition-all duration-700" />
      
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
        <div className="flex flex-col">
          <h3 className="text-[10px] font-heading font-bold tracking-widest text-white/40 uppercase mb-1">Mission Absolute Status</h3>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${pulse.status === "FINALIZED" ? "bg-emerald-500 shadow-[0_0_8px_#10b981]" : "bg-purple-500 animate-pulse shadow-[0_0_8px_#a855f7]"}`} />
            <span className="text-base md:text-lg font-bold text-white tracking-tight">{pulse.status}</span>
          </div>
        </div>
        <div className="px-3 py-1.5 glass-pill rounded-lg border border-white/5 flex items-center gap-2 self-start sm:self-auto">
          <Layers size={14} className="text-purple-400" />
          <span className="text-xs font-mono text-purple-200">Wave {pulse.current_wave}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 xs:grid-cols-2 gap-4 mb-6">
        <div className="p-4 rounded-xl bg-white/5 border border-white/5 hover:border-white/10 transition-colors">
          <div className="flex items-center gap-2 mb-2 text-white/30">
            <Shield size={14} />
            <span className="text-[10px] font-bold uppercase tracking-widest">Fidelity Score</span>
          </div>
          <span className="text-xl md:text-2xl font-heading font-bold text-gradient">
            {(pulse.fidelity_score * 100).toFixed(1)}%
          </span>
        </div>

        <div className="p-4 rounded-xl bg-white/5 border border-white/5 hover:border-white/10 transition-colors">
          <div className="flex items-center gap-2 mb-2 text-white/30">
            <Cpu size={14} />
            <span className="text-[10px] font-bold uppercase tracking-widest">CU Consume</span>
          </div>
          <span className="text-xl md:text-2xl font-heading font-bold text-white">
            {pulse.cu_consumed.toFixed(2)}
          </span>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-widest text-white/20 px-1">
          <span>Active Cognitive Agents</span>
          <span>{pulse.active_agents.length} Nodes</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {pulse.active_agents.map((agent, i) => (
            <div key={i} className="px-2.5 py-1 rounded bg-purple-500/10 border border-purple-500/20 flex items-center gap-1.5 transition-all hover:bg-purple-500/20">
              <Zap size={10} className="text-purple-400 fill-purple-400/20" />
              <span className="text-[10px] font-mono text-purple-300">{agent}</span>
            </div>
          ))}
        </div>
      </div>

      {pulse.resource_saturation && (
         <div className="mt-6 pt-4 border-t border-white/5 flex items-center justify-between">
            <span className="text-[9px] text-white/20 uppercase tracking-tighter">Resource Saturation</span>
            <div className="h-1 w-24 sm:w-32 bg-white/5 rounded-full overflow-hidden">
               <div ref={saturationRef} className="h-full bg-gradient-to-r from-purple-500 to-emerald-500 transition-all duration-1000" />
            </div>
         </div>
      )}
    </div>
  );
}
