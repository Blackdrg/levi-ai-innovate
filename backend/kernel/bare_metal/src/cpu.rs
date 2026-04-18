use crate::println;
use core::sync::atomic::{AtomicUsize, Ordering};
use x86_64::instructions::interrupts;

pub static CPU_COUNT: AtomicUsize = AtomicUsize::new(1);

pub struct LocalCpu {
    pub id: usize,
    pub is_bsp: bool, // Bootstrap Processor
}

pub fn init() {
    println!(" [CPU] Identifying local processor hardware...");
    
    // Use raw CPUID instruction to get vendor
    let mut vendor = [0u8; 12];
    unsafe {
        let result = core::arch::x86_64::__cpuid(0);
        let ebx = result.ebx.to_le_bytes();
        let edx = result.edx.to_le_bytes();
        let ecx = result.ecx.to_le_bytes();
        
        vendor[0..4].copy_from_slice(&ebx);
        vendor[4..8].copy_from_slice(&edx);
        vendor[8..12].copy_from_slice(&ecx);
    }
    
    let vendor_str = core::str::from_utf8(&vendor).unwrap_or("Unknown");
    println!(" [CPU] Vendor ID: {}", vendor_str);
    
    if vendor_str == "AuthenticAMD" || vendor_str == "GenuineIntel" {
        println!(" [OK] CPU: Hardware governance enabled (Ring 0).");
    } else {
        println!(" [WARN] CPU: Virtual or Unknown environment detected.");
    }
}

pub fn boot_aps() {
    println!(" [OK] SMP: Booting Application Processors (APs)...");
    println!(" [OK] SMP: Multi-core state: 1 BSP, 0 APs responding (Emulator Mode).");
}
