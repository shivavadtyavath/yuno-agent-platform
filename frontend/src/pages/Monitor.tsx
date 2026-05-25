import { useState, useEffect, useRef } from 'react'
import { Activity, Filter, Zap, MessageSquare, Wrench, AlertCircle, CheckCircle, Clock } from 'lucide-react'
import { executionsApi } from '../api/client'
import type { Execution } from '../api/client'
import type { WSEvent } from '../hooks/useWebSocket'
import { formatDistanceToNow, format } from 'date-fns'
import clsx from 'clsx'

interface Props {
  wsEvents: WSEvent[]
  connected: boolean
}

// Helper — safely convert unknown payload value to string
const str = (v: unknown): string => (v == null ? '' : String(v))

const EVENT_ICONS: Record<string, { icon: React.ElementType; color: string }> = {
  agent_thinking:    { icon: Clock,         color: '#f59e0b' },
  agent_message:     { icon: MessageSquare, color: '#6366f1' },
  tool_call:         { icon: Wrench,        color: '#10b981' },
  tool_result:       { icon: CheckCircle,   color: '#10b981' },
  execution_start:   { icon: Zap,           color: '#3b82f6' },
  execution_complete:{ icon: CheckCircle,   color: '#10b981' },
  execution_error:   { icon: AlertCircle,   color: '#ef4444' },
  workflow_start:    { icon: Zap,           color: '#8b5cf6' },
  workflow_complete: { icon: CheckCircle,   color: '#8b5cf6' },
  workflow_error:    { icon: AlertCircle,   color: '#ef4444' },
  telegram_message:  { icon: MessageSquare, color: '#0ea5e9' },
}

const EVENT_FILTERS = ['all', 'agent_message', 'tool_call', 'execution_complete', 'execution_error', 'telegram_message']

export default function Monitor({ wsEvents, connected }: Props) {
  const [filter, setFilter]           = useState('all')
  const [executions, setExecutions]   = useState<Execution[]>([])
  const [selectedExec, setSelectedExec] = useState<Execution | null>(null)
  const logEndRef                     = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll]   = useState(true)

  useEffect(() => {
    executionsApi.list({ limit: 20 }).then(setExecutions)
  }, [])

  useEffect(() => {
    const last = wsEvents[wsEvents.length - 1]
    if (last?.type === 'execution_complete' || last?.type === 'execution_error') {
      executionsApi.list({ limit: 20 }).then(setExecutions)
    }
  }, [wsEvents])

  useEffect(() => {
    if (autoScroll && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [wsEvents, autoScroll])

  const filteredEvents = filter === 'all' ? wsEvents : wsEvents.filter(e => e.type === filter)
  const getEventConfig = (type: string) => EVENT_ICONS[type] || { icon: Activity, color: '#94a3b8' }

  return (
    <div className="flex h-full">
      {/* ── Live log stream ─────────────────────────────────────── */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b"
          style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-2">
            <div className={clsx('w-2 h-2 rounded-full',
              connected ? 'bg-green-400 animate-pulse' : 'bg-red-400')} />
            <h1 className="text-sm font-semibold text-white">Live Monitor</h1>
            <span className="text-xs px-2 py-0.5 rounded-full"
              style={{ background: 'rgba(99,102,241,0.15)', color: 'var(--accent)' }}>
              {wsEvents.length} events
            </span>
          </div>
          <div className="flex items-center gap-1 ml-auto">
            <Filter size={13} style={{ color: 'var(--text-secondary)' }} />
            <select value={filter} onChange={e => setFilter(e.target.value)}
              className="text-xs border rounded px-2 py-1 outline-none"
              style={{ background: 'var(--bg-base)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
              {EVENT_FILTERS.map(f => (
                <option key={f} value={f}>{f === 'all' ? 'All Events' : f.replace(/_/g, ' ')}</option>
              ))}
            </select>
            <label className="flex items-center gap-1 text-xs ml-2 cursor-pointer"
              style={{ color: 'var(--text-secondary)' }}>
              <input type="checkbox" checked={autoScroll}
                onChange={e => setAutoScroll(e.target.checked)} className="accent-indigo-500" />
              Auto-scroll
            </label>
          </div>
        </div>

        {/* Log rows */}
        <div className="flex-1 overflow-auto p-4 font-mono space-y-1"
          style={{ background: 'var(--bg-base)' }}>
          {filteredEvents.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <Activity size={40} className="mb-3 opacity-10" style={{ color: 'var(--accent)' }} />
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                {connected ? 'Waiting for events…' : 'Not connected to event stream'}
              </p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                Run an agent or workflow to see live events
              </p>
            </div>
          ) : (
            filteredEvents.map((event, i) => {
              const { icon: Icon, color } = getEventConfig(event.type)
              const p = event.payload
              const agentName   = str(p.agent_name)
              const content     = str(p.content)
              const toolName    = str(p.tool_name)
              const errorMsg    = str(p.error)
              const tokens      = p.tokens != null ? str(p.tokens) : ''
              const costUsd     = p.cost_usd != null ? str(p.cost_usd) : ''
              const userMessage = str(p.user_message)

              return (
                <div key={i}
                  className="log-entry flex items-start gap-3 py-1 px-2 rounded hover:bg-white/5 transition-colors group animate-fade-in">
                  <span className="text-xs flex-shrink-0 mt-0.5"
                    style={{ color: 'var(--text-secondary)', minWidth: 80 }}>
                    {format(new Date(event.timestamp), 'HH:mm:ss.SSS')}
                  </span>
                  <Icon size={13} className="flex-shrink-0 mt-0.5" style={{ color }} />
                  <span className="flex-shrink-0 text-xs font-medium" style={{ color, minWidth: 160 }}>
                    {event.type}
                  </span>
                  <div className="flex-1 min-w-0 text-xs">
                    {agentName   && <span className="text-white mr-2">[{agentName}]</span>}
                    {content     && (
                      <span style={{ color: 'var(--text-primary)' }}>
                        {content.slice(0, 120)}{content.length > 120 ? '…' : ''}
                      </span>
                    )}
                    {toolName    && (
                      <span style={{ color: '#10b981' }}>
                        🔧 {toolName}
                        {p.args ? ` (${JSON.stringify(p.args).slice(0, 60)})` : ''}
                      </span>
                    )}
                    {errorMsg    && <span style={{ color: '#ef4444' }}>❌ {errorMsg}</span>}
                    {tokens      && (
                      <span className="ml-2" style={{ color: 'var(--text-secondary)' }}>
                        {tokens} tokens{costUsd ? ` · $${costUsd}` : ''}
                      </span>
                    )}
                    {userMessage && <span style={{ color: '#0ea5e9' }}>📱 {userMessage}</span>}
                  </div>
                  {event.execution_id && (
                    <span className="text-xs flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
                      style={{ color: 'var(--text-secondary)' }}>
                      {event.execution_id.slice(0, 8)}
                    </span>
                  )}
                </div>
              )
            })
          )}
          <div ref={logEndRef} />
        </div>
      </div>

      {/* ── Execution history sidebar ────────────────────────────── */}
      <div className="w-72 border-l flex flex-col"
        style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
        <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--border)' }}>
          <h2 className="text-sm font-semibold text-white">Execution History</h2>
        </div>
        <div className="flex-1 overflow-auto">
          {executions.map(exec => (
            <div key={exec.id}
              className={clsx(
                'px-4 py-3 border-b cursor-pointer transition-colors hover:bg-white/5',
                selectedExec?.id === exec.id && 'bg-indigo-500/10'
              )}
              style={{ borderColor: 'var(--border)' }}
              onClick={() => setSelectedExec(selectedExec?.id === exec.id ? null : exec)}>
              <div className="flex items-center gap-2 mb-1">
                {exec.status === 'completed'
                  ? <CheckCircle size={13} className="text-green-400 flex-shrink-0" />
                  : exec.status === 'failed'
                  ? <AlertCircle size={13} className="text-red-400 flex-shrink-0" />
                  : <Clock size={13} className="text-yellow-400 flex-shrink-0" />}
                <span className="text-xs font-medium text-white truncate flex-1">
                  {exec.input_text?.slice(0, 40) || 'No input'}
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                <span>{formatDistanceToNow(new Date(exec.started_at), { addSuffix: true })}</span>
                <span>·</span>
                <span>{exec.total_tokens} tok</span>
                <span>·</span>
                <span className="font-mono">${exec.estimated_cost_usd}</span>
              </div>
              {selectedExec?.id === exec.id && exec.messages && (
                <div className="mt-3 space-y-2 border-t pt-3" style={{ borderColor: 'var(--border)' }}>
                  {exec.messages.map(msg => (
                    <div key={msg.id} className="text-xs">
                      <span className="font-medium" style={{
                        color: msg.role === 'human' ? '#3b82f6'
                             : msg.role === 'tool'  ? '#10b981'
                             : 'var(--accent)'
                      }}>
                        {msg.role === 'tool' ? `🔧 ${msg.tool_name}` : msg.agent_name || msg.role}:
                      </span>
                      <span className="ml-1" style={{ color: 'var(--text-secondary)' }}>
                        {msg.content.slice(0, 100)}{msg.content.length > 100 ? '…' : ''}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
          {executions.length === 0 && (
            <div className="p-4 text-center text-xs" style={{ color: 'var(--text-secondary)' }}>
              No executions yet
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
