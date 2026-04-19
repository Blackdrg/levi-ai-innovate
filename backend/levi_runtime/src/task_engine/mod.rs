// backend/levi_runtime/src/task_engine/mod.rs
use std::sync::Arc;
use anyhow::Result;
use uuid::Uuid;
use crate::orchestrator::SwarmOrchestrator;
use tracing::info;

pub struct TaskEngine {
    orchestrator: Arc<SwarmOrchestrator>,
}

use std::collections::HashMap;
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct MissionResult {
    pub mission_id: Uuid,
    pub agents_involved: Vec<String>,
    pub step_results: Vec<String>,
    pub latency_ms: u64,
    pub vram_usage_mb: u64,
    pub success: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TaskNode {
    pub id: String,
    pub tool_name: String,
    pub input: String,
    pub dependencies: Vec<String>,
    pub retries: u32,
    pub max_retries: u32,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct MissionGraph {
    pub nodes: Vec<TaskNode>,
}

impl TaskEngine {
    pub fn new(orchestrator: Arc<SwarmOrchestrator>) -> Self {
        Self { orchestrator }
    }

    pub async fn admit_mission(&self, mission_id: Uuid, description: &str) -> Result<MissionResult> {
        info!(" 🎯 [Workflow Engine] Admitting Mission {}: {}", mission_id, description);
        let start = std::time::Instant::now();
        
        let graph = self.plan_mock_mission(description);
        self.execute_graph_parallel(mission_id, graph).await?;
        
        let duration = start.elapsed().as_millis() as u64;

        Ok(MissionResult {
            mission_id,
            agents_involved: vec!["architect".to_string(), "analyst".to_string()],
            step_results: vec!["Standard wave execution completed.".to_string()],
            latency_ms: duration,
            vram_usage_mb: 142,
            success: true,
        })
    }

    fn plan_mock_mission(&self, _description: &str) -> MissionGraph {
        MissionGraph {
            nodes: vec![
                TaskNode {
                    id: "step_init_0".to_string(),
                    tool_name: "system_info".to_string(),
                    input: "{}".to_string(),
                    dependencies: vec![],
                    retries: 0,
                    max_retries: 3,
                },
                TaskNode {
                    id: "step_net_1".to_string(),
                    tool_name: "network_probe".to_string(),
                    input: "google.com".to_string(),
                    dependencies: vec!["step_init_0".to_string()],
                    retries: 0,
                    max_retries: 3,
                }
            ],
        }
    }


    async fn execute_graph_parallel(&self, mission_id: Uuid, mut graph: MissionGraph) -> Result<()> {
        let mut completed: HashMap<String, bool> = HashMap::new();
        let total_nodes = graph.nodes.len();

        info!(" [Workflow Engine] Parallel Wave Execution started for mission {}", mission_id);

        while completed.len() < total_nodes {
            let mut current_wave = Vec::new();
            
            for node in &graph.nodes {
                if completed.contains_key(&node.id) { continue; }
                
                let deps_satisfied = node.dependencies.iter().all(|d| completed.get(d).cloned().unwrap_or(false));
                if deps_satisfied {
                    current_wave.push(node.clone());
                }
            }

            if current_wave.is_empty() {
                anyhow::bail!("Deadlock in MissionGraph");
            }

            // [DCN Offloading] If wave is too large (> 5 tasks), offload to cluster
            if current_wave.len() > 5 {
                info!(" [Workflow Engine] Wave size {} exceeds local threshold. Offloading to DCN...", current_wave.len());
                let dcn = self.orchestrator.dcn.clone();
                let _ = dcn.handle_remote_task(task_description).await;
            }

            info!(" [Workflow Engine] Dispatching Wave: {} tasks", current_wave.len());

            
            // Parallel dispatch using tokio::spawn for each task in the wave
            let mut handles = Vec::new();
            for node in current_wave {
                let orchestrator = self.orchestrator.clone();
                let mission_id = mission_id.clone();
                
                handles.push(tokio::spawn(async move {
                    let mut success = false;
                    let mut current_retries = 0;
                    
                    while !success && current_retries <= node.max_retries {
                        info!(" [Workflow Engine] Executing Node {} (Attempt {})", node.id, current_retries + 1);
                        
                        match orchestrator.deploy_swarm(mission_id, 1).await {
                            Ok(_) => {
                                success = true;
                            }
                            Err(e) => {
                                warn!(" [Workflow Engine] Node {} Failed: {}. Retrying...", node.id, e);
                                current_retries += 1;
                                tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;
                            }
                        }
                    }
                    
                    if success {
                        Ok(node.id)
                    } else {
                        Err(anyhow::anyhow!("Node {} failed after {} retries", node.id, node.max_retries))
                    }
                }));
            }

            // Wait for all tasks in the current wave to finish
            for handle in handles {
                match handle.await? {
                    Ok(node_id) => {
                        completed.insert(node_id, true);
                    }
                    Err(e) => {
                        error!(" [Workflow Engine] Wave Failure: {}", e);
                        anyhow::bail!("Critical mission failure: {}", e);
                    }
                }
            }
        }

        info!(" [Workflow Engine] Mission {} Successfully Resolved.", mission_id);
        Ok(())
    }
}


