import { useEffect, useRef } from 'react'
import { CheckCircle, AlertOctagon, Brain, Cpu, Database, Timer } from 'lucide-react'

const ICON_MAP = {
  perception: <Brain className="w-4 h-4" />,
  memory:     <Database className="w-4 h-4" />,
  planning:   <Cpu className="w-4 h-4" />,
  execution:  <Timer className="w-4 h-4" />,
  audit:      <CheckCircle className="w-4 h-4" />,
  final:      <CheckCircle className="w-4 h-4" />,
  error:      <AlertOctagon className="w-4 h-4" />,
}

export default function StreamEventLog({ events, eventColors }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events])

  if (!events.length) return (
    <div className="flex-1 flex flex-col items-center justify-center text-neutral-600 gap-4 glass rounded-2xl border-dashed border-2 border-neutral-800/50">
      <Timer className="w-12 h-12 opacity-20" />
      <span className="text-sm font-medium tracking-wide uppercase">Awaiting Mission Protocol</span>
    </div>
  )

  return (
    <div className="flex-1 overflow-y-auto rounded-2xl bg-neutral-950/40 
                    border border-neutral-900 p-6 font-mono text-[13px] space-y-4 custom-scrollbar shadow-inner">
      {events.map((ev, i) => (
        <div key={i} className="flex gap-4 group animate-fade-in">
          <div className="flex flex-col items-center gap-1 shrink-0">
            <div className={`p-2 rounded-lg bg-neutral-900 border border-white/5 ${eventColors[ev.type] || 'text-white'}`}>
              {ICON_MAP[ev.type] || <Cpu className="w-4 h-4" />}
            </div>
            <div className="w-[1px] h-full bg-neutral-900"></div>
          </div>
          
          <div className="flex-1 py-1">
            <div className="flex items-center gap-3 mb-1">
              <span className={`uppercase font-bold tracking-tighter ${eventColors[ev.type] || 'text-white'}`}>
                {ev.type}
              </span>
              <span className="text-[10px] text-neutral-600 font-bold">
                {new Date(ev.timestamp).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
            </div>
            <div className="text-neutral-400 leading-relaxed bg-neutral-900/30 p-2 rounded-lg border border-white/5">
              {typeof ev.data === 'string' ? ev.data : JSON.stringify(ev.data, null, 2)}
            </div>
          </div>
        </div>
      ))}
      <div ref={bottomRef} className="h-4" />
    </div>
  )
}
