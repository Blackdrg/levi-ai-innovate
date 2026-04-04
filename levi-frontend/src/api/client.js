import axios from 'axios'
import { useAuthStore } from '../stores/authStore'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'https://localhost/api',
  timeout: 30000,
})

// Auto-attach JWT on every request
api.interceptors.request.use(config => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auto-logout on 401
api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      useAuthStore.getState().setToken(null)
      useAuthStore.getState().setUser(null)
      // window.location.href = '/login' // Re-enable for production SPA
    }
    return Promise.reject(err)
  }
)

export default api
