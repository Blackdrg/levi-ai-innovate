// frontend_react/src/components/ErrorBoundary.tsx
import React, { Component, ErrorInfo, ReactNode } from "react";
import './ErrorBoundary.css';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Sovereign v15.0: Cognitive Error Boundary.
 * Catches runtime failures and provides a graceful neural fallback.
 */
export class CognitiveErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Cognitive Crash Detected:", error, errorInfo);
    // In production, we'd log to Sentry or internal Telemetry
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="crash-overlay">
          <h1>SYSTEM ANOMALY</h1>
          <p className="crash-message">
            The cognitive visualization layer has encountered a critical failure.
            Attempting neural reset...
          </p>
          <button 
            onClick={() => window.location.reload()}
            className="reset-button"
          >
            RE-INITIALIZE CORE
          </button>
          {process.env.NODE_ENV === 'development' && (
            <pre className="error-stack">
              {this.state.error?.stack}
            </pre>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}
