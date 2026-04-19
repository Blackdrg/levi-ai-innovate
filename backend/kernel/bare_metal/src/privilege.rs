// backend/kernel/bare_metal/src/privilege.rs
//
// ─────────────────────────────────────────────────────────────────────────────
// HARD PRIVILEGE GRADUATION — Ring-3 Transition Logic
//
// ─────────────────────────────────────────────────────────────────────────────

use crate::println;
use crate::usermode;

#[derive(Debug, Clone, Copy, PartialEq)]
pub enum PrivilegeLevel {
    Ring0, // Kernel — unrestricted CPU access
    Ring3, // User   — hardware-enforced memory & instruction restrictions
}

/// Perform a hardware-level privilege transition.
/// If Level is Ring3, we allocate a stack and jump via iretq.
pub fn enforce_isolation(level: PrivilegeLevel) {
    match level {
        PrivilegeLevel::Ring0 => {
            println!(" [PRIV] CPL=0: Kernel space — unrestricted hardware access.");
        }
        PrivilegeLevel::Ring3 => {
            println!(" [PRIV] ATTEMPTING CPL=3 TRANSITION via iretq...");
            
            // 1. Allocate a Ring-3 user stack (mocked here as a fixed block in .bss)
            // In a real process manager this is a per-task page allocation.
            static mut USER_STACK: [u8; 4096] = [0u8; 4096];
            let stack_top = unsafe { USER_STACK.as_ptr().add(4096) as u64 };

            println!(" [PRIV] Ring-3 stack allocated at 0x{:X}", stack_top);
            println!(" [PRIV] Executing iretq trampoline...");

            // 2. Execute iretq. This function DOES NOT RETURN.
            unsafe {
                usermode::enter_usermode(usermode::user_entry_stub as u64, stack_top);
            }
        }
    }
}

pub fn log_privilege(level: PrivilegeLevel) {
    enforce_isolation(level);
}
