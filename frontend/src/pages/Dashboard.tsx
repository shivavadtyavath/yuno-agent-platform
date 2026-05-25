import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Bot, GitBranch, Zap, TrendingUp, CheckCircle, XCircle, Clock, ArrowRight } from 'lucide-react'
import { agentsApi, executionsApi, workflowsApi } from '../api/client'
import type { Stats, Agent, Execution } from '../api/client'
import type { WSEvent } from '../hooks/useWebSocket'
import { formatDistanceToNow } from 'date-fns'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

interface Props {
  wsEvents: WSEvent[]
  connected: boolean
}

const STAT_CARDS = [
  { key: 'total_agents', label: 'Total Agents', icon: Bot, color: '#6366f1' },
  { key: 'total_workflows', label: 'Workflows', icon: GitBranch, color: '#10b981' },
  { key: 'total_executions', label: 'Executions', icon: Zap, color: '#f59e0b' },
  { key: 'success_rate', label: 'Success Rate', icon: TrendingUp, color: '#3b82f6', suffix: '%' },
]

export default function Dashboard({ wsEvents, connected }: Props) {
  const [stats, setStats] = useState<Stats | null>(null)
  const [agents, setAgents] = useState<Agent[]>([])
  const [executions, setExecutions] = useState<Execution[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      executionsApi.stats(),
      agentsApi.list(),
      executionsApi.list({ limit: 10 }),
    ]).then(([s, a, e]) => {
      setStats(s)
      setAgents(a)
      setExecutions(e)
    }).finally(() => setLoading(false))
  }, [])

  // Build mini chart data from recent WS events
  const chartData = wsEvents
    .filter(e => e.type === 'execution_complete' || e.type === 'execution_error')
    .slice(-20)
    .map((e, i) => ({
      i,
      tokens: (e.payload.total_tokens as number) || 0,
      type: e.type,
    }))

  const recentActivity = wsEvents.slice(-8).reverse()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p style={{ color: 'var(--text-secondary)' }}>Loading platform...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Platform Overview</h1>
          <p style={{ color: 'var(--text-secondary)' }} className="text-sm mt-1">
            Real-time AI agent orchestration dashboard
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium"
          style={{
            background: connected ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
            color: connected ? '#10b981' : '#ef4444',
            border: `1px solid ${connected ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
          }}>
          <div className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
          {connected ? 'Live' : 'Offline'}
        </div>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {STAT_CARDS.map(({ key, label, icon: Icon, color, suffix }) => (
          <div key={key} className="rounded-xl p-4 border transition-all hover:scale-[1.02]"
            style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>{label}</span>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                style={{ background: `${color}20` }}>
                <Icon size={16} style={{ color }} />
              </div>
            </div>
            <div className="text-2xl font-bold text-white">
              {stats ? (stats[key as keyof Stats] as number) : 0}{suffix || ''}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Token usage chart */}
        <div className="lg:col-span-2 rounded-xl p-4 border"
          style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
          <h2 className="text-sm font-semibold text-white mb-4">Token Usage (Live)</h2>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="tokenGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="i" hide />
                <YAxis hide />
                <Tooltip
                  contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8 }}
                  labelStyle={{ color: 'var(--text-secondary)' }}
                  itemStyle={{ color: '#6366f1' }}
                />
                <Area type="monotone" dataKey="tokens" stroke="#6366f1" fill="url(#tokenGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-40 flex items-center justify-center" style={{ color: 'var(--text-secondary)' }}>
              <div className="text-center">
                <Zap size={24} className="mx-auto mb-2 opacity-30" />
                <p className="text-sm">Run an agent to see live token usage</p>
              </div>
            </div>
          )}
        </div>

        {/* Live activity feed */}
        <div className="rounded-xl p-4 border"
          style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
          <h2 className="text-sm font-semibold text-white mb-4">Live Activity</h2>
          <div className="space-y-2 overflow-y-auto max-h-48">
            {recentActivity.length === 0 ? (
              <p className="text-xs text-center py-4" style={{ color: 'var(--text-secondary)' }}>
                No activity yet
              </p>
            ) : (
              recentActivity.map((e, i) => (
                <div key={i} className="flex items-start gap-2 text-xs animate-slide-up">
                  <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${
                    e.type.includes('error') ? 'bg-red-400' :
                    e.type.includes('complete') ? 'bg-green-400' : 'bg-indigo-400'
                  }`} />
                  <div>
                    <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                      {e.type.replace(/_/g, ' ')}
                    </span>
                    {!!e.payload.agent_name && (
                      <span className="ml-1 text-white">· {String(e.payload.agent_name)}</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Agents + Recent executions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Agents */}
        <div className="rounded-xl border" style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
          <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--border)' }}>
            <h2 className="text-sm font-semibold text-white">Agents</h2>
            <Link to="/agents" className="text-xs flex items-center gap-1 hover:text-white transition-colors"
              style={{ color: 'var(--accent)' }}>
              Manage <ArrowRight size={12} />
            </Link>
          </div>
          <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
            {agents.slice(0, 5).map(agent => (
              <div key={agent.id} className="flex items-center gap-3 px-4 py-3">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-white"
                  style={{ background: 'var(--accent)' }}>
                  {agent.name[0].toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-white truncate">{agent.name}</div>
                  <div className="text-xs truncate" style={{ color: 'var(--text-secondary)' }}>{agent.role}</div>
                </div>
                <div className={`w-2 h-2 rounded-full ${agent.is_active ? 'bg-green-400' : 'bg-gray-500'}`} />
              </div>
            ))}
            {agents.length === 0 && (
              <div className="px-4 py-6 text-center text-sm" style={{ color: 'var(--text-secondary)' }}>
                No agents yet.{' '}
                <Link to="/agents" className="underline" style={{ color: 'var(--accent)' }}>Create one</Link>
              </div>
            )}
          </div>
        </div>

        {/* Recent executions */}
        <div className="rounded-xl border" style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
          <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--border)' }}>
            <h2 className="text-sm font-semibold text-white">Recent Executions</h2>
            <Link to="/monitor" className="text-xs flex items-center gap-1 hover:text-white transition-colors"
              style={{ color: 'var(--accent)' }}>
              View all <ArrowRight size={12} />
            </Link>
          </div>
          <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
            {executions.slice(0, 5).map(exec => (
              <div key={exec.id} className="flex items-center gap-3 px-4 py-3">
                {exec.status === 'completed' ? (
                  <CheckCircle size={16} className="text-green-400 flex-shrink-0" />
                ) : exec.status === 'failed' ? (
                  <XCircle size={16} className="text-red-400 flex-shrink-0" />
                ) : (
                  <Clock size={16} className="text-yellow-400 flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-white truncate">{exec.input_text || 'No input'}</div>
                  <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                    {formatDistanceToNow(new Date(exec.started_at), { addSuffix: true })}
                    {' · '}{exec.total_tokens} tokens
                  </div>
                </div>
              </div>
            ))}
            {executions.length === 0 && (
              <div className="px-4 py-6 text-center text-sm" style={{ color: 'var(--text-secondary)' }}>
                No executions yet
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
