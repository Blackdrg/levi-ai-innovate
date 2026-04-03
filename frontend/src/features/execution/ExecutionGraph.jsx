import React, { useMemo, useEffect } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';

const nodeTypes = {}; // Custom node types if needed

export const ExecutionGraph = ({ graph, results }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    if (!graph || !graph.nodes) return;

    // Calculate waves for better positioning
    const nodeWaves = {};
    const calculateWave = (nodeId) => {
      if (nodeWaves[nodeId] !== undefined) return nodeWaves[nodeId];
      const node = graph.nodes.find(n => n.id === nodeId);
      if (!node || node.dependencies.length === 0) return nodeWaves[nodeId] = 0;
      return nodeWaves[nodeId] = Math.max(...node.dependencies.map(calculateWave)) + 1;
    };
    graph.nodes.forEach(n => calculateWave(n.id));

    const initialNodes = graph.nodes.map((node, index) => {
      const result = results?.find(r => r.id === node.id || r.agent === node.agent);
      const isExecuting = !result && results?.length > 0;
      const status = result ? (result.success ? 'success' : 'error') : 'pending';
      const isConsensus = node.agent === 'consensus_agent';
      
      const borderColor = isConsensus ? '#f59e0b' : (status === 'success' ? '#10b981' : status === 'error' ? '#ef4444' : '#6366f1');
      const glowColor = isConsensus ? 'rgba(245, 158, 11, 0.4)' : (status === 'success' ? 'rgba(16, 185, 129, 0.4)' : status === 'error' ? 'rgba(239, 68, 68, 0.4)' : 'rgba(99, 102, 241, 0.2)');

      return {
        id: node.id,
        data: { 
          label: (
            <div className={`node-content ${isExecuting ? 'pulse' : ''}`}>
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '4px', marginBottom: '2px' }}>
                 {isConsensus && <span style={{ color: '#f59e0b', fontSize: '10px' }}>⚡</span>}
                 <div style={{ fontSize: '9px', opacity: 0.6 }}>{node.id.toUpperCase()}</div>
              </div>
              <div style={{ fontWeight: '800', fontSize: '11px', color: isConsensus ? '#f59e0b' : '#fff' }}>
                {isConsensus ? 'SWARM CONSENSUS' : node.agent.split('_')[0].toUpperCase()}
              </div>
              <div style={{ fontSize: '8px', marginTop: '4px', color: borderColor, fontWeight: 'bold' }}>{status.toUpperCase()}</div>
            </div>
          ) 
        },
        position: { x: nodeWaves[node.id] * 220, y: (index % 4) * 90 }, // Slightly more spacing for v8.5 waves
        style: { 
          background: isConsensus ? 'rgba(245, 158, 11, 0.05)' : 'rgba(10, 10, 10, 0.7)', 
          backdropFilter: 'blur(12px)',
          color: '#fff', 
          border: `1px solid ${borderColor}`,
          borderRadius: '14px',
          padding: '12px',
          width: 160,
          textAlign: 'center',
          boxShadow: `0 8px 25px ${glowColor}`,
          transition: 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)',
          animation: isConsensus && isExecuting ? 'consensusPulse 2s infinite' : ''
        },
      };
    });

    const initialEdges = graph.nodes.flatMap(node => 
      node.dependencies.map(depId => {
        const isTargetConsensus = node.agent === 'consensus_agent';
        return {
          id: `e-${depId}-${node.id}`,
          source: depId,
          target: node.id,
          animated: !results?.find(r => r.id === node.id),
          style: { 
            stroke: isTargetConsensus ? '#f59e0b' : '#4f46e5', 
            strokeWidth: isTargetConsensus ? 3 : 2, 
            opacity: isTargetConsensus ? 0.8 : 0.6 
          },
          markerEnd: { type: MarkerType.ArrowClosed, color: isTargetConsensus ? '#f59e0b' : '#4f46e5' },
        };
      })
    );

    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [graph, results, setNodes, setEdges]);

  return (
    <div style={{ width: '100%', height: '300px', background: '#050505', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#111" gap={16} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
};
