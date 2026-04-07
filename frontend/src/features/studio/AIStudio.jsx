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
      try {
        const [t, tn] = await Promise.all([
          studioService.getTypes(),
          studioService.getTones()
        ]);
        setTypes(t);
        setTones(tn);
      } catch (err) {
        console.error("Studio hydration failed", err);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const handleGenerate = async () => {
    if (!form.topic.trim()) return;
    setGenerating(true);
    setResult(null);
    setTrace([]);

    const steps = [
      "Synchronizing Neural Mesh...",
      "Hydrating Ephemeral Context...",
      "Mapping Latent Vector Subspaces...",
      "Synthesizing Cognitive Waves...",
      "Manifesting Material Form..."
    ];
    
    try {
      for (const step of steps) {
        setTrace(prev => [...prev, { id: Date.now(), text: step }]);
        await new Promise(r => setTimeout(r, 800));
      }
      
      const res = await studioService.generate(form);
      setResult(res);
    } catch (err) {
      console.error("Manifestation collapse", err);
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return (
     <div className="flex-1 flex flex-col items-center justify-center space-y-4">
        <RefreshCw className="text-emerald-500 animate-spin" size={32} />
        <div className="text-[10px] uppercase tracking-[0.4em] text-white/20 font-black">Hydrating Creative Matrix</div>
     </div>
  );

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar bg-[#020202]">
      <div className="max-w-6xl mx-auto px-8 py-12 space-y-12">
        {/* Header Section */}
        <header className="flex items-end justify-between border-b border-white/5 pb-8">
           <div className="space-y-2">
              <div className="flex items-center gap-2">
                 <span className="w-10 h-[1px] bg-purple-500" />
                 <span className="text-[10px] uppercase tracking-[0.3em] text-purple-400 font-bold">Neural Harmonizer v13.1</span>
              </div>
              <h1 className="text-5xl font-heading font-black tracking-tighter text-white uppercase italic leading-none">
                 AI<span className="text-purple-500">.</span>Studio
              </h1>
              <p className="text-[11px] text-white/30 font-medium max-w-md">Orchestrate high-fidelity manifestations through advanced cognitive wave synthesis.</p>
           </div>
           <div className="hidden md:flex flex-col items-end gap-2 text-right">
              <div className="px-3 py-1.5 glass rounded-lg border border-purple-500/20 flex items-center gap-2">
                 <Wind className="text-purple-500 animate-pulse" size={14} />
                 <span className="text-[9px] font-mono text-purple-300 uppercase tracking-widest font-black">Flux: Synchronized</span>
              </div>
              <span className="text-[8px] text-white/10 font-mono">LATENT CLUSTER: AX-92</span>
           </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
          {/* Config Panel */}
          <div className="lg:col-span-5 space-y-8">
            <div className="glass p-8 rounded-[2rem] border border-white/5 space-y-8 shadow-2xl relative overflow-hidden">
              <div className="absolute -right-20 -top-20 w-40 h-40 bg-purple-500/10 blur-[80px] rounded-full pointer-events-none" />
              
              <section className="space-y-4">
                <label className="text-[10px] uppercase tracking-[0.2em] text-white/30 font-black flex items-center gap-2">
                   <Layers size={12} className="text-purple-500" /> Content Dimension
                </label>
                <div className="grid grid-cols-2 gap-3">
                   {types.map(t => (
                     <button
                       key={t}
                       onClick={() => setForm({...form, type: t})}
                       className={cn(
                         "relative group px-4 py-3 rounded-2xl text-[10px] uppercase font-black tracking-widest transition-all overflow-hidden border",
                         form.type === t 
                           ? "bg-white text-black border-white shadow-[0_0_20px_rgba(255,255,255,0.1)]" 
                           : "bg-white/5 border-white/5 text-white/40 hover:border-white/20 hover:bg-white/10"
                       )}
                     >
                       {t}
                       {form.type === t && <motion.div layoutId="active-type" className="absolute inset-0 bg-white" />}
                       <span className="relative z-10">{t}</span>
                     </button>
                   ))}
                </div>
              </section>

              <section className="space-y-4">
                <label className="text-[10px] uppercase tracking-[0.2em] text-white/30 font-black flex items-center gap-2">
                   <Type size={12} className="text-purple-500" /> Resonance Tone
                </label>
                <div className="relative group">
                  <select 
                    value={form.tone}
                    onChange={(e) => setForm({...form, tone: e.target.value})}
                    className="w-full bg-white/5 border border-white/5 rounded-2xl px-5 py-4 text-xs font-bold text-white/80 focus:outline-none focus:border-purple-500/40 transition-all appearance-none cursor-pointer"
                  >
                    {tones.map(t => <option key={t} value={t} className="bg-[#111]">{t.toUpperCase()}</option>)}
                  </select>
                  <div className="absolute right-5 top-1/2 -translate-y-1/2 pointer-events-none opacity-40">
                     <Wind size={14} />
                  </div>
                </div>
              </section>

              <section className="space-y-6">
                <div className="flex justify-between items-center text-[10px] uppercase tracking-[0.2em] text-white/30 font-black">
                   <span className="flex items-center gap-2"><Wind size={12} className="text-purple-500" /> Cognitive Depth</span>
                   <span className="text-purple-500 font-mono">{form.depth}</span>
                </div>
                <input 
                  type="range" min="1" max="10" 
                  value={form.depth}
                  onChange={(e) => setForm({...form, depth: parseInt(e.target.value)})}
                  className="w-full h-1.5 bg-white/5 rounded-full appearance-none cursor-pointer accent-purple-500 hover:accent-purple-400 transition-all" 
                />
              </section>

              <section className="space-y-4">
                <label className="text-[10px] uppercase tracking-[0.2em] text-white/30 font-black flex items-center gap-2">
                   <Sparkles size={12} className="text-purple-500" /> Originator Intent
                </label>
                <textarea
                  value={form.topic}
                  onChange={(e) => setForm({...form, topic: e.target.value})}
                  placeholder="Describe the desired manifestation..."
                  className="w-full h-40 bg-white/5 border border-white/5 rounded-[1.5rem] p-5 text-sm font-medium text-white placeholder:text-white/10 focus:outline-none focus:border-purple-500/40 transition-all resize-none leading-relaxed"
                />
              </section>

              <button
                onClick={handleGenerate}
                disabled={generating || !form.topic}
                className="group relative w-full py-5 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-2xl text-[11px] font-black uppercase tracking-[0.3em] text-white shadow-2xl hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-20 disabled:scale-100 overflow-hidden"
              >
                <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-10 transition-opacity" />
                <div className="flex items-center justify-center gap-3 relative z-10">
                   {generating ? <RefreshCw className="animate-spin" size={18} /> : <Sparkles size={18} />}
                   <span>{generating ? "Synthesizing..." : "Initiate Manifestation"}</span>
                </div>
              </button>
            </div>
          </div>

          {/* Results Panel */}
          <div className="lg:col-span-7">
             <AnimatePresence mode="wait">
                {result ? (
                  <motion.div
                    key="result"
                    initial={{ opacity: 0, scale: 0.98, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    className="glass p-10 rounded-[2.5rem] h-full border border-white/10 flex flex-col relative shadow-2xl overflow-hidden min-h-[600px]"
                  >
                    <div className="absolute -left-20 -bottom-20 w-60 h-60 bg-emerald-500/5 blur-[100px] rounded-full pointer-events-none" />
                    
                    <div className="flex justify-between items-center mb-10 pb-6 border-b border-white/5">
                       <div className="flex flex-col gap-1">
                          <span className="text-[9px] uppercase tracking-[0.4em] text-emerald-500 font-black">Pulse Result</span>
                          <h3 className="text-xs font-black uppercase tracking-widest text-white">Neural Manifestation Complete</h3>
                       </div>
                       <div className="flex gap-3">
                          <button 
                            onClick={() => {
                               navigator.clipboard.writeText(result.content || result.answer);
                            }}
                            className="p-3 glass rounded-xl text-white/30 hover:text-white hover:border-emerald-500/30 transition-all flex items-center gap-2"
                          >
                             <Check size={14} className="text-emerald-500" />
                             <span className="text-[9px] uppercase font-black">Persist</span>
                          </button>
                          <button className="p-3 glass rounded-xl text-white/30 hover:text-white transition-all">
                             <Copy size={14} />
                          </button>
                       </div>
                    </div>
                    
                    <div className="flex-1 overflow-y-auto custom-scrollbar text-[15px] text-white/80 leading-loose selection:bg-purple-500/30 font-medium">
                       <div className="prose prose-invert prose-sm max-w-none">
                          {result.content || result.answer}
                       </div>
                    </div>
                  </motion.div>
                ) : (
                  <motion.div
                    key="placeholder"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="glass border-2 border-dashed border-white/5 rounded-[2.5rem] h-full flex flex-col items-center justify-center text-center p-12 min-h-[600px] relative overflow-hidden group"
                  >
                    <div className="absolute inset-0 bg-gradient-to-b from-transparent via-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-1000" />
                    
                    {generating ? (
                      <div className="w-full max-w-sm space-y-10 relative z-10">
                        <div className="flex flex-col items-center gap-4">
                           <div className="w-16 h-16 rounded-3xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20 shadow-[0_0_30px_rgba(147,51,234,0.2)]">
                              <RefreshCw className="animate-spin text-purple-400" size={28} />
                           </div>
                           <h4 className="text-[10px] uppercase tracking-[0.4em] font-black text-white/40">Synthesizing Waves</h4>
                        </div>
                        
                        <div className="space-y-4">
                          {trace.map((t, idx) => (
                            <motion.div 
                              key={t.id}
                              initial={{ opacity: 0, x: -10 }}
                              animate={{ opacity: 1, x: 0 }}
                              className={cn(
                                "flex items-center gap-4 text-[10px] uppercase tracking-[0.2em] font-black px-4 py-3 rounded-xl transition-all",
                                idx === trace.length - 1 ? "bg-white/5 text-white" : "text-white/10"
                              )}
                            >
                              <div className={cn(
                                "w-1 h-3 rounded-full transition-all", 
                                idx === trace.length - 1 ? "bg-purple-500 animate-pulse" : "bg-white/5"
                              )} />
                              {t.text}
                            </motion.div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center gap-6 relative z-10">
                        <div className="w-24 h-24 rounded-[2rem] bg-white/5 flex items-center justify-center border border-white/5 group-hover:border-purple-500/20 transition-all duration-1000 rotate-45 group-hover:rotate-180">
                           <Layers size={40} className="text-white/20 -rotate-45 group-hover:-rotate-180 transition-all duration-1000" />
                        </div>
                        <div className="space-y-2">
                           <h4 className="text-xs font-black uppercase tracking-[0.3em] text-white">Quantum Void</h4>
                           <p className="text-[10px] text-white/20 uppercase tracking-widest max-w-[200px] leading-relaxed">Awaiting cognitive intent to manifest the next creation.</p>
                        </div>
                      </div>
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
