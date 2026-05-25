import { useEffect, useState } from 'react'
import { Plus, Bot, Trash2, Edit3, Play, Brain, X, ChevronDown, ChevronUp, Zap } from 'lucide-react'
import toast from 'react-hot-toast'
import { agentsApi } from '../api/client'
import type { Agent, AgentCreate, Tool } from '../api/client'

const MODELS = [
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini (Recommended)' },
  { value: 'gpt-4o', label: 'GPT-4o' },
  { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
]

const CHANNELS = ['telegram', 'slack', 'whatsapp']

const DEFAULT_FORM: AgentCreate = {
  name: '',
  role: 'AI Assistant',
  system_prompt: 'You are a helpful AI assistant.',
  model: 'gpt-4o-mini',
  tools: [],
  channels: [],
  memory_enabled: true,
  memory_window: '10',
  max_tokens_per_turn: '2000',
  temperature: '0.7',
  schedule: '',
  schedule_task: '',
  personality: {},
}

interface ChatMessage {
  role: 'user' | 'agent'
  content: string
  loading?: boolean
}

export default function AgentBuilder() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [tools, setTools] = useState<Tool[]>([])
  const [showForm, setShowForm] = useState(false)
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null)
  const [form, setForm] = useState<AgentCreate>(DEFAULT_FORM)
  const [saving, setSaving] = useState(false)
  const [chatAgent, setChatAgent] = useState<Agent | null>(null)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)

  useEffect(() => {
    loadAgents()
    agentsApi.tools().then(setTools)
  }, [])

  const loadAgents = () => {
    agentsApi.list().then(setAgents)
  }

  const openCreate = () => {
    setEditingAgent(null)
    setForm(DEFAULT_FORM)
    setShowForm(true)
    setShowAdvanced(false)
  }

  const openEdit = (agent: Agent) => {
    setEditingAgent(agent)
    setForm({
      name: agent.name,
      role: agent.role,
      system_prompt: agent.system_prompt,
      model: agent.model,
      tools: agent.tools,
      channels: agent.channels,
      memory_enabled: agent.memory_enabled,
      memory_window: agent.memory_window,
      max_tokens_per_turn: agent.max_tokens_per_turn,
      temperature: agent.temperature,
      schedule: agent.schedule,
      schedule_task: agent.schedule_task,
      personality: agent.personality,
    })
    setShowForm(true)
  }

  const handleSave = async () => {
    if (!form.name.trim()) { toast.error('Agent name is required'); return }
    setSaving(true)
    try {
      if (editingAgent) {
        const updated = await agentsApi.update(editingAgent.id, form)
        setAgents(prev => prev.map(a => a.id === updated.id ? updated : a))
        toast.success('Agent updated')
      } else {
        const created = await agentsApi.create(form)
        setAgents(prev => [created, ...prev])
        toast.success('Agent created')
      }
      setShowForm(false)
    } catch (e: unknown) {
      toast.error('Failed to save agent')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (agent: Agent) => {
    if (!confirm(`Delete agent "${agent.name}"?`)) return
    try {
      await agentsApi.delete(agent.id)
      setAgents(prev => prev.filter(a => a.id !== agent.id))
      toast.success('Agent deleted')
    } catch {
      toast.error('Failed to delete agent')
    }
  }

  const openChat = (agent: Agent) => {
    setChatAgent(agent)
    setChatMessages([{
      role: 'agent',
      content: `Hi! I'm **${agent.name}** — ${agent.role}. How can I help you?`,
    }])
    setChatInput('')
  }

  const sendChat = async () => {
    if (!chatInput.trim() || !chatAgent || chatLoading) return
    const msg = chatInput.trim()
    setChatInput('')
    setChatMessages(prev => [...prev, { role: 'user', content: msg }])
    setChatLoading(true)
    setChatMessages(prev => [...prev, { role: 'agent', content: '', loading: true }])

    try {
      const result = await agentsApi.invoke(chatAgent.id, msg)
      setChatMessages(prev => [
        ...prev.filter(m => !m.loading),
        { role: 'agent', content: result.response },
      ])
    } catch {
      setChatMessages(prev => [
        ...prev.filter(m => !m.loading),
        { role: 'agent', content: '⚠️ Error: Failed to get response.' },
      ])
    } finally {
      setChatLoading(false)
    }
  }

  const toggleTool = (toolName: string) => {
    setForm(f => ({
      ...f,
      tools: f.tools?.includes(toolName)
        ? f.tools.filter(t => t !== toolName)
        : [...(f.tools || []), toolName],
    }))
  }

  const toggleChannel = (ch: string) => {
    setForm(f => ({
      ...f,
      channels: f.channels?.includes(ch)
        ? f.channels.filter(c => c !== ch)
        : [...(f.channels || []), ch],
    }))
  }

  return (
    <div className="flex h-full">
      {/* Agent list */}
      <div className="flex-1 p-6 overflow-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white">Agents</h1>
            <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
              Create and configure AI agents
            </p>
          </div>
          <button onClick={openCreate}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white transition-all hover:opacity-90"
            style={{ background: 'var(--accent)' }}>
            <Plus size={16} /> New Agent
          </button>
        </div>

        {agents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Bot size={48} className="mb-4 opacity-20" style={{ color: 'var(--accent)' }} />
            <h3 className="text-lg font-medium text-white mb-2">No agents yet</h3>
            <p className="text-sm mb-4" style={{ color: 'var(--text-secondary)' }}>
              Create your first AI agent to get started
            </p>
            <button onClick={openCreate}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white"
              style={{ background: 'var(--accent)' }}>
              <Plus size={16} /> Create Agent
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {agents.map(agent => (
              <div key={agent.id}
                className="rounded-xl border p-4 hover:border-indigo-500/50 transition-all group"
                style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold text-white"
                      style={{ background: 'var(--accent)' }}>
                      {agent.name[0].toUpperCase()}
                    </div>
                    <div>
                      <div className="font-semibold text-white text-sm">{agent.name}</div>
                      <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>{agent.role}</div>
                    </div>
                  </div>
                  <div className={`w-2 h-2 rounded-full mt-1 ${agent.is_active ? 'bg-green-400' : 'bg-gray-500'}`} />
                </div>

                {/* Model + tools */}
                <div className="text-xs mb-3 space-y-1">
                  <div className="flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
                    <Zap size={11} />
                    <span>{agent.model}</span>
                  </div>
                  {agent.tools.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {agent.tools.map(t => (
                        <span key={t} className="px-1.5 py-0.5 rounded text-xs"
                          style={{ background: 'rgba(99,102,241,0.15)', color: '#818cf8' }}>
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* System prompt preview */}
                <p className="text-xs mb-4 line-clamp-2" style={{ color: 'var(--text-secondary)' }}>
                  {agent.system_prompt}
                </p>

                {/* Actions */}
                <div className="flex gap-2">
                  <button onClick={() => openChat(agent)}
                    className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-medium text-white transition-all hover:opacity-90"
                    style={{ background: 'var(--accent)' }}>
                    <Play size={12} /> Chat
                  </button>
                  <button onClick={() => openEdit(agent)}
                    className="p-1.5 rounded-lg transition-colors hover:bg-white/10"
                    style={{ color: 'var(--text-secondary)' }}>
                    <Edit3 size={14} />
                  </button>
                  <button onClick={() => handleDelete(agent)}
                    className="p-1.5 rounded-lg transition-colors hover:bg-red-500/10 hover:text-red-400"
                    style={{ color: 'var(--text-secondary)' }}>
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Agent form panel */}
      {showForm && (
        <div className="w-96 border-l overflow-auto flex flex-col"
          style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
          <div className="flex items-center justify-between px-4 py-4 border-b sticky top-0 z-10"
            style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
            <h2 className="font-semibold text-white text-sm">
              {editingAgent ? 'Edit Agent' : 'New Agent'}
            </h2>
            <button onClick={() => setShowForm(false)}
              className="p-1 rounded hover:bg-white/10" style={{ color: 'var(--text-secondary)' }}>
              <X size={16} />
            </button>
          </div>

          <div className="p-4 space-y-4 flex-1">
            {/* Name */}
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                Name *
              </label>
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Research Agent"
                className="w-full px-3 py-2 rounded-lg text-sm text-white border outline-none focus:border-indigo-500 transition-colors"
                style={{ background: 'var(--bg-base)', borderColor: 'var(--border)' }} />
            </div>

            {/* Role */}
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                Role
              </label>
              <input value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                placeholder="e.g. Research Specialist"
                className="w-full px-3 py-2 rounded-lg text-sm text-white border outline-none focus:border-indigo-500 transition-colors"
                style={{ background: 'var(--bg-base)', borderColor: 'var(--border)' }} />
            </div>

            {/* System prompt */}
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                System Prompt
              </label>
              <textarea value={form.system_prompt}
                onChange={e => setForm(f => ({ ...f, system_prompt: e.target.value }))}
                rows={4} placeholder="Describe the agent's personality and behavior..."
                className="w-full px-3 py-2 rounded-lg text-sm text-white border outline-none focus:border-indigo-500 transition-colors resize-none"
                style={{ background: 'var(--bg-base)', borderColor: 'var(--border)' }} />
            </div>

            {/* Model */}
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                Model
              </label>
              <select value={form.model} onChange={e => setForm(f => ({ ...f, model: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg text-sm text-white border outline-none focus:border-indigo-500 transition-colors"
                style={{ background: 'var(--bg-base)', borderColor: 'var(--border)' }}>
                {MODELS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>

            {/* Tools */}
            <div>
              <label className="block text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
                Tools
              </label>
              <div className="space-y-1.5">
                {tools.map(tool => (
                  <label key={tool.name} className="flex items-start gap-2.5 cursor-pointer group">
                    <input type="checkbox"
                      checked={form.tools?.includes(tool.name) || false}
                      onChange={() => toggleTool(tool.name)}
                      className="mt-0.5 accent-indigo-500" />
                    <div>
                      <div className="text-xs font-medium text-white">{tool.name}</div>
                      <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                        {tool.description.slice(0, 60)}...
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Channels */}
            <div>
              <label className="block text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
                Channels
              </label>
              <div className="flex gap-2">
                {CHANNELS.map(ch => (
                  <button key={ch} onClick={() => toggleChannel(ch)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all capitalize ${
                      form.channels?.includes(ch)
                        ? 'text-white'
                        : 'hover:bg-white/5'
                    }`}
                    style={{
                      background: form.channels?.includes(ch) ? 'var(--accent)' : 'var(--bg-base)',
                      border: `1px solid ${form.channels?.includes(ch) ? 'var(--accent)' : 'var(--border)'}`,
                      color: form.channels?.includes(ch) ? 'white' : 'var(--text-secondary)',
                    }}>
                    {ch}
                  </button>
                ))}
              </div>
            </div>

            {/* Advanced */}
            <button onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 text-xs font-medium w-full py-2 border-t"
              style={{ color: 'var(--text-secondary)', borderColor: 'var(--border)' }}>
              {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              Advanced Configuration
            </button>

            {showAdvanced && (
              <div className="space-y-3 animate-fade-in">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>
                      Temperature
                    </label>
                    <input value={form.temperature}
                      onChange={e => setForm(f => ({ ...f, temperature: e.target.value }))}
                      type="number" min="0" max="2" step="0.1"
                      className="w-full px-2 py-1.5 rounded text-xs text-white border outline-none"
                      style={{ background: 'var(--bg-base)', borderColor: 'var(--border)' }} />
                  </div>
                  <div>
                    <label className="block text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>
                      Max Tokens
                    </label>
                    <input value={form.max_tokens_per_turn}
                      onChange={e => setForm(f => ({ ...f, max_tokens_per_turn: e.target.value }))}
                      type="number"
                      className="w-full px-2 py-1.5 rounded text-xs text-white border outline-none"
                      style={{ background: 'var(--bg-base)', borderColor: 'var(--border)' }} />
                  </div>
                </div>

                <div>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={form.memory_enabled}
                      onChange={e => setForm(f => ({ ...f, memory_enabled: e.target.checked }))}
                      className="accent-indigo-500" />
                    <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                      Enable Memory (ChromaDB)
                    </span>
                  </label>
                </div>

                <div>
                  <label className="block text-xs mb-1" style={{ color: 'var(--text-secondary)' }}>
                    Schedule (cron)
                  </label>
                  <input value={form.schedule}
                    onChange={e => setForm(f => ({ ...f, schedule: e.target.value }))}
                    placeholder="e.g. 0 9 * * 1-5"
                    className="w-full px-2 py-1.5 rounded text-xs text-white border outline-none"
                    style={{ background: 'var(--bg-base)', borderColor: 'var(--border)' }} />
                </div>
              </div>
            )}
          </div>

          <div className="p-4 border-t sticky bottom-0"
            style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
            <button onClick={handleSave} disabled={saving}
              className="w-full py-2.5 rounded-lg text-sm font-medium text-white transition-all hover:opacity-90 disabled:opacity-50"
              style={{ background: 'var(--accent)' }}>
              {saving ? 'Saving...' : editingAgent ? 'Update Agent' : 'Create Agent'}
            </button>
          </div>
        </div>
      )}

      {/* Chat panel */}
      {chatAgent && (
        <div className="w-96 border-l flex flex-col"
          style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
          <div className="flex items-center justify-between px-4 py-4 border-b"
            style={{ borderColor: 'var(--border)' }}>
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-white"
                style={{ background: 'var(--accent)' }}>
                {chatAgent.name[0]}
              </div>
              <div>
                <div className="text-sm font-medium text-white">{chatAgent.name}</div>
                <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Test Chat</div>
              </div>
            </div>
            <button onClick={() => setChatAgent(null)}
              className="p-1 rounded hover:bg-white/10" style={{ color: 'var(--text-secondary)' }}>
              <X size={16} />
            </button>
          </div>

          <div className="flex-1 overflow-auto p-4 space-y-3">
            {chatMessages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] px-3 py-2 rounded-xl text-sm ${
                  msg.role === 'user'
                    ? 'text-white rounded-br-sm'
                    : 'rounded-bl-sm'
                }`}
                  style={{
                    background: msg.role === 'user' ? 'var(--accent)' : 'var(--bg-elevated)',
                    color: msg.role === 'user' ? 'white' : 'var(--text-primary)',
                    border: msg.role === 'agent' ? '1px solid var(--border)' : undefined,
                  }}>
                  {msg.loading ? (
                    <div className="flex gap-1 py-1">
                      {[0, 1, 2].map(i => (
                        <div key={i} className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-bounce"
                          style={{ animationDelay: `${i * 0.15}s` }} />
                      ))}
                    </div>
                  ) : (
                    <span className="whitespace-pre-wrap">{msg.content}</span>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="p-3 border-t" style={{ borderColor: 'var(--border)' }}>
            <div className="flex gap-2">
              <input value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendChat()}
                placeholder="Type a message..."
                className="flex-1 px-3 py-2 rounded-lg text-sm text-white border outline-none focus:border-indigo-500"
                style={{ background: 'var(--bg-base)', borderColor: 'var(--border)' }} />
              <button onClick={sendChat} disabled={chatLoading || !chatInput.trim()}
                className="px-3 py-2 rounded-lg text-white transition-all hover:opacity-90 disabled:opacity-40"
                style={{ background: 'var(--accent)' }}>
                <Play size={14} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
