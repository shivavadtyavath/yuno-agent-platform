import { create } from 'zustand'
import type { Agent, Workflow, Execution, Stats } from '../api/client'

interface AppState {
  agents: Agent[]
  workflows: Workflow[]
  executions: Execution[]
  stats: Stats | null
  loading: boolean
  setAgents: (agents: Agent[]) => void
  setWorkflows: (workflows: Workflow[]) => void
  setExecutions: (executions: Execution[]) => void
  setStats: (stats: Stats) => void
  setLoading: (loading: boolean) => void
  addAgent: (agent: Agent) => void
  updateAgent: (agent: Agent) => void
  removeAgent: (id: string) => void
  addWorkflow: (workflow: Workflow) => void
  updateWorkflow: (workflow: Workflow) => void
  removeWorkflow: (id: string) => void
}

export const useAppStore = create<AppState>((set) => ({
  agents: [],
  workflows: [],
  executions: [],
  stats: null,
  loading: false,

  setAgents: (agents) => set({ agents }),
  setWorkflows: (workflows) => set({ workflows }),
  setExecutions: (executions) => set({ executions }),
  setStats: (stats) => set({ stats }),
  setLoading: (loading) => set({ loading }),

  addAgent: (agent) => set((s) => ({ agents: [agent, ...s.agents] })),
  updateAgent: (agent) =>
    set((s) => ({ agents: s.agents.map((a) => (a.id === agent.id ? agent : a)) })),
  removeAgent: (id) => set((s) => ({ agents: s.agents.filter((a) => a.id !== id) })),

  addWorkflow: (workflow) => set((s) => ({ workflows: [workflow, ...s.workflows] })),
  updateWorkflow: (workflow) =>
    set((s) => ({ workflows: s.workflows.map((w) => (w.id === workflow.id ? workflow : w)) })),
  removeWorkflow: (id) => set((s) => ({ workflows: s.workflows.filter((w) => w.id !== id) })),
}))
