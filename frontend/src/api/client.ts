import axios from 'axios'

// 通过 Vite 代理访问后端（/api → localhost:8000）
const http = axios.create({ baseURL: '/api', timeout: 120000 })

// ---------- 类型（与后端契约对齐） ----------
export interface Agent {
  id: string
  name: string
  description?: string
  current_version_id?: string
  current_version?: Version | null
  created_at?: string
}
export interface Version {
  id: string
  agent_id: string
  version_no: number
  prompt: string
  workflow_config: WorkflowConfig
  capability_bindings: Record<string, unknown>
  knowledge_bindings: string[]
  model_settings: Record<string, unknown>
  status: string
}
export interface WorkflowConfig {
  start: string
  steps: Record<string, WorkflowNode>
}
export interface WorkflowNode {
  type: 'llm' | 'decision' | 'end' | 'http'
  prompt?: string | null
  save_as?: string | null
  next?: string | null
  branches?: Record<string, string> | null
  model_settings?: { model?: string; temperature?: number; max_tokens?: number } | null
  datasource?: string | null
  params?: Record<string, string> | null
  image_input?: boolean
}
export interface Trace {
  id: string
  agent_id: string
  version_id: string
  env: string
  input: string
  steps: TraceStep[]
  output: string
  model: string
  created_at?: string
}
export interface TraceStep {
  node_id: string
  node_type: string
  input?: string | null
  output?: unknown
  branch?: string | null
  model?: string | null
  prompt?: string | null
  latency_ms?: number | null
}
export interface Feedback {
  id: string
  trace_id: string
  text: string
  status: string
}
export interface Plan {
  id: string
  feedback_id: string
  agent_id: string
  problem_analysis: string
  root_cause: string
  suggestions: string[]
  changes: Change[]
  status: string
  applied_version_id?: string
}
export interface Change {
  target: string
  operation: string
  path?: string | null
  value?: unknown
  description: string
}
export interface Knowledge {
  id: string
  name: string
  kind: string
  content: string
}
export interface Capability {
  id: string
  name: string
  description: string
  behavior_instruction: string
}
export interface Datasource {
  id: string
  name: string
  base_url: string
  method: string
  headers: Record<string, unknown>
  kind?: string
}

// ---------- API ----------
export const api = {
  // agents / versions
  listAgents: () => http.get<Agent[]>('/agents').then((r) => r.data),
  getAgent: (id: string) => http.get<Agent>(`/agents/${id}`).then((r) => r.data),
  createAgent: (body: { name: string; description?: string }) =>
    http.post<Agent>('/agents', body).then((r) => r.data),
  deleteAgent: (id: string) => http.delete(`/agents/${id}`).then((r) => r.data),
  listVersions: (agentId: string) => http.get<Version[]>(`/agents/${agentId}/versions`).then((r) => r.data),
  createDraft: (agentId: string) => http.post<Version>(`/agents/${agentId}/versions`).then((r) => r.data),
  getVersion: (id: string) => http.get<Version>(`/versions/${id}`).then((r) => r.data),
  updateDraft: (id: string, body: Partial<Version>) => http.put<Version>(`/versions/${id}`, body).then((r) => r.data),

  // publish
  publish: (id: string, body: { approved_by: string }) =>
    http.post<Version>(`/versions/${id}/publish`, body).then((r) => r.data),
  rollback: (agentId: string, body: { target_version_id: string; approved_by: string }) =>
    http.post(`/agents/${agentId}/rollback`, body).then((r) => r.data),

  // run / traces / feedback
  run: (agentId: string, body: { input: string; image_url?: string; version_id?: string; env?: string }) =>
    http.post<Trace>(`/agents/${agentId}/run`, body).then((r) => r.data),
  listTraces: (params: { agent_id?: string; env?: string; limit?: number }) =>
    http.get<Trace[]>('/traces', { params }).then((r) => r.data),
  getTrace: (id: string) => http.get<Trace>(`/traces/${id}`).then((r) => r.data),
  addFeedback: (traceId: string, body: { text: string; created_by?: string }) =>
    http.post<Feedback>(`/traces/${traceId}/feedback`, body).then((r) => r.data),

  // optimize
  optimize: (feedbackId: string) => http.post<Plan>(`/feedbacks/${feedbackId}/optimize`).then((r) => r.data),
  getPlan: (id: string) => http.get<Plan>(`/plans/${id}`).then((r) => r.data),
  applyPlan: (id: string, body: { approved_by?: string }) =>
    http.post<Version>(`/plans/${id}/apply`, body).then((r) => r.data),
  rejectPlan: (id: string) => http.post(`/plans/${id}/reject`).then((r) => r.data),

  // knowledge
  listKnowledge: () => http.get<Knowledge[]>('/knowledge').then((r) => r.data),
  createKnowledge: (body: { name: string; kind: string; content: string; created_by?: string }) =>
    http.post<Knowledge>('/knowledge', body).then((r) => r.data),
  updateKnowledge: (name: string, body: { content: string }) =>
    http.put<Knowledge>(`/knowledge/${name}`, body).then((r) => r.data),
  bindKnowledge: (versionId: string, body: { name: string }) =>
    http.post<Version>(`/versions/${versionId}/knowledge`, body).then((r) => r.data),
  unbindKnowledge: (versionId: string, name: string) =>
    http.delete(`/versions/${versionId}/knowledge/${name}`).then((r) => r.data),

  // capabilities
  listCapabilities: () => http.get<Capability[]>('/capabilities').then((r) => r.data),
  createCapability: (body: Partial<Capability>) => http.post<Capability>('/capabilities', body).then((r) => r.data),
  bindCapability: (versionId: string, body: { name: string; params?: unknown }) =>
    http.post<Version>(`/versions/${versionId}/capabilities`, body).then((r) => r.data),
  saveAsCapability: (versionId: string, nodeId: string, body: { name: string; description?: string }) =>
    http.post<Capability>(`/versions/${versionId}/capabilities/${nodeId}/save-as`, body).then((r) => r.data),

  // datasources
  listDatasources: () => http.get<Datasource[]>('/datasources').then((r) => r.data),
  createDatasource: (body: Partial<Datasource>) => http.post<Datasource>('/datasources', body).then((r) => r.data),
  updateDatasource: (name: string, body: Partial<Datasource>) =>
    http.put<Datasource>(`/datasources/${name}`, body).then((r) => r.data),
  deleteDatasource: (name: string) => http.delete(`/datasources/${name}`).then((r) => r.data),
}
