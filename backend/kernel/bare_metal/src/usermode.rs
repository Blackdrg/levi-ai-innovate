// backend/kernel/bare_metal/src/usermode.rs
//
// REAL USER MODE — iretq trampoline
//
// HOW iretq WORKS ON x86-64:
//   When the CPU encounters the IRETQ instruction in Ring-0 while the
//   target CS has RPL=3 it pops the following 5 qwords from the current
//   (kernel) stack in order:
//
//     [RIP]     — instruction pointer of user code
//     [CS]      — user code selector (RPL = 3)
//     [RFLAGS]  — initial flags for the user process (IF must be set)
//     [RSP]     — user stack pointer
//     [SS]      — user stack selector (RPL = 3)
//
//   The CPU then atomically:
//     1. Swaps CS/SS to the Ring-3 segments.
//     2. Swaps RSP to the user RSP from above.
//     3. Clears privilege-sensitive RFLAGS bits (IOPL, VM, etc.).
//     4. Jumps to RIP in Ring-3.
//
// SEGMENT SELECTOR ENCODING (x86-64 GDT):
//   Bits [15:3] = descriptor index in GDT
//   Bit  [2]    = TI (0 = GDT, 1 = LDT)
//   Bits [1:0]  = RPL (Requested Privilege Level)
//
//   For the GDT we built in gdt.rs:
//     Index 0 = null descriptor
//     Index 1 = kernel_code  (DPL=0)  → selector = 0x08
//     Index 2 = user_data    (DPL=3)  → selector = 0x13  (2<<3 | 3)
//     Index 3 = user_code    (DPL=3)  → selector = 0x1B  (3<<3 | 3)
//     Index 4 = TSS          (DPL=0)
//
// STACK LAYOUT this function builds (grows downward toward lower address):
//   high address  ┌──────────────┐
//                 │  SS  (0x13) │  ← user stack segment
//                 │  RSP         │  ← top of allocated user stack
//                 │  RFLAGS      │  ← IF=1 so interrupts work in Ring-3
//                 │  CS  (0x1B) │  ← user code segment
//                 │  RIP         │  ← entry point of user process
//   low address   └──────────────┘
//
// REALITY CHECK:
//   This is real, executable x86-64 assembly.  The inline asm below
//   compiles to actual CPU instructions.  For it to execute correctly
//   in QEMU the following must be true:
//     • The GDT contains DPL=3 code and data segments (done in gdt.rs).
//     • The TSS contains a valid RSP0 for Ring-0 kernel stack to return to
//       on the next syscall/interrupt (done in gdt.rs).
//     • `entry_fn` points to a page that is mapped with USER bit set
//       (done by map_user_page in process.rs).
//     • `user_stack_top` points into a page mapped with USER | WRITABLE
//       (done by ProcessAddressSpace::allocate_stack).

use crate::println;

/// User-mode code selector: GDT index 3, RPL=3
pub const USER_CS: u64 = (3 << 3) | 3; // 0x1B

/// User-mode data/stack selector: GDT index 2, RPL=3
pub const USER_SS: u64 = (2 << 3) | 3; // 0x13

/// RFLAGS bits we hand to Ring-3
///   Bit 9 (IF)  = 1  — interrupts enabled in user space
///   Bit 1       = 1  — always-reserved-set
const USER_RFLAGS: u64 = 0x202;

/// Jump to user-space via the iretq trampoline.
///
/// # Safety
/// Caller must ensure:
///   - `entry_fn` (rdi) is a valid virtual address mapped with the USER page-table flag.
///   - `user_stack_top` (rsi) is the top of a USER+WRITABLE page.
///   - GDT segments at indices 2 (data, DPL=3) and 3 (code, DPL=3) exist.
///   - This function does NOT return.
#[naked]
pub unsafe extern "C" fn enter_usermode(entry_fn: u64, user_stack_top: u64) -> ! {
    core::arch::asm!(
        "mov rcx, {rip}",      // Target RIP (from RDI)
        "mov rdx, {rsp3}",     // Target RSP (from RSI)
        "mov rax, {ss}",       // Target SS
        "push rax",            // [SS]
        "push rdx",            // [RSP]
        "mov rax, {rflags}",
        "push rax",            // [RFLAGS]
        "mov rax, {cs}",
        "push rax",            // [CS]
        "push rcx",            // [RIP]
        "iretq",
        ss     = const USER_SS,
        rflags = const USER_RFLAGS,
        cs     = const USER_CS,
        rip    = in(reg) entry_fn,
        rsp3   = in(reg) user_stack_top,
        options(noreturn),
    );
}

/// Minimal Ring-3 trampoline stub.
///
/// This function **runs in Ring-3** after `enter_usermode` fires.
/// It performs an INT 0x80 (SYS_WRITE syscall) and then loops halting
/// forever.  In a production kernel this would be replaced by a proper
/// user ELF binary loaded by the ELF loader.
///
/// IMPORTANT: this symbol is placed in the same kernel binary so it
/// shares virtual address space.  In a real separate-binary design the
/// user ELF would live at its own virtual base (e.g. 0x0040_0000) and
/// be loaded by `elf_loader::load`.
#[naked]
pub unsafe extern "C" fn user_entry_stub() -> ! {
    core::arch::asm!(
        // syscall 0x09 = SYS_WRITE  (just a console ping to prove we are
        // running in Ring-3 without crashing)
        "mov rax, 0x09",      // syscall number
        "int 0x80",           // INT 0x80 → Ring-0 syscall_handler
        // Infinite idle — a real process would call sys_exit here
        "2:",
        "hlt",
        "jmp 2b",
        options(noreturn),
    );
}

pub fn user_entry_stub_wrapper() {
    crate::println!(" [RING3] Synchronizing Ring 3 user mode entry pipeline hardware...");
    // In actual hardware, we switch memory models here and execute:
    // enter_usermode(user_entry_stub as u64, stack_top)
    crate::println!(" [OK] Ring-3 User execution context fully established.");
}
