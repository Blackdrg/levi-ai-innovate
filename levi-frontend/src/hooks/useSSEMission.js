import { useCallback, useRef } from 'react'
import pako from 'pako'
import { useMissionStore } from '../stores/missionStore'
import { useAuthStore } from '../stores/authStore'

export function useSSEMission() {
  const esRef = useRef(null)
  const { pushEvent, setStreaming, clearStream } = useMissionStore()
  const token = useAuthStore(s => s.token)

  const startMission = useCallback(async (prompt, fidelityThreshold = 0.95) => {
    if (esRef.current) esRef.current.close()
    clearStream()
    setStreaming(true)

    const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const url = new URL(`${baseURL}/api/v1/orchestrator/stream`)
    url.searchParams.set('prompt', prompt)
    url.searchParams.set('fidelity_threshold', fidelityThreshold.toString())
    url.searchParams.set('token', token)

    try {
      const es = new EventSource(url.toString())
      esRef.current = es

      const eventTypes = ['perception', 'memory', 'planning', 'execution', 'audit', 'final', 'error', 'confidence']
      
      eventTypes.forEach(type => {
        es.addEventListener(type, (e) => {
          try {
            let parsedData;
            
            // v15.0: Adaptive Decompression (Base64 -> Zlib -> JSON)
            try {
              // Try to decode base64 and inflate
              const binaryString = atob(e.data)
              const charData = binaryString.split('').map(x => x.charCodeAt(0))
              const binData = new Uint8Array(charData)
              const decompressed = pako.inflate(binData, { to: 'string' })
              parsedData = JSON.parse(decompressed)
            } catch (pakoErr) {
              // Fallback for uncompressed legacy or debug pulses
              parsedData = JSON.parse(e.data)
            }

            pushEvent({ type, data: parsedData, timestamp: Date.now() })
            
            if (type === 'final' || type === 'error') {
              setStreaming(false)
              es.close()
            }
          } catch (err) {
            console.error('[SSE] Decompression or Parse failure:', err)
          }
        })
      })

      es.onerror = (e) => {
        console.error('[SSE] Protocol Error:', e)
        pushEvent({ type: 'error', data: { message: 'Lost heartbeat with Sovereign node.' }, timestamp: Date.now() })
        setStreaming(false)
        es.close()
      }
    } catch (err) {
      setStreaming(false)
      console.error('[SSE] Initialization failed:', err)
    }

    return () => esRef.current?.close()
  }, [token, pushEvent, setStreaming, clearStream])

  const stopMission = useCallback(() => {
    esRef.current?.close()
    setStreaming(false)
  }, [setStreaming])

  return { startMission, stopMission }
}
