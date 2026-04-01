import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useChatStore } from "./store/useChatStore";
import { useBrain } from "./hooks/useBrain";
import { useStream } from "./hooks/useStream";
import { ChatWindow } from "./features/chat/ChatWindow";
import { ChatInput } from "./features/chat/ChatInput";
import { Upload } from "./features/document/Upload";
import { SearchResults } from "./features/search/SearchResults";
import { MemoryVault } from "./features/memory/MemoryVault";
import { EvolutionDashboard } from "./features/evolution/EvolutionDashboard";
import { AIStudio } from "./features/studio/AIStudio";
import { searchService } from "./services/searchService";


import { Layout } from "./components/Layout";
import { Sidebar } from "./components/Sidebar";
import { Zap, Shield, User, Sparkles } from "lucide-react";


function App() {
  const { decideRoute } = useBrain();
  const { startStream } = useStream();
  const messages = useChatStore((state) => state.messages);
  const mode = useChatStore((state) => state.mode);
  const addMessage = useChatStore((state) => state.addMessage);
  const isStreaming = useChatStore((state) => state.isStreaming);
  
  const [searchResults, setSearchResults] = useState(null);
  const [activeView, setActiveView] = useState("chat");

  const handleSend = async (message) => {
    setActiveView("chat");

    setSearchResults(null);
    addMessage({ role: "user", content: message });

    const { route } = await decideRoute(message);

    if (route === "search") {
        addMessage({ role: "assistant", content: "Accessing the Collective Wisdom...", streaming: true });
        try {
            const res = await searchService.search(message);
            setSearchResults(res);
            useChatStore.getState().updateLastMessage({ content: res.answer, streaming: false });
        } catch (err) {
            useChatStore.getState().updateLastMessage({ content: "The search channel was disrupted.", streaming: false });
        }
    } else {
        addMessage({ role: "assistant", content: "", streaming: true });
        try {
          await startStream("/api/stream", { 
            method: "POST",
            body: JSON.stringify({ message, session_id: "default-session" })
          });
        } catch (err) {
          console.error("Stream failed", err);
          useChatStore.getState().updateLastMessage({ content: "The cosmic transmission was severed.", streaming: false });
        }
    }
  };

  return (
    <Layout 
      sidebar={<Sidebar activeView={activeView} onViewChange={setActiveView} />}
      header={
        <header className="h-16 px-6 glass flex items-center justify-between z-50">
          <div className="flex items-center gap-3">
            <div className="text-xl font-bold font-heading flex items-center gap-2">
              <Zap size={22} className="text-purple-500 fill-purple-500/20" />
              <span className="text-gradient">LEVI</span>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 glass-pill rounded-full border border-emerald-500/20">
               <Shield size={14} className="text-emerald-500" />
               <span className="text-[9px] uppercase tracking-tighter text-emerald-500 font-bold">Secure</span>
            </div>
            <div className="w-8 h-8 rounded-full bg-gradient-sovereign p-[1px] cursor-pointer">
              <div className="w-full h-full bg-[#050505] rounded-full flex items-center justify-center">
                <User size={14} className="text-white/60" />
              </div>
            </div>
          </div>
        </header>
      }
    >
      <AnimatePresence mode="wait">
        {activeView === "chat" ? (
          <motion.div 
            key="chat" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="flex-1 overflow-hidden flex flex-col pt-4"
          >
            <div className="flex-1 overflow-hidden flex flex-col">
              <AnimatePresence>
                {mode === "document" && (
                  <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="px-6">
                    <Upload onComplete={(filename) => console.log(`Ingested ${filename}`)} />
                  </motion.div>
                )}
              </AnimatePresence>

              {searchResults && (
                <div className="px-6 pt-4">
                  <SearchResults results={searchResults} query={""} />
                </div>
              )}

              <ChatWindow />
            </div>
            
            <div className="w-full max-w-4xl mx-auto px-6 pb-10 relative z-20">
              <ChatInput onSend={handleSend} disabled={isStreaming} />
              <div className="absolute top-[-40px] left-1/2 -translate-x-1/2 flex items-center gap-2 text-white/10 select-none">
                 <Sparkles size={12} />
                 <span className="text-[9px] uppercase tracking-widest font-heading font-bold">Resonance Core Active</span>
              </div>
            </div>
          </motion.div>
        ) : activeView === "studio" ? (
          <motion.div key="studio" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col overflow-hidden">
             <AIStudio />
          </motion.div>
        ) : activeView === "memory" ? (
          <motion.div key="memory" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col overflow-hidden">
             <MemoryVault />
          </motion.div>
        ) : (
          <motion.div key="evolution" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col overflow-hidden">
             <EvolutionDashboard />
          </motion.div>
        )}


      </AnimatePresence>
    </Layout>
  )
}


export default App
