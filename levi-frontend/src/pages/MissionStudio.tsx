import React, { useCallback, useState } from 'react';
import { Activity, Thermometer, Cpu, Shield, Braces } from 'lucide-react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Panel,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

const initialNodes = [
  { 
    id: '1', 
    position: { x: 250, y: 5 }, 
    data: { label: 'Perception: Objective Entry' },
    style: { background: 'rgba(139, 92, 246, 0.1)', color: '#a78bfa', border: '1px solid #7c3aed', padding: '10px', borderRadius: '8px', fontWeight: 'bold' } 
  },
  { 
    id: '2', 
    position: { x: 100, y: 150 }, 
    data: { label: 'Wave 1: Research (Librarian)' },
    style: { background: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa', border: '1px solid #2563eb', padding: '10px', borderRadius: '8px' } 
  },
  { 
    id: '3', 
    position: { x: 400, y: 150 }, 
    data: { label: 'Wave 1: Recon (Scout)' },
    style: { background: 'rgba(45, 212, 191, 0.1)', color: '#2dd4bf', border: '1px solid #0d9488', padding: '10px', borderRadius: '8px' } 
  },
  { 
    id: '4', 
    position: { x: 250, y: 300 }, 
    data: { label: 'Wave 2: Reasoning (Cognition)' },
    style: { background: 'rgba(236, 72, 153, 0.1)', color: '#f472b6', border: '1px solid #db2777', padding: '10px', borderRadius: '8px' } 
  },
  { 
    id: '5', 
    position: { x: 250, y: 450 }, 
    data: { label: 'Wave 3: Synthesis (Final Output)' },
    style: { background: 'rgba(16, 185, 129, 0.1)', color: '#34d399', border: '1px solid #059669', padding: '10px', borderRadius: '8px' } 
  },
];

const initialEdges = [
  { id: 'e1-2', source: '1', target: '2', animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#475569' } },
  { id: 'e1-3', source: '1', target: '3', animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#475569' } },
  { id: 'e2-4', source: '2', target: '4', animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#475569' } },
  { id: 'e3-4', source: '3', target: '4', animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#475569' } },
  { id: 'e4-5', source: '4', target: '5', animated: true, markerEnd: { type: MarkerType.ArrowClosed, color: '#475569' } },
];

export const MissionStudio: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [sel, setSel] = useState<any>(null);

  const onConnect = useCallback(
    (params: any) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onNodeClick = useCallback((event: any, node: any) => {
    setSel(node);
  }, []);

  return (
    <div className="w-full h-full bg-neutral-950 flex">
      <div className="flex-1 flex flex-col border-r border-white/5">
        <header className="p-6 border-b border-white/5 flex justify-between items-center bg-white/[0.02] backdrop-blur-xl">
          <div>
            <h2 className="text-xl font-black uppercase tracking-tight">Mission Studio v22</h2>
            <p className="text-[10px] text-neutral-500 uppercase tracking-widest mt-1">Interactive DAG Visualizer • Multi-Agent Waves</p>
          </div>
          <button className="px-6 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-black uppercase transition-all shadow-lg shadow-purple-900/20 active:scale-95">
            Execute Sequence
          </button>
        </header>

        <div className="flex-1">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            fitView
            colorMode="dark"
          >
            <Background color="#1e293b" gap={20} />
            <Controls />
            <MiniMap 
              nodeColor={(n) => (n.style?.border as string) || '#475569'}
              maskColor="rgba(0,0,0,0.5)"
              className="rounded-2xl border border-white/10 overflow-hidden"
            />
            <Panel position="top-right" className="bg-neutral-900/80 p-4 rounded-2xl border border-white/10 backdrop-blur-xl text-[10px] uppercase font-bold tracking-widest text-neutral-400">
              Select nodes to view Forensic Contract (TEC)
            </Panel>
          </ReactFlow>
        </div>
      </div>

      {/* TEC Detail Panel */}
      <div className="w-80 bg-neutral-900/50 backdrop-blur-3xl overflow-y-auto border-l border-white/5 p-6 animate-fade-in">
        {sel ? (
          <div className="space-y-6">
            <div>
              <span className="text-[10px] font-black uppercase tracking-widest text-purple-500 block mb-2">TEC_IDENTIFIER</span>
              <h3 className="text-lg font-black font-mono">0x{sel.id.repeat(4)}</h3>
            </div>
            
            <div className="p-4 rounded-xl bg-white/5 border border-white/10">
              <span className="text-[10px] font-bold text-neutral-500 uppercase">Agent Assigned</span>
              <div className="text-sm font-black mt-1">{sel.data.label}</div>
            </div>

            <div className="space-y-2">
              <span className="text-[10px] font-bold text-neutral-500 uppercase">Contract Terms</span>
              {[
                { k: 'Pre-Conditions', v: 'Context_Verified' },
                { k: 'Post-Conditions', v: 'Memory_Crystallized' },
                { k: 'Security_Level', v: 'Container_Isolated' },
                { k: 'Proof_Type', v: 'Ed25519_Sovereign' },
                { k: 'Hardware_Anchor', v: 'TPM_PCR_VERIFIED' },
                { k: 'Signatures', v: 'KMS_Forensic_Sig' },
                { k: 'Neo4j_Audit', v: 'MISSION_NODE_ANCHORED' }
              ].map(term => (
                <div key={term.k} className="flex justify-between text-[10px] font-mono p-2 bg-black/20 rounded">
                  <span className="opacity-40">{term.k}</span>
                  <span className={`${term.v.includes('FAILED') ? 'text-red-500' : 'text-emerald-500'}`}>{term.v}</span>
                </div>
              ))}
            </div>

            <div className="pt-6 border-t border-white/5">
              <button onClick={() => setSel(null)} className="w-full py-2 text-[10px] font-black uppercase tracking-[0.2em] text-neutral-500 hover:text-white transition-colors">
                Clear Selection
              </button>
            </div>
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-30">
            <Braces size={40} />
            <span className="text-[10px] font-black uppercase tracking-widest">No Node Selected</span>
          </div>
        )}
      </div>

      <style>{`
        .react-flow__edge-path { stroke: #475569; stroke-width: 2; }
        .react-flow__handle { background: #475569; width: 8px; height: 8px; }
        .react-flow__controls-button { background: #1e293b; border-color: #334155; color: #94a3b8; }
        .react-flow__controls-button:hover { background: #334155; }
      `}</style>
    </div>
  );
};
