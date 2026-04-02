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

    const initialNodes = graph.nodes.map((node, index) => {
      const result = results?.find(r => r.agent === node.agent || r.id === node.id);
      const status = result ? (result.success ? 'success' : 'error') : 'pending';
      const color = status === 'success' ? '#10b981' : status === 'error' ? '#ef4444' : '#6366f1';

      return {
        id: node.id,
        data: { label: `${node.agent}\n${status.toUpperCase()}` },
        position: { x: index * 250, y: (node.dependencies.length) * 100 },
        style: { 
          background: '#0a0a0a', 
          color: '#fff', 
          border: `1px solid ${color}`,
          borderRadius: '8px',
          padding: '10px',
          fontSize: '10px',
          width: 150,
          textAlign: 'center',
          boxShadow: `0 0 10px ${color}44`
        },
      };
    });

    const initialEdges = [];
    graph.nodes.forEach(node => {
      node.dependencies.forEach(depId => {
        initialEdges.push({
          id: `e-${depId}-${node.id}`,
          source: depId,
          target: node.id,
          animated: true,
          style: { stroke: '#4f46e5' },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#4f46e5',
          },
        });
      });
    });

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
