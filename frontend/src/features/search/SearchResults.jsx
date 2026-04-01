import { motion } from "framer-motion";
import { Globe, ArrowRight } from "lucide-react";
import { cn } from "../../utils/styles";

/**
 * SearchResults
 * Displays factual data points and source-backed answers.
 */
export const SearchResults = ({ results, query }) => {
  if (!results) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-4xl mx-auto mb-12"
    >
      <div className="glass p-6 md:p-8 rounded-3xl overflow-hidden relative">
        <div className="absolute top-0 right-0 p-8 opacity-5">
           <Globe size={120} />
        </div>
        
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-blue-500/20 rounded-lg text-blue-400">
             <Globe size={18} />
          </div>
          <h2 className="text-xl font-bold font-heading">Cosmic Retrieval</h2>
        </div>

        <div className="space-y-6 relative z-10">
          <div className="text-white/80 leading-relaxed text-sm md:text-base">
            {results.answer || "Retrieving relevant factual data points..."}
          </div>

          {results.sources && results.sources.length > 0 && (
            <div className="pt-6 border-t border-white/5">
              <h3 className="text-[10px] uppercase tracking-widest text-white/30 mb-4">Verified Sources</h3>
              <div className="flex flex-wrap gap-3">
                {results.sources.map((source, i) => (
                  <SourceTag key={i} source={source} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

const SourceTag = ({ source }) => (
  <a 
    href={source.url} 
    target="_blank" 
    rel="noreferrer"
    className="glass-pill px-3 py-1.5 rounded-full text-[10px] flex items-center gap-2 
               hover:border-blue-500/50 hover:bg-blue-500/10 transition-all group"
  >
    <span className="text-white/60 truncate max-w-[120px]">{source.name}</span>
    <ArrowRight size={10} className="text-white/20 group-hover:text-blue-400 group-hover:translate-x-1 transition-all" />
  </a>
);
