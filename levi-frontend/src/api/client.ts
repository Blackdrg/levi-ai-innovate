import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Mocking some Auth logic for now or linking to existing store if needed
api.interceptors.request.use((config) => {
  // We can't use hooks here, but we can access localStorage or a global state
  const token = localStorage.getItem('levi-token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
