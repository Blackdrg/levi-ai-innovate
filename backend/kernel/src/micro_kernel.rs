// backend/kernel/src/micro_kernel.rs
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::mpsc;
use serde::{Deserialize, Serialize};
use crate::stdlib::{StdLib, SysCall};

pub type AgentId = String;

#[derive(Debug, Serialize, Deserialize)]
pub enum Message {
    MissionRequest(MissionRequest),
    ResourceRequest(ResourceRequest),
    SysCallRequest(AgentId, SysCall), // New: Standard Library SysCalls
    AgentCrash(AgentId),
    ResourceGrant(f32),
    Telemetry(String), 
    _None,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct MissionRequest {
    pub mission_id: String,
    pub payload: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ResourceRequest {
    pub agent_id: AgentId,
    pub amount: f32,
}

pub struct Microkernel {
    pub trusted_core: Arc<TrustedCore>,
    pub agents: HashMap<AgentId, Agent>,
    pub message_rx: mpsc::Receiver<Message>,
    pub telemetry_tx: mpsc::Sender<String>,
}

pub struct TrustedCore {
    pub mission_router: MissionRouter,
    pub resource_allocator: ResourceAllocator,
    pub security_gate: SecurityGate,
    pub stdlib: StdLib, // Standard library bridge
}

pub struct MissionRouter;
pub struct ResourceAllocator;
pub struct SecurityGate;

pub struct Agent {
    pub id: AgentId,
}

impl Agent {
    pub async fn restart(&self) {
        // Restart agent process (Simulated)
    }
}

impl SecurityGate {
    pub async fn validate(&self, _req: &MissionRequest) -> Result<bool, String> {
        Ok(true)
    }
}

impl ResourceAllocator {
    pub fn allocate(&self, _req: &ResourceRequest) -> Result<f32, String> {
        Ok(0.0)
    }
}

impl MissionRouter {
    pub async fn route(&self, _req: MissionRequest) {
        // Route to the appropriate engine (Simulated)
    }
}

impl Microkernel {
    pub async fn run(mut self) -> ! {
        loop {
            let msg = self.message_rx.recv().await;
            
            if let Some(msg) = msg {
                match msg {
                    Message::MissionRequest(req) => {
                        if let Ok(true) = self.trusted_core.security_gate.validate(&req).await {
                            let _ = self.telemetry_tx.send(format!(r#"{{"type":"MissionRoute","id":"{}"}}"#, req.mission_id)).await;
                            self.trusted_core.mission_router.route(req).await;
                        }
                    },
                    Message::ResourceRequest(req) => {
                        if let Ok(quota) = self.trusted_core.resource_allocator.allocate(&req) {
                            let _ = self.telemetry_tx.send(format!(r#"{{"type":"ResourceGrant","agent":"{}","quota":{}}}"#, req.agent_id, quota)).await;
                        }
                    },
                    Message::SysCallRequest(agent_id, call) => {
                        // Execute through standard library
                        let result = self.trusted_core.stdlib.execute(call);
                        let log_msg = match result {
                            Ok(res) => format!(r#"{{"type":"SysCall","agent":"{}","status":"SUCCESS","data":"{}"}}"#, agent_id, res),
                            Err(e) => format!(r#"{{"type":"SysCall","agent":"{}","status":"ERROR","data":"{}"}}"#, agent_id, e),
                        };
                        let _ = self.telemetry_tx.send(log_msg).await;
                    },
                    Message::AgentCrash(agent_id) => {
                        let _ = self.telemetry_tx.send(format!(r#"{{"type":"AgentCrash","id":"{}"}}"#, agent_id)).await;
                        if let Some(agent) = self.agents.get(&agent_id) {
                            agent.restart().await;
                        }
                    },
                    Message::Telemetry(pulse) => {
                        let _ = self.telemetry_tx.send(pulse).await;
                    },
                    _ => {}
                }
            }
        }
    }
}
