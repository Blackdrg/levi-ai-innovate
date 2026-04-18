// backend/kernel/bare_metal/src/memory.rs
use x86_64::{
    structures::paging::{PageTable, OffsetPageTable},
    VirtAddr,
};

/// Initialize a new OffsetPageTable.
pub unsafe fn init(physical_memory_offset: VirtAddr) -> OffsetPageTable<'static> {
    let level_4_table = active_level_4_table(physical_memory_offset);
    OffsetPageTable::new(level_4_table, physical_memory_offset)
}

/// Returns a mutable reference to the active level 4 table.
unsafe fn active_level_4_table(physical_memory_offset: VirtAddr)
    -> &'static mut PageTable
{
    use x86_64::registers::control::Cr3;

    let (level_4_table_frame, _) = Cr3::read();

    let phys = level_4_table_frame.start_address();
    let virt = physical_memory_offset + phys.as_u64();
    let page_table_ptr: *mut PageTable = virt.as_mut_ptr();

    &mut *page_table_ptr
}

pub struct BootInfoFrameAllocator {
    pub(crate) memory_map: &'static [u8], // Simplified for now
    pub(crate) next: usize,
}

impl BootInfoFrameAllocator {
    pub unsafe fn new(memory_map: &'static [u8]) -> Self {
        BootInfoFrameAllocator {
            memory_map,
            next: 0,
        }
    }
}
