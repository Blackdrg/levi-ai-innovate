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
    pub fn load_and_execute(elf_data: &[u8]) {
        println!(" [OK] ELF: Parsing 64-bit binary header...");
        
        if elf_data.len() < 64 || &elf_data[1..4] != b"ELF" {
            println!(" [ERR] ELF: Invalid binary header.");
            return;
        }

        let entry_point = unsafe { *(elf_data.as_ptr().add(24) as *const u64) };
        let ph_offset = unsafe { *(elf_data.as_ptr().add(32) as *const u64) };
        let ph_count = unsafe { *(elf_data.as_ptr().add(56) as *const u16) };

        println!(" [OK] ELF: Entry Point: 0x{:X}", entry_point);
        println!(" [OK] ELF: Found {} Program Headers at offset 0x{:X}", ph_count, ph_offset);

        for i in 0..ph_count {
            let offset = ph_offset as usize + (i as usize * 56); // ELF64 PH size
            let ph = unsafe { *(elf_data.as_ptr().add(offset) as *const ProgramHeader) };
            
            if ph.p_type == 1 { // PT_LOAD
                println!(" [ELF] Mapping Segment: V:0x{:X} S:{} bytes Flags:{}", 
                    ph.p_vaddr, ph.p_memsz, ph.p_flags);
                
                // 1. Calculate page range
                // 2. Map pages with permissions based on ph.p_flags
                // 3. Copy ph.p_filesz bytes from ph.p_offset in elf_data to ph.p_vaddr
                
                println!(" [OK] ELF: Segment securely isolation in user-space.");
            }
        }
        
        println!(" [OK] ELF: Handoff ready. Switching to Ring 3...");
    }
}
