import { useState, useRef } from "react";
import { Upload as UploadIcon, FileText, X, CheckCircle, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "../../utils/styles";
import { documentService } from "../../services/documentService";

/**
 * Upload
 * Minimalist, high-speed document ingestion.
 */
export const Upload = ({ onComplete }) => {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | uploading | success | error
  const [error, setError] = useState(null);
  const fileRef = useRef(null);

  const handleSelect = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      if (selected.size > 10 * 1024 * 1024) {
        setError("File exceeds 10MB cosmic limit.");
        return;
      }
      setFile(selected);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setStatus("uploading");
    
    try {
      await documentService.upload(file);
      setStatus("success");
      setTimeout(() => {
        onComplete?.(file.name);
        setFile(null);
        setStatus("idle");
      }, 2000);
    } catch (err) {
      setError(err.message || "Ingestion failed.");
      setStatus("error");
    }
  };

  return (
    <div className="w-full max-w-lg mx-auto mb-8">
      <div 
        className={cn(
          "glass p-8 rounded-3xl border-dashed border-2 transition-all cursor-pointer relative overflow-hidden",
          status === "uploading" ? "border-purple-500/50" : "border-white/10 hover:border-white/20"
        )}
        onClick={() => status === "idle" && fileRef.current?.click()}
      >
        <input type="file" ref={fileRef} className="hidden" accept=".pdf,.docx,.txt" onChange={handleSelect} />
        
        <AnimatePresence mode="wait">
          {status === "idle" && (
            <motion.div 
               key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
               className="flex flex-col items-center justify-center text-center"
            >
              <div className="w-12 h-12 rounded-full bg-white/5 flex items-center justify-center mb-4 group-hover:bg-white/10 transition-colors">
                {file ? <FileText size={20} className="text-purple-400" /> : <UploadIcon size={20} className="text-white/40" />}
              </div>
              <p className="text-sm font-heading font-bold mb-1">
                {file ? file.name : "Initiate Ingestion"}
              </p>
              <p className="text-[10px] uppercase tracking-widest text-white/20">
                PDF, DOCX, TXT (MAX 10MB)
              </p>
              
              {file && (
                <button 
                  onClick={(e) => { e.stopPropagation(); handleUpload(); }}
                  className="mt-6 px-6 py-2 bg-gradient-sovereign rounded-xl text-xs font-bold glow-hover transition-all"
                >
                  Crystallize Knowledge
                </button>
              )}
            </motion.div>
          )}

          {status === "uploading" && (
            <motion.div 
              key="uploading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center text-center py-4"
            >
              <Loader2 size={32} className="text-purple-500 animate-spin mb-4" />
              <p className="text-sm font-bold font-heading mb-1 text-purple-400">Syncing with Brain...</p>
              <p className="text-[10px] uppercase tracking-widest text-white/20">Do not sever the link.</p>
            </motion.div>
          )}

          {status === "success" && (
            <motion.div 
              key="success" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center text-center py-4 text-emerald-400"
            >
              <CheckCircle size={32} className="mb-4" />
              <p className="text-sm font-bold font-heading mb-1">Knowledge Integrated.</p>
              <p className="text-[10px] uppercase tracking-widest text-emerald-500/50">Cosmic memory updated.</p>
            </motion.div>
          )}
        </AnimatePresence>

        {error && (
            <div className="absolute bottom-4 left-0 w-full text-center px-8">
                <p className="text-[10px] text-red-500/80 uppercase font-bold tracking-widest">{error}</p>
            </div>
        )}
      </div>
    </div>
  );
};
