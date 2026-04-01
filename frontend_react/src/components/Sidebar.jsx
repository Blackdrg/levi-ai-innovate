import { motion } from "framer-motion";
import { Zap, Database, Brain, Settings, MessageSquare, Plus, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "../utils/styles";
import { useState } from "react";

export const Sidebar = ({ activeView, onViewChange }) => {
  const [collapsed, setCollapsed] = useState(false);

  const menuItems = [
    { id: "chat", label: "Core Intelligence", icon: MessageSquare, color: "text-purple-400" },
    { id: "studio", label: "AI Studio", icon: Sparkles, color: "text-amber-400" },
    { id: "memory", label: "Memory Archive", icon: Database, color: "text-blue-400" },
    { id: "evolution", label: "Global Evolution", icon: Brain, color: "text-emerald-400" },
  ];


  return (
    <motion.div
      animate={{ width: collapsed ? 80 : 260 }}
      className="h-full glass border-r border-white/5 flex flex-col relative z-50 transition-all duration-300"
    >
      {/* Toggle Button */}
      <button 
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-20 w-6 h-6 rounded-full bg-[#111] border border-white/10 flex items-center justify-center text-white/40 hover:text-white transition-colors"
      >
        {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
      </button>

      {/* New Conversation Button */}
      <div className="p-4 mb-4">
        <button className="w-full flex items-center justify-center gap-2 py-3 bg-gradient-sovereign rounded-xl text-xs font-bold font-heading uppercase tracking-widest glow-hover transition-all">
          <Plus size={16} />
          {!collapsed && <span>New Resonance</span>}
        </button>
      </div>

      {/* Primary Navigation */}
      <nav className="flex-1 px-4 space-y-2">
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onViewChange(item.id)}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-3 rounded-xl transition-all group",
              activeView === item.id 
                ? "bg-white/5 border border-white/10 text-white" 
                : "text-white/40 hover:bg-white/5 hover:text-white"
            )}
          >
            <item.icon size={18} className={cn(activeView === item.id ? item.color : "group-hover:text-white transition-colors")} />
            {!collapsed && <span className="text-xs font-medium">{item.label}</span>}
          </button>
        ))}
      </nav>

      {/* Secondary / User Settings */}
      <div className="p-4 border-t border-white/5">
        <button className="w-full flex items-center gap-3 px-3 py-3 text-white/40 hover:text-white transition-colors">
          <Settings size={18} />
          {!collapsed && <span className="text-xs font-medium">System Terminal</span>}
        </button>
      </div>
    </motion.div>
  );
};
