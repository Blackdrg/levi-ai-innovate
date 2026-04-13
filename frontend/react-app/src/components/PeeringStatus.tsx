import * as React from 'react';
import { useEffect, useState } from 'react';
import { Share2, Server } from 'lucide-react';
import './PeeringStatus.css';

interface Peer {
  id: string;
  region: string;
  load: number;
  status: 'online' | 'degraded' | 'offline';
}

const PeerLoadBar = ({ load }: { load: number }) => {
  const loadRef = React.useRef<HTMLDivElement>(null);
  
  React.useEffect(() => {
    if (loadRef.current) {
      loadRef.current.style.width = `${load * 100}%`;
    }
  }, [load]);

  return (
    <div className="load-bar">
      <div 
        ref={loadRef} 
        className={`load-fill ${load > 0.8 ? 'load-high' : 'load-normal'}`} 
      />
    </div>
  );
};

export const PeeringStatus = () => {
  const [peers, setPeers] = useState<Peer[]>([]);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const response = await fetch('/api/v8/telemetry/health');
        const data = await response.json();
        if (data.status === 'online' && data.dcn) {
          // Format peers from DCN health
          const peerList: Peer[] = Object.entries(data.dcn.peers || {}).map(([id, meta]: [string, any]) => ({
            id,
            region: meta.region || 'unknown',
            load: meta.cpu_percent / 100 || 0,
            status: 'online'
          }));
          setPeers(peerList);
        }
      } catch (err) {
        console.error("DCN Health probe failed:", err);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="peering-status-widget">
      <h3><Share2 size={16} /> DCN Cluster Nodes ({peers.length})</h3>
      <div className="peers-list">
        {peers.length > 0 ? (
          peers.map((peer: Peer) => (
            <div key={peer.id} className="peer-card">
              <div className="peer-icon"><Server size={14} /></div>
              <div className="peer-info">
                <div className="peer-name">{peer.id.substring(0, 12)}</div>
                <div className="peer-region">{peer.region}</div>
              </div>
              <div className="peer-load">
                <PeerLoadBar load={peer.load} />
              </div>
            </div>
          ))
        ) : (
          <p className="no-peers">No remote peers detected. Running in Sovereign Isolated mode.</p>
        )}
      </div>
    </div>
  );
};
