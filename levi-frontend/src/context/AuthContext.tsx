import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, UserRole } from '../lib/types';
import { api } from '../lib/api';

interface AuthContextType {
  user: User | null;
  role: UserRole;
  isAuthenticated: boolean;
  login: (credentials: any) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const savedToken = localStorage.getItem('sovereign_token');
    const savedUser = localStorage.getItem('sovereign_user');
    
    if (savedToken && savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setIsLoading(false);
  }, []);

  const login = async (credentials: any) => {
    setIsLoading(true);
    try {
      const userData = await api.login(credentials);
      setUser(userData);
      localStorage.setItem('sovereign_token', userData.token || '');
      localStorage.setItem('sovereign_user', JSON.stringify(userData));
    } catch (err) {
      console.error('Login failed:', err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('sovereign_token');
    localStorage.removeItem('sovereign_user');
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      role: user?.role || 'User', 
      isAuthenticated: !!user, 
      login, 
      logout,
      isLoading
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
