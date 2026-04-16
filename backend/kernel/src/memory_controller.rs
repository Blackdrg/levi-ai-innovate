// backend/kernel/src/memory_controller.rs
use std::sync::{Arc, Mutex};
use crate::process_manager::ProcessManager;

pub struct MemoryController {
    process_manager: Arc<ProcessManager>,
    hard_limit_kb: u64,
}

impl MemoryController {
    pub fn new(process_manager: Arc<ProcessManager>, limit_mb: u64) -> Self {
        Self {
            process_manager,
            hard_limit_kb: limit_mb * 1024,
        }
    }

    pub fn enforce_limits(&self) {
        let processes = self.process_manager.get_process_list();
        for proc in processes {
            if proc.memory_usage_kb > self.hard_limit_kb {
                log::warn!("OOM: Process {} ({}) exceeded limit {}KB with {}KB. Killing...", 
                    proc.id, proc.name, self.hard_limit_kb, proc.memory_usage_kb);
                let _ = self.process_manager.kill_process(proc.id);
            }
        }
    }
}
