import { useEffect, useState, useCallback } from 'react'
import ReactFlow, {
  Background, Controls, MiniMap,
  addEdge, useNodesState, useEdgesState,
  type Connection, type Node, type Edge,
  BackgroundVariant,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Plus, Play, Save, Trash2, GitBranch, X, Layers, ChevronRight } from 'lucide-react'
import toast from 'react-hot-toast'
import { workflowsApi, agentsApi } from '../api/client'
import type { Workflow, Agent } from '../api/client'

// Custom agent node component
function AgentNode({ data }: { data: Record<string, unknown> }) {
  const color    = String(data.color || '#6366f1')
  const isStart  = Boolean(data.isStart)
  const label    = String(data.label || 'Agent')
  const role     = data.role ? String(data.role) : ''
  const tools    = Array.isArray(data.tools) ? (data.tools as string[]) : []

  return (
    <div className="rounded-xl border-2 p-3 min-w-[160px] shadow-lg"
      style={{
        background: 'var(--bg-surface)',
        borderColor: color,
        boxShadow: `0 0 20px ${color}40`,
      }}>
      {isStart && (
        <div className="text-xs px-2 py-0.5 rounded-full mb-2 inline-block font-medium"
          style={{ background: `${color}20`, color }}>
          START
        </div>
      )}
      <div className="flex items-center gap-2 mb-1">
        <div className="w-6 h-6 rounded-lg flex items-center justify-center text-xs font-bold text-white"
          style={{ background: color }}>
          {label[0]?.toUpperCase() || 'A'}
        </div>
        <span className="text-sm font-semibold text-white">{label}</span>
      </div>
      {role && (
        <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>{role}</div>
      )}
      {tools.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {tools.map((t: string) => (
            <span key={t} className="text-xs px-1.5 py-0.5 rounded"
              style={{ background: `${color}20`, color }}>
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

const nodeTypes = { agent: AgentNode }

export default function WorkflowCanvas() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [agents, setAgents] = useState<Agent[]>([])
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null)
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [showTemplates, setShowTemplates] = useState(false)
  const [templates, setTemplates] = useState<Record<string, unknown>[]>([])
  const [runInput, setRunInput] = useState('')
  const [running, setRunning] = useState(false)
  const [runResult, setRunResult] = useState('')
  const [showRunPanel, setShowRunPanel] = useState(false)

  useEffect(() => {
    workflowsApi.list().then(setWorkflows)
    agentsApi.list().then(setAgents)
    workflowsApi.templates().then(setTemplates)
  }, [])

  const loadWorkflow = (wf: Workflow) => {
    setSelectedWorkflow(wf)
    const graph = wf.graph || { nodes: [], edges: [] }
    const rfNodes: Node[] = (graph.nodes || []).map((n) => ({
      id: n.id,
      type: n.type === 'agent' ? 'agent' : 'default',
      position: n.position,
      data: n.data,
    }))
    const rfEdges: Edge[] = (graph.edges || []).map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      style: { stroke: '#6366f1', strokeWidth: 2 },
      labelStyle: { fill: '#94a3b8', fontSize: 11 },
      labelBgStyle: { fill: 'var(--bg-surface)' },
    }))
    setNodes(rfNodes)
    setEdges(rfEdges)
  }

  const onConnect = useCallback(
    (params: Connection) => setEdges(eds => addEdge({
      ...params,
      style: { stroke: '#6366f1', strokeWidth: 2 },
    }, eds)),
    [setEdges]
  )

  const addAgentNode = (agent: Agent) => {
    const id = `node_${Date.now()}`
    const newNode: Node = {
      id,
      type: 'agent',
      position: { x: 100 + nodes.length * 220, y: 200 },
      data: {
        label: agent.name,
        agentId: agent.id,
        agentName: agent.name,
        role: agent.role,
        tools: agent.tools,
        color: '#6366f1',
        isStart: nodes.length === 0,
      },
    }
    setNodes(nds => [...nds, newNode])
  }

  const saveWorkflow = async () => {
    if (!selectedWorkflow) {
      // Create new
      const name = prompt('Workflow name:')
      if (!name) return
      const graph = {
        nodes: nodes.map(n => ({ id: n.id, type: n.type ?? 'default', position: n.position, data: n.data })),
        edges: edges.map(e => ({ id: e.id, source: e.source, target: e.target, label: String(e.label ?? '') })),
      }
      try {
        const wf = await workflowsApi.create({ name, graph })
        setWorkflows(prev => [wf, ...prev])
        setSelectedWorkflow(wf)
        toast.success('Workflow saved')
      } catch {
        toast.error('Failed to save')
      }
    } else {
      const graph = {
        nodes: nodes.map(n => ({ id: n.id, type: n.type ?? 'default', position: n.position, data: n.data })),
        edges: edges.map(e => ({ id: e.id, source: e.source, target: e.target, label: String(e.label ?? '') })),
      }
      try {
        const updated = await workflowsApi.update(selectedWorkflow.id, { graph })
        setWorkflows(prev => prev.map(w => w.id === updated.id ? updated : w))
        toast.success('Workflow saved')
      } catch {
        toast.error('Failed to save')
      }
    }
  }

  const runWorkflow = async () => {
    if (!selectedWorkflow || !runInput.trim()) return
    setRunning(true)
    setRunResult('')
    try {
      const result = await workflowsApi.run(selectedWorkflow.id, runInput)
      setRunResult(result.response)
      toast.success('Workflow completed')
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Workflow failed'
      toast.error(msg)
      setRunResult(`Error: ${msg}`)
    } finally {
      setRunning(false)
    }
  }

  const loadTemplate = async (templateName: string) => {
    try {
      const wf = await workflowsApi.fromTemplate(templateName)
      setWorkflows(prev => [wf, ...prev])
      loadWorkflow(wf)
      setShowTemplates(false)
      toast.success(`Template "${wf.name}" loaded`)
    } catch {
      toast.error('Failed to load template')
    }
  }

  const deleteWorkflow = async (wf: Workflow) => {
    if (!confirm(`Delete "${wf.name}"?`)) return
    try {
      await workflowsApi.delete(wf.id)
      setWorkflows(prev => prev.filter(w => w.id !== wf.id))
      if (selectedWorkflow?.id === wf.id) {
        setSelectedWorkflow(null)
        setNodes([])
        setEdges([])
      }
      toast.success('Deleted')
    } catch {
      toast.error('Failed to delete')
    }
  }

  return (
    <div className="flex h-full">
      {/* Left sidebar — workflow list */}
      <div className="w-56 border-r flex flex-col"
        style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
        <div className="px-3 py-4 border-b" style={{ borderColor: 'var(--border)' }}>
          <h2 className="text-sm font-semibold text-white mb-3">Workflows</h2>
          <div className="space-y-1.5">
            <button onClick={() => { setSelectedWorkflow(null); setNodes([]); setEdges([]) }}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium text-white transition-all hover:opacity-90"
              style={{ background: 'var(--accent)' }}>
              <Plus size={13} /> New Workflow
            </button>
            <button onClick={() => setShowTemplates(!showTemplates)}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all hover:bg-white/5"
              style={{ color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
              <Layers size={13} /> Templates
            </button>
          </div>
        </div>

        {/* Templates dropdown */}
        {showTemplates && (
          <div className="border-b" style={{ borderColor: 'var(--border)' }}>
            {templates.map((t) => (
              <button key={t.template_name as string}
                onClick={() => loadTemplate(t.template_name as string)}
                className="w-full text-left px-3 py-2.5 hover:bg-white/5 transition-colors">
                <div className="text-xs font-medium text-white">{t.name as string}</div>
                <div className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                  {t.node_count as number} agents
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Workflow list */}
        <div className="flex-1 overflow-auto py-2">
          {workflows.map(wf => (
            <div key={wf.id}
              className={`group flex items-center gap-2 px-3 py-2.5 cursor-pointer transition-colors ${
                selectedWorkflow?.id === wf.id ? 'bg-indigo-500/10' : 'hover:bg-white/5'
              }`}
              onClick={() => loadWorkflow(wf)}>
              <GitBranch size={14} style={{
                color: selectedWorkflow?.id === wf.id ? 'var(--accent)' : 'var(--text-secondary)'
              }} />
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium text-white truncate">{wf.name}</div>
                {wf.is_template && (
                  <div className="text-xs" style={{ color: 'var(--accent)' }}>template</div>
                )}
              </div>
              <button onClick={e => { e.stopPropagation(); deleteWorkflow(wf) }}
                className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:text-red-400 transition-all"
                style={{ color: 'var(--text-secondary)' }}>
                <Trash2 size={11} />
              </button>
            </div>
          ))}
        </div>

        {/* Add agent to canvas */}
        {(selectedWorkflow || nodes.length >= 0) && (
          <div className="border-t p-3" style={{ borderColor: 'var(--border)' }}>
            <div className="text-xs font-medium mb-2" style={{ color: 'var(--text-secondary)' }}>
              Add Agent Node
            </div>
            <div className="space-y-1 max-h-40 overflow-auto">
              {agents.map(agent => (
                <button key={agent.id} onClick={() => addAgentNode(agent)}
                  className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs hover:bg-white/5 transition-colors text-left">
                  <div className="w-5 h-5 rounded flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                    style={{ background: 'var(--accent)' }}>
                    {agent.name[0]}
                  </div>
                  <span className="text-white truncate">{agent.name}</span>
                </button>
              ))}
              {agents.length === 0 && (
                <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  Create agents first
                </p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Canvas */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="flex items-center gap-2 px-4 py-2.5 border-b"
          style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
          <span className="text-sm font-medium text-white flex-1">
            {selectedWorkflow ? selectedWorkflow.name : 'New Workflow'}
          </span>
          <button onClick={saveWorkflow}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-white transition-all hover:opacity-90"
            style={{ background: 'rgba(99,102,241,0.2)', border: '1px solid var(--accent)', color: 'var(--accent)' }}>
            <Save size={13} /> Save
          </button>
          {selectedWorkflow && (
            <button onClick={() => setShowRunPanel(!showRunPanel)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-white transition-all hover:opacity-90"
              style={{ background: 'var(--accent)' }}>
              <Play size={13} /> Run
            </button>
          )}
        </div>

        <div className="flex-1 relative">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
            attributionPosition="bottom-right"
          >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#2a2a4a" />
            <Controls />
            <MiniMap
              nodeColor={() => '#6366f1'}
              maskColor="rgba(0,0,0,0.5)"
            />
          </ReactFlow>

          {nodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="text-center">
                <GitBranch size={48} className="mx-auto mb-4 opacity-10" style={{ color: 'var(--accent)' }} />
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  Add agents from the sidebar or load a template
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Run panel */}
      {showRunPanel && selectedWorkflow && (
        <div className="w-80 border-l flex flex-col"
          style={{ background: 'var(--bg-surface)', borderColor: 'var(--border)' }}>
          <div className="flex items-center justify-between px-4 py-3 border-b"
            style={{ borderColor: 'var(--border)' }}>
            <h3 className="text-sm font-semibold text-white">Run Workflow</h3>
            <button onClick={() => setShowRunPanel(false)}
              className="p-1 rounded hover:bg-white/10" style={{ color: 'var(--text-secondary)' }}>
              <X size={14} />
            </button>
          </div>
          <div className="p-4 space-y-3 flex-1">
            <div>
              <label className="block text-xs mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                Input Message
              </label>
              <textarea value={runInput} onChange={e => setRunInput(e.target.value)}
                rows={4} placeholder="What should the workflow do?"
                className="w-full px-3 py-2 rounded-lg text-sm text-white border outline-none focus:border-indigo-500 resize-none"
                style={{ background: 'var(--bg-base)', borderColor: 'var(--border)' }} />
            </div>
            <button onClick={runWorkflow} disabled={running || !runInput.trim()}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium text-white transition-all hover:opacity-90 disabled:opacity-50"
              style={{ background: 'var(--accent)' }}>
              {running ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Running...
                </>
              ) : (
                <><Play size={14} /> Execute</>
              )}
            </button>

            {runResult && (
              <div className="rounded-lg p-3 border text-sm"
                style={{ background: 'var(--bg-base)', borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
                <div className="text-xs font-medium mb-2 flex items-center gap-1"
                  style={{ color: 'var(--accent)' }}>
                  <ChevronRight size={12} /> Result
                </div>
                <p className="whitespace-pre-wrap text-xs leading-relaxed">{runResult}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
