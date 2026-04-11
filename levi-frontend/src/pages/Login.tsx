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
      setError('NEURAL_SIGNATURE_MISMATCH: Authentication rejected by Sovereign Gateway.');
    }
  };

  return (
    <div className="login-page font-['Outfit']">
      <motion.div 
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        className="login-card relative overflow-hidden"
      >
        {/* Decorative Glow */}
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-purple-600/10 blur-[60px] rounded-full"></div>
        <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-cyan-600/10 blur-[60px] rounded-full"></div>

        <div className="login-header mb-12 relative z-10">
           <div className="flex justify-center mb-6">
              <div className="p-4 rounded-2xl bg-purple-600/10 border border-purple-500/20 shadow-xl shadow-purple-900/10">
                <Shield size={40} className="text-purple-500" />
              </div>
           </div>
           <h1 className="text-3xl font-black tracking-tighter text-white uppercase italic">LEVI-AI <span className="text-purple-500">v15.0</span></h1>
           <p className="text-[10px] uppercase tracking-[0.3em] font-black text-neutral-500 mt-2">Sovereign Artificial Intelligence OS</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form space-y-6 relative z-10">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 px-4 py-3.5 bg-neutral-900/60 border border-white/5 rounded-xl focus-within:border-purple-500/40 transition-all">
               <User size={18} className="text-neutral-500" />
               <input 
                  type="email" 
                  placeholder="IDENTITY_KEY" 
                  className="bg-transparent border-none outline-none text-sm text-white placeholder-neutral-600 w-full font-bold"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
               />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center gap-2 px-4 py-3.5 bg-neutral-900/60 border border-white/5 rounded-xl focus-within:border-purple-500/40 transition-all">
               <Lock size={18} className="text-neutral-500" />
               <input 
                  type="password" 
                  placeholder="CRYPT_SIGNATURE" 
                  className="bg-transparent border-none outline-none text-sm text-white placeholder-neutral-600 w-full font-bold"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
               />
            </div>
          </div>

          <button type="submit" className="w-full bg-gradient-to-tr from-purple-600 to-purple-500 hover:to-purple-400 text-white py-4 rounded-xl font-black text-xs uppercase tracking-widest shadow-xl shadow-purple-900/20 active:scale-[0.98] transition-all flex items-center justify-center gap-3">
             <Activity size={18} />
             Authorize Access
          </button>

          {error && <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center text-red-500 text-[10px] font-black uppercase tracking-widest border border-red-500/20 p-3 rounded-lg bg-red-500/5">{error}</motion.div>}
        </form>

        <div className="login-footer mt-12 text-center border-t border-white/5 pt-8 relative z-10">
          <span className="text-[10px] font-black text-neutral-600 uppercase tracking-widest">Sovereign_Node_Status: <span className="text-green-500/60">GA-STABLE</span></span>
          <p className="text-[9px] text-neutral-700 font-bold mt-2 uppercase tracking-[0.2em]">LEVI-AI v15.0.0-GA GRADUATED</p>
        </div>
      </motion.div>

      <style>{`
        .login-page { width: 100vw; height: 100vh; display: flex; align-items: center; justify-content: center; background: #020617; position: relative; overflow: hidden; }
        .login-card { 
          width: 100%; 
          max-width: 440px; 
          background: rgba(15, 23, 42, 0.4); 
          border: 1px solid rgba(255, 255, 255, 0.05); 
          border-radius: 32px; 
          padding: 4rem; 
          backdrop-filter: blur(24px); 
          box-shadow: 0 40px 120px rgba(0,0,0,0.8); 
        }
      `}</style>
    </div>
  );
};
