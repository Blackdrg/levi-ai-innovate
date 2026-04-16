// backend/kernel/src/gpu_controller.rs
use std::sync::{Arc, Mutex};
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GpuMetrics {
    pub vram_total_mb: u64,
    pub vram_used_mb: u64,
    pub load_pct: f32,
    pub temp_c: f32,
}

pub struct GpuController {
    metrics: Arc<Mutex<GpuMetrics>>,
    allocation: Arc<Mutex<std::collections::HashMap<String, u64>>>,
}

impl GpuController {
    pub fn new() -> Self {
        Self {
            metrics: Arc::new(Mutex::new(GpuMetrics {
                vram_total_mb: 8192, // Simulated 8GB
                vram_used_mb: 0,
                load_pct: 0.0,
                temp_c: 45.0,
            })),
            allocation: Arc::new(Mutex::new(std::collections::HashMap::new())),
        }
    }

    pub fn update_metrics(&self, used: u64, load: f32, temp: f32) {
        let mut m = self.metrics.lock().unwrap();
        m.vram_used_mb = used;
        m.load_pct = load;
        m.temp_c = temp;
    }

    pub fn request_vram(&self, agent_id: String, amount_mb: u64) -> Result<(), String> {
        let mut metrics = self.metrics.lock().unwrap();
        if metrics.vram_used_mb + amount_mb > metrics.vram_total_mb {
            return Err("GPU VRAM Exhausted".to_string());
        }

        metrics.vram_used_mb += amount_mb;
        let mut alloc = self.allocation.lock().unwrap();
        let entry = alloc.entry(agent_id).or_insert(0);
        *entry += amount_mb;
        
        Ok(())
    }

    pub fn release_vram(&self, agent_id: String) {
        let mut alloc = self.allocation.lock().unwrap();
        if let Some(held) = alloc.remove(&agent_id) {
            let mut metrics = self.metrics.lock().unwrap();
            metrics.vram_used_mb = metrics.vram_used_mb.saturating_sub(held);
        }
    }

    pub fn get_metrics(&self) -> GpuMetrics {
        self.metrics.lock().unwrap().clone()
    }
}
