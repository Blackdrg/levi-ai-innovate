// backend/levi_runtime/src/orchestrator/mod.rs
use std::sync::Arc;
use tokio::sync::{mpsc, broadcast};
use anyhow::Result;
use tracing::{info, warn};
use uuid::Uuid;
use crate::memory::MemoryLedger;
use crate::plugins::PluginRegistry;
use crate::evolution::EvolutionaryEngine;
use crate::dcn::DistributedCognitiveNetwork;


use serde::{Serialize, Deserialize};

pub struct Agent {
    pub id: Uuid,
    pub name: String,
    pub capabilities: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolResult {
    pub tool: String,
    pub output: String,
    pub success: bool,
}

pub struct SwarmOrchestrator {
    memory: Arc<MemoryLedger>,
    plugins: Arc<PluginRegistry>,
    evolution: Arc<EvolutionaryEngine>,
    pub dcn: Arc<DistributedCognitiveNetwork>,
    pub memory_graph: Arc<tokio::sync::Mutex<crate::memory::graph::MemoryGraph>>,
    pub semaphore: Arc<tokio::sync::Semaphore>,

    // Channel for agents to communicate back to the orchestrator
    agent_tx: mpsc::Sender<AgentMessage>,
    // Broadcast for the orchestrator to send global events/commands
    event_tx: broadcast::Sender<GlobalEvent>,
    // Heartbeat tracking
    agent_heartbeats: Arc<dashmap::DashMap<Uuid, DateTime<Utc>>>,
}


#[derive(Debug, Clone)]
pub enum AgentMessage {
    StatusUpdate(Uuid, String),
    FoundResult(Uuid, String),
    RequestTool(Uuid, String, String), // AgentID, ToolName, Input
    MissionComplete(Uuid, String),
}


#[derive(Debug, Clone)]
pub enum GlobalEvent {
    MissionStart(Uuid),
    AbortAll,
}

impl SwarmOrchestrator {
    pub fn new(
        memory: Arc<MemoryLedger>, 
        plugins: Arc<PluginRegistry>, 
        evolution: Arc<EvolutionaryEngine>, 
        dcn: Arc<DistributedCognitiveNetwork>,
        memory_graph: Arc<tokio::sync::Mutex<crate::memory::graph::MemoryGraph>>
    ) -> Self {

        let (agent_tx, mut agent_rx) = mpsc::channel(100);
        let (event_tx, _) = broadcast::channel(100);
        let semaphore = Arc::new(tokio::sync::Semaphore::new(10)); // Max 10 concurrent agents

        let orchestrator_tx = agent_tx.clone();
        let plugins_inner = plugins.clone();
        let memory_inner = memory.clone();
        let evolution_inner = evolution.clone();
        let heartbeats = Arc::new(dashmap::DashMap::new());
        let heartbeats_inner = heartbeats.clone();
        
        // Background listener for agent updates
        tokio::spawn(async move {
            while let Some(msg) = agent_rx.recv().await {
                match msg {
                    AgentMessage::StatusUpdate(id, status) => {
                        info!(" [Agent {}] Status: {}", id, status);
                        heartbeats_inner.insert(id, Utc::now());
                    }
                    AgentMessage::FoundResult(id, res) => {
                        info!(" [Agent {}] Result Found: {}", id, res);
                        let _ = evolution_inner.record_pulse(&id.to_string(), 1.0).await;
                    }
                    AgentMessage::RequestTool(id, tool_name, input) => {
                        info!(" [Agent {}] Requesting Tool: {}", id, tool_name);
                        let plugins = plugins_inner.clone();
                        let tx = orchestrator_tx.clone();
                        
                        tokio::spawn(async move {
                            match plugins.call_tool(&tool_name, &input).await {
                                Ok(output) => {
                                    info!(" [Agent {}] Tool {} Success", id, tool_name);
                                    let _ = tx.send(AgentMessage::StatusUpdate(id, format!("Tool {} output: {}", tool_name, output))).await;
                                }
                                Err(e) => {
                                    error!(" [Agent {}] Tool {} Error: {}", id, tool_name, e);
                                }
                            }
                        });
                    }
                    AgentMessage::MissionComplete(id, summary) => {
                        info!(" [Agent {}] Mission Complete: {}", id, summary);
                    }
                }
            }
        });

        // 3. Self-Healing Monitor (Scans for dead agents)

        let hb_monitor = heartbeats.clone();
        tokio::spawn(async move {
            loop {
                tokio::time::sleep(tokio::time::Duration::from_secs(10)).await;
                let now = Utc::now();
                let mut dead_agents = Vec::new();

                for entry in hb_monitor.iter() {
                    let (id, last_hb) = entry.pair();
                    if now.signed_duration_since(*last_hb).num_seconds() > 30 {
                        dead_agents.push(*id);
                    }
                }

                for id in dead_agents {
                    warn!(" [Self-Healing] Agent {} timed out. Evicting from swarm.", id);
                    hb_monitor.remove(&id);
                }
            }
        });

        Self {

            memory,
            plugins,
            evolution,
            dcn,
            agent_tx,
            event_tx,
            agent_heartbeats: heartbeats,
        }
    }


    pub async fn deploy_swarm(&self, mission_id: Uuid, count: usize) -> Result<()> {
        info!(" 🐝 [Orchestrator] Deploying swarm of {} agents for mission {}", count, mission_id);
        
        for i in 0..count {
            // BACKPRESSURE: Acquire permit before spawning
            let permit = self.semaphore.clone().acquire_owned().await?;
            let mission_id = mission_id.clone();
            let agent_id = Uuid::new_v4();
            let tx = self.agent_tx.clone();
            let mut rx = self.event_tx.subscribe();

            tokio::spawn(async move {
                let _permit = permit; // Keep permit alive during agent execution
                info!(" [Agent {}] Starting cognitive mission unit...", agent_id);
                
                loop {
                    tokio::select! {
                        Ok(event) = rx.recv() => {
                            match event {
                                GlobalEvent::AbortAll => break,
                                GlobalEvent::MissionStart(_) => {
                                    let _ = tx.send(AgentMessage::StatusUpdate(agent_id, "Mission Running".to_string())).await;
                                }
                            }
                        }
                        _ = tokio::time::sleep(tokio::time::Duration::from_secs(2)) => {
                            // Simulation of work
                            let _ = tx.send(AgentMessage::StatusUpdate(agent_id, "Synthesizing Thought...".to_string())).await;
                        }
                    }
                }
                
                let _ = tx.send(AgentMessage::StatusUpdate(agent_id, "Shutdown".to_string())).await;
            });
        }
        
        self.event_tx.send(GlobalEvent::MissionStart(mission_id))?;
        Ok(())
    }
}
