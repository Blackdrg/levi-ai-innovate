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
      const isExecuting = !result && results?.length > 0; // Simplified "active" check
      const status = result ? (result.success ? 'success' : 'error') : 'pending';
      
      const borderColor = status === 'success' ? '#10b981' : status === 'error' ? '#ef4444' : '#6366f1';
      const glowColor = status === 'success' ? 'rgba(16, 185, 129, 0.4)' : status === 'error' ? 'rgba(239, 68, 68, 0.4)' : 'rgba(99, 102, 241, 0.2)';

      return {
        id: node.id,
        data: { 
          label: (
            <div className={`node-content ${isExecuting ? 'pulse' : ''}`}>
              <div style={{ fontSize: '9px', opacity: 0.6, marginBottom: '2px' }}>{node.id.toUpperCase()}</div>
              <div style={{ fontWeight: '600', fontSize: '11px' }}>{node.agent.split('_')[0].toUpperCase()}</div>
              <div style={{ fontSize: '8px', marginTop: '4px', color: borderColor }}>{status.toUpperCase()}</div>
            </div>
          ) 
        },
        position: { x: nodeWaves[node.id] * 200, y: (index % 3) * 80 }, // Wave-based horizontal, distributed vertical
        style: { 
          background: 'rgba(10, 10, 10, 0.7)', 
          backdropFilter: 'blur(8px)',
          color: '#fff', 
          border: `1px solid ${borderColor}`,
          borderRadius: '12px',
          padding: '12px',
          width: 140,
          textAlign: 'center',
          boxShadow: `0 4px 15px ${glowColor}`,
          transition: 'all 0.3s ease-in-out'
        },
      };
    });

    const initialEdges = graph.nodes.flatMap(node => 
      node.dependencies.map(depId => ({
        id: `e-${depId}-${node.id}`,
        source: depId,
        target: node.id,
        animated: !results?.find(r => r.id === node.id),
        style: { stroke: '#4f46e5', strokeWidth: 2, opacity: 0.6 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#4f46e5' },
      }))
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
