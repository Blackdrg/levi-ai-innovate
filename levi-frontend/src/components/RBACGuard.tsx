import React from 'react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../lib/types';

interface RBACGuardProps {
  roles: UserRole[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const RBACGuard: React.FC<RBACGuardProps> = ({ roles, children, fallback = null }) => {
  const { role, isAuthenticated } = useAuth();

  if (!isAuthenticated || !roles.includes(role)) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};
