import { motion } from "framer-motion";
import { cn } from "../utils/styles";

/**
 * Layout
 * Premium wrapper for the Sovereign UI.
 */
export const Layout = ({ children, header, sidebar }) => {
  return (
    <div className="flex flex-col h-screen bg-[#050505] text-white selection:bg-purple-500/30 overflow-hidden">
      {/* Header */}
      {header}

      <div className="flex flex-1 overflow-hidden relative">
        {/* Sidebar */}
        {sidebar}

        {/* Hero Background Glow */}
        <div className="fixed top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-600/5 blur-[120px] rounded-full z-0 pointer-events-none" />
        <div className="fixed bottom-[-10%] right-[-10%] w-[30%] h-[30%] bg-blue-600/5 blur-[100px] rounded-full z-0 pointer-events-none" />

        {/* Main Content Area */}
        <main className="flex-1 relative z-10 flex flex-col min-h-0 overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  );
};

