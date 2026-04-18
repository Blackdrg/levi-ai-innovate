// backend/kernel/src/drivers/mod.rs
use std::sync::{Arc, Mutex};
use serde::{Serialize, Deserialize};
use sysinfo::{System, SystemExt, CpuExt};
use nvml_wrapper::Nvml;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DriverType {
    Compute,
    Memory,
    Perception,
    Storage,
    Gpu,
}

pub trait SovereignDriver {
    fn get_type(&self) -> DriverType;
    fn get_name(&self) -> &str;
    fn status(&self) -> String;
}

pub struct DriverRegistry {
    drivers: Arc<Mutex<Vec<Box<dyn SovereignDriver + Send>>>>,
}

impl DriverRegistry {
    pub fn new() -> Self {
        Self {
            drivers: Arc::new(Mutex::new(Vec::new())),
        }
    }

    pub fn register(&self, driver: Box<dyn SovereignDriver + Send>) {
        let mut d = self.drivers.lock().unwrap();
        d.push(driver);
    }

    pub fn list_drivers(&self) -> Vec<(String, DriverType, String)> {
        let d = self.drivers.lock().unwrap();
        d.iter().map(|dr| (dr.get_name().to_string(), dr.get_type(), dr.status())).collect()
    }
}

// 🚀 REAL HAL Driver: System Memory
pub struct HardenedMemoryDriver {
    sys: Arc<Mutex<System>>,
}

impl HardenedMemoryDriver {
    pub fn new() -> Self {
        let mut sys = System::new_all();
        sys.refresh_memory();
        Self { sys: Arc::new(Mutex::new(sys)) }
    }
}

impl SovereignDriver for HardenedMemoryDriver {
    fn get_type(&self) -> DriverType { DriverType::Memory }
    fn get_name(&self) -> &str { "HAL-0-SysMem" }
    fn status(&self) -> String {
        let mut sys = self.sys.lock().unwrap();
        sys.refresh_memory();
        format!("Total: {} MB, Free: {} MB", sys.total_memory() / 1024 / 1024, sys.available_memory() / 1024 / 1024)
    }
}

// 🚀 REAL HAL Driver: CPU
pub struct HardenedCpuDriver {
    sys: Arc<Mutex<System>>,
}

impl HardenedCpuDriver {
    pub fn new() -> Self {
        let mut sys = System::new_all();
        sys.refresh_cpu();
        Self { sys: Arc::new(Mutex::new(sys)) }
    }
}

impl SovereignDriver for HardenedCpuDriver {
    fn get_type(&self) -> DriverType { DriverType::Compute }
    fn get_name(&self) -> &str { "HAL-0-CPU" }
    fn status(&self) -> String {
        let mut sys = self.sys.lock().unwrap();
        sys.refresh_cpu();
        let load: f32 = sys.cpus().iter().map(|c| c.cpu_usage()).sum::<f32>() / sys.cpus().len() as f32;
        format!("Cores: {}, Load: {:.1}%", sys.cpus().len(), load)
    }
}

// 🚀 REAL HAL Driver: NVIDIA GPU (if available)
pub struct HardenedGpuDriver {
    nvml: Option<Nvml>,
}

impl HardenedGpuDriver {
    pub fn new() -> Self {
        Self { nvml: Nvml::init().ok() }
    }
}

impl SovereignDriver for HardenedGpuDriver {
    fn get_type(&self) -> DriverType { DriverType::Gpu }
    fn get_name(&self) -> &str { "HAL-0-NVML" }
    fn status(&self) -> String {
        if let Some(ref n) = self.nvml {
            if let Ok(device) = n.device_by_index(0) {
                let name = device.name().unwrap_or("Unknown".to_string());
                let mem = device.memory_info().map(|m| m.total / 1024 / 1024).unwrap_or(0);
                return format!("{}: {}MB VRAM", name, mem);
            }
        }
        "No NVIDIA GPU detected".to_string()
    }
}

// Fallback/Legacy for IO
pub struct NetworkMeshDriver {
    pub throughput_mbps: u32,
}

impl SovereignDriver for NetworkMeshDriver {
    fn get_type(&self) -> DriverType { DriverType::Storage }
    fn get_name(&self) -> &str { "HAL-0-NetMesh" }
    fn status(&self) -> String { format!("Bandwidth: {} Mbps", self.throughput_mbps) }
}
