import { Routes, Route, Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Database, Activity, ShieldCircle, LogOut, Shield } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import MissionPanel from '../components/MissionPanel'
import { MemoryExplorer } from './MemoryExplorer'
import { AgentGrid } from '../components/AgentGrid'
import { SecurityPanel } from './SecurityPanel'

export default function Dashboard() {
  const { user, logout } = useAuthStore()
  const location = useLocation()

  const navItems = [
    { name: 'Missions', path: '/', icon: <LayoutDashboard size={20} /> },
    { name: 'Memory',   path: '/memory', icon: <Database size={20} /> },
    { name: 'Agents',   path: '/agents', icon: <Activity size={20} /> },
    { name: 'Security', path: '/settings', icon: <ShieldCircle size={20} /> },
  ]

  return (
    <div className="flex h-screen bg-neutral-950 text-white overflow-hidden font-['Outfit']">
      {/* Sidebar */}
      <aside className="w-64 glass border-r border-white/5 flex flex-col p-4 z-10 shadow-2xl">
        <div className="flex items-center gap-3 px-2 mb-10 group cursor-default">
          <div className="p-2 rounded-xl bg-purple-600/10 border border-purple-500/20 group-hover:bg-purple-600/20 group-hover:border-purple-500/40 transition-all duration-300">
            <Shield className="text-purple-500" size={24} />
          </div>
          <div>
            <h1 className="text-lg font-black tracking-tight leading-none uppercase">LEVI-AI</h1>
            <span className="text-[10px] uppercase tracking-widest font-black text-purple-500 opacity-80">Sovereign v15.0</span>
          </div>
        </div>

        <nav className="flex-1 space-y-2">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group ${
                location.pathname === item.path
                  ? 'bg-purple-600/10 text-purple-400 border-l-[3px] border-purple-500 translate-x-1 shadow-lg shadow-purple-900/10'
                  : 'text-neutral-500 hover:text-neutral-200 hover:bg-white/5'
              }`}
            >
              <span className={`transition-all duration-300 ${location.pathname === item.path ? 'text-purple-400' : 'text-neutral-600 group-hover:text-neutral-400'}`}>
                {item.icon}
              </span>
              <span className="text-sm font-black tracking-tight uppercase">{item.name}</span>
            </Link>
          ))}
        </nav>

        {/* User Card */}
        <div className="mt-auto pt-6 border-t border-white/5">
          <div className="flex items-center gap-3 p-3 rounded-2xl bg-neutral-900/40 border border-white/5 mb-4 shadow-sm group">
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-purple-600 to-cyan-600 flex items-center justify-center font-black text-xs group-hover:rotate-12 transition-transform shadow-lg shadow-purple-900/20">
              {user?.email?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-black truncate">{user?.email || 'User Session'}</p>
              <p className="text-[10px] text-neutral-500 uppercase font-black tracking-widest text-purple-500/60">Sovereign-Tier</p>
            </div>
          </div>
          
          <button 
            onClick={logout}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-red-600/5 hover:bg-red-600/10 text-red-500/80 hover:text-red-500 text-xs font-black tracking-widest uppercase transition-all duration-300 border border-transparent hover:border-red-500/20 shadow-sm"
          >
            <LogOut size={14} />
            <span>Terminate</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 relative overflow-hidden flex flex-col">
        {/* Background Gradients */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-purple-600/5 blur-[120px] -z-10 rounded-full animate-pulse"></div>
        <div className="absolute bottom-0 left-0 w-[300px] h-[300px] bg-cyan-600/5 blur-[100px] -z-10 rounded-full"></div>
        
        <Routes>
          <Route path="/"        element={<MissionPanel />} />
          <Route path="/memory"  element={<MemoryExplorer />} />
          <Route path="/agents"  element={<AgentGrid />} />
          <Route path="/settings" element={<SecurityPanel />} />
        </Routes>
      </main>
    </div>
  )
}
