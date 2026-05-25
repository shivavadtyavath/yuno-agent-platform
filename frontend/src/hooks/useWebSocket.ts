import { useEffect, useRef, useState, useCallback } from 'react'

export interface WSEvent {
  type: string
  payload: Record<string, unknown>
  execution_id?: string
  agent_id?: string
  timestamp: string
}

export function useWebSocket(url: string) {
  const [events, setEvents] = useState<WSEvent[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      // Ping every 30s to keep alive
      const pingInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send('ping')
      }, 30000)
      ws.onclose = () => {
        clearInterval(pingInterval)
        setConnected(false)
        // Reconnect after 3s
        reconnectTimer.current = setTimeout(connect, 3000)
      }
    }

    ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data) as WSEvent
        if (event.type === 'pong') return
        setEvents(prev => {
          const next = [...prev, event]
          return next.slice(-200) // keep last 200
        })
      } catch {
        // ignore parse errors
      }
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [url])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  const clearEvents = useCallback(() => setEvents([]), [])

  return { events, connected, clearEvents }
}
