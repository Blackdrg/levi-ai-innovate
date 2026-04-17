// backend/kernel/src/security_monitor.rs
use serde::{Serialize, Deserialize};
use std::collections::{HashSet, HashMap};
use std::sync::{Arc, Mutex};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum Capability {
    NetworkAccess,
    FileSystemWrite,
    GpuOverride,
    KernelAdmin,
    ArweaveCommit,
    ProcessSpawn,    // Sovereign v17.0
    MemoryOverride,  // Sovereign v17.0
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapabilitySet {
    pub active: HashSet<Capability>,
}

pub struct SecurityMonitor {
    agent_caps: Arc<Mutex<HashMap<String, CapabilitySet>>>,
}

impl SecurityMonitor {
    pub fn new() -> Self {
        Self {
            agent_caps: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub fn register_agent(&self, agent_id: String, caps: CapabilitySet) {
        let mut ac = self.agent_caps.lock().unwrap();
        ac.insert(agent_id, caps);
    }

    pub fn check_agent_cap(&self, agent_id: &str, required: Capability) -> bool {
        let ac = self.agent_caps.lock().unwrap();
        if let Some(caps) = ac.get(agent_id) {
            return caps.active.contains(&required);
        }
        false
    }

    pub fn get_caps(&self, agent_id: &str) -> CapabilitySet {
        let ac = self.agent_caps.lock().unwrap();
        ac.get(agent_id).cloned().unwrap_or_else(|| Self::default_agent_caps())
    }

    pub fn validate(caps: &CapabilitySet, required: Capability) -> bool {
        caps.active.contains(&required)
    }

    pub fn default_agent_caps() -> CapabilitySet {
        let mut active = HashSet::new();
        active.insert(Capability::FileSystemWrite);
        active.insert(Capability::NetworkAccess);
        active.insert(Capability::ProcessSpawn);
        CapabilitySet { active }
    }

    pub fn kernel_caps() -> CapabilitySet {
        let mut active = HashSet::new();
        active.insert(Capability::NetworkAccess);
        active.insert(Capability::FileSystemWrite);
        active.insert(Capability::GpuOverride);
        active.insert(Capability::KernelAdmin);
        active.insert(Capability::ArweaveCommit);
        active.insert(Capability::ProcessSpawn);
        active.insert(Capability::MemoryOverride);
        CapabilitySet { active }
    }
}
