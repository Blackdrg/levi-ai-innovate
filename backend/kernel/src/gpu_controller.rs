// backend/kernel/src/gpu_controller.rs
use std::sync::{Arc, Mutex};
use serde::{Serialize, Deserialize};
use crate::scheduler::MissionPriority;
use nvml_wrapper::Nvml;
use nvml_wrapper::enum_wrappers::device::TemperatureSensor;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GpuMetrics {
    pub vram_total_mb: u64,
    pub vram_used_mb: u64,
    pub load_pct: f32,
    pub temp_c: f32,
    pub device_name: String,
}

#[derive(Debug, Clone)]
struct GPUAllocation {
    pub amount_mb: u64,
    pub priority: MissionPriority,
}

pub struct GpuController {
    metrics: Arc<Mutex<GpuMetrics>>,
    allocation: Arc<Mutex<std::collections::HashMap<String, GPUAllocation>>>,
    nvml: Option<Nvml>,
}

impl GpuController {
    pub fn new() -> Self {
        let nvml = Nvml::init().ok();
        let mut initial_metrics = GpuMetrics {
            vram_total_mb: 8192,
            vram_used_mb: 0,
            load_pct: 0.0,
            temp_c: 45.0,
            device_name: "Simulated GPU".to_string(),
        };

        if let Some(ref n) = nvml {
            if let Ok(device) = n.device_by_index(0) {
                if let Ok(mem) = device.memory_info() {
                    initial_metrics.vram_total_mb = mem.total / 1024 / 1024;
                }
                if let Ok(name) = device.name() {
                    initial_metrics.device_name = name;
                }
            }
        }

        Self {
            metrics: Arc::new(Mutex::new(initial_metrics)),
            allocation: Arc::new(Mutex::new(std::collections::HashMap::new())),
            nvml,
        }
    }

    pub fn get_metrics(&self) -> GpuMetrics {
        if let Some(ref n) = self.nvml {
            if let Ok(device) = n.device_by_index(0) {
                let mut m = self.metrics.lock().unwrap();
                if let Ok(mem) = device.memory_info() {
                    m.vram_used_mb = mem.used / 1024 / 1024;
                }
                if let Ok(util) = device.utilization_rates() {
                    m.load_pct = util.gpu as f32;
                }
                if let Ok(temp) = device.temperature(TemperatureSensor::Gpu) {
                    m.temp_c = temp as f32;
                }
                return m.clone();
            }
        }
        self.metrics.lock().unwrap().clone()
    }

    pub fn request_vram(&self, mission_id: String, amount_mb: u64, priority: MissionPriority) -> Result<(), String> {
        let metrics = self.get_metrics();
        
        // 🚨 VRAM Governor: Admission Control (92% Saturation limit as per manifest)
        let saturation = (metrics.vram_used_mb + amount_mb) as f32 / metrics.vram_total_mb as f32;
        if saturation >= 0.92 {
            self.rebalance(amount_mb, &priority)?;
        }

        // Secondary Check: Thermal Integrity (82°C as per manifest)
        if metrics.temp_c > 82.0 {
            return Err(format!("THERMAL THROTTLE: GPU Temp is {:.1}°C. Delaying mission.", metrics.temp_c));
        }

        let mut alloc = self.allocation.lock().unwrap();
        alloc.insert(mission_id, GPUAllocation { amount_mb, priority });
        
        Ok(())
    }

    fn rebalance(&self, needed_mb: u64, requester_priority: &MissionPriority) -> Result<(), String> {
        let metrics = self.get_metrics();
        let mut alloc = self.allocation.lock().unwrap();
        
        let mut missions_to_evict = Vec::new();
        let mut freed_mb = 0;
        
        // Find lower priority missions (Lower priority missions have HIGHER numeric values)
        let mut sorted_allocs: Vec<_> = alloc.iter().collect();
        sorted_allocs.sort_by(|a, b| (b.1.priority.clone() as u32).cmp(&(a.1.priority.clone() as u32)));

        for (mid, a) in sorted_allocs {
            if (a.priority.clone() as u32) > (*requester_priority as u32) {
                missions_to_evict.push(mid.clone());
                freed_mb += a.amount_mb;
                if (metrics.vram_used_mb as i64 - freed_mb as i64 + needed_mb as i64) as f32 / metrics.vram_total_mb as f32 < 0.92 {
                    break;
                }
            }
        }

        if (metrics.vram_used_mb as i64 - freed_mb as i64 + needed_mb as i64) as f32 / metrics.vram_total_mb as f32 >= 0.92 {
            return Err("GPU VRAM ADMISSION DENIED: Saturation projection exceeds 92% buffer.".to_string());
        }

        for mid in missions_to_evict {
            if let Some(a) = alloc.remove(&mid) {
                log::warn!("🚀 [GpuController] EVICTING Mission {} to free {}MB.", mid, a.amount_mb);
            }
        }
        
        Ok(())
    }

    pub fn release_vram(&self, mission_id: String) {
        let mut alloc = self.allocation.lock().unwrap();
        alloc.remove(&mission_id);
    }
}
