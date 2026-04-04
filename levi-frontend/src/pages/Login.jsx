import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import { Shield, Mail, Lock, ArrowRight } from 'lucide-react'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { login, isLoading } = useAuthStore()
  const navigate = useNavigate()
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed. Access denied.')
    }
  }

  return (
    <div className="min-h-screen bg-neutral-950 flex items-center justify-center p-6 relative overflow-hidden font-['Outfit']">
      {/* Dynamic Background */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-purple-600/5 blur-[150px] -z-10 rounded-full animate-pulse"></div>
      
      <div className="w-full max-w-md animate-fade-in group">
        <div className="text-center mb-10">
          <div className="inline-flex p-4 rounded-3xl bg-purple-600/10 border border-purple-500/20 mb-6 group-hover:scale-110 group-hover:rotate-3 transition-all duration-500">
            <Shield size={48} className="text-purple-500" />
          </div>
          <h1 className="text-4xl font-black tracking-tight text-white mb-2">Sovereign Node</h1>
          <p className="text-neutral-500 font-black tracking-widest text-xs uppercase">Authorization Required v13.0</p>
        </div>

        <div className="glass p-8 rounded-[2.5rem] shadow-2xl relative">
          {error && (
            <div className="mb-6 p-4 rounded-2xl bg-red-600/10 border border-red-500/20 text-red-500 text-sm font-bold text-center animate-shake">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-1.5 px-1">
              <label className="text-[10px] uppercase tracking-[0.2em] font-black text-neutral-500">Node Identifier</label>
              <div className="relative group">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-600 group-focus-within:text-purple-500 transition-colors" size={18} />
                <input
                  type="email"
                  className="w-full bg-neutral-900/50 border border-neutral-800 rounded-2xl py-4 pl-12 pr-4 text-white focus:outline-none focus:border-purple-600/50 focus:ring-1 focus:ring-purple-600/20 transition-all font-bold placeholder:text-neutral-700"
                  placeholder="admin@sovereign.local"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5 px-1">
              <label className="text-[10px] uppercase tracking-[0.2em] font-black text-neutral-500">Security Key</label>
              <div className="relative group">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-600 group-focus-within:text-purple-500 transition-colors" size={18} />
                <input
                  type="password"
                  className="w-full bg-neutral-900/50 border border-neutral-800 rounded-2xl py-4 pl-12 pr-4 text-white focus:outline-none focus:border-purple-600/50 focus:ring-1 focus:ring-purple-600/20 transition-all font-bold placeholder:text-neutral-700"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-purple-600 hover:bg-purple-500 text-white font-black uppercase tracking-widest text-xs py-5 rounded-2xl flex items-center justify-center gap-3 shadow-xl shadow-purple-900/20 hover:shadow-purple-600/20 active:scale-[0.98] transition-all disabled:opacity-50"
            >
              {isLoading ? 'Infiltrating...' : 'Authorize Access'}
              <ArrowRight size={18} />
            </button>
          </form>
        </div>

        <div className="mt-10 text-center opacity-30 hover:opacity-100 transition-opacity">
          <p className="text-[10px] font-black uppercase tracking-[0.3em] text-neutral-500 cursor-default">
            Autonomous Sovereign Fabric &copy; 2026
          </p>
        </div>
      </div>
    </div>
  )
}
