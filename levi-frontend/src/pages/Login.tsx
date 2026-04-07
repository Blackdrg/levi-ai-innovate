import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Shield, Lock, User, Activity } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

export const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await login({ email, password });
      navigate('/');
    } catch (err) {
      setError('Neural signature mismatch. Access denied.');
    }
  };

  return (
    <div className="login-page">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="login-card"
      >
        <div className="login-header">
           <div className="brand-logo">
              <Activity size={32} className="text-blue-500" />
           </div>
           <h1>LEVI-AI v14.0</h1>
           <p>SYSTEM ACCESS GATEWAY</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="input-grp">
             <User size={18} />
             <input 
                type="email" 
                placeholder="NEURAL_ID (Email)" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
             />
          </div>

          <div className="input-grp">
             <Lock size={18} />
             <input 
                type="password" 
                placeholder="CRYPT_KEY (Password)" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
             />
          </div>

          <button type="submit" className="login-btn">
             <Shield size={18} />
             AUTHORIZE ENTITY
          </button>

          {error && <div className="error-msg">{error}</div>}
        </form>

        <div className="login-footer">
          <span>SOVEREIGN_OS v14.0.0-Autonomous-SOVEREIGN</span>
        </div>
      </motion.div>

      <style>{`
        .login-page { width: 100vw; height: 100vh; display: flex; align-items: center; justify-content: center; background: #020617; }
        .login-card { 
          width: 100%; 
          max-width: 400px; 
          background: rgba(15, 23, 42, 0.4); 
          border: 1px solid rgba(56, 189, 248, 0.2); 
          border-radius: 20px; 
          padding: 3rem; 
          backdrop-filter: blur(12px); 
          box-shadow: 0 20px 80px rgba(0,0,0,0.6); 
        }
        .login-header { text-align: center; margin-bottom: 2.5rem; }
        .brand-logo { margin-bottom: 1.5rem; display: flex; justify-content: center; }
        h1 { font-family: 'JetBrains Mono', monospace; font-size: 1.5rem; letter-spacing: 0.1em; color: #f1f5f9; margin-bottom: 0.5rem; }
        p { font-size: 0.7rem; color: #38bdf8; font-weight: 800; letter-spacing: 0.2em; }

        .login-form { display: flex; flex-direction: column; gap: 1.5rem; }
        .input-grp { 
          position: relative; 
          background: rgba(2, 6, 23, 0.4); 
          border: 1px solid rgba(255, 255, 255, 0.05); 
          border-radius: 10px; 
          display: flex; 
          align-items: center; 
          padding: 0 1rem; 
          color: #64748b; 
          transition: all 0.2s ease;
        }
        .input-grp:focus-within { border-color: #38bdf8; color: #38bdf8; }
        .input-grp input { 
          background: transparent; 
          border: none; 
          color: white; 
          padding: 1rem; 
          width: 100%; 
          outline: none; 
          font-family: 'Inter', sans-serif; 
        }
        .login-btn { 
          background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); 
          border: none; color: white; 
          padding: 1rem; 
          border-radius: 10px; 
          font-weight: 700; 
          font-family: 'JetBrains Mono', monospace; 
          display: flex; 
          align-items: center; 
          justify-content: center; 
          gap: 0.75rem; 
          cursor: pointer; 
          transition: all 0.2s ease; 
          margin-top: 1rem;
        }
        .login-btn:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(37, 99, 235, 0.3); }
        .error-msg { text-align: center; color: #ef4444; font-size: 0.8rem; font-family: 'JetBrains Mono', monospace; }

        .login-footer { margin-top: 3rem; text-align: center; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 1.5rem; }
        .login-footer span { font-size: 0.6rem; color: #475569; font-family: 'JetBrains Mono', monospace; font-weight: 600; letter-spacing: 0.05em; }
      `}</style>
    </div>
  );
};
