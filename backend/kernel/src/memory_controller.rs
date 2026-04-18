use std::sync::{Arc, Mutex};
use crate::process_manager::ProcessManager;

#[cfg(windows)]
use windows_sys::Win32::System::Memory::{VirtualAlloc, MEM_RESERVE, PAGE_NOACCESS, VirtualFree, MEM_RELEASE};

#[cfg(unix)]
use libc::{mmap, munmap, PROT_NONE, MAP_PRIVATE, MAP_ANONYMOUS};

pub struct MemoryController {
    process_manager: Arc<ProcessManager>,
    soft_limit_kb: u64,
    hard_limit_kb: u64,
    reservations: Arc<Mutex<std::collections::HashMap<u64, u64>>>, // ptr -> size
}

impl MemoryController {
    pub fn new(process_manager: Arc<ProcessManager>, limit_mb: u64) -> Self {
        Self {
            process_manager,
            soft_limit_kb: (limit_mb * 1024) * 8 / 10, // 80% soft limit
            hard_limit_kb: limit_mb * 1024,
            reservations: Arc::new(Mutex::new(std::collections::HashMap::new())),
        }
    }

    pub fn reserve_memory(&self, size_bytes: u64) -> Result<u64, String> {
        let ptr: *mut std::ffi::c_void;
        
        #[cfg(windows)]
        unsafe {
            ptr = VirtualAlloc(std::ptr::null(), size_bytes as usize, MEM_RESERVE, PAGE_NOACCESS);
        }

        #[cfg(unix)]
        unsafe {
            ptr = mmap(std::ptr::null_mut(), size_bytes as usize, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
            if ptr == libc::MAP_FAILED {
                return Err("mmap failed".to_string());
            }
        }

        if ptr.is_null() {
            return Err("System memory reservation failed".to_string());
        }

        let address = ptr as u64;
        self.reservations.lock().unwrap().insert(address, size_bytes);
        
        log::info!("🧠 [Kernel] MEM_RESERVE: Allocated {} bytes at 0x{:X}", size_bytes, address);
        Ok(address)
    }

    pub fn enforce_limits(&self) {
        let processes = self.process_manager.get_process_list();
        for proc in processes {
            if proc.memory_usage_kb > self.hard_limit_kb {
                log::error!("❌ [OOM-HARD] Process {} ({}) killed: {}KB > {}KB", 
                    proc.id, proc.name, proc.memory_usage_kb, self.hard_limit_kb);
                let _ = self.process_manager.kill_process(proc.id);
            } else if proc.memory_usage_kb > self.soft_limit_kb {
                log::warn!("⚠️ [OOM-SOFT] Process {} ({}) triggers Virtual Swap: {}KB > {}KB", 
                    proc.id, proc.name, proc.memory_usage_kb, self.soft_limit_kb);
                self.swap_to_disk(&proc.id, proc.memory_usage_kb - self.soft_limit_kb);
            }
        }
    }

    fn swap_to_disk(&self, process_id: &str, amount_kb: u64) {
        // Sovereign v17.0: Simulated Virtual Swap to Tier 5 (IPFS/Disk)
        log::info!("💾 [MemoryController] Swapping {}KB for process {} to Tier 5 storage...", amount_kb, process_id);
    }
}
