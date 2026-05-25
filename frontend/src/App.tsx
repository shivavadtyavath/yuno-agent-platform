import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import {
  LayoutDashboard, Bot, GitBranch, Activity, Zap, Menu, X
} from 'lucide-react'
import clsx from 'clsx'
import Dashboard from './pages/Dashboard'
import AgentBuilder from './pages/AgentBuilder'
import WorkflowCanvas from './pages/WorkflowCanvas'
import Monitor from './pages/Monitor'
import { useWebSocket } from './hooks/useWebSocket'

const WS_URL = `ws://${window.location.hostname}:8000/api/v1/monitor/ws`

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/agents', icon: Bot, label: 'Agents' },
  { to: '/workflows', icon: GitBranch, label: 'Workflows' },
  { to: '/monitor', icon: Activity, label: 'Live Monitor' },
]

export default function App() {
  const { connected, events } = useWebSocket(WS_URL)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const location = useLocation()

  // Count recent events for badge
  const recentEvents = events.filter(e => {
    const age = Date.now() - new Date(e.timestamp).getTime()
    return age < 5000
  }).length

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--bg-base)' }}>
      {/* Sidebar */}
      <aside
        className={clsx(
          'flex flex-col transition-all duration-300 border-r',
          sidebarOpen ? 'w-56' : 'w-16',
        )}
        style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5 border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 glow-indigo"
            style={{ background: 'var(--accent)' }}>
            <Zap size={16} className="text-white" />
          </div>
          {sidebarOpen && (
            <div className="overflow-hidden">
              <div className="font-bold text-sm text-white whitespace-nowrap">Yuno AI</div>
              <div className="text-xs whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>
                Agent Platform
              </div>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="ml-auto p-1 rounded hover:bg-white/10 transition-colors"
            style={{ color: 'var(--text-secondary)' }}
          >
            {sidebarOpen ? <X size={14} /> : <Menu size={14} />}
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 space-y-1 px-2">
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150',
                  isActive
                    ? 'text-white glow-indigo'
                    : 'hover:bg-white/5',
                )
              }
              style={({ isActive }) => ({
                background: isActive ? 'var(--accent)' : undefined,
                color: isActive ? 'white' : 'var(--text-secondary)',
              })}
            >
              <Icon size={18} className="flex-shrink-0" />
              {sidebarOpen && (
                <span className="whitespace-nowrap overflow-hidden">
                  {label}
                  {label === 'Live Monitor' && recentEvents > 0 && (
                    <span className="ml-2 px-1.5 py-0.5 text-xs rounded-full bg-green-500 text-white">
                      {recentEvents}
                    </span>
                  )}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Connection status */}
        <div className="px-4 py-3 border-t" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-2">
            <div className={clsx(
              'w-2 h-2 rounded-full flex-shrink-0',
              connected ? 'bg-green-400 animate-pulse' : 'bg-red-400'
            )} />
            {sidebarOpen && (
              <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                {connected ? 'Live' : 'Disconnected'}
              </span>
            )}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard wsEvents={events} connected={connected} />} />
          <Route path="/agents" element={<AgentBuilder />} />
          <Route path="/workflows" element={<WorkflowCanvas />} />
          <Route path="/monitor" element={<Monitor wsEvents={events} connected={connected} />} />
        </Routes>
      </main>
    </div>
  )
}
