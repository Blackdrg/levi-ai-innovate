import { useState, useRef } from 'react'
import { useMissionStore } from '../stores/missionStore'
import { useSSEMission } from '../hooks/useSSEMission'
import { api } from '../lib/api'
import StreamEventLog from './StreamEventLog'
import { Mic, Square, ShieldAlert } from 'lucide-react'

const EVENT_COLORS = {
  perception: 'text-purple-400',
  memory:     'text-blue-400',
  planning:   'text-cyan-400',
  execution:  'text-amber-400',
  audit:      'text-teal-400',
  final:      'text-green-400',
  error:      'text-red-400',
  confidence: 'text-indigo-400',
}

export default function MissionPanel() {
  const [prompt, setPrompt] = useState('')
  const [fidelity, setFidelity] = useState(0.95)
  const [isRecording, setIsRecording] = useState(false)
  const { streamEvents, isStreaming } = useMissionStore()
  const { startMission, stopMission } = useSSEMission()
  
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  const handleSubmit = () => {
    if (!prompt.trim() || isStreaming) return
    startMission(prompt.trim(), fidelity)
  }

  const toggleRecording = async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop()
      setIsRecording(false)
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: { noiseSuppression: true, echoCancellation: true } 
      })
      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder
      chunksRef.current = []

      recorder.ondataavailable = (e) => chunksRef.current.push(e.data)
      recorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        stream.getTracks().forEach(track => track.stop())
        
        try {
          const result = await api.uploadVoiceCommand(blob)
          if (result.status === 'success') {
            setPrompt(result.transcription)
            startMission(result.transcription, fidelity)
          } else if (result.status === 'verify_required') {
            setPrompt(result.transcription)
            // Visual feedback for verification
          }
        } catch (err) {
          console.error('Voice submission failed:', err)
        }
      }

      recorder.start()
      setIsRecording(true)
    } catch (err) {
      console.error('Microphone access denied:', err)
    }
  }

  return (
    <div className="flex flex-col gap-4 p-4 h-full animate-fade-in font-['Outfit']">
      {/* Input Section */}
      <div className="glass p-6 rounded-2xl flex flex-col gap-4 shadow-2xl border border-white/5 relative overflow-hidden">
        {/* Recording Overlay Pulse */}
        {isRecording && (
          <div className="absolute inset-0 bg-purple-600/5 animate-pulse pointer-events-none" />
        )}

        <div className="flex justify-between items-center px-1">
          <h2 className="text-xl font-black tracking-tight text-white/90 flex items-center gap-2">
            Mission Controller 
            <span className="text-purple-500 font-black text-xs bg-purple-500/10 px-2 py-0.5 rounded-full border border-purple-500/20">v15.0-GA</span>
          </h2>
          <div className="flex items-center gap-2 bg-neutral-900/50 px-3 py-1.5 rounded-full border border-white/5">
            <div className={`w-2 h-2 rounded-full ${isStreaming || isRecording ? 'bg-amber-500 animate-pulse' : 'bg-neutral-600'}`}></div>
            <span className="text-[10px] uppercase tracking-widest font-bold text-neutral-400">
              {isRecording ? 'Listening' : (isStreaming ? 'Streaming' : 'Idle')}
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
          disabled={isStreaming || isRecording}
        />

        <div className="flex flex-wrap items-center gap-4">
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
              disabled={isStreaming || isRecording}
            />
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={toggleRecording}
              disabled={isStreaming}
              className={`p-3.5 rounded-xl transition-all duration-300 border ${
                isRecording 
                  ? 'bg-red-600/20 border-red-500/40 text-red-500 animate-pulse' 
                  : 'bg-neutral-900 border-white/5 text-neutral-400 hover:text-white hover:bg-neutral-800'
              }`}
            >
              {isRecording ? <Square size={20} fill="currentColor" /> : <Mic size={20} />}
            </button>

            <button
              onClick={isStreaming ? stopMission : handleSubmit}
              disabled={(!isStreaming && !prompt.trim()) || isRecording}
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
      </div>

      {/* Event Stream Log */}
      <StreamEventLog events={streamEvents} eventColors={EVENT_COLORS} />
    </div>
  )
}
