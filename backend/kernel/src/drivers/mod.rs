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
