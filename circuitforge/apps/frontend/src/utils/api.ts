import axios from 'axios'
import type { Project, ProjectSummary, SystemStatus, CatalogComponent, BOM } from '../types'

const api = axios.create({
  baseURL: '/api',
  timeout: 180000, // 3 min for AI operations
})

// ── Health ──────────────────────────────────────────────────────────────────

export const getHealth = () => api.get('/health').then(r => r.data)
export const getSystemStatus = (): Promise<SystemStatus> =>
  api.get('/system').then(r => r.data)
export const getModels = () => api.get('/models').then(r => r.data)
export const installModel = (model_name: string) =>
  api.post('/models/install', { model_name }).then(r => r.data)

// ── Catalog ─────────────────────────────────────────────────────────────────

export const getCatalog = (): Promise<CatalogComponent[]> =>
  api.get('/catalog').then(r => r.data)

// ── Projects ─────────────────────────────────────────────────────────────────

export const listProjects = (): Promise<ProjectSummary[]> =>
  api.get('/projects').then(r => r.data)

export const createProject = (user_request: string): Promise<Project> =>
  api.post('/projects', { user_request }).then(r => r.data)

export const getProject = (id: string): Promise<Project> =>
  api.get(`/projects/${id}`).then(r => r.data)

export const deleteProject = (id: string) =>
  api.delete(`/projects/${id}`).then(r => r.data)

// ── Workflow ──────────────────────────────────────────────────────────────────

export const planProject = (id: string): Promise<Project> =>
  api.post(`/projects/${id}/plan`).then(r => r.data)

export const generateProject = (id: string): Promise<Project> =>
  api.post(`/projects/${id}/generate`).then(r => r.data)

export const validateProject = (id: string) =>
  api.post(`/projects/${id}/validate`).then(r => r.data)

export const compileProject = (id: string) =>
  api.post(`/projects/${id}/compile`).then(r => r.data)

export const repairProject = (id: string) =>
  api.post(`/projects/${id}/repair`).then(r => r.data)

export const simulateProject = (id: string) =>
  api.post(`/projects/${id}/simulate`).then(r => r.data)

// ── Export ────────────────────────────────────────────────────────────────────

export const getProjectBOM = (id: string): Promise<BOM> =>
  api.get(`/projects/${id}/bom`).then(r => r.data)

export const getProjectLogs = (id: string) =>
  api.get(`/projects/${id}/logs`).then(r => r.data)

export const downloadProject = (id: string) => {
  window.open(`/api/projects/${id}/download`, '_blank')
}

// ── Error helper ──────────────────────────────────────────────────────────────

export function getErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.detail || err.message
  }
  if (err instanceof Error) return err.message
  return String(err)
}
