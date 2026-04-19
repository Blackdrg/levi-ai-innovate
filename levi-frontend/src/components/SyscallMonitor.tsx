import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import leviService from '../api/leviService';

interface SyscallRecord {
  seq: number;
  pid: number;
  event: string;
  id: number;
  timestamp: number;
  status: string;
}

const SyscallMonitor: React.FC = () => {
  const [logs, setLogs] = useState<SyscallRecord[]>([]);
  const [connected, setConnected] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const wsUrl = leviService.getTelemetryWebSocketUrl();
    console.log(`📡 [SyscallMonitor] Connecting to ${wsUrl}`);
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      console.log('✅ [SyscallMonitor] WebSocket Connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // SovereignBroadcaster sends { event: topic, data: { type, payload } }
        const pulse = data.data;
        if (pulse && pulse.type === 'kernel_event') {
          setLogs(prev => [pulse.payload, ...prev].slice(0, 100));
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message', err);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      console.log('❌ [SyscallMonitor] WebSocket Disconnected');
    };

    return () => {
      ws.close();
    };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [logs]);

  return (
    <div className="relative group overflow-hidden rounded-xl border border-white/10 bg-black/40 backdrop-blur-md p-4 h-[400px] flex flex-col font-mono text-xs">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
          <h3 className="text-white/80 font-bold uppercase tracking-widest text-[10px]">HAL-0 SYSCALL MONITOR</h3>
        </div>
        <div className="text-white/40 text-[9px] uppercase tracking-tighter">
          NATIVE ABI-0 FEED // v22.0.0
        </div>
      </div>

      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-1 pr-2 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent"
      >
        <AnimatePresence initial={false}>
          {logs.map((log) => (
            <motion.div
              key={`${log.seq}-${log.timestamp}`}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-start gap-3 py-1 border-b border-white/5 last:border-0 hover:bg-white/5 transition-colors"
            >
              <div className="text-blue-400/80 w-12 text-right">[{log.seq}]</div>
              <div className="text-purple-400 w-10">PID:{log.pid}</div>
              <div className="flex-1 flex items-center gap-2">
                <span className="text-emerald-400 font-bold">{log.event}</span>
                <span className="text-white/20 text-[9px]">(0x{log.id.toString(16).padStart(2, '0')})</span>
              </div>
              <div className="text-white/60 w-16 text-right">TS:{log.timestamp}</div>
              <div className="text-green-500/80 px-1 rounded bg-green-500/10 text-[9px]">OK</div>
            </motion.div>
          ))}
        </AnimatePresence>
        
        {logs.length === 0 && (
          <div className="h-full flex items-center justify-center text-white/20 italic">
            Waiting for kernel telemetry interrupt...
          </div>
        )}
      </div>

      <div className="mt-4 pt-2 border-t border-white/10 flex justify-between items-center text-[9px] text-white/30">
        <div>DCN_ADDR: 192.168.1.100</div>
        <div className="flex gap-4">
           <div>BUFFER: {logs.length}/100</div>
           <div>MODE: NATIVE_ABI</div>
        </div>
      </div>
    </div>
  );
};

export default SyscallMonitor;
