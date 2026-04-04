import api from './client'

export const missionAPI = {
  create: (prompt, fidelityThreshold = 0.95) =>
    api.post('/v13/chat', { prompt, fidelity_threshold: fidelityThreshold }),

  getAll: () => api.get('/v13/missions'),

  getById: (id) => api.get(`/v13/missions/${id}`),

  cancel: (id) => api.post(`/v13/missions/${id}/cancel`),
}

export const memoryAPI = {
  search: (query, topK = 10) =>
    api.get('/v13/memory/search', { params: { q: query, top_k: topK } }),

  getAll: (tier) =>
    api.get('/v13/memory', { params: { tier } }),

  delete: (id) => api.delete(`/v13/memory/${id}`),
}

export const authAPI = {
  login: (email, password) =>
    api.post('/v13/auth/login', { email, password }),

  register: (email, password) =>
    api.post('/v13/auth/register', { email, password }),

  me: () => api.get('/v13/auth/me'),
}
