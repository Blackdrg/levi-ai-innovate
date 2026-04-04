import { useState } from 'react'
import { useMissionStore } from '../stores/missionStore'
import { useSSEMission } from '../hooks/useSSEMission'
import StreamEventLog from './StreamEventLog'

const EVENT_COLORS = {
  perception: 'text-purple-400',
  memory:     'text-blue-400',
  planning:   'text-cyan-400',
  execution:  'text-amber-400',
  audit:      'text-teal-400',
  final:      'text-green-400',
  error:      'text-red-400',
}

export default function MissionPanel() {
  const [prompt, setPrompt] = useState('')
  const [fidelity, setFidelity] = useState(0.95)
  const { streamEvents, isStreaming } = useMissionStore()
  const { startMission, stopMission } = useSSEMission()

  const handleSubmit = () => {
    if (!prompt.trim() || isStreaming) return
    startMission(prompt.trim(), fidelity)
  }

  return (
    <div className="flex flex-col gap-4 p-4 h-full animate-fade-in">
      {/* Input Section */}
      <div className="glass p-6 rounded-2xl flex flex-col gap-4 shadow-2xl">
        <div className="flex justify-between items-center px-1">
          <h2 className="text-xl font-bold tracking-tight text-white/90">
            Mission Controller <span className="text-purple-500 font-mono text-sm ml-2">v13.0</span>
          </h2>
          <div className="flex items-center gap-2 bg-neutral-900/50 px-3 py-1.5 rounded-full border border-white/5">
            <div className={`w-2 h-2 rounded-full ${isStreaming ? 'bg-amber-500 animate-pulse' : 'bg-neutral-600'}`}></div>
            <span className="text-[10px] uppercase tracking-widest font-bold text-neutral-400">
              {isStreaming ? 'Streaming' : 'Idle'}
            </span>
          </div>
        </div>

        <textarea
          className="w-full p-4 rounded-xl border resize-none h-32 bg-neutral-950/50 
                     border-neutral-800 text-white placeholder-neutral-600 
                     focus:outline-none focus:border-purple-600/50 focus:ring-1 focus:ring-purple-600/20 
                     transition-all duration-300 text-lg leading-relaxed"
          placeholder="Describe the cognitive mission objective..."
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter' && e.ctrlKey) {
              e.preventDefault()
              handleSubmit()
            }
          }}
          disabled={isStreaming}
        />

        <div className="flex flex-wrap items-center gap-6">
          <div className="flex flex-col gap-1.5 flex-1 min-w-[200px]">
            <div className="flex justify-between text-[11px] font-bold uppercase tracking-wider text-neutral-500">
              <span>Fidelity Threshold</span>
              <span className="text-purple-400">{(fidelity * 100).toFixed(0)}%</span>
            </div>
            <input
              type="range" min="0.5" max="1" step="0.01"
              value={fidelity}
              onChange={e => setFidelity(parseFloat(e.target.value))}
              className="w-full h-1 bg-neutral-800 rounded-lg appearance-none cursor-pointer accent-purple-500 hover:accent-purple-400 transition-all"
              disabled={isStreaming}
            />
          </div>

          <button
            onClick={isStreaming ? stopMission : handleSubmit}
            disabled={!isStreaming && !prompt.trim()}
            className={`px-8 py-3.5 rounded-xl font-bold tracking-tight transition-all duration-300 transform active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed ${
              isStreaming
                ? 'bg-red-600/10 hover:bg-red-600/20 text-red-500 border border-red-500/30'
                : 'bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-900/20'
            }`}
          >
            {isStreaming ? 'Terminate Mission' : 'Initiate Sequence'}
          </button>
        </div>
      </div>

      {/* Event Stream Log */}
      <StreamEventLog events={streamEvents} eventColors={EVENT_COLORS} />
    </div>
  )
}
