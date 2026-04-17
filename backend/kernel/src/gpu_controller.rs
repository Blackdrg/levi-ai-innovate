// backend/kernel/src/gpu_controller.rs
use std::sync::{Arc, Mutex};
use serde::{Serialize, Deserialize};
use crate::scheduler::MissionPriority;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GpuMetrics {
    pub vram_total_mb: u64,
    pub vram_used_mb: u64,
    pub load_pct: f32,
    pub temp_c: f32,
}

#[derive(Debug, Clone)]
struct GPUAllocation {
    pub amount_mb: u64,
    pub priority: MissionPriority,
}

pub struct GpuController {
    metrics: Arc<Mutex<GpuMetrics>>,
    allocation: Arc<Mutex<std::collections::HashMap<String, GPUAllocation>>>,
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

    pub fn request_vram(&self, mission_id: String, amount_mb: u64, priority: MissionPriority) -> Result<(), String> {
        let mut metrics = self.metrics.lock().unwrap();
        
        // Dynamic Rebalancing: If exhausted, try to evict lower priority
        if metrics.vram_used_mb + amount_mb > metrics.vram_total_mb {
            self.rebalance(amount_mb, &priority)?;
        }

        metrics.vram_used_mb += amount_mb;
        let mut alloc = self.allocation.lock().unwrap();
        alloc.insert(mission_id, GPUAllocation { amount_mb, priority });
        
        Ok(())
    }

    fn rebalance(&self, needed_mb: u64, requester_priority: &MissionPriority) -> Result<(), String> {
        let mut alloc = self.allocation.lock().unwrap();
        let mut metrics = self.metrics.lock().unwrap();
        
        let mut missions_to_evict = Vec::new();
        let mut freed_mb = 0;
        
        // Find lower priority missions
        for (mid, a) in alloc.iter() {
            if (a.priority.clone() as u32) > (*requester_priority as u32) { // Lower priority has higher numeric value
                missions_to_evict.push(mid.clone());
                freed_mb += a.amount_mb;
                if metrics.vram_used_mb - freed_mb + needed_mb <= metrics.vram_total_mb {
                    break;
                }
            }
        }

        if metrics.vram_used_mb - freed_mb + needed_mb > metrics.vram_total_mb {
            return Err("GPU VRAM Exhausted: No lower-priority missions to evict".to_string());
        }

        for mid in missions_to_evict {
            if let Some(a) = alloc.remove(&mid) {
                log::warn!("🚀 [GpuController] EVICTING Mission {} (VRAM Rebalance) to free {}MB.", mid, a.amount_mb);
                metrics.vram_used_mb -= a.amount_mb;
                // In a real system, we'd notify the mission handler to pause/swap
            }
        }
        
        Ok(())
    }

    pub fn release_vram(&self, mission_id: String) {
        let mut alloc = self.allocation.lock().unwrap();
        if let Some(held) = alloc.remove(&mission_id) {
            let mut metrics = self.metrics.lock().unwrap();
            metrics.vram_used_mb = metrics.vram_used_mb.saturating_sub(held.amount_mb);
        }
    }

    pub fn get_metrics(&self) -> GpuMetrics {
        self.metrics.lock().unwrap().clone()
    }
}
