import React, { createContext, useContext, useState, useEffect } from 'react';

export type ThemeType = 'neural' | 'dark' | 'light' | 'obsidian' | 'amethyst' | 'cyan' | 'gold' | 'rose' | 'aether' | 'emerald';

interface ThemeTokens {
  bg: string;
  s1: string;
  s2: string;
  p: string;
  pd: string;
  pdd: string;
  cy: string;
  cyd: string;
  pk: string;
  gn: string;
  am: string;
  rd: string;
  t1: string;
  t2: string;
  t3: string;
  bd: string;
  glow: (c: string, r?: number) => string;
}

const themes: Record<ThemeType, ThemeTokens> = {
  neural: {
    bg: "#F8FAFC", s1: "rgba(255,255,255,0.7)", s2: "rgba(255,255,255,0.65)",
    p: "#6366F1", pd: "#4F46E5", pdd: "#4338CA",
    cy: "#22D3EE", cyd: "#0891B2",
    pk: "#ec4899", gn: "#10b981", am: "#f59e0b", rd: "#ef4444",
    t1: "#0F172A", t2: "#64748B", t3: "#CBD5E1",
    bd: "#E2E8F0",
    glow: (c, r=16) => `0 4px ${r}px ${c}22`,
  },
  dark: {
    bg:"#03030e", s1:"rgba(7,7,20,0.94)", s2:"rgba(11,11,28,0.88)",
    p:"#b490f5", pd:"#8b5cf6", pdd:"#6d28d9",
    cy:"#22d3ee", cyd:"#0891b2",
    pk:"#f472b6", gn:"#34d399", am:"#fbbf24", rd:"#fb7185",
    t1:"#f1f5f9", t2:"#94a3b8", t3:"#1e293b",
    bd:"rgba(167,139,250,0.14)",
    glow: (c, r=20) => `0 0 ${r}px ${c}44`,
  },
  light: {
    bg:"#f8fafc", s1:"rgba(255,255,255,0.96)", s2:"rgba(241,245,249,0.9)",
    p:"#7c3aed", pd:"#8b5cf6", pdd:"#c4b5fd",
    cy:"#0ea5e9", cyd:"#0284c7",
    pk:"#db2777", gn:"#10b981", am:"#f59e0b", rd:"#ef4444",
    t1:"#0f172a", t2:"#64748b", t3:"#e2e8f0",
    bd:"rgba(124,58,237,0.1)",
    glow: (c, r=10) => `0 0 ${r}px ${c}22`,
  },
  obsidian: {
    bg:"#f1f5f9", s1:"rgba(255,255,255,0.98)", s2:"rgba(226,232,240,0.6)",
    p:"#334155", pd:"#1e293b", pdd:"#0f172a",
    cy:"#0284c7", cyd:"#075985",
    pk:"#be123c", gn:"#15803d", am:"#b45309", rd:"#b91c1c",
    t1:"#0f172a", t2:"#475569", t3:"#cbd5e1",
    bd:"rgba(30,41,59,0.08)",
    glow: (c, r=8) => `0 2px ${r}px ${c}11`,
  },
  aether: {
    bg:"#ffffff", s1:"rgba(255,255,255,0.95)", s2:"rgba(248,250,252,0.8)",
    p:"#6366f1", pd:"#4f46e5", pdd:"#4338ca",
    cy:"#06b6d4", cyd:"#0891b2",
    pk:"#ec4899", gn:"#10b981", am:"#f59e0b", rd:"#ef4444",
    t1:"#1e293b", t2:"#64748b", t3:"#f1f5f9",
    bd:"rgba(99,102,241,0.06)",
    glow: (c, r=12) => `0 4px ${r}px ${c}08`,
  },
  emerald: {
    bg:"#f0fdfa", s1:"rgba(255,255,255,0.9)", s2:"rgba(204,251,241,0.6)",
    p:"#059669", pd:"#047857", pdd:"#065f46",
    cy:"#0891b2", cyd:"#0e7490",
    pk:"#be185d", gn:"#10b981", am:"#f59e0b", rd:"#dc2626",
    t1:"#064e3b", t2:"#047857", t3:"#ccfbf1",
    bd:"rgba(5,150,105,0.1)",
    glow: (c, r=10) => `0 2px ${r}px ${c}1a`,
  },
  amethyst: {
    bg:"#0f051a", s1:"rgba(30,12,50,0.94)", s2:"rgba(45,20,70,0.88)",
    p:"#d8b4fe", pd:"#a855f7", pdd:"#7e22ce",
    cy:"#38bdf8", cyd:"#0ea5e9",
    pk:"#f472b6", gn:"#4ade80", am:"#fbbf24", rd:"#f87171",
    t1:"#f5f3ff", t2:"#c4b5fd", t3:"#4c1d95",
    bd:"rgba(168,85,247,0.2)",
    glow: (c, r=20) => `0 0 ${r}px ${c}44`,
  },
  cyan: {
    bg:"#000b0e", s1:"rgba(0,30,40,0.94)", s2:"rgba(0,45,60,0.88)",
    p:"#22d3ee", pd:"#0891b2", pdd:"#0e7490",
    cy:"#a5f3fc", cyd:"#22d3ee",
    pk:"#fb7185", gn:"#34d399", am:"#fbbf24", rd:"#f43f5e",
    t1:"#ecfeff", t2:"#a5f3fc", t3:"#164e63",
    bd:"rgba(34,211,238,0.2)",
    glow: (c, r=20) => `0 0 ${r}px ${c}44`,
  },
  gold: {
    bg:"#0a0800", s1:"rgba(30,25,0,0.94)", s2:"rgba(45,40,0,0.88)",
    p:"#fbbf24", pd:"#d97706", pdd:"#b45309",
    cy:"#22d3ee", cyd:"#0891b2",
    pk:"#f472b6", gn:"#34d399", am:"#fcd34d", rd:"#fb7185",
    t1:"#fffdf0", t2:"#fde68a", t3:"#78350f",
    bd:"rgba(251,191,36,0.2)",
    glow: (c, r=20) => `0 0 ${r}px ${c}44`,
  },
  rose: {
    bg:"#0b0004", s1:"rgba(40,0,15,0.94)", s2:"rgba(60,0,25,0.88)",
    p:"#fb7185", pd:"#e11d48", pdd:"#be123c",
    cy:"#22d3ee", cyd:"#0891b2",
    pk:"#fda4af", gn:"#34d399", am:"#fbbf24", rd:"#9f1239",
    t1:"#fff1f2", t2:"#fecdd3", t3:"#881337",
    bd:"rgba(251,113,133,0.2)",
    glow: (c, r=20) => `0 0 ${r}px ${c}44`,
  }
};

interface ThemeContextProps {
  theme: ThemeType;
  tokens: ThemeTokens;
  setTheme: (t: ThemeType) => void;
}

const ThemeContext = createContext<ThemeContextProps | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [themeName, setThemeName] = useState<ThemeType>(() => {
    const saved = localStorage.getItem('levi-theme') as ThemeType;
    return themes[saved] ? saved : 'neural';
  });

  const tokens = themes[themeName];

  useEffect(() => {
    localStorage.setItem('levi-theme', themeName);
    // Inject CSS variables
    const root = document.documentElement;
    Object.entries(tokens).forEach(([key, val]) => {
      root.style.setProperty(`--${key}`, val);
    });
  }, [themeName, tokens]);

  return (
    <ThemeContext.Provider value={{ theme: themeName, tokens, setTheme: setThemeName }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within ThemeProvider');
  return context;
};
