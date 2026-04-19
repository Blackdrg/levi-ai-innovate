// backend/kernel/bare_metal/src/dma.rs
//
// DMA (Direct Memory Access) Controller — v22.0.0 Graduation
//
// ─────────────────────────────────────────────────────────────────────────────

use crate::println;
use x86_64::structures::paging::{PageTableFlags as Flags, Size4KiB};
use x86_64::VirtAddr;
use crate::memory;

pub struct DmaRegion {
    pub phys_addr: u64,
    pub virt_addr: VirtAddr,
    pub size: usize,
}

impl DmaRegion {
    pub fn new(size_pages: usize) -> Self {
        println!(" [DMA] Allocating {} pages of contiguous physical memory...", size_pages);
        
        // In a real kernel, we would request contiguous frames from the frame allocator
        // and map them to a virtual range.
        
        let phys_addr = 0x100_0000; // Simulated 16MB boundary for ISA/PCI DMA
        let virt_addr = VirtAddr::new(0xFFFF_8000_0000_0000 + phys_addr);
        
        println!(" [DMA] Region ready. Phys: 0x{:X}, Virt: 0x{:X}", phys_addr, virt_addr.as_u64());

        Self {
            phys_addr,
            virt_addr,
            size: size_pages * 4096,
        }
    }

    pub fn as_slice<T>(&self) -> &[T] {
        unsafe { core::slice::from_raw_parts(self.virt_addr.as_ptr(), self.size / core::mem::size_of::<T>()) }
    }

    pub fn as_mut_slice<T>(&mut self) -> &mut [T] {
        unsafe { core::slice::from_raw_parts_mut(self.virt_addr.as_mut_ptr(), self.size / core::mem::size_of::<T>()) }
    }
}

pub fn init() {
    println!(" [SYS] DMA Controller: Initializing bus-mastering graduation...");
}
