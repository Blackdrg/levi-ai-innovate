import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Cpu, 
  Database, 
  Activity, 
  History, 
  ShieldCheck, 
  Terminal,
  LogOut,
  Zap
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { CircuitBreaker } from '../components/CircuitBreaker';
import { RBACGuard } from '../components/RBACGuard';
import { motion } from 'framer-motion';

export const Shell: React.FC = () => {
  const { user, logout } = useAuth();

  const navItems = [
    { to: '/', icon: <Terminal size={20} />, label: 'TASK PLENUM' },
    { to: '/agents', icon: <Cpu size={20} />, label: 'AGENT SWARM' },
    { to: '/memory', icon: <Database size={20} />, label: 'MEMORY GRID' },
    { to: '/inference', icon: <Zap size={20} />, label: 'NEURAL EXEC' },
    { to: '/metrics', icon: <Activity size={20} />, label: 'TELEMETRY' },
    { to: '/history', icon: <History size={20} />, label: 'AUDIT LOG' },
    { to: '/security', icon: <ShieldCheck size={20} />, label: 'SECURITY', roles: ['Core'] as any },
  ];

  return (
    <div className="shell-layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo-box">
             <motion.div animate={{ rotate: [0, 90, 180, 270, 360] }} transition={{ repeat: Infinity, duration: 4, ease: "linear" }}>
                <Activity className="text-blue-500" />
             </motion.div>
          </div>
          <span className="brand-name">LEVI-AI <small>v14.0</small></span>
        </div>

        <nav className="sidebar-nav">
          {navItems.map(item => (
            <RBACGuard key={item.to} roles={item.roles || ['User', 'Provider', 'Core']}>
              <NavLink to={item.to} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                {item.icon}
                <span>{item.label}</span>
              </NavLink>
            </RBACGuard>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-profile">
            <div className="avatar">{user?.email?.[0].toUpperCase() || 'U'}</div>
            <div className="user-info">
              <span className="user-email">{user?.email || 'sovereign_user'}</span>
              <span className="user-role">{user?.role || 'GUEST'}</span>
            </div>
          </div>
          <button onClick={logout} className="logout-btn" title="Logout">
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      <main className="main-viewport">
        <header className="top-bar">
          <div className="breadcrumb">
            SYSTEM_STATUS: <span className="text-emerald-400">NOMINAL</span>
          </div>
          <div className="top-actions">
            <CircuitBreaker />
          </div>
        </header>

        <section className="content-area">
          <Outlet />
        </section>
      </main>

      <style>{`
        .shell-layout { display: flex; width: 100vw; height: 100vh; background: #020617; color: #f1f5f9; overflow: hidden; }
        .sidebar { width: 280px; background: #0f172a; border-right: 1px solid rgba(255,255,255,0.05); display: flex; flex-direction: column; padding: 1.5rem; }
        .brand { display: flex; align-items: center; gap: 1rem; margin-bottom: 3rem; }
        .logo-box { width: 40px; height: 40px; background: rgba(56, 189, 248, 0.1); border-radius: 8px; display: flex; align-items: center; justify-content: center; }
        .brand-name { font-family: 'JetBrains Mono', monospace; font-weight: 800; font-size: 1.25rem; letter-spacing: 0.1em; color: #f1f5f9; }
        .brand-name small { font-size: 0.6rem; color: #38bdf8; opacity: 0.8; }

        .sidebar-nav { flex: 1; display: flex; flex-direction: column; gap: 0.5rem; }
        .nav-link { display: flex; align-items: center; gap: 1rem; padding: 0.75rem 1rem; border-radius: 8px; color: #94a3b8; text-decoration: none; font-weight: 600; font-size: 0.85rem; transition: all 0.2s ease; border: 1px solid transparent; }
        .nav-link:hover { color: #f1f5f9; background: rgba(255,255,255,0.02); }
        .nav-link.active { color: #38bdf8; background: rgba(56, 189, 248, 0.05); border-color: rgba(56, 189, 248, 0.2); }

        .sidebar-footer { margin-top: 2rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 2rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
        .user-profile { display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0; }
        .avatar { width: 32px; height: 32px; background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 0.9rem; flex-shrink: 0; }
        .user-info { display: flex; flex-direction: column; min-width: 0; }
        .user-email { font-size: 0.75rem; color: #f1f5f9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 600; }
        .user-role { font-size: 0.65rem; color: #38bdf8; font-family: 'JetBrains Mono', monospace; font-weight: bold; }
        .logout-btn { background: transparent; border: none; color: #64748b; cursor: pointer; transition: color 0.2s; }
        .logout-btn:hover { color: #f1f5f9; }

        .main-viewport { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
        .top-bar { height: 60px; display: flex; align-items: center; justify-content: space-between; padding: 0 3rem; background: rgba(15, 23, 42, 0.4); backdrop-filter: blur(8px); border-bottom: 1px solid rgba(255,255,255,0.05); flex-shrink: 0; }
        .breadcrumb { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #64748b; letter-spacing: 0.1em; }
        .top-actions { display: flex; align-items: center; gap: 1.5rem; }

        .content-area { flex: 1; overflow-y: auto; background: radial-gradient(circle at 50% 0%, rgba(56, 189, 248, 0.05) 0%, transparent 70%); }
      `}</style>
    </div>
  );
};
