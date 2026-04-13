// frontend_react/src/components/AuthBoundary.tsx
import React, { useEffect, useState } from 'react';
import './AuthBoundary.css';

/**
 * Sovereign v15.0: Authentication Boundary.
 * Verifies JWT presence and validity before rendering core dashboard.
 */

interface AuthProps {
  children: React.ReactNode;
}

export const AuthBoundary = ({ children }: { children: React.ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('sovereign_token');
      if (!token) {
        setIsAuthenticated(false);
        return;
      }

      try {
        // In a real system, we'd ping /api/v1/auth/verify
        // For now, we decode basic JWT info (e.g., expiry)
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload.exp * 1000 < Date.now()) {
          setIsAuthenticated(false);
        } else {
          setIsAuthenticated(true);
        }
      } catch (e) {
        setIsAuthenticated(false);
      }
    };

    checkAuth();
  }, []);

  if (isAuthenticated === null) {
    return <div className="loading">Initializing Cognitive Security...</div>;
  }

  if (!isAuthenticated) {
    return (
      <div className="auth-overlay">
        <h1>ACCESS RESTRICTED</h1>
        <p className="auth-message">
          Please authenticate with your Sovereign Identity to proceed.
        </p>
        <button 
          onClick={() => window.location.href = '/login'}
          className="login-button"
        >
          Initialize Login
        </button>
      </div>
    );
  }

  return <>{children}</>;
};
