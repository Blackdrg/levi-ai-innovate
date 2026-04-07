import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertCircle, RefreshCcw, Home } from 'lucide-react';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary-view">
          <div className="error-card">
            <AlertCircle size={48} className="text-red-400" />
            <h1>KERNEL PANIC: NEURAL_FAULT_0xFC</h1>
            <p className="error-msg">{this.state.error?.message || 'An unexpected cognitive dissonance occurred.'}</p>
            
            <div className="error-actions">
              <button onClick={() => window.location.reload()} className="btn-retry">
                <RefreshCcw size={18} />
                RETRY HANDSHAKE
              </button>
              <a href="/" className="btn-home">
                <Home size={18} />
                RETURN TO PLENUM
              </a>
            </div>
          </div>

          <style>{`
            .error-boundary-view {
              height: 100vh; width: 100vw;
              display: flex; align-items: center; justify-content: center;
              background: #020617; color: #f1f5f9;
            }
            .error-card {
              max-width: 500px; text-align: center;
              background: rgba(239, 68, 68, 0.05);
              border: 1px solid rgba(239, 68, 68, 0.2);
              padding: 3rem; border-radius: 20px;
              backdrop-filter: blur(12px);
            }
            h1 { font-family: 'JetBrains Mono', monospace; font-size: 1.25rem; margin: 1.5rem 0 1rem; color: #f87171; letter-spacing: 0.1em; }
            .error-msg { font-size: 0.9rem; color: #94a3b8; margin-bottom: 2.5rem; font-family: 'JetBrains Mono', monospace; }
            .error-actions { display: flex; gap: 1rem; justify-content: center; }
            button, a {
              display: flex; align-items: center; gap: 0.75rem;
              padding: 0.75rem 1.5rem; border-radius: 8px;
              font-weight: 600; text-decoration: none; font-size: 0.9rem;
              cursor: pointer; transition: all 0.2s;
              font-family: 'Inter', sans-serif;
            }
            .btn-retry { background: #ef4444; color: white; border: none; }
            .btn-home { background: transparent; border: 1px solid rgba(255,255,255,0.1); color: #94a3b8; }
            button:hover { transform: translateY(-2px); filter: brightness(1.1); }
          `}</style>
        </div>
      );
    }

    return this.props.children;
  }
}
