// backend/kernel/bare_metal/src/elf_loader.rs
use crate::println;
use crate::memory;
use x86_64::VirtAddr;
use x86_64::structures::paging::{Page, PageTableFlags, Size4KiB, Mapper, FrameAllocator};

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub struct ProgramHeader {
    pub p_type: u32,
    pub p_flags: u32,
    pub p_offset: u64,
    pub p_vaddr: u64,
    pub p_paddr: u64,
    pub p_filesz: u64,
    pub p_memsz: u64,
    pub p_align: u64,
}

impl ElfLoader {
    pub fn load_and_execute<M, A>(
        elf_data: &[u8],
        mapper: &mut M,
        frame_allocator: &mut A,
    ) -> Result<VirtAddr, &'static str>
    where
        M: Mapper<Size4KiB>,
        A: FrameAllocator<Size4KiB>,
    {
        println!(" [OK] ELF: Parsing 64-bit binary header...");
        
        if elf_data.len() < 64 || &elf_data[1..4] != b"ELF" {
            return Err("Invalid ELF header");
        }

        let entry_point = unsafe { *(elf_data.as_ptr().add(24) as *const u64) };
        let ph_offset = unsafe { *(elf_data.as_ptr().add(32) as *const u64) };
        let ph_count = unsafe { *(elf_data.as_ptr().add(56) as *const u16) };

        println!(" [OK] ELF: Entry Point: 0x{:X}", entry_point);

        for i in 0..ph_count {
            let offset = ph_offset as usize + (i as usize * 56);
            let ph = unsafe { *(elf_data.as_ptr().add(offset) as *const ProgramHeader) };
            
            if ph.p_type == 1 { // PT_LOAD
                let start_addr = VirtAddr::new(ph.p_vaddr);
                let mem_size = ph.p_memsz;
                
                let start_page = Page::containing_address(start_addr);
                let end_page = Page::containing_address(start_addr + mem_size - 1u64);
                let pages = Page::range_inclusive(start_page, end_page);

                for page in pages {
                    let frame = frame_allocator.allocate_frame()
                        .ok_or("No frames available for ELF loading")?;
                    let flags = PageTableFlags::PRESENT | PageTableFlags::WRITABLE | PageTableFlags::USER_ACCESSIBLE;
                    unsafe { mapper.map_to(page, frame, flags, frame_allocator).map_err(|_| "Mapping failed")?.flush() };
                }

                // Copy data
                let data_start = ph.p_offset as usize;
                let data_end = data_start + ph.p_filesz as usize;
                let target = unsafe { core::slice::from_raw_parts_mut(ph.p_vaddr as *mut u8, ph.p_filesz as usize) };
                target.copy_from_slice(&elf_data[data_start..data_end]);
                
                println!(" [ELF] Mapped Segment: V:0x{:X} ({} bytes)", ph.p_vaddr, ph.p_memsz);
            }
        }
        
        println!(" [OK] ELF: Handoff ready.");
        Ok(VirtAddr::new(entry_point))
    }
}
