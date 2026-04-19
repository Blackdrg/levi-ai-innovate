// backend/levi_runtime/src/dcn/mod.rs
use std::sync::Arc;
use tokio::sync::Mutex;
use serde::{Serialize, Deserialize};
use anyhow::Result;
use tracing::{info, warn, error};
use uuid::Uuid;
use reqwest::Client;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NodeState {
    Follower,
    Candidate,
    Leader,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RaftPulse {
    pub node_id: String,
    pub term: u64,
    pub state: NodeState,
}

pub struct DistributedCognitiveNetwork {
    pub node_id: String,
    state: Mutex<NodeState>,
    term: Mutex<u64>,
    peers: Mutex<Vec<String>>, // Peer URLs
    client: Client,
}

impl DistributedCognitiveNetwork {
    pub fn new(node_id: &str, peers: Vec<String>) -> Self {
        Self {
            node_id: node_id.to_string(),
            state: Mutex::new(NodeState::Follower),
            term: Mutex::new(0),
            peers: Mutex::new(peers),
            client: Client::new(),
        }
    }

    pub async fn start_heartbeat_loop(self: Arc<Self>) {
        info!(" 🛰️  [DCN] Node {} pulse loop awakened.", self.node_id);
        loop {
            tokio::time::sleep(tokio::time::Duration::from_secs(5)).await;
            let state = self.state.lock().await;
            
            if matches!(*state, NodeState::Leader) {
                let _ = self.broadcast_heartbeat().await;
            } else {
                // Follower logic: check for leader timeout
                // For this graduation, we'll simulate a stable cluster
            }
        }
    }

    async fn broadcast_heartbeat(&self) -> Result<()> {
        let term = *self.term.lock().await;
        let peers = self.peers.lock().await;
        
        for peer in peers.iter() {
            let url = format!("{}/dcn/pulse", peer);
            let pulse = RaftPulse {
                node_id: self.node_id.clone(),
                term,
                state: NodeState::Leader,
            };

            let client = self.client.clone();
            tokio::spawn(async move {
                match client.post(&url).json(&pulse).send().await {
                    Ok(_) => {},
                    Err(e) => warn!(" [DCN] Failed to pulse peer {}: {}", url, e),
                }
            });
        }
        Ok(())
    }

    pub async fn handle_remote_task(&self, task: &str) -> Result<String> {
        info!(" 🛰️  [DCN] Autonomous Load Balancer: Offloading mission to cluster...");
        
        let peers = self.peers.lock().await;
        if peers.is_empty() {
            anyhow::bail!("No peers available for offloading.");
        }

        // Logic: Pick a peer (Simple Round Robin or Random for this graduation)
        let peer = &peers[0]; 
        let url = format!("{}/mission/admit", peer);
        
        info!(" 🛰️  [DCN] Offloading Mission to Node: {}", peer);
        let resp = self.client.post(&url)
            .json(&serde_json::json!({ "task": task }))
            .send().await?;

        let res_json: serde_json::Value = resp.json().await?;
        let mid = res_json["mission_id"].as_str().unwrap_or("unknown");
        
        Ok(mid.to_string())
    }


    pub async fn sync_memory_fragment(&self, fragment_json: &str) -> Result<()> {
        let peers = self.peers.lock().await;
        for peer in peers.iter() {
            let url = format!("{}/dcn/sync_memory", peer);
            let client = self.client.clone();
            let json = fragment_json.to_string();
            tokio::spawn(async move {
                let _ = client.post(&url).body(json).send().await;
            });
        }
        Ok(())
    }
}
