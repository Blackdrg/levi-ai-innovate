import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { Task, AgentStatus, MemoryEntry, User } from './types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private axiosInstance: AxiosInstance;

  constructor() {
    this.axiosInstance = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.axiosInstance.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('sovereign_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.axiosInstance.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized globally
          localStorage.removeItem('sovereign_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth
  async login(credentials: any): Promise<User> {
    const response = await this.axiosInstance.post('/api/v1/auth/login', credentials);
    return response.data;
  }

  // Tasks
  async submitTask(prompt: string): Promise<Task> {
    const response = await this.axiosInstance.post('/api/v1/orchestrator/tasks', { prompt });
    return response.data;
  }

  async getTask(id: string): Promise<Task> {
    const response = await this.axiosInstance.get(`/api/v1/orchestrator/tasks/${id}`);
    return response.data;
  }

  async approveTask(id: string): Promise<void> {
    await this.axiosInstance.patch(`/api/v1/orchestrator/tasks/${id}/approve`);
  }

  // Agents
  async getAgents(): Promise<AgentStatus[]> {
    const response = await this.axiosInstance.get('/api/v1/agents');
    return response.data;
  }

  // Memory
  async searchMemory(query: string, type: 'working' | 'episodic' | 'relational' | 'semantic'): Promise<MemoryEntry[]> {
    const response = await this.axiosInstance.get(`/api/v1/memory/${type}/search`, { params: { query } });
    return response.data;
  }

  // Inference
  async getInferenceStatus(): Promise<any> {
    const response = await this.axiosInstance.get('/api/v1/scheduling/status');
    return response.data;
  }

  // Health
  async checkHealth(): Promise<any> {
    const response = await this.axiosInstance.get('/health');
    return response.data;
  }
}

export const api = new ApiClient();
