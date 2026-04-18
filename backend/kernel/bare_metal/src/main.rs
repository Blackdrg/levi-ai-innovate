#![no_std]
#![no_main]

mod vga_buffer;
mod gdt;
mod interrupts;
mod memory;
mod keyboard;
mod ata;
mod allocator;
mod task;
mod pci;
mod acpi;
mod nic;
mod journaling;
mod elf_loader;
mod secure_boot;
mod tpm;
mod network;
mod syscalls;


extern crate alloc;

use core::panic::PanicInfo;
use task::{Task, executor::Executor};
use x86_64::VirtAddr;

#[no_mangle]
pub extern "C" fn _start() -> ! {
    println!("🚀 [HAL-0] SOVEREIGN KERNEL BOOTING...");
    
    gdt::init();
    interrupts::init_idt();
    unsafe { interrupts::PICS.lock().initialize() };
    x86_64::instructions::interrupts::enable();

    // Step 4: Initialize Heap & Paging
    let phys_mem_offset = VirtAddr::new(0x0); // Standard for now
    let mut mapper = unsafe { memory::init(phys_mem_offset) };
    let mut frame_allocator = memory::EmptyFrameAllocator;

    allocator::init_heap(&mut mapper, &mut frame_allocator)
        .expect("heap initialization failed");
    println!(" [OK] Heap Allocator Online ({} KiB).", allocator::HEAP_SIZE / 1024);

    // Step 5: PCI-e & ACPI Discovery
    pci::check_all_buses();
    acpi::init();

    // Step 6: NIC Initialization
    let mut nic = nic::NicDriver::new();
    nic.init();


    // Step 6: Start Multi-Tasking Executor
    let mut executor = Executor::new();
    executor.spawn(Task::new(async_demo()));
    println!(" [OK] Executor Online. Sovereign Missions Starting...");

    executor.run();
}

async fn async_demo() {
    println!(" [TASK] Native async mission running in Ring 0.");
}

#[panic_handler]
fn panic(info: &PanicInfo) -> ! {
    println!("{}", info);
    loop {}
}
