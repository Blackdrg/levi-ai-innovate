import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Type, Wind, Layers, Send, RefreshCw, Check, Copy } from "lucide-react";
import { studioService } from "../../services/studioService";
import { cn } from "../../utils/styles";

export const AIStudio = () => {
  const [types, setTypes] = useState([]);
  const [tones, setTones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const [trace, setTrace] = useState([]);
  
  const [form, setForm] = useState({
    type: "essay",
    topic: "",
    tone: "philosophical",
    depth: 5,
    language: "en"
  });

  useEffect(() => {
    const init = async () => {
      const [t, tn] = await Promise.all([
        studioService.getTypes(),
        studioService.getTones()
      ]);
      setTypes(t);
      setTones(tn);
      setLoading(false);
    };
    init();
  }, []);

  const handleGenerate = async () => {
    if (!form.topic.trim()) return;
    setGenerating(true);
    setResult(null);
    setTrace([]);

    // Simulate Trace Steps (In production, these come from backend metadata)
    const steps = ["Initializing Neural Mesh", "Hydrating Memory Context", "Scanning Vector Clusters", "Synthesizing Patterns", "Manifesting Content"];
    
    try {
      for (const step of steps) {
        setTrace(prev => [...prev, { id: Date.now(), text: step }]);
        await new Promise(r => setTimeout(r, 600));
      }
      
      const res = await studioService.generate(form);
      setResult(res);
    } catch (err) {
      console.error("Generation failed", err);
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return (
     <div className="flex-1 flex items-center justify-center text-white/20 uppercase tracking-widest text-xs">
        Hydrating Creative Matrix...
     </div>
  );

  return (
    <div className="flex-1 overflow-y-auto px-6 md:px-12 py-10">
      <div className="max-w-5xl mx-auto">
        <header className="mb-12">
           <h1 className="text-3xl md:text-5xl font-bold font-heading text-gradient mb-2">AI Studio</h1>
           <p className="text-xs uppercase tracking-[0.2em] text-white/40">Advanced Creative Orchestration</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Config Panel */}
          <div className="lg:col-span-5 space-y-6">
            <div className="glass p-6 rounded-3xl space-y-6">
              <div>
                <label className="text-[10px] uppercase tracking-widest text-white/40 mb-3 block">Content Dimension</label>
                <div className="grid grid-cols-2 gap-2">
                   {types.map(t => (
                     <button
                       key={t}
                       onClick={() => setForm({...form, type: t})}
                       className={cn(
                         "px-3 py-2 rounded-xl text-[10px] uppercase font-bold transition-all border",
                         form.type === t ? "bg-purple-500/20 border-purple-500 text-purple-400" : "bg-white/5 border-white/5 text-white/40 hover:border-white/10"
                       )}
                     >
                       {t}
                     </button>
                   ))}
                </div>
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-widest text-white/40 mb-3 block">Resonance Tone</label>
                <select 
                  value={form.tone}
                  onChange={(e) => setForm({...form, tone: e.target.value})}
                  className="w-full bg-[#111] border border-white/10 rounded-xl px-4 py-3 text-xs focus:outline-none focus:border-purple-500/50"
                >
                  {tones.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-widest text-white/40 mb-3 block flex justify-between">
                  Reasoning Depth <span>{form.depth}</span>
                </label>
                <input 
                  type="range" min="1" max="10" 
                  value={form.depth}
                  onChange={(e) => setForm({...form, depth: parseInt(e.target.value)})}
                  className="w-full accent-purple-500" 
                />
              </div>

              <div>
                <label className="text-[10px] uppercase tracking-widest text-white/40 mb-3 block">Originator Prompt</label>
                <textarea
                  value={form.topic}
                  onChange={(e) => setForm({...form, topic: e.target.value})}
                  placeholder="Describe the manifestation topic..."
                  className="w-full bg-[#111] border border-white/10 rounded-xl px-4 py-3 text-xs focus:outline-none focus:border-purple-500/50 h-24 resize-none"
                />
              </div>

              <button
                onClick={handleGenerate}
                disabled={generating || !form.topic}
                className="w-full py-4 bg-gradient-sovereign rounded-2xl text-xs font-bold uppercase tracking-[0.2em] shadow-lg shadow-purple-500/20 glow-hover transition-all flex items-center justify-center gap-2"
              >
                {generating ? <RefreshCw className="animate-spin" size={16} /> : <Sparkles size={16} />}
                {generating ? "Manifesting..." : "Initialize Generation"}
              </button>
            </div>
          </div>

          {/* Results Panel */}
          <div className="lg:col-span-12 xl:col-span-7">
             <AnimatePresence mode="wait">
                {result ? (
                  <motion.div
                    key="result"
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="glass p-8 rounded-3xl h-full flex flex-col relative"
                  >
                    <div className="flex justify-between items-center mb-6">
                       <div className="text-[10px] uppercase tracking-widest text-purple-400 font-bold bg-purple-500/10 px-3 py-1 rounded-lg">Manifested Content</div>
                       <button className="p-2 glass rounded-xl text-white/40 hover:text-white transition-colors">
                          <Copy size={16} />
                       </button>
                    </div>
                    <div className="flex-1 overflow-y-auto text-sm text-white/70 leading-relaxed italic border-t border-white/5 pt-6 markdown-content">
                       {result.content || result.answer}
                    </div>
                  </motion.div>
                ) : (
                  <motion.div
                    key="placeholder"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="glass border-dashed border-2 border-white/5 p-12 rounded-3xl h-full flex flex-col items-center justify-center text-center text-white/20 min-h-[400px]"
                  >
                    {generating ? (
                      <div className="w-full max-w-sm space-y-4">
                        <div className="text-[10px] uppercase tracking-[0.3em] font-bold text-purple-500 mb-8 flex items-center justify-center gap-2">
                           <RefreshCw className="animate-spin" size={14} /> Reasoning Trace
                        </div>
                        <div className="space-y-3">
                          {trace.map((t, idx) => (
                            <motion.div 
                              key={t.id}
                              initial={{ opacity: 0, x: -10 }}
                              animate={{ opacity: 1, x: 0 }}
                              className={cn(
                                "flex items-center gap-3 text-[10px] uppercase tracking-widest",
                                idx === trace.length - 1 ? "text-white" : "text-white/20"
                              )}
                            >
                              <div className={cn("w-1 h-1 rounded-full", idx === trace.length - 1 ? "bg-purple-500 animate-pulse" : "bg-white/10")} />
                              {t.text}
                            </motion.div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <>
                        <Layers size={48} className="mb-4 opacity-50" />
                        <p className="text-sm uppercase tracking-widest">Waiting for Creative Sequence</p>
                      </>
                    )}
                  </motion.div>
                )}
             </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
};
