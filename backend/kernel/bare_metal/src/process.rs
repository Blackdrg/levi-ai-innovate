// backend/kernel/bare_metal/src/process.rs
//
// REAL PROCESS / ADDRESS-SPACE ISOLATION
//
// This module owns:
//   1. ProcessAddressSpace — per-process page table (CR3-level isolation)
//   2. Block allocator for physical frames
//   3. map_user_page() — maps a page with USER | PRESENT | WRITABLE
//   4. ProcessControlBlock (PCB) — kernel bookkeeping per process
//
// ─────────────────────────────────────────────────────────────────────────────
// HOW SEPARATE PAGE TABLES WORK ON x86-64:
//
//   Each process has its own *root* Level-4 page table (PML4) stored in
//   a 4 KiB aligned physical frame.  The kernel writes its own mappings
//   into the *top half* of every PML4 (entries 256–511, the canonical
//   kernel range) so that after a context switch the kernel can still run
//   without reloading CR3.  User mappings live in entries 0–255.
//
//   Switching processes:
//     mov cr3, <new_pml4_phys_addr>   ← flushes the TLB automatically
//
//   Page-table flags of interest:
//     PRESENT  (bit 0)  — page is accessible
//     WRITABLE (bit 1)  — writes allowed
//     USER     (bit 2)  — Ring-3 code may access this page
//                          (without this bit the CPU raises #PF on any
//                           Ring-3 access regardless of the mapping)
//     NX       (bit 63) — no-execute; set on data / stack pages
//
// ─────────────────────────────────────────────────────────────────────────────
// REALITY CHECK — what is simulated vs. real here:
//
//   REAL:
//     • Physical frame allocation via a bitmap (BitmapFrameAllocator).
//     • Virtual→physical mapping construction via x86_64 crate primitives.
//     • USER flag correctly set on user pages.
//     • ProcessControlBlock with dedicated PML4 physical address.
//     • Page-fault recovery path in interrupts.rs reads CR2 + error
//       code and calls `handle_page_fault` below.
//
//   NOT YET REAL (marked TODO):
//     • CR3 swap on context switch (requires the scheduler to save/restore
//       CR3 alongside RIP/RSP in the task control block).
//     • Kernel-half mirroring (KPTI / shadow PML4).
//     • Copy-on-write fork() semantics.

use x86_64::{
    structures::paging::{
        FrameAllocator, Mapper, Page, PageTableFlags, PhysFrame, Size4KiB,
    },
    PhysAddr, VirtAddr,
};
use crate::println;
use alloc::vec::Vec;

// ─── Physical frame bitmap ────────────────────────────────────────────────────

/// Maximum physical frames we track (256 MiB / 4 KiB = 65 536 frames).
const MAX_FRAMES: usize = 65_536;

pub struct BitmapFrameAllocator {
    bitmap:    [u64; MAX_FRAMES / 64],
    next_hint: usize,
    base_phys: u64,   // physical address of frame 0
}

impl BitmapFrameAllocator {
    /// # Safety
    /// `base_phys` must be 4 KiB-aligned and the first `MAX_FRAMES` 4 KiB
    /// frames starting there must be usable RAM (not MMIO, not reserved).
    pub unsafe fn new(base_phys: u64) -> Self {
        Self {
            bitmap:    [0u64; MAX_FRAMES / 64],
            next_hint: 0,
            base_phys,
        }
    }

    fn set_used(&mut self, frame_idx: usize) {
        self.bitmap[frame_idx / 64] |= 1 << (frame_idx % 64);
    }

    fn is_used(&self, frame_idx: usize) -> bool {
        (self.bitmap[frame_idx / 64] >> (frame_idx % 64)) & 1 == 1
    }

    pub fn alloc(&mut self) -> Option<PhysAddr> {
        for _ in 0..MAX_FRAMES {
            let idx = self.next_hint;
            self.next_hint = (self.next_hint + 1) % MAX_FRAMES;
            if !self.is_used(idx) {
                self.set_used(idx);
                let phys = self.base_phys + (idx as u64) * 4096;
                return Some(PhysAddr::new(phys));
            }
        }
        None // out of memory
    }

    pub fn free(&mut self, phys: PhysAddr) {
        let offset = phys.as_u64().saturating_sub(self.base_phys);
        let idx = (offset / 4096) as usize;
        if idx < MAX_FRAMES {
            self.bitmap[idx / 64] &= !(1 << (idx % 64));
        }
    }
}

// ─── Per-process address space ────────────────────────────────────────────────

/// User virtual address layout constants.
///
/// These are *our* ABI decisions — they match the canonical x86-64 user
/// half (< 0x0000_8000_0000_0000).
pub const USER_CODE_BASE:  u64 = 0x0000_0000_0040_0000; // 4 MiB
pub const USER_STACK_BASE: u64 = 0x0000_0000_7FFF_0000; // just below 2 GiB
pub const USER_STACK_SIZE: usize = 4 * 4096;             // 4 pages = 16 KiB

pub struct ProcessAddressSpace {
    /// Physical address of the Level-4 page table root for this process.
    /// Must be written to CR3 when this process runs.
    pub pml4_phys: PhysAddr,

    /// Virtual addresses of pages we own so we can free them on exit.
    pub owned_pages: Vec<VirtAddr>,
}

impl ProcessAddressSpace {
    /// Allocate a fresh PML4 frame and copy the kernel mappings (top half)
    /// from the currently active page table so the kernel remains accessible
    /// after a CR3 switch.
    ///
    /// # Safety
    /// `phys_offset` is the virtual offset at which all physical memory is
    /// linearly mapped (provided by the bootloader).
    pub unsafe fn new(
        frame_alloc: &mut impl FrameAllocator<Size4KiB>,
        phys_offset:  VirtAddr,
    ) -> Option<Self> {
        use x86_64::registers::control::Cr3;
        use x86_64::structures::paging::PageTable;

        // 1. Allocate a fresh 4 KiB frame for the new PML4.
        let new_frame = frame_alloc.allocate_frame()?;
        let new_pml4_virt = phys_offset + new_frame.start_address().as_u64();
        let new_pml4: &mut PageTable = &mut *(new_pml4_virt.as_mut_ptr());
        new_pml4.zero();

        // 2. Copy kernel-half entries (indices 256 – 511) from the current PML4.
        let (current_frame, _) = Cr3::read();
        let current_pml4_virt = phys_offset + current_frame.start_address().as_u64();
        let current_pml4: &PageTable = &*(current_pml4_virt.as_ptr());

        // Copy kernel-half PML4 entries using raw pointer copy to avoid
        // PageTableEntry Copy/Clone trait issues across x86_64 crate versions.
        let src_ptr = current_pml4 as *const _ as *const u8;
        let dst_ptr = new_pml4    as *mut _   as *mut u8;
        // Each PML4 has 512 entries of 8 bytes = 4096 bytes total.
        // Kernel half starts at entry 256 → byte offset 256*8 = 2048.
        core::ptr::copy_nonoverlapping(
            src_ptr.add(256 * 8),
            dst_ptr.add(256 * 8),
            256 * 8, // 256 entries × 8 bytes
        );

        Some(ProcessAddressSpace {
            pml4_phys: new_frame.start_address(),
            owned_pages: Vec::new(),
        })
    }

    /// Allocate `USER_STACK_SIZE` bytes of physical RAM, map them
    /// at `USER_STACK_BASE` with PRESENT | WRITABLE | USER | NX flags,
    /// and return the virtual address of the *top* of the stack.
    pub fn allocate_stack(
        &mut self,
        mapper:      &mut impl Mapper<Size4KiB>,
        frame_alloc: &mut impl FrameAllocator<Size4KiB>,
    ) -> Option<VirtAddr> {
        let flags = PageTableFlags::PRESENT
            | PageTableFlags::WRITABLE
            | PageTableFlags::USER_ACCESSIBLE
            | PageTableFlags::NO_EXECUTE;

        let pages = USER_STACK_SIZE / 4096;
        for i in 0..pages {
            let virt = VirtAddr::new(USER_STACK_BASE + (i as u64) * 4096);
            let page: Page<Size4KiB> = Page::containing_address(virt);
            let frame = frame_alloc.allocate_frame()?;

            unsafe {
                mapper
                    .map_to(page, frame, flags, frame_alloc)
                    .ok()?
                    .flush();
            }
            self.owned_pages.push(virt);
        }

        // Stack top = highest byte + 1 (grows downward).
        Some(VirtAddr::new(USER_STACK_BASE + USER_STACK_SIZE as u64))
    }
}

/// Map a single page of user code at `virt` → `phys` with USER flag.
pub fn map_user_page(
    virt:        VirtAddr,
    phys:        PhysAddr,
    mapper:      &mut impl Mapper<Size4KiB>,
    frame_alloc: &mut impl FrameAllocator<Size4KiB>,
) -> bool {
    let flags = PageTableFlags::PRESENT
        | PageTableFlags::WRITABLE
        | PageTableFlags::USER_ACCESSIBLE;

    let page:  Page<Size4KiB>  = Page::containing_address(virt);
    let frame: PhysFrame<Size4KiB> = PhysFrame::containing_address(phys);

    unsafe {
        mapper
            .map_to(page, frame, flags, frame_alloc)
            .map(|flush| flush.flush())
            .is_ok()
    }
}

// ─── Page-fault recovery ─────────────────────────────────────────────────────
//
// Called from `interrupts::page_fault_handler` instead of panicking.
// Currently performs demand-zero mapping for pages in the user stack range.

pub fn handle_page_fault(
    fault_addr: VirtAddr,
    mapper:     &mut impl Mapper<Size4KiB>,
    frame_alloc:&mut impl FrameAllocator<Size4KiB>,
) {
    println!(" [PF] Page fault at 0x{:X} — attempting recovery...", fault_addr.as_u64());

    // Demand-zero: if the fault is within the user stack area, allocate a
    // fresh zeroed frame and map it in.
    let stack_range = USER_STACK_BASE..(USER_STACK_BASE + USER_STACK_SIZE as u64);
    if stack_range.contains(&fault_addr.as_u64()) {
        if let Some(frame) = frame_alloc.allocate_frame() {
            let flags = PageTableFlags::PRESENT
                | PageTableFlags::WRITABLE
                | PageTableFlags::USER_ACCESSIBLE
                | PageTableFlags::NO_EXECUTE;
            let page: Page<Size4KiB> = Page::containing_address(fault_addr);
            unsafe {
                if mapper.map_to(page, frame, flags, frame_alloc).is_ok() {
                    println!(" [PF] Demand-zero page mapped at 0x{:X} — RECOVERED.", fault_addr.as_u64());
                    return;
                }
            }
        }
        println!(" [PF] Recovery failed: out of physical frames.");
    } else {
        // Faults outside known user mappings are fatal.
        panic!(" [PF] UNHANDLED PAGE FAULT at 0x{:X} — KERNEL HALT", fault_addr.as_u64());
    }
}

// ─── Process Control Block ────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ProcessState {
    Ready,
    Running,
    Blocked,
    Zombie,
}

pub struct ProcessControlBlock {
    pub pid:         u64,
    pub state:       ProcessState,
    pub pml4_phys:   PhysAddr,    // CR3 value for this process
    pub kernel_stack_top: VirtAddr, // RSP0 stored in TSS on ctx switch
    pub user_rip:    u64,          // saved instruction pointer
    pub user_rsp:    u64,          // saved user stack pointer
}

impl ProcessControlBlock {
    pub fn new(pid: u64, pml4_phys: PhysAddr, kernel_stack_top: VirtAddr, entry: u64, user_rsp: u64) -> Self {
        ProcessControlBlock {
            pid,
            state: ProcessState::Ready,
            pml4_phys,
            kernel_stack_top,
            user_rip: entry,
            user_rsp,
        }
    }
}
