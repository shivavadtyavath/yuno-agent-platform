import axios from 'axios'

const BASE_URL = '/api/v1'

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Agent {
  id: string
  name: string
  role: string
  system_prompt: string
  model: string
  tools: string[]
  channels: string[]
  memory_enabled: boolean
  memory_window: string
  max_tokens_per_turn: string
  max_turns: string
  temperature: string
  schedule: string
  schedule_task: string
  personality: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AgentCreate {
  name: string
  role?: string
  system_prompt?: string
  model?: string
  tools?: string[]
  channels?: string[]
  memory_enabled?: boolean
  memory_window?: string
  max_tokens_per_turn?: string
  temperature?: string
  schedule?: string
  schedule_task?: string
  personality?: Record<string, unknown>
}

export interface Workflow {
  id: string
  name: string
  description: string
  graph: { nodes: FlowNode[]; edges: FlowEdge[] }
  is_template: boolean
  template_name: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface FlowNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: Record<string, unknown>
}

export interface FlowEdge {
  id: string
  source: string
  target: string
  label?: string
}

export interface Execution {
  id: string
  workflow_id?: string
  agent_id?: string
  trigger: string
  status: string
  input_text: string
  output_text: string
  error: string
  total_tokens: number
  estimated_cost_usd: string
  started_at: string
  finished_at?: string
  messages: Message[]
}

export interface Message {
  id: string
  role: string
  content: string
  agent_id?: string
  agent_name?: string
  tool_name?: string
  tokens: number
  created_at: string
}

export interface Tool {
  name: string
  description: string
}

export interface Stats {
  total_agents: number
  total_workflows: number
  total_executions: number
  completed_executions: number
  failed_executions: number
  total_tokens_used: number
  success_rate: number
}

// ─── Agent API ────────────────────────────────────────────────────────────────

export const agentsApi = {
  list: () => api.get<Agent[]>('/agents/').then(r => r.data),
  get: (id: string) => api.get<Agent>(`/agents/${id}`).then(r => r.data),
  create: (data: AgentCreate) => api.post<Agent>('/agents/', data).then(r => r.data),
  update: (id: string, data: Partial<AgentCreate>) =>
    api.put<Agent>(`/agents/${id}`, data).then(r => r.data),
  delete: (id: string) => api.delete(`/agents/${id}`),
  invoke: (id: string, message: string, executionId?: string) =>
    api.post(`/agents/${id}/invoke`, { message, execution_id: executionId }).then(r => r.data),
  clearMemory: (id: string) => api.post(`/agents/${id}/clear-memory`).then(r => r.data),
  tools: () => api.get<Tool[]>('/agents/tools').then(r => r.data),
}

// ─── Workflow API ─────────────────────────────────────────────────────────────

export const workflowsApi = {
  list: () => api.get<Workflow[]>('/workflows/').then(r => r.data),
  get: (id: string) => api.get<Workflow>(`/workflows/${id}`).then(r => r.data),
  create: (data: Partial<Workflow>) => api.post<Workflow>('/workflows/', data).then(r => r.data),
  update: (id: string, data: Partial<Workflow>) =>
    api.put<Workflow>(`/workflows/${id}`, data).then(r => r.data),
  delete: (id: string) => api.delete(`/workflows/${id}`),
  run: (id: string, message: string) =>
    api.post(`/workflows/${id}/run`, { message }).then(r => r.data),
  templates: () => api.get('/workflows/templates').then(r => r.data),
  fromTemplate: (templateName: string) =>
    api.post<Workflow>(`/workflows/from-template/${templateName}`).then(r => r.data),
}

// ─── Executions API ───────────────────────────────────────────────────────────

export const executionsApi = {
  list: (params?: { agent_id?: string; status?: string; limit?: number }) =>
    api.get<Execution[]>('/executions/', { params }).then(r => r.data),
  get: (id: string) => api.get<Execution>(`/executions/${id}`).then(r => r.data),
  stats: () => api.get<Stats>('/executions/stats/summary').then(r => r.data),
}
