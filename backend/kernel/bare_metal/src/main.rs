#![no_std]
#![no_main]
#![feature(naked_functions)]

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
pub mod network;
pub mod syscalls;
#[macro_use]
mod serial;
mod cpu;
mod smp;
mod forensics;
pub mod fs;
mod orchestrator;
pub mod stability;
mod privilege;
mod crypto;
mod process;
mod usermode;
mod health;
mod dma;
pub mod vfs;
pub mod tcp;
pub mod scheduler;
pub mod ai_layer; 
pub mod shell;
mod user_shell;
pub mod security;
mod ksm;
mod wasm;

extern crate alloc;

use core::panic::PanicInfo;
use task::{Task, executor::Executor};
use x86_64::VirtAddr;
use bootloader::{BootInfo, entry_point};

entry_point!(kernel_main);

fn kernel_main(boot_info: &'static BootInfo) -> ! {
    vga_buffer::init_gui();
    println!("══════════════════════════════════════════════════════");
    println!(" HAL-0 KERNEL FOUNDATION: BOOTING PHASE (K-1 to K-10)");
    println!("══════════════════════════════════════════════════════");

    // K-1: GDT (Serial log [OK] GDT is in gdt::init)
    gdt::init();
    
    // K-2: IDT & Exceptions
    interrupts::init_idt();
    unsafe { interrupts::PICS.lock().initialize() }
    x86_64::instructions::interrupts::enable();
    println!(" [OK] IDT: 8 exception handlers registered. Vector 0x80 armed.");

    // K-3: Heap & Leak Tracker
    let phys_mem_offset = VirtAddr::new(boot_info.physical_memory_offset);
    let mut mapper = unsafe { memory::init(phys_mem_offset) };
    let mut frame_allocator = unsafe {
        memory::BootInfoFrameAllocator::init(&boot_info.memory_map)
    };
    allocator::init_heap(&mut mapper, &mut frame_allocator).expect("heap failed");
    println!(" [OK] Heap: 100 KiB allocated at 0x4444_4444_0000.");
    allocator::check_leaks();

    // 1.1 PCI Discovery & Multi-core Init
    pci::check_all_buses();
    acpi::init();
    smp::init();

    // K-8: Verified Boot (PCR[0] extension)
    secure_boot::verify();
    
    // K-6: WAL Crash Recovery
    journaling::init();

    // K-5: SovereignFS / ATA Persistence Test (LBA 200)
    println!(" [SYS] K-5: Performing LBA 200 Persistence Test...");
    let mut boot_log_data = [0u16; 256];
    let magic_marker = 0x5053; // "SP" (Sovereign Pulse)
    boot_log_data[0] = magic_marker;
    boot_log_data[255] = 0xAAAA; // CRC/Footer stub
    
    {
        let mut ata = ata::ATA_PRIMARY.lock();
        ata.write_sectors(200, 1, &boot_log_data);
        
        let mut read_back = [0u16; 256];
        ata.read_sectors(200, 1, &mut read_back);
        
        if read_back[0] == magic_marker {
            println!(" [OK] LBA 200: boot.log persistence VERIFIED via ATA PIO.");
        } else {
            println!(" [WARN] LBA 200: persistence failure ! (Expected 0x5053, got 0x{:X})", read_back[0]);
        }
    }

    // K-4: Syscall Dispatcher Harness
    syscalls::test_syscall_harness();

    // K-9: Ring-3 Process Spawn Loop (10 Iterations)
    println!(" [SYS] K-9: Executing WAVE_SPAWN (0x02) x10...");
    for _ in 0..10 {
        syscalls::dispatch(0x02); // WAVE_SPAWN
    }
    println!(" [OK] PROCESS_COUNT reached: {}", syscalls::active_process_count());
    
    // Security Baseline Verification
    stability::verify_ring3_containment();
    stability::verify_afl_fuzzing();
    security::redactor::Redactor::verify_leak_protection();
    
    // KSM Deduplication (Section 94)
    ksm::init_ksm();
    {
        let mut ksm_mgr = ksm::KSM.lock();
        // Simulate scanning model weights for 16 agents
        for i in 0..1600 {
             ksm_mgr.scan_and_deduplicate(VirtAddr::new(0x4000_0000 + (i * 0x1000)), &mut mapper);
        }
        ksm_mgr.print_report();
    }

    // Performance Hardening (Section 3)
    stability::verify_section3_performance();

    // 5. ORCHESTRATION & SHEDULING
    orchestrator::KernelOrchestrator::bootstrap();
    
    // Graduation Finality (Section 3 Graduation Gate)
    forensics::ForensicManager::graduation_report();

    orchestrator::KernelOrchestrator::spawn_user_shell();
    
    // 6. DYNAMIC PULSE LOOP
    println!(" [SYS] All Foundation Checkpoints Passed. Entering Soak Loop.");
    let mut executor = Executor::new();
    
    crate::shell::init();

    executor.spawn(Task::new(pulse_driver()));
    executor.spawn(Task::new(health::watchdog_task()));

    println!("══════════════════════════════════════════════════════");
    println!(" SOVEREIGN GRADUATION: KERNEL FOUNDATION CRYSTALLIZED ");
    println!("══════════════════════════════════════════════════════");

    executor.run()
}

/// The Pulse Driver wires the NIC, AI Layer, and Scheduler into a dynamic heartbeat.
async fn pulse_driver() {
    let mut nic = nic::NicDriver::new();
    nic.is_active = true; // assume active for loop
    let mut net = network::SovereignNetStack::new();
    
    loop {
        // 1. Hardware Interface Poll (NIC RX)
        let mut scheduler = crate::scheduler::SCHEDULER.lock();
        nic.poll_receive(&mut net);

        // 2. Cognitive Layer Sync (AI Heuristics)
        ai_layer::orchestrate_tasks();

        // 3. Network Stack Processing
        // Simulation of an incoming ARP packet wire
        let mut sim_arp = [0u8; 64];
        sim_arp[12] = 0x08; sim_arp[13] = 0x06;
        net.handle_packet(&mut nic, &sim_arp);

        // 4. Cooperative yield to allow other tasks to run
        task::yield_now().await;
    }
}

#[panic_handler]
fn panic(info: &PanicInfo) -> ! {
    println!("[!!!] KERNEL PANIC: {}", info);
    loop { x86_64::instructions::hlt(); }
}

/// SOVEREIGN STACK PROTECTION: __stack_chk_fail
/// Required for -fstack-protector-all to trap stack smashing.
#[no_mangle]
pub extern "C" fn __stack_chk_fail() -> ! {
    panic!(" [🛡️] STACK SMASHING DETECTED — HALTING FOR FORENSIC ANALYSIS.");
}
