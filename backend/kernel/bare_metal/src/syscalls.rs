// backend/kernel/bare_metal/src/syscalls.rs
use crate::println;
use crate::interrupts;
use x86_64::structures::idt::{InterruptStackFrame};

pub fn init() {
    println!(" [OS] SYSCALL: Mapping vector 0x80 for Sovereign ABI...");
    // IDT registration for 0x80 is handled in interrupts.rs
}

#[no_mangle]
pub extern "x86-interrupt" fn syscall_handler(
    stack_frame: InterruptStackFrame) 
{
    // 🧪 Native ABI Dispatcher
    // In real system, RAX would contain the syscall ID
    let syscall_id: u64 = 0; // Simulated
    
    match syscall_id {
        0x01 => println!(" [SYS] MEM_RESERVE: Allocation requested."),
        0x02 => println!(" [SYS] WAVE_SPAWN: Creating sandboxed pulse."),
        0x03 => println!(" [SYS] BFT_SIGN: Signing hardware pulse."),
        0x09 => println!(" [SYS] SYS_WRITE: Buffered console output."),
        _ => println!(" [SYS] Unknown syscall ID: 0x{:X}", syscall_id),
    }

    // Return logic would go here
}
