// backend/kernel/src/memory_paging.rs
use std::collections::HashMap;
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PageFlags {
    Present = 1 << 0,
    Writable = 1 << 1,
    UserAccessible = 1 << 2,
    WriteThrough = 1 << 3,
    NoExecute = 1 << 63,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PageTableEntry {
    pub frame_address: u64,
    pub flags: u64,
}

pub struct VirtualMemoryManager {
    // Simulated Page Tables: Virtual Page Number -> Page Table Entry
    pub page_tables: HashMap<u64, PageTableEntry>,
    pub physical_frames: Vec<bool>, // true = allocated
    pub total_frames: usize,
}

impl VirtualMemoryManager {
    pub fn new(ram_mb: usize) -> Self {
        let frames = (ram_mb * 1024 * 1024) / 4096; // 4KB Pages
        Self {
            page_tables: HashMap::new(),
            physical_frames: vec![false; frames],
            total_frames: frames,
        }
    }

    pub fn map_page(&mut self, virtual_addr: u64, flags: u64) -> Result<u64, String> {
        let vpn = virtual_addr >> 12;
        
        // Find a free physical frame
        if let Some(frame_idx) = self.physical_frames.iter().position(|&f| !f) {
            self.physical_frames[frame_idx] = true;
            let physical_addr = (frame_idx as u64) << 12;
            
            self.page_tables.insert(vpn, PageTableEntry {
                frame_address: physical_addr,
                flags,
            });
            
            Ok(physical_addr)
        } else {
            Err("Out of Physical RAM (OOM)".to_string())
        }
    }

    pub fn translate(&self, virtual_addr: u64) -> Option<u64> {
        let vpn = virtual_addr >> 12;
        let offset = virtual_addr & 0xFFF;
        
        self.page_tables.get(&vpn).map(|pte| pte.frame_address + offset)
    }

    pub fn free_page(&mut self, virtual_addr: u64) {
        let vpn = virtual_addr >> 12;
        if let Some(pte) = self.page_tables.remove(&vpn) {
            let frame_idx = (pte.frame_address >> 12) as usize;
            if frame_idx < self.physical_frames.len() {
                self.physical_frames[frame_idx] = false;
            }
        }
    }
}
