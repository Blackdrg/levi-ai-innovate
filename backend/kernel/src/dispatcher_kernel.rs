// backend/kernel/src/dispatcher_kernel.rs
use std::collections::VecDeque;
use std::sync::atomic::{AtomicU32, Ordering};
use std::sync::Arc;
use crate::dag_executor::Task;

#[derive(Debug)]
pub enum Error {
    VRAMExhausted,
    DispatcherFailed(String),
}

pub struct DispatcherKernel {
    pub vram_quota: f32,
    pub vram_used: AtomicU32,
    pub agent_queue: VecDeque<Task>,
}

pub struct Handle {
    pub task_id: String,
    pub handle_id: String,
}

impl DispatcherKernel {
    pub fn new(quota: f32) -> Self {
        Self {
            vram_quota: quota,
            vram_used: AtomicU32::new(0),
            agent_queue: VecDeque::new(),
        }
    }

    pub async fn dispatch(&self, task: Task) -> Result<Handle, Error> {
        let vram_needed = self.get_vram_estimate(&task);
        
        // Hard VRAM guard: Don't dispatch if would exceed
        let current_usage = self.vram_used.load(Ordering::Relaxed) as f32;
        if current_usage + vram_needed > self.vram_quota {
            // Backpressure: Return error, don't queue
            return Err(Error::VRAMExhausted);
        }
        
        // Safe to dispatch
        self.vram_used.fetch_add((vram_needed * 100.0) as u32, Ordering::Relaxed);
        
        // Simulating handle return
        Ok(Handle {
            task_id: task.id.clone(),
            handle_id: format!("h-{}", task.id),
        })
    }

    fn get_vram_estimate(&self, _task: &Task) -> f32 {
        // Model-aware VRAM calculation
        500.0 // Placeholder for 500MB
    }
}
