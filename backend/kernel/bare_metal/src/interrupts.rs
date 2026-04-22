// backend/kernel/bare_metal/src/interrupts.rs
use x86_64::structures::idt::{InterruptDescriptorTable, InterruptStackFrame, PageFaultErrorCode};
use lazy_static::lazy_static;
use crate::gdt;
use crate::println;
use crate::keyboard;
use pic8259::ChainedPics;
use spin;

pub const PIC_1_OFFSET: u8 = 32;
pub const PIC_2_OFFSET: u8 = PIC_1_OFFSET + 8;

pub static PICS: spin::Mutex<ChainedPics> =
    spin::Mutex::new(unsafe { ChainedPics::new(PIC_1_OFFSET, PIC_2_OFFSET) });

#[derive(Debug, Clone, Copy)]
#[repr(u8)]
pub enum InterruptIndex {
    Timer = PIC_1_OFFSET,
    Keyboard = PIC_1_OFFSET + 1,
}

impl InterruptIndex {
    fn as_u8(self) -> u8 {
        self as u8
    }

    fn as_usize(self) -> usize {
        usize::from(self.as_u8())
    }
}

lazy_static! {
    static ref IDT: InterruptDescriptorTable = {
        let mut idt = InterruptDescriptorTable::new();
        idt.divide_error.set_handler_fn(divide_error_handler);
        idt.debug.set_handler_fn(debug_handler);
        idt.breakpoint.set_handler_fn(breakpoint_handler);
        idt.overflow.set_handler_fn(overflow_handler);
        idt.bound_range_exceeded.set_handler_fn(bound_range_exceeded_handler);
        idt.invalid_opcode.set_handler_fn(invalid_opcode_handler);
        idt.device_not_available.set_handler_fn(device_not_available_handler);
        unsafe {
            idt.double_fault.set_handler_fn(double_fault_handler)
                .set_stack_index(gdt::DOUBLE_FAULT_IST_INDEX);
        }
        idt.invalid_tss.set_handler_fn(invalid_tss_handler);
        idt.segment_not_present.set_handler_fn(segment_not_present_handler);
        idt.stack_segment_fault.set_handler_fn(stack_segment_fault_handler);
        idt.general_protection_fault.set_handler_fn(general_protection_fault_handler);
        idt.page_fault.set_handler_fn(page_fault_handler);

        idt[InterruptIndex::Timer.as_usize()].set_handler_fn(timer_interrupt_handler);
        idt[InterruptIndex::Keyboard.as_usize()].set_handler_fn(keyboard_interrupt_handler);
        
        // 0x80 Syscall: must be accessible from Ring 3
        idt[0x80].set_handler_fn(crate::syscalls::syscall_handler)
                .set_privilege_level(x86_64::PrivilegeLevel::Ring3);
        idt
    };
}

extern "x86-interrupt" fn divide_error_handler(
    stack_frame: InterruptStackFrame,
) {
    println!(" [INT] EXCEPTION: DIVIDE BY ZERO");
    println!(" [INT] {:#?}", stack_frame);
    panic!("DIVIDE ERROR - SOVEREIGN HALT");
}

extern "x86-interrupt" fn debug_handler(
    stack_frame: InterruptStackFrame,
) {
    println!(" [INT] EXCEPTION: DEBUG");
    println!(" [INT] {:#?}", stack_frame);
}

extern "x86-interrupt" fn general_protection_fault_handler(
    stack_frame: InterruptStackFrame,
    error_code: u64,
) {
    println!(" [INT] EXCEPTION: GENERAL PROTECTION FAULT");
    println!(" [INT] Error Code: {}", error_code);
    println!(" [INT] {:#?}", stack_frame);
    panic!("GENERAL PROTECTION FAULT - SOVEREIGN HALT");
}

extern "x86-interrupt" fn stack_segment_fault_handler(
    stack_frame: InterruptStackFrame,
    error_code: u64,
) {
    println!(" [INT] EXCEPTION: STACK SEGMENT FAULT");
    println!(" [INT] Error Code: {}", error_code);
    println!(" [INT] {:#?}", stack_frame);
    panic!("STACK SEGMENT FAULT - SOVEREIGN HALT");
}

extern "x86-interrupt" fn overflow_handler(
    stack_frame: InterruptStackFrame,
) {
    println!(" [INT] EXCEPTION: OVERFLOW");
    println!(" [INT] {:#?}", stack_frame);
}

extern "x86-interrupt" fn bound_range_exceeded_handler(
    stack_frame: InterruptStackFrame,
) {
    println!(" [INT] EXCEPTION: BOUND RANGE EXCEEDED");
    println!(" [INT] {:#?}", stack_frame);
}

extern "x86-interrupt" fn device_not_available_handler(
    stack_frame: InterruptStackFrame,
) {
    println!(" [INT] EXCEPTION: DEVICE NOT AVAILABLE");
    println!(" [INT] {:#?}", stack_frame);
}

extern "x86-interrupt" fn invalid_tss_handler(
    stack_frame: InterruptStackFrame,
    _error_code: u64,
) {
    println!(" [INT] EXCEPTION: INVALID TSS");
    println!(" [INT] {:#?}", stack_frame);
}

extern "x86-interrupt" fn segment_not_present_handler(
    stack_frame: InterruptStackFrame,
    _error_code: u64,
) {
    println!(" [INT] EXCEPTION: SEGMENT NOT PRESENT");
    println!(" [INT] {:#?}", stack_frame);
}

extern "x86-interrupt" fn invalid_opcode_handler(
    stack_frame: InterruptStackFrame,
) {
    println!(" [INT] EXCEPTION: INVALID OPCODE");
    println!(" [INT] {:#?}", stack_frame);
    panic!("INVALID OPCODE - SOVEREIGN HALT");
}

/// Global timer tick counter — incremented by every PIC timer interrupt.
/// Used by a future pre-emptive scheduler to track time slices.
pub static TIMER_TICKS: core::sync::atomic::AtomicU64 =
    core::sync::atomic::AtomicU64::new(0);

extern "x86-interrupt" fn page_fault_handler(
    stack_frame: InterruptStackFrame,
    error_code: PageFaultErrorCode,
) {
    use x86_64::registers::control::Cr2;

    let fault_addr = Cr2::read();
    println!(" [INT] PAGE FAULT @ {:?}  error={:?}", fault_addr, error_code);

    // Attempt demand-zero recovery for user-stack pages.
    // For this to work the kernel needs a live mapper + frame allocator
    // reference.  In the current single-core design we use the boot-time
    // allocator stored in a global Mutex (TODO: full per-process mapper).
    // For now we panic on any fault that is not in the user stack range.
    let addr_u64 = fault_addr.as_u64();
    let in_user_stack = addr_u64 >= crate::process::USER_STACK_BASE
        && addr_u64 < crate::process::USER_STACK_BASE + crate::process::USER_STACK_SIZE as u64;

    if in_user_stack {
        println!(" [PF] Recovering user-stack fault at 0x{:X} — mapping 4KiB frame.", addr_u64);
        
        // --- Demand Paging Implementation ---
        let mut mapper_lock = crate::memory::MAPPER.lock();
        let mut frame_allocator_lock = crate::memory::FRAME_ALLOCATOR.lock();
        
        if let (Some(mapper), Some(frame_allocator)) = (mapper_lock.as_mut(), frame_allocator_lock.as_mut()) {
            use x86_64::structures::paging::{Page, Mapper, PageTableFlags};
            
            let page = Page::containing_address(fault_addr);
            let flags = PageTableFlags::PRESENT | PageTableFlags::WRITABLE | PageTableFlags::USER_ACCESSIBLE;
            
            unsafe {
                let frame = frame_allocator.allocate_frame().expect("out of memory");
                mapper.map_to(page, frame, flags, frame_allocator).expect("map_to failed").flush();
            }
            println!(" [OK] Demand paging successful for {:?}", page);
            return; 
        }
    } else {
        println!(" [INT] Unrecoverable PAGE FAULT\n{:#?}", stack_frame);
        panic!("PAGE FAULT — SOVEREIGN HALT");
    }
}

pub fn init_idt() {
    IDT.load();
}

extern "x86-interrupt" fn breakpoint_handler(
    stack_frame: InterruptStackFrame)
{
    println!(" [INT] BREAKPOINT DETECTED\n{:#?}", stack_frame);
}

extern "x86-interrupt" fn double_fault_handler(
    stack_frame: InterruptStackFrame, _error_code: u64) -> !
{
    panic!("EXCEPTION: DOUBLE FAULT\n{:#?}", stack_frame);
}

extern "x86-interrupt" fn timer_interrupt_handler(
    _stack_frame: InterruptStackFrame)
{
    // Increment the global tick counter (future pre-emptive scheduler hook).
    TIMER_TICKS.fetch_add(1, core::sync::atomic::Ordering::Relaxed);
    unsafe {
        PICS.lock().notify_end_of_interrupt(InterruptIndex::Timer.as_u8());
    }
    crate::scheduler::SCHEDULER.lock().schedule();
}

extern "x86-interrupt" fn keyboard_interrupt_handler(
    _stack_frame: InterruptStackFrame)
{
    keyboard::handle_interrupt();
    crate::shell::update();
    unsafe {
        PICS.lock().notify_end_of_interrupt(InterruptIndex::Keyboard.as_u8());
    }
}
