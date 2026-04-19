// backend/kernel/bare_metal/src/shmem.rs
//
// SHARED MEMORY IPC — v22.0.0 Graduation
//
// ─────────────────────────────────────────────────────────────────────────────

use crate::println;
use alloc::vec::Vec;
use spin::Mutex;
use lazy_static::lazy_static;

pub struct ShMemRegion {
    pub paddr: u64,
    pub size: usize,
    pub owner_pid: u64,
}

pub struct SharedMemoryManager {
    regions: Vec<ShMemRegion>,
}

impl SharedMemoryManager {
    pub fn new() -> Self {
        Self { regions: Vec::new() }
    }

    pub fn create_region(&mut self, pid: u64, size: usize) -> u64 {
        // In a real kernel this would grab a free physical frame.
        let paddr = 0x8000_0000 + (self.regions.len() as u64 * 0x1000);
        self.regions.push(ShMemRegion { paddr, size, owner_pid: pid });
        println!(" [IPC] Shared Memory Region created at 0x{:X} for PID {}.", paddr, pid);
        paddr
    }
}

lazy_static! {
    pub static ref SHMEM_MANAGER: Mutex<SharedMemoryManager> = Mutex::new(SharedMemoryManager::new());
}
