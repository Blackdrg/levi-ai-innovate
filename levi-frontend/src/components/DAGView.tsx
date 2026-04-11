import React, { useMemo, useEffect, useState } from 'react';
import { 
  ReactFlow, 
  Background, 
  Controls, 
  Panel,
  useNodesState, 
  useEdgesState,
  MarkerType,
  Handle,
  Position,
  NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useTelemetryStore } from '../stores/telemetryStore';
import { TaskStatus } from '../lib/types';
import { motion } from 'framer-motion';

interface SovereignNodeData extends Record<string, unknown> {
  label: string;
  status: TaskStatus;
}

// Custom Node Component
const SovereignNode = ({ id, data }: any) => {
  const nodeData = data as SovereignNodeData;
  const currentStatus = useTelemetryStore((state) => state.taskStatuses[id] || nodeData.status) as TaskStatus;

  const getStatusColor = (status: TaskStatus) => {
    switch (status) {
      case 'QUEUED': return '#64748b'; // Slate
      case 'RUNNING': return '#3b82f6'; // Blue
      case 'DONE': return '#10b981'; // Emerald
      case 'FAILED': return '#ef4444'; // Red
      default: return '#64748b';
    }
  };

  return (
    <div className="sovereign-node">
      <Handle type="target" position={Position.Top} />
      <motion.div
        animate={currentStatus === 'RUNNING' ? { 
          boxShadow: [
            "0 0 0px rgba(59, 130, 246, 0.4)",
            "0 0 20px rgba(59, 130, 246, 0.8)",
            "0 0 0px rgba(59, 130, 246, 0.4)"
          ]
        } : {}}
        transition={{ repeat: Infinity, duration: 2 }}
        className="node-body"
        style={{ borderColor: getStatusColor(currentStatus), '--status-color': getStatusColor(currentStatus) } as any}
      >
        <div className="node-label">{nodeData.label}</div>
        <div className="node-status">
          {currentStatus}
        </div>
      </motion.div>
      <Handle type="source" position={Position.Bottom} />

      <style>{`
        .sovereign-node {
          padding: 10px;
          border-radius: 8px;
          background: rgba(15, 23, 42, 0.9);
          border: 1px solid rgba(255, 255, 255, 0.1);
          min-width: 150px;
          color: white;
          font-family: 'Inter', sans-serif;
        }
        .node-body {
          border-left: 4px solid;
          padding-left: 10px;
          border-color: inherit;
        }
        .node-label {
          font-weight: 600;
          font-size: 14px;
        }
        .node-status {
          font-size: 10px;
          text-transform: uppercase;
          margin-top: 4px;
          font-family: 'JetBrains Mono', monospace;
          color: var(--status-color);
        }
      `}</style>
    </div>
  );
};

const nodeTypes = {
  sovereign: SovereignNode,
};

interface DAGViewProps {
  initialNodes: any[];
  initialEdges: any[];
}

export const DAGView: React.FC<DAGViewProps> = ({ initialNodes, initialEdges }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div className="dag-viewer-root">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
      >
        <Background color="#1e293b" gap={20} />
        <Controls />
        <Panel position="top-right" className="dag-panel">
          SWARM DAG v14.0
        </Panel>
      </ReactFlow>

      <style>{`
        .dag-panel {
          background: rgba(30, 41, 59, 0.8);
          padding: 8px 12px;
          border-radius: 6px;
          color: #38bdf8;
          font-weight: bold;
          font-family: 'JetBrains Mono', monospace;
          border: 1px solid rgba(56, 189, 248, 0.3);
          backdrop-filter: blur(4px);
        }
        .dag-viewer-root {
          width: 100%;
          height: 500px;
          background: #020617;
        }
      `}</style>
    </div>
  );
};
