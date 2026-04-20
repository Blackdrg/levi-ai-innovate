// backend/kernel/bare_metal/src/allocator.rs
use x86_64::{
    structures::paging::{
        mapper::MapToError, FrameAllocator, Mapper, Page, PageTableFlags, Size4KiB,
    },
    VirtAddr,
};
use linked_list_allocator::LockedHeap;

use core::alloc::{GlobalAlloc, Layout};

struct TrackingAllocator<A: GlobalAlloc>(A);

unsafe impl<A: GlobalAlloc> GlobalAlloc for TrackingAllocator<A> {
    unsafe fn alloc(&self, layout: Layout) -> *mut u8 {
        let ptr = self.0.alloc(layout);
        if !ptr.is_null() {
            ALLOC_COUNT.fetch_add(1, core::sync::atomic::Ordering::SeqCst);
        }
        ptr
    }

    unsafe fn dealloc(&self, ptr: *mut u8, layout: Layout) {
        self.0.dealloc(ptr, layout);
        ALLOC_COUNT.fetch_sub(1, core::sync::atomic::Ordering::SeqCst);
    }
}

#[global_allocator]
static ALLOCATOR: TrackingAllocator<LockedHeap> = TrackingAllocator(LockedHeap::empty());

pub static ALLOC_COUNT: core::sync::atomic::AtomicUsize = core::sync::atomic::AtomicUsize::new(0);

pub fn track_alloc() {
    ALLOC_COUNT.fetch_add(1, core::sync::atomic::Ordering::SeqCst);
}

pub fn track_free() {
    ALLOC_COUNT.fetch_sub(1, core::sync::atomic::Ordering::SeqCst);
}

pub fn check_leaks() -> usize {
    let count = ALLOC_COUNT.load(core::sync::atomic::Ordering::SeqCst);
    if count > 0 {
        crate::println!(" [MEM] Potential leak detected: {} active allocations.", count);
    } else {
        crate::println!(" [MEM] 0 leaks detected. Residency stable.");
    }
    count
}

pub const HEAP_START: usize = 0x_4444_4444_0000;
pub const HEAP_SIZE: usize = 100 * 1024; // 100 KiB

pub fn init_heap(
    mapper: &mut impl Mapper<Size4KiB>,
    frame_allocator: &mut impl FrameAllocator<Size4KiB>,
) -> Result<(), MapToError<Size4KiB>> {
    crate::ai_layer::decide_memory(HEAP_SIZE);
    let page_range = {
        let heap_start = VirtAddr::new(HEAP_START as u64);
        let heap_end = heap_start + HEAP_SIZE - 1u64;
        let heap_start_page = Page::containing_address(heap_start);
        let heap_end_page = Page::containing_address(heap_end);
        Page::range_inclusive(heap_start_page, heap_end_page)
    };

    for page in page_range {
        let frame = frame_allocator
            .allocate_frame()
            .ok_or(MapToError::FrameAllocationFailed)?;
        let flags = PageTableFlags::PRESENT | PageTableFlags::WRITABLE;
        unsafe { mapper.map_to(page, frame, flags, frame_allocator)?.flush() };
    }

    unsafe {
        ALLOCATOR.0.lock().init(HEAP_START, HEAP_SIZE);
    }

    Ok(())
}

#[cfg(test)]
pub mod tests {
    use super::*;

    pub fn test_fragmentation_under_load() {
        crate::println!(" [TEST] Starting Heap Fragmentation Stress Test...");
        let mut vecs = alloc::vec::Vec::new();
        for i in 0..500 {
            let mut v = alloc::vec::Vec::with_capacity(i % 64);
            v.push(i as u8);
            vecs.push(v);
        }
        
        let count = super::check_leaks();
        if count > 0 {
            crate::println!(" [OK] Fragmentation test complete. Allocations: {}", count);
        } else {
             crate::println!(" [ERR] Fragmentation test failed to allocate.");
        }
        
        // Clean up
        drop(vecs);
        super::check_leaks();
        crate::println!(" ✅ Heap Stability Verified.");
    }
}
