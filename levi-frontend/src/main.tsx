import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Shell } from './layouts/Shell';
import { Login } from './pages/Login';
import { Home } from './pages/Home';
import { AgentGrid } from './components/AgentGrid';
import { MemoryExplorer } from './pages/MemoryExplorer';
import { InferencePanel } from './pages/InferencePanel';
import { MetricsDashboard } from './pages/MetricsDashboard';
import { TaskHistory } from './pages/TaskHistory';
import { SecurityPanel } from './pages/SecurityPanel';
import { HITLModal } from './components/HITLModal';
import { ToastContainer } from './components/Toast';
import './index.css';

const qc = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) return <div className="loading-gate">CALIBRATING NEURAL LINK...</div>;
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<ProtectedRoute><Shell /></ProtectedRoute>}>
              <Route index element={<Home />} />
              <Route path="agents" element={<AgentGrid />} />
              <Route path="memory" element={<MemoryExplorer />} />
              <Route path="inference" element={<InferencePanel />} />
              <Route path="metrics" element={<MetricsDashboard />} />
              <Route path="history" element={<TaskHistory />} />
              <Route path="security" element={<SecurityPanel />} />
            </Route>
          </Routes>
          <HITLModal />
          <ToastContainer />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>
);

