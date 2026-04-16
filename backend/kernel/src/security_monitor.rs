// backend/kernel/src/security_monitor.rs
use serde::{Serialize, Deserialize};
use std::collections::HashSet;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum Capability {
    NetworkAccess,
    FileSystemWrite,
    GpuOverride,
    KernelAdmin,
    ArweaveCommit,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CapabilitySet {
    pub active: HashSet<Capability>,
}

pub struct SecurityMonitor;

impl SecurityMonitor {
    pub fn validate(caps: &CapabilitySet, required: Capability) -> bool {
        caps.active.contains(&required)
    }

    pub fn default_agent_caps() -> CapabilitySet {
        let mut active = HashSet::new();
        active.insert(Capability::FileSystemWrite);
        active.insert(Capability::NetworkAccess);
        CapabilitySet { active }
    }

    pub fn kernel_caps() -> CapabilitySet {
        let mut active = HashSet::new();
        active.insert(Capability::NetworkAccess);
        active.insert(Capability::FileSystemWrite);
        active.insert(Capability::GpuOverride);
        active.insert(Capability::KernelAdmin);
        active.insert(Capability::ArweaveCommit);
        CapabilitySet { active }
    }
}
