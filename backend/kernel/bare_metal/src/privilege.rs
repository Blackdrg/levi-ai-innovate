// backend/kernel/bare_metal/src/privilege.rs
//
// ─────────────────────────────────────────────────────────────────────────────
// HONEST PRIVILEGE REALITY CHECK
//
// What "Ring-3 isolation" actually means in x86-64:
//
//   Ring-0 (kernel mode): full access to all CPU instructions (HLT, CR3 write,
//   I/O ports, etc.) and all memory pages regardless of page-table flags.
//
//   Ring-3 (user mode): the CPU enforces the following hardware gates:
//     1. Memory access: any page NOT marked with the USER flag (bit 2 in the
//        page-table entry) raises a #PF with error bit 2 (U/S) = 0.
//     2. Privileged instructions: LGDT, LLDT, LTR, LMSW, CLTS, HLT,
//        IN/OUT (if IOPL < 3), WRMSR, RDMSR, MOV CRn, MOV DRn all
//        raise #GP(0) if executed from Ring-3.
//     3. Syscall path: the CPU needs either SYSCALL/SYSRET (MSR-based fast
//        path) or INT n with a Gate DPL ≥ 3 (e.g. our INT 0x80 with DPL=3).
//
// The `enter_usermode()` function in usermode.rs is the REAL mechanism:
//   it builds a proper iretq frame and jumps to Ring-3 code.
//
// This module's `enforce_isolation()` is a LOGGING FUNCTION ONLY.  It does
// not change hardware state.  Hardware state changes happen in:
//   • gdt::init()           — loads the GDT with DPL=3 segments
//   • usermode::enter_usermode() — executes iretq to jump to Ring-3
//   • Memory mapping flags  — PAGE_USER bit in every page-table entry
//
// If you see code calling enforce_isolation() and expecting hardware isolation
// to activate at that point — that is WRONG.  Isolation is a consequence of
// what page tables and GDT entries you loaded, not of calling this function.
// ─────────────────────────────────────────────────────────────────────────────

use crate::println;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PrivilegeLevel {
    Ring0, // Kernel — unrestricted CPU access
    Ring3, // User   — hardware-enforced memory & instruction restrictions
}

/// Log the current execution context.  This function itself does NOT
/// change the CPU privilege level — it can only run in Ring-0.
/// The actual Ring-3 entry is performed by `usermode::enter_usermode()`.
pub fn log_privilege(level: PrivilegeLevel) {
    match level {
        PrivilegeLevel::Ring0 => {
            println!(" [PRIV] CPL=0: Kernel space — unrestricted hardware access.");
        }
        PrivilegeLevel::Ring3 => {
            println!(" [PRIV] CPL=3: User space — page-table + instruction restrictions active.");
            println!(" [PRIV] Real entry: usermode::enter_usermode() performs iretq → Ring-3.");
        }
    }
}

/// Back-compat alias used in main.rs (was enforce_isolation).
/// Now documents the truth: this is logging only.
pub fn enforce_isolation(level: PrivilegeLevel) {
    log_privilege(level);
}
