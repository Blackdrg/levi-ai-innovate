import { useCallback, useRef } from 'react'
import { useMissionStore } from '../stores/missionStore'
import { useAuthStore } from './authStore'

export function useSSEMission() {
  const esRef = useRef(null)
  const { pushEvent, setStreaming, clearStream } = useMissionStore()
  const token = useAuthStore(s => s.token)

  const startMission = useCallback(async (prompt, fidelityThreshold = 0.95) => {
    // Close any existing stream
    if (esRef.current) esRef.current.close()
    clearStream()
    setStreaming(true)

    const baseURL = import.meta.env.VITE_API_URL || 'https://localhost/api'
    const url = new URL(`${baseURL}/v13/chat/stream`)
    url.searchParams.set('prompt', prompt)
    url.searchParams.set('fidelity_threshold', fidelityThreshold)
    url.searchParams.set('token', token) // pass JWT as query param for SSE

    try {
      const es = new EventSource(url.toString())
      esRef.current = es

      // Handle each event type from backend
      const eventTypes = ['perception', 'memory', 'planning', 'execution', 'audit', 'final', 'error']
      eventTypes.forEach(type => {
        es.addEventListener(type, (e) => {
          try {
            const data = JSON.parse(e.data)
            pushEvent({ type, data, timestamp: Date.now() })
            if (type === 'final' || type === 'error') {
              setStreaming(false)
              es.close()
            }
          } catch (err) {
            console.error('Failed to parse SSE event:', e)
          }
        })
      })

      es.onerror = (e) => {
        console.error('SSE Error:', e)
        pushEvent({ type: 'error', data: { message: 'Connection lost or unauthorized' }, timestamp: Date.now() })
        setStreaming(false)
        es.close()
      }
    } catch (err) {
      setStreaming(false)
      console.error('Failed to start SSE:', err)
    }

    return () => {
      esRef.current?.close()
    }
  }, [token, pushEvent, setStreaming, clearStream])

  const stopMission = useCallback(() => {
    esRef.current?.close()
    setStreaming(false)
  }, [setStreaming])

  return { startMission, stopMission }
}
