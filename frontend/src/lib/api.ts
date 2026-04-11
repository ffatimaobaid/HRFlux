import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to add auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('hrflux_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authApi = {
  login: (data: any) => api.post('/api/auth/login', data),
  signup: (data: any) => api.post('/api/auth/signup', data),
  getMe: () => api.get('/api/auth/me'),
};

export const chatApi = {
  employeeChat: (data: { user_id: string; question: string; model?: string }) => 
    api.post('/api/chat', data),
  adminChat: (data: { user_id: string; question: string; model?: string }) => 
    api.post('/api/admin/chat', data),
  getHistory: (userId: string) => api.get(`/api/chat/history/${userId}`),
  clearHistory: (userId: string) => api.delete(`/api/chat/history/${userId}`),
};

export const hrApi = {
  getEmployees: () => api.get('/api/employees'),
  getEmployee: (id: string) => api.get(`/api/employees/${id}`),
  getLeaveBalance: (id: string) => api.get(`/api/leave-balance/${id}`),
  submitLeaveRequest: (data: any) => api.post('/api/leave-requests', data),
  getLeaveRequests: (id: string) => api.get(`/api/leave-requests/${id}`),
  getAttendance: (id: string) => api.get(`/api/attendance/${id}`),
  getProactiveNotifications: () => api.get('/api/notifications/proactive'),
  updateNotification: (id: number, status: 'read' | 'dismissed') => api.patch(`/api/notifications/${id}`, { status }),
};

export const taskApi = {
  getTasks: (id: string) => api.get(`/api/tasks/${id}`),
  createTask: (data: any) => api.post('/api/tasks', data),
  updateTask: (id: number, data: any) => api.patch(`/api/tasks/${id}`, data),
};

export const adminApi = {
  getStats: () => api.get('/api/admin/stats'),
  getPendingLeaves: () => api.get('/api/admin/pending-leaves'),
  getActiveEscalations: () => api.get('/api/admin/active-escalations'),
  getLogs: () => api.get('/api/admin/logs'),
  getDocuments: () => api.get('/api/admin/documents'),
  uploadDocument: (formData: FormData) => api.post('/api/admin/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  deleteDocument: (id: string) => api.delete(`/api/admin/documents/${id}`),
  getChatEscalations: () => api.get('/api/admin/escalations/chat'),
  resolveChatEscalation: (id: number, note: string) => api.post(`/api/admin/escalations/chat/${id}/resolve`, { note }),
  resolveWorkflowEscalation: (id: number, note: string) => api.post(`/api/admin/escalations/workflow/${id}/resolve`, { note }),
  getConfig: () => api.get('/api/admin/config'),
  updateConfig: (data: any) => api.post('/api/admin/config', data),
  processLeave: (id: number, action: 'approve' | 'reject', comments?: string) => 
    api.post('/api/leave-approvals', { request_id: id, action, comments, approver_id: 'ADMIN' }),
};

export default api;
