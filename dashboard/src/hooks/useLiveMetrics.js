import { useState, useEffect, useRef, useCallback } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/live'
const RECONNECT_DELAY_MS = 3000

export default function useLiveMetrics() {
  const [metrics, setMetrics] = useState(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const timerRef = useRef(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      clearTimeout(timerRef.current)
    }

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'ping') return
        setMetrics(data)
      } catch (_) {}
    }

    ws.onclose = () => {
      setConnected(false)
      timerRef.current = setTimeout(connect, RECONNECT_DELAY_MS)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(timerRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { metrics, connected }
}
