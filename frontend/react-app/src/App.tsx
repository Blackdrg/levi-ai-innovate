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
