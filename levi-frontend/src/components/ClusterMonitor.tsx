import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

const ClusterMonitor: React.FC = () => {
    const [nodes, setNodes] = useState<any[]>([]);

    useEffect(() => {
        const interval = setInterval(() => {
            // Mocking the cluster data that would come from the /metrics or /status endpoint
            setNodes([
                { id: 'HAL-0', role: 'Leader', term: 34, status: 'Online', health: 100 },
                { id: 'HAL-1', role: 'Follower', term: 34, status: 'Stable', health: 98 },
                { id: 'HAL-2', role: 'Follower', term: 34, status: 'Syncing', health: 92 },
            ]);
        }, 3000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="rounded-xl border border-white/10 bg-black/40 backdrop-blur-md p-4 flex flex-col font-mono text-xs">
            <h3 className="text-white/80 font-bold uppercase tracking-widest text-[10px] mb-4">DCN CLUSTER MESH</h3>
            <div className="space-y-4">
                {nodes.map(node => (
                    <div key={node.id} className="flex justify-between items-center bg-white/5 p-2 rounded">
                        <div>
                            <span className="text-blue-400">{node.id}</span>
                            <span className="text-white/40 ml-2">[{node.role}]</span>
                        </div>
                        <div className="flex gap-4">
                            <span className="text-purple-400">TERM: {node.term}</span>
                            <span className={`px-1 rounded text-[9px] ${node.status === 'Online' ? 'bg-green-500/20 text-green-500' : 'bg-blue-500/20 text-blue-400'}`}>
                                {node.status}
                            </span>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default ClusterMonitor;
