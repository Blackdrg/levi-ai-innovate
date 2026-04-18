// backend/kernel/src/gpu_controller.rs
//
// GPU Controller — VRAM admission, telemetry, and buffer management.
// Integrates with NVML when a real NVIDIA driver is present; otherwise
// uses stub values so the system still runs without a GPU.
use std::sync::{Arc, Mutex};
use std::collections::HashMap;
use serde::{Serialize, Deserialize};

// ── Allocation priority ───────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "PascalCase")]
pub enum AllocPriority {
    Critical = 0,
    High     = 1,
    Normal   = 2,
    Low      = 3,
}

impl Default for AllocPriority {
    fn default() -> Self { AllocPriority::Normal }
}

// ── GPU metrics ───────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GpuMetrics {
    pub vram_total_mb: u64,
    pub vram_used_mb:  u64,
    pub load_pct:      f32,
    pub temp_c:        f32,
    pub gpu_name:      String,
}

// ── Buffer ────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone)]
pub struct GpuBuffer {
    pub id:   u64,
    pub size: u64,
    pub ptr:  u64, // pseudo GPU address
}

struct GpuAlloc {
    amount_mb: u64,
    priority:  AllocPriority,
}

// ── Controller ────────────────────────────────────────────────────────────────

pub struct GpuController {
    metrics:        Arc<Mutex<GpuMetrics>>,
    allocations:    Arc<Mutex<HashMap<String, GpuAlloc>>>,
    buffers:        Arc<Mutex<HashMap<u64, GpuBuffer>>>,
    next_buffer_id: Arc<Mutex<u64>>,

    #[cfg(feature = "nvml")]
    nvml: Option<nvml_wrapper::Nvml>,
}

impl GpuController {
    pub fn new() -> Self {
        #[cfg(feature = "nvml")]
        let (nvml, initial) = {
            let n  = nvml_wrapper::Nvml::init().ok();
            let mut m = Self::fallback_metrics();
            if let Some(ref nv) = n {
                if let Ok(dev) = nv.device_by_index(0) {
                    if let Ok(mem)  = dev.memory_info()    { m.vram_total_mb = mem.total / 1024 / 1024; }
                    if let Ok(name) = dev.name()           { m.gpu_name = name; }
                }
            }
            (n, m)
        };

        #[cfg(not(feature = "nvml"))]
        let initial = Self::fallback_metrics();

        Self {
            metrics:        Arc::new(Mutex::new(initial)),
            allocations:    Arc::new(Mutex::new(HashMap::new())),
            buffers:        Arc::new(Mutex::new(HashMap::new())),
            next_buffer_id: Arc::new(Mutex::new(1)),
            #[cfg(feature = "nvml")]
            nvml,
        }
    }

    fn fallback_metrics() -> GpuMetrics {
        GpuMetrics {
            vram_total_mb: 8192,
            vram_used_mb:  512,
            load_pct:      5.0,
            temp_c:        45.0,
            gpu_name:      "Simulated GPU (no NVML)".to_string(),
        }
    }

    // ── Live metrics ──────────────────────────────────────────────────────────

    pub fn get_metrics(&self) -> GpuMetrics {
        #[cfg(feature = "nvml")]
        if let Some(ref n) = self.nvml {
            if let Ok(dev) = n.device_by_index(0) {
                let mut m = self.metrics.lock().unwrap();
                if let Ok(mem)  = dev.memory_info()   { m.vram_used_mb = mem.used / 1024 / 1024; }
                if let Ok(util) = dev.utilization_rates() { m.load_pct = util.gpu as f32; }
                if let Ok(temp) = dev.temperature(nvml_wrapper::enum_wrappers::device::TemperatureSensor::Gpu) {
                    m.temp_c = temp as f32;
                }
                return m.clone();
            }
        }
        self.metrics.lock().unwrap().clone()
    }

    // ── VRAM admission ────────────────────────────────────────────────────────

    /// Returns true if the allocation succeeds (or if we're in fallback mode).
    pub fn request_vram(&self, id: &str, amount_mb: u64, priority: AllocPriority) -> bool {
        let metrics = self.get_metrics();
        let saturation = (metrics.vram_used_mb + amount_mb) as f64
            / metrics.vram_total_mb.max(1) as f64;

        if saturation >= 0.92 {
            // Attempt eviction of lower-priority allocations
            if !self.rebalance(amount_mb, &priority) {
                log::warn!("[GPU] VRAM admission denied for {} ({}MB). Saturation: {:.1}%",
                           id, amount_mb, saturation * 100.0);
                return false;
            }
        }

        if metrics.temp_c > 82.0 {
            log::warn!("[GPU] Thermal throttle: {:.1}°C. Delaying {}.", metrics.temp_c, id);
            return false;
        }

        let mut m = self.metrics.lock().unwrap();
        m.vram_used_mb = (m.vram_used_mb + amount_mb).min(m.vram_total_mb);

        self.allocations.lock().unwrap().insert(id.to_string(), GpuAlloc { amount_mb, priority });
        log::info!("[GPU] VRAM allocated: {} → {}MB  total_used={}MB",
                   id, amount_mb, m.vram_used_mb);
        true
    }

    pub fn release_vram(&self, id: &str) {
        let mut alloc = self.allocations.lock().unwrap();
        if let Some(a) = alloc.remove(id) {
            let mut m = self.metrics.lock().unwrap();
            m.vram_used_mb = m.vram_used_mb.saturating_sub(a.amount_mb);
            log::info!("[GPU] VRAM released: {} ({}MB)", id, a.amount_mb);
        }
    }

    /// Flush all buffers and reset allocation accounting (self-healing path).
    pub fn flush_buffers(&self) {
        self.buffers.lock().unwrap().clear();
        self.allocations.lock().unwrap().clear();
        let mut m = self.metrics.lock().unwrap();
        m.vram_used_mb = 0;
        log::info!("[GPU] All VRAM buffers flushed (self-healing).");
    }

    // ── Buffer allocation ──────────────────────────────────────────────────────

    pub fn allocate_buffer(&self, size_mb: u64) -> GpuBuffer {
        let mut id_gen = self.next_buffer_id.lock().unwrap();
        let id = *id_gen;
        *id_gen += 1;

        let buf = GpuBuffer {
            id,
            size: size_mb,
            ptr:  (id << 32) | 0xDEAD_BEEF,
        };
        self.buffers.lock().unwrap().insert(id, buf.clone());
        log::info!("[GPU] Buffer {} allocated ({}MB @ 0x{:X})", id, size_mb, buf.ptr);
        buf
    }

    // ── Internal ──────────────────────────────────────────────────────────────

    fn rebalance(&self, needed_mb: u64, requester_prio: &AllocPriority) -> bool {
        let metrics     = self.get_metrics();
        let mut alloc   = self.allocations.lock().unwrap();
        let mut freed   = 0u64;
        let mut to_evict = vec![];

        // Sort by priority ascending (evict low-priority first)
        let mut sorted: Vec<(&String, &GpuAlloc)> = alloc.iter().collect();
        sorted.sort_by_key(|(_, a)| a.priority.clone() as u32);

        for (mid, a) in sorted.iter().rev() {
            if (a.priority.clone() as u32) > (*requester_prio as u32) {
                to_evict.push(mid.to_string());
                freed += a.amount_mb;
                let projected = (metrics.vram_used_mb + needed_mb).saturating_sub(freed);
                if projected as f64 / metrics.vram_total_mb as f64 < 0.92 {
                    break;
                }
            }
        }

        let still_over = {
            let projected = (metrics.vram_used_mb + needed_mb).saturating_sub(freed);
            (projected as f64 / metrics.vram_total_mb as f64) >= 0.92
        };
        if still_over { return false; }

        for mid in to_evict {
            if let Some(a) = alloc.remove(&mid) {
                log::warn!("[GPU] Evicting {} ({}MB) for rebalance.", mid, a.amount_mb);
            }
        }
        true
    }
}
