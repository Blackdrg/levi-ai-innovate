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
import { ExecutionGraph } from "./features/execution/ExecutionGraph";
import { MissionAuditor } from "./components/MissionAuditor";
import Console from "./pages/Console";


import { Layout } from "./components/Layout";
import { Sidebar } from "./components/Sidebar";
import { Zap, Shield, User, Sparkles, Orbit } from "lucide-react";


function App() {
  const { decideRoute } = useBrain();
  const { startStream } = useStream();
  const messages = useChatStore((state) => state.messages);
  const mode = useChatStore((state) => state.mode);
  const addMessage = useChatStore((state) => state.addMessage);
  const isStreaming = useChatStore((state) => state.isStreaming);
  const executionGraph = useChatStore((state) => state.executionGraph);
  const executionResults = useChatStore((state) => state.executionResults);
  const auditResult = useChatStore((state) => state.auditResult);
  
  const [searchResults, setSearchResults] = useState(null);
  const [activeView, setActiveView] = useState("chat");

  const handleSend = async (message) => {
    setActiveView("chat");

    setSearchResults(null);
    addMessage({ role: "user", content: message });

    const { route } = await decideRoute(message);

    if (route === "search") {
        addMessage({ role: "assistant", content: "Accessing Sovereign Intelligence...", streaming: true });
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
          // Engages the Sovereign LeviBrain v14.0.0 Stream
          await startStream("/api/v1/orchestrator/chat/stream", { 
            method: "POST",
            body: JSON.stringify({ message, session_id: "s_main_v14" })
          });
        } catch (err) {
          console.error("Sovereign Stream failure", err);
          useChatStore.getState().updateLastMessage({ content: "The Sovereign OS brain encountered a quantum misalignment.", streaming: false });
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
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">V14.0.0</span>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 glass-pill rounded-full border border-emerald-500/20">
               <Shield size={14} className="text-emerald-500" />
               <span className="text-[9px] uppercase tracking-tighter text-emerald-500 font-bold">Secure Core</span>
            </div>
            <div className="w-8 h-8 rounded-full bg-gradient-sovereign p-[1px] cursor-pointer">
              <div className="w-full h-full bg-neural-bg rounded-full flex items-center justify-center">
                <Orbit size={14} className="text-neural-text/60 animate-spin-slow" />
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

              {executionGraph && (
                <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="px-6 pt-4">
                   <div className="mb-2 flex items-center justify-between">
                     <span className="text-[10px] uppercase tracking-widest text-neural-text/30 font-bold">Cognitive Mission Graph</span>
                     <span className="text-[9px] text-neural-text/20 italic">v14.0.0 DCN Architecture</span>
                   </div>
                  <ExecutionGraph graph={executionGraph} results={executionResults} />
                  
                  {/* High-Fidelity Mission Auditor Integration */}
                  <MissionAuditor />
                </motion.div>
              )}

              <ChatWindow />
            </div>
            
            <div className="w-full max-w-4xl mx-auto px-6 pb-10 relative z-20">
              <ChatInput onSend={handleSend} disabled={isStreaming} />
              <div className="absolute top-[-40px] left-1/2 -translate-x-1/2 flex items-center gap-2 text-neural-muted select-none">
                 <Sparkles size={12} strokeWidth={2.5} className="animate-pulse" />
                 <span className="text-[9px] uppercase tracking-widest font-heading font-bold">Sovereign OS v14.0.0 Active</span>
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
        ) : activeView === "evolution" ? (
          <motion.div key="evolution" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col overflow-hidden">
             <EvolutionDashboard />
          </motion.div>
        ) : (
          <motion.div key="console" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 flex flex-col overflow-hidden">
             <Console />
          </motion.div>
        )}


      </AnimatePresence>
    </Layout>
  )
}


export default App
