import axios from 'axios';
import type { Workflow, Approval, Memory, AgentStats, Metrics } from '@/types';

const API_BASE = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// Auth
export const authAPI = {
  register: (email: string, password: string) =>
    api.post('/auth/register', { email, password }),
  login: (email: string, password: string) =>
    api.post<{ access_token: string }>('/auth/login', { email, password }),
  me: () => api.get('/auth/me'),
};

// Workflows
export const workflowAPI = {
  create: (task: string, require_approval: boolean, max_steps?: number) =>
    api.post<Workflow>('/workflows', { task, require_approval, max_steps }),
  list: (limit = 20, offset = 0) =>
    api.get<Workflow[]>(`/workflows?limit=${limit}&offset=${offset}`),
  get: (id: string) => api.get<Workflow & { events: Workflow['events'] }>(`/workflows/${id}`),
  events: (id: string) => api.get(`/workflows/${id}/events`),
  state: (id: string) => api.get(`/workflows/${id}/state`),
  cancel: (id: string) => api.delete(`/workflows/${id}`),
  metrics: () => api.get<Metrics>('/workflows/metrics'),
};

// Approvals
export const approvalAPI = {
  list: (status = 'pending') => api.get<Approval[]>(`/approvals?status=${status}`),
  approve: (id: string, note?: string) =>
    api.post<Approval>(`/approvals/${id}/approve`, { decision_note: note }),
  reject: (id: string, note?: string) =>
    api.post<Approval>(`/approvals/${id}/reject`, { decision_note: note }),
};

// Memory
export const memoryAPI = {
  list: (type = 'all') => api.get<Memory[]>(`/memory?memory_type=${type}`),
  create: (content: string, memory_type: string) =>
    api.post<Memory>('/memory', { content, memory_type }),
  update: (id: string, content: string, memory_type: string) =>
    api.put<Memory>(`/memory/${id}`, { content, memory_type }),
  delete: (id: string) => api.delete(`/memory/${id}`),
};

// Agents
export const agentAPI = {
  list: () => api.get<AgentStats[]>('/agents'),
};

// Admin (secret provider toggle)
export const adminAPI = {
  getProvider: () => api.get<{ active: string; label: string; model_label: string }>('/admin/provider'),
  toggleProvider: () => api.post<{ active: string; switched_from: string; label: string; model_label: string }>('/admin/provider/toggle'),
};

export default api;
