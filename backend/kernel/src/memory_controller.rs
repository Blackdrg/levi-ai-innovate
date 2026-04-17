// backend/kernel/src/memory_controller.rs
use std::sync::{Arc, Mutex};
use crate::process_manager::ProcessManager;

pub struct MemoryController {
    process_manager: Arc<ProcessManager>,
    soft_limit_kb: u64,
    hard_limit_kb: u64,
}

impl MemoryController {
    pub fn new(process_manager: Arc<ProcessManager>, limit_mb: u64) -> Self {
        Self {
            process_manager,
            soft_limit_kb: (limit_mb * 1024) * 8 / 10, // 80% soft limit
            hard_limit_kb: limit_mb * 1024,
        }
    }

    pub fn enforce_limits(&self) {
        let processes = self.process_manager.get_process_list();
        for proc in processes {
            if proc.memory_usage_kb > self.hard_limit_kb {
                log::error!("❌ [OOM-HARD] Process {} ({}) killed: {}KB > {}KB", 
                    proc.id, proc.name, proc.memory_usage_kb, self.hard_limit_kb);
                let _ = self.process_manager.kill_process(proc.id);
            } else if proc.memory_usage_kb > self.soft_limit_kb {
                log::warn!("⚠️ [OOM-SOFT] Process {} ({}) triggers Virtual Swap: {}KB > {}KB", 
                    proc.id, proc.name, proc.memory_usage_kb, self.soft_limit_kb);
                self.swap_to_disk(&proc.id, proc.memory_usage_kb - self.soft_limit_kb);
            }
        }
    }

    fn swap_to_disk(&self, process_id: &str, amount_kb: u64) {
        // Sovereign v17.0: Simulated Virtual Swap to Tier 5 (IPFS/Disk)
        log::info!("💾 [MemoryController] Swapping {}KB for process {} to Tier 5 storage...", amount_kb, process_id);
    }
}
