// backend/kernel/bare_metal/src/user_shell.rs
//
// NATIVE USER-MODE SHELL — v22.0.0 Graduation [RING 3]
//
// ─────────────────────────────────────────────────────────────────────────────

use crate::println;

/// This function represents a binary that would be loaded into Ring 3.
/// It uses the 'syscall' or 'int 0x80' instruction to talk to the kernel.
#[no_mangle]
pub extern "C" fn user_shell_main() {
    // 1. Hello from Ring 3
    unsafe {
        core::arch::asm!(
            "mov rax, 1",        // sys_write
            "mov rdi, 1",        // fd (stdout)
            "mov rsi, {msg}",    // buffer
            "mov rdx, {len}",    // length
            "int 0x80",          // SYSCALL trigger
            msg = in(reg) " [USER] Hello from Ring 3 Sovereign Shell!\n".as_ptr(),
            len = in(reg) 42,
        );
    }

    // 2. Request a BENCHMARK
    unsafe {
        core::arch::asm!(
            "mov rax, 0x10",     // SYS_BENCH_RTT
            "int 0x80",
        );
    }

    // 3. Request a TPM PCR read (Hardware-Attested)
    unsafe {
        core::arch::asm!(
             "mov rax, 0x11",    // SYS_TPM_READ_PCR
             "mov rdi, 0",       // PCR index 0
             "int 0x80",
        );
    }

    // 4. Exit
    unsafe {
        core::arch::asm!(
            "mov rax, 60",       // sys_exit
            "int 0x80",
        );
    }

    loop {}
}
