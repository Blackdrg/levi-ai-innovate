// frontend_react/src/App.tsx
import React from 'react';
import { NeuralProvider } from './contexts/NeuralContext';
import { Dashboard } from './components/Dashboard';
import './styles/theme.css';

export const App: React.FC = () => {
  return (
    <NeuralProvider>
      <Dashboard />
    </NeuralProvider>
  );
};

// frontend_react/src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
