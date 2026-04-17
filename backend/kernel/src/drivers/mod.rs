// backend/kernel/src/drivers/mod.rs
use std::sync::{Arc, Mutex};
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum DriverType {
    Compute,
    Memory,
    Perception,
    Storage,
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

// Sample Memory Driver
pub struct VirtualMemoryDriver {
    pub total_vmem: u64,
}

impl SovereignDriver for VirtualMemoryDriver {
    fn get_type(&self) -> DriverType { DriverType::Memory }
    fn get_name(&self) -> &str { "VMem-Driver-01" }
    fn status(&self) -> String { format!("Available: {}MB", self.total_vmem) }
}

pub struct CpuDriver {
    pub cores: u32,
}

impl SovereignDriver for CpuDriver {
    fn get_type(&self) -> DriverType { DriverType::Compute }
    fn get_name(&self) -> &str { "CPU-Core-Driver" }
    fn status(&self) -> String { format!("Active Cores: {}", self.cores) }
}

pub struct NetworkDriver {
    pub throughput_mbps: u32,
}

impl SovereignDriver for NetworkDriver {
    fn get_type(&self) -> DriverType { DriverType::Storage } // Mapped to storage for IO
    fn get_name(&self) -> &str { "Net-Mesh-Driver" }
    fn status(&self) -> String { format!("Bandwidth: {} Mbps", self.throughput_mbps) }
}

pub struct PerceptionDriver {
    pub latency_ms: u32,
}

impl SovereignDriver for PerceptionDriver {
    fn get_type(&self) -> DriverType { DriverType::Perception }
    fn get_name(&self) -> &str { "Intent-HAL-v2" }
    fn status(&self) -> String { format!("Latency: {}ms", self.latency_ms) }
}
